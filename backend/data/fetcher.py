import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from database import get_conn

_OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]
_CACHE_TTL_HOURS = 4

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
# OHLCV fetch — Alpaca primary, yfinance fallback
# ---------------------------------------------------------------------------
def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
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

    # yfinance fallback
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
        conn = get_conn()
        row = conn.execute(
            "SELECT data_json FROM fundamentals_cache "
            "WHERE ticker=? AND cached_at > datetime('now', ? || ' hours')",
            (ticker, f"-{_CACHE_TTL_HOURS}")
        ).fetchone()
        conn.close()
        return json.loads(row["data_json"]) if row else None
    except Exception:
        return None


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


def fetch_fundamentals(ticker: str) -> dict:
    cached = _cache_get(ticker)
    if cached:
        return cached

    t = yf.Ticker(ticker)

    fast = {"avg_volume": 1_000_000, "market_cap": None}
    try:
        fi = t.fast_info
        fast = {
            "avg_volume": getattr(fi, "three_month_average_volume", None) or 1_000_000,
            "market_cap": getattr(fi, "market_cap", None),
        }
    except Exception:
        pass

    try:
        info = t.info
        if not isinstance(info, dict) or info.get("quoteType") is None:
            raise ValueError("empty info")
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
        result = {**_EMPTY_FUNDAMENTALS, "avg_volume": fast["avg_volume"], "market_cap": fast["market_cap"]}

    if result.get("eps_growth_yoy") is not None or result.get("sector", "Unknown") != "Unknown":
        _cache_set(ticker, result)

    return result


def _safe(info: dict, key: str, default=None):
    val = info.get(key)
    return val if val is not None else default
