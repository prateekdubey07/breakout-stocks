from data.fetcher import fetch_ohlcv, fetch_fundamentals
from scoring.technical import compute_technical_score
from scoring.fundamental import compute_fundamental_score
from scoring.risk_filters import apply_risk_filters
from ml.predictor import predict_breakout_prob
from models import BpsResult, SignalSummary, Fundamentals


def _conviction(bps: float) -> str:
    if bps >= 80:
        return "HIGH"
    if bps >= 65:
        return "MEDIUM"
    if bps >= 50:
        return "WATCH"
    return "PASS"


def _entry_stop_targets(price: float, atr: float) -> tuple[str, str, str, str, str]:
    entry_lo = round(price * 0.995, 2)
    entry_hi = round(price * 1.005, 2)
    stop = round(price - 1.5 * atr, 2)
    t1 = round(price + 2.5 * atr, 2)
    t2 = round(price + 5.0 * atr, 2)
    risk = price - stop
    reward = t1 - price
    rr = f"{round(reward/risk, 1)}:1" if risk > 0 else "N/A"
    return f"${entry_lo}–${entry_hi}", f"${stop}", f"${t1}", f"${t2}", rr


def score_ticker(ticker: str) -> BpsResult:
    df = fetch_ohlcv(ticker, period="1y")
    info = fetch_fundamentals(ticker)

    tech = compute_technical_score(df)
    fund = compute_fundamental_score(info)
    disqualified, risk_flags, penalty = apply_risk_filters(info, fund.flags)

    if disqualified:
        return _zero_result(ticker, risk_flags)

    ml_prob = predict_breakout_prob(df, sector=info.get("sector", "Unknown"))
    # ML maps to 0-20 pts (pattern recognition slot)
    ml_pts = round(ml_prob * 20, 1)

    total = min(tech.total + fund.total + ml_pts - penalty, 100.0)
    total = max(total, 0.0)

    price = float(df["Close"].iloc[-1])
    entry, stop, t1, t2, rr = _entry_stop_targets(price, tech.atr_20)

    return BpsResult(
        ticker=ticker.upper(),
        breakout_probability_score=round(total, 1),
        conviction=_conviction(total),
        technical_score=round(tech.total, 1),
        fundamental_score=round(fund.total, 1),
        signal_summary=SignalSummary(
            pattern=f"ML prob {ml_prob:.0%}",
            volume_surge=tech.volume_surge,
            volume_ratio=tech.volume_ratio,
            above_key_mas=tech.above_key_mas,
            rsi_14=tech.rsi_14,
            macd_signal=tech.macd_signal,
            volatility_contracting=tech.volatility_contracting,
            pct_from_52w_high=tech.pct_from_52w_high,
            ml_breakout_prob=ml_prob,
        ),
        fundamentals=Fundamentals(
            eps_growth_yoy=fund.eps_growth_yoy,
            revenue_growth_yoy=fund.revenue_growth_yoy,
            peg_ratio=fund.peg_ratio,
            catalyst=fund.catalyst,
        ),
        risk_flags=risk_flags,
        entry_zone=entry,
        stop_loss=stop,
        target_1=t1,
        target_2=t2,
        risk_reward=rr,
        timeframe="5–10 trading sessions",
    )


def _zero_result(ticker: str, flags: list) -> BpsResult:
    return BpsResult(
        ticker=ticker,
        breakout_probability_score=0,
        conviction="PASS",
        technical_score=0,
        fundamental_score=0,
        signal_summary=SignalSummary(
            pattern="DISQUALIFIED",
            volume_surge=False,
            volume_ratio=0,
            above_key_mas=False,
            rsi_14=0,
            macd_signal="N/A",
            volatility_contracting=False,
            pct_from_52w_high=0,
            ml_breakout_prob=0,
        ),
        fundamentals=Fundamentals(
            eps_growth_yoy="N/A",
            revenue_growth_yoy="N/A",
            peg_ratio=None,
            catalyst="Disqualified",
        ),
        risk_flags=flags,
        entry_zone="N/A",
        stop_loss="N/A",
        target_1="N/A",
        target_2="N/A",
        risk_reward="N/A",
        timeframe="N/A",
    )
