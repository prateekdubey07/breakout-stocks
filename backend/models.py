from pydantic import BaseModel
from typing import Optional, List

class SignalSummary(BaseModel):
    pattern: str
    volume_surge: bool
    volume_ratio: float
    above_key_mas: bool
    rsi_14: float
    macd_signal: str
    volatility_contracting: bool
    pct_from_52w_high: float
    ml_breakout_prob: float

class Fundamentals(BaseModel):
    eps_growth_yoy: str
    revenue_growth_yoy: str
    peg_ratio: Optional[float] = None
    catalyst: str

class BpsResult(BaseModel):
    ticker: str
    breakout_probability_score: float
    conviction: str
    technical_score: float
    fundamental_score: float
    signal_summary: SignalSummary
    fundamentals: Fundamentals
    risk_flags: List[str]
    entry_zone: str
    stop_loss: str
    target_1: str
    target_2: str
    risk_reward: str
    timeframe: str

class ScanRequest(BaseModel):
    tickers: List[str]
    min_bps: float = 65.0

class BacktestRequest(BaseModel):
    ticker: str
    start: str
    end: str
