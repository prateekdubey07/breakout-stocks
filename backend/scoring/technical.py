import pandas as pd
import pandas_ta as ta
from dataclasses import dataclass


@dataclass
class TechnicalScore:
    total: float
    volume_surge: bool
    volume_ratio: float
    near_52w_high: bool
    pct_from_52w_high: float
    volatility_contracting: bool
    rsi_14: float
    macd_bullish: bool
    macd_signal: str
    above_20ma: bool
    above_50ma: bool
    above_200ma: bool
    above_key_mas: bool
    atr_20: float


def compute_technical_score(df: pd.DataFrame) -> TechnicalScore:
    close = df["Close"]
    volume = df["Volume"]

    # Volume
    vol_avg_20 = volume.rolling(20).mean().iloc[-1]
    vol_today = volume.iloc[-1]
    volume_ratio = round(vol_today / vol_avg_20, 2) if vol_avg_20 > 0 else 0
    volume_surge = volume_ratio >= 1.5

    # 52w high
    high_52w = close.rolling(252).max().iloc[-1]
    pct_from_high = round((close.iloc[-1] - high_52w) / high_52w * 100, 2)
    near_52w_high = pct_from_high >= -3.0

    # ATR
    atr = ta.atr(df["High"], df["Low"], df["Close"], length=20)
    atr_5 = ta.atr(df["High"], df["Low"], df["Close"], length=5)
    atr_20_val = atr.iloc[-1] if atr is not None else 0
    atr_5_val = atr_5.iloc[-1] if atr_5 is not None else 0
    volatility_contracting = (atr_5_val < atr_20_val * 0.75) if atr_20_val > 0 else False

    # RSI
    rsi = ta.rsi(close, length=14)
    rsi_val = round(rsi.iloc[-1], 1) if rsi is not None else 50.0

    # MACD
    macd_df = ta.macd(close)
    macd_bullish = False
    macd_signal_str = "neutral"
    if macd_df is not None and not macd_df.empty:
        hist = macd_df.iloc[:, 1]  # histogram column
        macd_bullish = hist.iloc[-1] > 0 and hist.iloc[-2] <= 0
        if hist.iloc[-1] > hist.iloc[-2]:
            macd_signal_str = "bullish crossover" if macd_bullish else "histogram rising"
        else:
            macd_signal_str = "bearish"

    # Moving averages
    ma20 = ta.sma(close, length=20).iloc[-1]
    ma50 = ta.sma(close, length=50).iloc[-1]
    ma200 = ta.sma(close, length=200).iloc[-1]
    price = close.iloc[-1]
    above_20 = price > ma20
    above_50 = price > ma50
    above_200 = price > ma200
    above_key_mas = above_20 and above_50 and above_200

    # Score
    score = 0.0
    if volume_surge:
        score += 10
    if near_52w_high:
        score += 8
    if volatility_contracting:
        score += 7
    if 55 <= rsi_val <= 75:
        score += 8
    if macd_bullish:
        score += 7
    if above_key_mas:
        score += 5

    return TechnicalScore(
        total=score,
        volume_surge=volume_surge,
        volume_ratio=volume_ratio,
        near_52w_high=near_52w_high,
        pct_from_52w_high=pct_from_high,
        volatility_contracting=volatility_contracting,
        rsi_14=rsi_val,
        macd_bullish=macd_bullish,
        macd_signal=macd_signal_str,
        above_20ma=above_20,
        above_50ma=above_50,
        above_200ma=above_200,
        above_key_mas=above_key_mas,
        atr_20=round(atr_20_val, 2),
    )
