import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from database import get_conn

_OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]
_CACHE_TTL_HOURS = 24          # fundamentals don't change intraday — 24h off-hours
_CACHE_TTL_MARKET_HOURS = 4   # still refresh every 4h during market hours
_CACHE_TTL_NULL_MINUTES = 60  # null/failed fundamentals — wait 1h before retry (avoids 429 loop)

# Limit concurrent yfinance calls — MUST stay low; yfinance bans IPs with >3-4 concurrent
_YF_SEMAPHORE = threading.Semaphore(3)

# ---------------------------------------------------------------------------
# OHLCV batch prefetch cache — populated once per scan, read per ticker
# ---------------------------------------------------------------------------
_OHLCV_BATCH_CACHE: dict = {}  # {TICKER: pd.DataFrame}


def _is_market_hours() -> bool:
    try:
        import pytz
        et = pytz.timezone("America/New_York")
        now = datetime.now(et)
        return now.weekday() < 5 and 9 <= now.hour < 16
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Alpaca client (lazy-init)
# ---------------------------------------------------------------------------
_alpaca_client = None

def _get_alpaca():
    global _alpaca_client
    if _alpaca_client is not None:
        return _alpaca_client
    key = os.getenv("ALPACA_API_KEY", "")
    secret = os.getenv("ALPACA_SECRET_KEY", "")
    if not key or not secret:
        return None
    try:
        from alpaca.data import StockHistoricalDataClient
        _alpaca_client = StockHistoricalDataClient(key, secret)
        return _alpaca_client
    except Exception:
        return None


def _period_to_start(period: str) -> datetime:
    mapping = {
        "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
        "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
    }
    days = mapping.get(period, 180)
    return datetime.now(tz=timezone.utc) - timedelta(days=days)


# ---------------------------------------------------------------------------
# OHLCV batch prefetch — ONE Alpaca call for all tickers in a scan
# ---------------------------------------------------------------------------
def prefetch_ohlcv_batch(tickers: list, period: str = "2y") -> None:
    """Fetch OHLCV for all tickers in a single Alpaca request.
    Always includes SPY for RS calculation. No-op if Alpaca unavailable."""
    global _OHLCV_BATCH_CACHE
    _OHLCV_BATCH_CACHE.clear()
    # Always include SPY for relative strength calculation
    tickers = list(dict.fromkeys(["SPY"] + list(tickers)))
    client = _get_alpaca()
    if not client:
        return
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        # Alpaca rejects symbols with special chars (BRK-B, BF-B, BRK.B) — filter them out;
        # they'll fall through to per-ticker yfinance fallback in fetch_ohlcv.
        alpaca_tickers = [t.upper() for t in tickers if t.replace("-", "").replace(".", "").isalnum() and "-" not in t and "." not in t]
        if not alpaca_tickers:
            return
        req = StockBarsRequest(
            symbol_or_symbols=alpaca_tickers,
            timeframe=TimeFrame.Day,
            start=_period_to_start(period),
            end=datetime.now(tz=timezone.utc),
            feed="iex",
        )
        df_all = client.get_stock_bars(req).df
        if df_all is None or df_all.empty:
            print("[PREFETCH] Alpaca returned empty DataFrame")
            return
        # MultiIndex: (symbol, timestamp) — split per symbol
        for symbol in df_all.index.get_level_values(0).unique():
            df = df_all.loc[symbol].copy()
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df.rename(columns={
                "open": "Open", "high": "High", "low": "Low",
                "close": "Close", "volume": "Volume",
            })
            existing = [c for c in _OHLCV_COLS if c in df.columns]
            df = df[existing].dropna()
            if len(df) > 10:
                _OHLCV_BATCH_CACHE[symbol.upper()] = df
        skipped = len(tickers) - len(alpaca_tickers)
        print(f"[PREFETCH] Loaded {len(_OHLCV_BATCH_CACHE)}/{len(alpaca_tickers)} tickers from Alpaca ({skipped} skipped — special chars)")
    except Exception as e:
        print(f"[PREFETCH] Batch fetch failed ({e}) — tickers will use per-ticker fallback")


# ---------------------------------------------------------------------------
# OHLCV fetch — checks batch cache first, then Alpaca single, then yfinance
# ---------------------------------------------------------------------------
def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    # Batch cache hit — avoids per-ticker Alpaca calls during scans
    cached = _OHLCV_BATCH_CACHE.get(ticker.upper())
    if cached is not None and len(cached) > 10:
        return cached

    client = _get_alpaca()
    if client:
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            req = StockBarsRequest(
                symbol_or_symbols=ticker.upper(),
                timeframe=TimeFrame.Day,
                start=_period_to_start(period),
                end=datetime.now(tz=timezone.utc),
                feed="iex",
            )
            bars = client.get_stock_bars(req)
            df = bars.df
            if df is not None and len(df) > 10:
                # Alpaca returns MultiIndex (symbol, timestamp) — drop symbol level
                if isinstance(df.index, pd.MultiIndex):
                    df = df.droplevel(0)
                df.index = pd.to_datetime(df.index).tz_localize(None)
                df = df.rename(columns={
                    "open": "Open", "high": "High", "low": "Low",
                    "close": "Close", "volume": "Volume",
                })
                existing = [c for c in _OHLCV_COLS if c in df.columns]
                return df[existing].dropna()
        except Exception:
            pass  # fall through to yfinance

    # yfinance fallback — gated by semaphore to prevent concurrent download flood
    with _YF_SEMAPHORE:
        time.sleep(0.5)
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    else:
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    existing = [c for c in _OHLCV_COLS if c in df.columns]
    return df[existing].dropna()


