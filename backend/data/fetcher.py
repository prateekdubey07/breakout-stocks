import yfinance as yf
import pandas as pd


_OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]


def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False, silent=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    else:
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    existing = [c for c in _OHLCV_COLS if c in df.columns]
    return df[existing].dropna()


_EMPTY_FUNDAMENTALS = {
    "eps_growth_yoy": None, "revenue_growth_yoy": None, "peg_ratio": None,
    "market_cap": None, "avg_volume": 1_000_000, "short_pct_float": 0.0,
    "forward_pe": None, "sector": "Unknown", "next_earnings": None,
}


def fetch_fundamentals(ticker: str) -> dict:
    t = yf.Ticker(ticker)

    # fast_info: lightweight, no crumb needed — gives volume + market cap
    fast = {}
    try:
        fi = t.fast_info
        fast = {
            "avg_volume": getattr(fi, "three_month_average_volume", None) or 1_000_000,
            "market_cap": getattr(fi, "market_cap", None),
        }
    except Exception:
        fast = {"avg_volume": 1_000_000, "market_cap": None}

    # full info: needs crumb — optional, fall back gracefully
    try:
        info = t.info
        if not isinstance(info, dict) or info.get("quoteType") is None:
            raise ValueError("empty info")
        return {
            "eps_growth_yoy": _safe(info, "earningsGrowth"),
            "revenue_growth_yoy": _safe(info, "revenueGrowth"),
            "peg_ratio": _safe(info, "pegRatio"),
            "market_cap": _safe(info, "marketCap") or fast.get("market_cap"),
            "avg_volume": _safe(info, "averageVolume") or fast["avg_volume"],
            "short_pct_float": _safe(info, "shortPercentOfFloat") or 0.0,
            "forward_pe": _safe(info, "forwardPE"),
            "sector": _safe(info, "sector", "Unknown"),
            "next_earnings": _safe(info, "earningsTimestamp"),
        }
    except Exception:
        # fundamentals unavailable — return fast_info basics, zeros for growth
        return {
            **_EMPTY_FUNDAMENTALS,
            "avg_volume": fast["avg_volume"],
            "market_cap": fast.get("market_cap"),
        }


def _safe(info: dict, key: str, default=None):
    val = info.get(key)
    return val if val is not None else default
