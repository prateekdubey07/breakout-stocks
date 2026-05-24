import pandas as pd
import pandas_ta as ta
import numpy as np

FEATURE_COLS = [
    "rsi_14", "rsi_slope",
    "macd_hist", "macd_hist_slope",
    "volume_ratio_20d", "volume_ratio_5d",
    "atr_ratio",          # 5d ATR / 20d ATR
    "pct_from_52w_high",
    "above_20ma", "above_50ma", "above_200ma",
    "obv_slope",          # OBV 10d slope (institutional proxy)
    "bb_pct_b",           # Bollinger %B
    "close_pct_chg_5d",
    "close_pct_chg_20d",
    "range_contraction",  # 5d avg range / 20d avg range
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix from OHLCV DataFrame. Returns one row per trading day."""
    out = pd.DataFrame(index=df.index)
    close = df["Close"]
    volume = df["Volume"]

    rsi = ta.rsi(close, 14)
    out["rsi_14"] = rsi
    out["rsi_slope"] = rsi.diff(3)

    macd_df = ta.macd(close)
    if macd_df is not None:
        hist = macd_df.iloc[:, 1]
        out["macd_hist"] = hist
        out["macd_hist_slope"] = hist.diff(3)
    else:
        out["macd_hist"] = 0
        out["macd_hist_slope"] = 0

    vol_ma20 = volume.rolling(20).mean()
    vol_ma5 = volume.rolling(5).mean()
    out["volume_ratio_20d"] = volume / vol_ma20
    out["volume_ratio_5d"] = vol_ma5 / vol_ma20

    atr20 = ta.atr(df["High"], df["Low"], close, 20)
    atr5 = ta.atr(df["High"], df["Low"], close, 5)
    out["atr_ratio"] = atr5 / atr20.replace(0, np.nan)

    high_252 = close.rolling(252, min_periods=150).max()
    out["pct_from_52w_high"] = (close - high_252) / high_252

    out["above_20ma"] = (close > ta.sma(close, 20)).fillna(0).astype(int)
    out["above_50ma"] = (close > ta.sma(close, 50)).fillna(0).astype(int)
    out["above_200ma"] = (close > ta.sma(close, 200)).fillna(0).astype(int)

    obv = ta.obv(close, volume)
    out["obv_slope"] = obv.diff(10) / obv.abs().rolling(10).mean().replace(0, np.nan)

    bb = ta.bbands(close, length=20)
    if bb is not None:
        bbp_cols = [c for c in bb.columns if "BBP" in str(c)]
        if bbp_cols:
            out["bb_pct_b"] = bb[bbp_cols[0]]
        else:
            out["bb_pct_b"] = bb.iloc[:, -1]
    else:
        out["bb_pct_b"] = 0.5

    out["close_pct_chg_5d"] = close.pct_change(5)
    out["close_pct_chg_20d"] = close.pct_change(20)

    day_range = df["High"] - df["Low"]
    out["range_contraction"] = (
        day_range.rolling(5).mean()
        / day_range.rolling(20).mean().replace(0, np.nan)
    )

    return out[FEATURE_COLS].dropna()


def build_labels(
    df: pd.DataFrame,
    forward_days: int = 10,
    threshold: float = 0.08,
) -> pd.Series:
    """Label = 1 if close rose >threshold% within forward_days sessions."""
    close = df["Close"]
    future_max = close[::-1].rolling(forward_days).max()[::-1].shift(-1)
    return ((future_max - close) / close >= threshold).astype(int)