# ---------------------------------------------------------------------------
# Fundamentals — yfinance only (Alpaca doesn't provide earnings/growth data)
# ---------------------------------------------------------------------------
_EMPTY_FUNDAMENTALS = {
    "eps_growth_yoy": None, "revenue_growth_yoy": None, "peg_ratio": None,
    "market_cap": None, "avg_volume": 1_000_000, "short_pct_float": 0.0,
    "forward_pe": None, "sector": "Unknown", "next_earnings": None,
}


def _cache_get(ticker: str) -> dict | None:
    try:
        ttl = _CACHE_TTL_MARKET_HOURS if _is_market_hours() else _CACHE_TTL_HOURS
        conn = get_conn()
        row = conn.execute(
            "SELECT data_json FROM fundamentals_cache "
            "WHERE ticker=? AND cached_at > datetime('now', ? || ' hours')",
            (ticker, f"-{ttl}")
        ).fetchone()
        conn.close()
        return json.loads(row["data_json"]) if row else None
    except Exception:
        return None


def _has_useful_data(data: dict) -> bool:
    return any([
        data.get("eps_growth_yoy") is not None,
        data.get("revenue_growth_yoy") is not None,
        data.get("market_cap") and data["market_cap"] > 0,
        data.get("sector") not in (None, "Unknown"),
    ])


def _cache_set(ticker: str, data: dict) -> None:
    try:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO fundamentals_cache (ticker, data_json, cached_at) "
            "VALUES (?, ?, datetime('now'))",
            (ticker, json.dumps(data))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _cache_get_null_aware(ticker: str) -> dict | None:
    """Returns cached result only if within TTL — shorter TTL for null/empty results."""
    try:
        ttl_hours = _CACHE_TTL_MARKET_HOURS if _is_market_hours() else _CACHE_TTL_HOURS
        conn = get_conn()
        row = conn.execute(
            "SELECT data_json, cached_at FROM fundamentals_cache WHERE ticker=?",
            (ticker,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        data = json.loads(row["data_json"])
        # Parse cached_at and compute age
        try:
            from datetime import datetime as dt
            cached_at = dt.fromisoformat(row["cached_at"])
            age_minutes = (dt.utcnow() - cached_at).total_seconds() / 60
        except Exception:
            return None
        max_age = ttl_hours * 60 if _has_useful_data(data) else _CACHE_TTL_NULL_MINUTES
        return data if age_minutes < max_age else None
    except Exception:
        return None


def fetch_fundamentals(ticker: str) -> dict:
    cached = _cache_get_null_aware(ticker)
    if cached:
        return cached

    t = yf.Ticker(ticker)

    # fast_info: different endpoint, never 429 — always yields market_cap + avg_volume
    fast = {"avg_volume": 1_000_000, "market_cap": None}
    try:
        fi = t.fast_info
        fast = {
            "avg_volume": getattr(fi, "three_month_average_volume", None) or 1_000_000,
            "market_cap": getattr(fi, "market_cap", None),
        }
    except Exception:
        pass

    result = None

    # Semaphore: 3 concurrent max — yfinance bans IPs beyond this threshold
    with _YF_SEMAPHORE:
        time.sleep(1.0)  # 1s between releases prevents rapid-fire 429s

        # Primary: t.info (full fundamentals, but can 429)
        try:
            info = t.info
            if isinstance(info, dict) and info.get("quoteType") is not None:
                result = {
                    "eps_growth_yoy": _safe(info, "earningsGrowth"),
                    "revenue_growth_yoy": _safe(info, "revenueGrowth"),
                    "peg_ratio": _safe(info, "pegRatio"),
                    "market_cap": _safe(info, "marketCap") or fast["market_cap"],
                    "avg_volume": _safe(info, "averageVolume") or fast["avg_volume"],
                    "short_pct_float": _safe(info, "shortPercentOfFloat") or 0.0,
                    "forward_pe": _safe(info, "forwardPE"),
                    "sector": _safe(info, "sector", "Unknown"),
                    "next_earnings": _safe(info, "earningsTimestamp"),
                }
        except Exception:
            pass

        # Fallback: income_stmt (different endpoint — often works when .info 429s)
        if result is None:
            result = {**_EMPTY_FUNDAMENTALS, "avg_volume": fast["avg_volume"], "market_cap": fast["market_cap"]}
            try:
                stmt = t.income_stmt
                if stmt is not None and not stmt.empty:
                    if "Net Income" in stmt.index:
                        net = stmt.loc["Net Income"].dropna()
                        if len(net) >= 2 and net.iloc[1] != 0:
                            result["eps_growth_yoy"] = round(
                                float((net.iloc[0] - net.iloc[1]) / abs(net.iloc[1])), 4
                            )
                    if "Total Revenue" in stmt.index:
                        rev = stmt.loc["Total Revenue"].dropna()
                        if len(rev) >= 2 and rev.iloc[1] != 0:
                            result["revenue_growth_yoy"] = round(
                                float((rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1])), 4
                            )
            except Exception:
                pass

            # Derive PEG if possible
            fpe = result.get("forward_pe")
            eps = result.get("eps_growth_yoy")
            if fpe and eps and eps > 0 and result.get("peg_ratio") is None:
                result["peg_ratio"] = round(fpe / (eps * 100), 2)

    print(f"[FUND] {ticker}: eps={result.get('eps_growth_yoy')} rev={result.get('revenue_growth_yoy')} "
          f"pe={result.get('forward_pe')} mktcap={result.get('market_cap')} sector={result.get('sector')}")

    _cache_set(ticker, result)
    return result


def _safe(info: dict, key: str, default=None):
    val = info.get(key)
    return val if val is not None else default
