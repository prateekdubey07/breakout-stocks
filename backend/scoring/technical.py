import pandas as pd
import pandas_ta as ta
from dataclasses import dataclass


@dataclass
class TechnicalScore:
    total: float
    pattern: str
    pattern_score: float
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
    ma20_price: float
    ma50_price: float


def _detect_pattern(
    vol_ratio: float, pct_high: float, contracting: bool,
    rsi: float, macd_bull: bool,
    above_ma20: bool, above_ma50: bool, above_ma200: bool,
) -> str:
    if contracting and 50 <= rsi <= 70 and macd_bull:
        return "Volatility Squeeze"
    if vol_ratio > 1.5 and pct_high > -5 and above_ma20 and above_ma50 and above_ma200:
        return "Bull Flag"
    if -1 >= pct_high > -4 and above_ma20 and 50 <= rsi <= 60:
        return "Breakout Retest"
    if -5 >= pct_high > -15 and contracting and above_ma50:
        return "Flat Base"
    if -8 >= pct_high > -20 and 45 <= rsi <= 60 and above_ma200:
        return "Cup & Handle"
    if above_ma20 and above_ma50 and above_ma200 and 55 <= rsi <= 65 and 0.9 <= vol_ratio <= 1.3:
        return "Rising Base"
    if contracting and above_ma50 and vol_ratio < 0.9:
        return "VCP"
    if above_ma50 and 55 <= rsi <= 70:
        return "Ascending Triangle"
    if not above_ma20 and not above_ma50 and not above_ma200:
        return "Downtrend"
    if 40 <= rsi <= 55:
        return "Range Bound"
    return "No Clear Pattern"


def _pattern_score(pattern: str) -> float:
    return {
        "Bull Flag": 20.0,
        "Volatility Squeeze": 20.0,
        "Rising Base": 15.0,
        "Breakout Retest": 15.0,
        "Flat Base": 12.0,
        "Cup & Handle": 12.0,
        "Ascending Triangle": 10.0,
        "VCP": 10.0,
        "Range Bound": 6.0,
        "No Clear Pattern": 5.0,
        "Downtrend": 0.0,
    }.get(pattern, 5.0)


def compute_technical_score(df: pd.DataFrame) -> TechnicalScore:
    close = df["Close"]
    volume = df["Volume"]

    # Volume scoring (max 10 pts)
    vol_avg_20 = volume.rolling(20).mean().iloc[-1]
    vol_today = volume.iloc[-1]
    volume_ratio = round(vol_today / vol_avg_20, 2) if vol_avg_20 > 0 else 0
    volume_surge = volume_ratio >= 1.5

    if volume_ratio > 2.0:
        vol_score = 10
    elif volume_ratio >= 1.5:
        vol_score = 6
    elif volume_ratio >= 1.2:
        vol_score = 3
    else:
        vol_score = 0

    # 52w high scoring (max 8 pts)
    high_52w = close.rolling(252).max().iloc[-1]
    pct_from_high = round((close.iloc[-1] - high_52w) / high_52w * 100, 2)
    near_52w_high = pct_from_high >= -3.0

    if pct_from_high >= -3.0:
        high_score = 8
    elif pct_from_high >= -8.0:
        high_score = 4
    else:
        high_score = 0

    # Volatility contraction (7 pts)
    atr = ta.atr(df["High"], df["Low"], df["Close"], length=20)
    atr_5 = ta.atr(df["High"], df["Low"], df["Close"], length=5)
    atr_20_val = atr.iloc[-1] if atr is not None else 0
    atr_5_val = atr_5.iloc[-1] if atr_5 is not None else 0
    volatility_contracting = (atr_5_val < atr_20_val * 0.75) if atr_20_val > 0 else False
    vol_contraction_score = 7 if volatility_contracting else 0

    # RSI scoring (max 8 pts)
    rsi = ta.rsi(close, length=14)
    rsi_val = round(rsi.iloc[-1], 1) if rsi is not None else 50.0

    if 55 <= rsi_val <= 75:
        rsi_score = 8
    elif 50 <= rsi_val < 55:
        rsi_score = 4
    elif 75 < rsi_val <= 80:
        rsi_score = 3
    else:
        rsi_score = 0

    # MACD scoring (max 7 pts)
    macd_df = ta.macd(close)
    macd_bullish = False
    macd_signal_str = "neutral"
    macd_score = 0
    if macd_df is not None and not macd_df.empty:
        hist = macd_df.iloc[:, 1]
        macd_bullish = hist.iloc[-1] > 0 and hist.iloc[-2] <= 0
        if macd_bullish:
            macd_signal_str = "bullish crossover"
            macd_score = 7
        elif hist.iloc[-1] > hist.iloc[-2]:
            macd_signal_str = "histogram rising"
            macd_score = 4
        else:
            macd_signal_str = "bearish"

    # Moving average scoring (max 5 pts)
    ma20 = ta.sma(close, length=20).iloc[-1]
    ma50 = ta.sma(close, length=50).iloc[-1]
    ma200 = ta.sma(close, length=200).iloc[-1]
    price = close.iloc[-1]
    above_20 = bool(price > ma20)
    above_50 = bool(price > ma50)
    above_200 = bool(price > ma200)
    above_key_mas = above_20 and above_50 and above_200

    if above_key_mas:
        ma_score = 5
    elif above_20 and above_50:
        ma_score = 3
    elif above_20:
        ma_score = 1
    else:
        ma_score = 0

    # Technical sub-total (max 45 pts, excludes pattern)
    tech_score = vol_score + high_score + vol_contraction_score + rsi_score + macd_score + ma_score

    # Pattern detection
    pattern = _detect_pattern(
        volume_ratio, pct_from_high, volatility_contracting,
        rsi_val, macd_bullish, above_20, above_50, above_200,
    )
    pat_score = _pattern_score(pattern)

    return TechnicalScore(
        total=tech_score,
        pattern=pattern,
        pattern_score=pat_score,
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
        ma20_price=round(float(ma20), 2),
        ma50_price=round(float(ma50), 2),
    )
