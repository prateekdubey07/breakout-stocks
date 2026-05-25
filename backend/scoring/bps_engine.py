import math
from data.fetcher import fetch_ohlcv, fetch_fundamentals
from scoring.technical import compute_technical_score
from scoring.fundamental import compute_fundamental_score
from scoring.risk_filters import apply_risk_filters
from ml.predictor import predict_breakout_prob
from models import BpsResult, SignalSummary, Fundamentals


def _safe_float(v: float, default: float = 0.0) -> float:
    return default if (math.isnan(v) or math.isinf(v)) else v


def _conviction(bps: float) -> str:
    if bps >= 75:
        return "HIGH"
    if bps >= 60:
        return "MEDIUM"
    if bps >= 45:
        return "WATCH"
    return "PASS"


_PATTERN_REWARD_MULT = {
    "Bull Flag": 3.0,
    "Volatility Squeeze": 2.5,
    "Breakout Retest": 2.5,
    "Cup & Handle": 2.5,
    "Ascending Triangle": 2.5,
    "VCP": 3.0,
    "Rising Base": 2.0,
    "Flat Base": 2.0,
    "Range Bound": 1.5,
    "No Clear Pattern": 2.0,
    "Downtrend": 1.5,
}


def _entry_stop_targets(
    price: float, ma20_price: float, above_ma20: bool, pattern: str
) -> tuple[str, str, str, str, str]:
    entry_lo = round(price * 0.998, 2)
    entry_hi = round(price * 1.002, 2)

    # Stop at MA20 (unique per ticker) — gives variable risk distance
    if above_ma20 and ma20_price > 0 and ma20_price < price:
        stop = round(ma20_price * 0.995, 2)
    else:
        stop = round(price * 0.94, 2)

    # Enforce minimum 3% below entry
    max_stop = round(price * 0.97, 2)
    if stop > max_stop:
        stop = max_stop

    risk = price - stop
    if risk <= 0:
        risk = price * 0.04

    # Pattern-specific reward multiplier → unique R:R per ticker
    reward_mult = _PATTERN_REWARD_MULT.get(pattern, 2.0)
    t1 = round(price + risk * reward_mult, 2)
    t2 = round(price + risk * reward_mult * 2, 2)
    rr = f"{reward_mult}:1"

    return f"${entry_lo}-${entry_hi}", f"${stop}", f"${t1}", f"${t2}", rr


def score_ticker(ticker: str) -> BpsResult:
    df = fetch_ohlcv(ticker, period="2y")
    if df is None or df.empty or len(df) < 50:
        return _zero_result(ticker, ["INSUFFICIENT_DATA"])

    info = fetch_fundamentals(ticker)

    tech = compute_technical_score(df)
    fund = compute_fundamental_score(info)
    disqualified, risk_flags, penalty = apply_risk_filters(info, fund.flags)

    if disqualified:
        return _zero_result(ticker, risk_flags)

    ml_prob = predict_breakout_prob(df, sector=info.get("sector", "Unknown"))

    # Pattern recognition (20 pts): rule-based + small ML boost when model trained
    pattern_pts = min(tech.pattern_score + round(ml_prob * 5, 1), 20.0)

    # Risk filter: overbought or far from highs
    if tech.rsi_14 > 80:
        penalty += 15
    if tech.pct_from_52w_high < -30:
        penalty += 15

    total = min(tech.total + fund.total + pattern_pts - penalty, 100.0)
    total = max(total, 0.0)

    price = float(df["Close"].iloc[-1])
    entry, stop, t1, t2, rr = _entry_stop_targets(
        price, tech.ma20_price, tech.above_20ma, tech.pattern
    )

    print(f"[DEBUG] {ticker}: bps={total:.1f} tech={tech.total} fund={fund.total} "
          f"pattern={tech.pattern}({pattern_pts}pts) ml={ml_prob:.0%} rr={rr} "
          f"eps={fund.eps_growth_yoy} rev={fund.revenue_growth_yoy} vol={tech.volume_ratio}")

    return BpsResult(
        ticker=ticker.upper(),
        breakout_probability_score=round(total, 1),
        conviction=_conviction(total),
        technical_score=round(tech.total, 1),
        fundamental_score=round(fund.total, 1),
        signal_summary=SignalSummary(
            pattern=tech.pattern,
            volume_surge=tech.volume_surge,
            volume_ratio=round(_safe_float(tech.volume_ratio), 2),
            above_key_mas=tech.above_key_mas,
            rsi_14=round(_safe_float(tech.rsi_14), 1),
            macd_signal=tech.macd_signal,
            volatility_contracting=tech.volatility_contracting,
            pct_from_52w_high=round(_safe_float(tech.pct_from_52w_high), 2),
            ml_breakout_prob=round(_safe_float(ml_prob), 4),
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
        timeframe="5-10 trading sessions",
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
