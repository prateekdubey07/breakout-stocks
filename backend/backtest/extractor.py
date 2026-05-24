import pandas as pd
import pandas_ta as ta
from data.fetcher import fetch_ohlcv


def extract_signals(ticker: str, start: str, end: str) -> list[dict]:
    df = fetch_ohlcv(ticker, period="5y")
    df = df.loc[start:end]
    if len(df) < 60:
        return []

    close = df["Close"]
    volume = df["Volume"]
    rsi = ta.rsi(close, 14)
    sma50 = ta.sma(close, 50)
    atr20 = ta.atr(df["High"], df["Low"], close, 20)
    vol_avg = volume.rolling(20).mean()
    resistance = close.rolling(20).max().shift(1)

    signals = []
    for i in range(25, len(df) - 11):
        if (
            volume.iloc[i] > vol_avg.iloc[i] * 1.5
            and close.iloc[i] > resistance.iloc[i]
            and 50 <= rsi.iloc[i] <= 75
            and close.iloc[i] > sma50.iloc[i]
        ):
            atr = atr20.iloc[i]
            entry = float(close.iloc[i])
            future = close.iloc[i+1:i+11].tolist()
            signals.append({
                "ticker": ticker,
                "signal_date": str(df.index[i].date()),
                "signal_type": "Volume Breakout",
                "entry_price": entry,
                "stop_loss": round(entry - 1.5 * float(atr), 2),
                "target_1": round(entry + 2.5 * float(atr), 2),
                "target_2": round(entry + 5.0 * float(atr), 2),
                "bps_at_signal": round(float(rsi.iloc[i]), 1),
                "pattern_context": f"ATR={float(atr):.2f}",
                "price_data_after_signal": [float(p) for p in future],
            })
    return signals
