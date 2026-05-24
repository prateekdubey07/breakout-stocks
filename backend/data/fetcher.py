import yfinance as yf
import pandas as pd
from typing import Optional


_OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]


def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Returns OHLCV DataFrame with columns: Open High Low Close Volume."""
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    else:
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    # Keep only the 5 canonical columns, drop extras like 'Adj Close'
    existing = [c for c in _OHLCV_COLS if c in df.columns]
    return df[existing].dropna()


_EMPTY_FUNDAMENTALS = {
    "eps_growth_yoy": None, "revenue_growth_yoy": None, "peg_ratio": None,
    "market_cap": None, "avg_volume": 1_000_000, "short_pct_float": 0.0,
    "forward_pe": None, "sector": "Unknown", "next_earnings": None,
}

def fetch_fundamentals(ticker: str) -> dict:
    """Returns key fundamental fields from yfinance info."""
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return dict(_EMPTY_FUNDAMENTALS)
    return {
        "eps_growth_yoy": _safe(info, "earningsGrowth"),
        "revenue_growth_yoy": _safe(info, "revenueGrowth"),
        "peg_ratio": _safe(info, "pegRatio"),
        "market_cap": _safe(info, "marketCap"),
        "avg_volume": _safe(info, "averageVolume"),
        "short_pct_float": _safe(info, "shortPercentOfFloat"),
        "forward_pe": _safe(info, "forwardPE"),
        "sector": _safe(info, "sector", "Unknown"),
        "next_earnings": _safe(info, "earningsTimestamp"),
    }


def _safe(info: dict, key: str, default=None):
    val = info.get(key)
    return val if val is not None else default
