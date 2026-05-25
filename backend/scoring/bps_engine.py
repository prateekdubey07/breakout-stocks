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
    price: float, atr_20: float, bps: float
) -> tuple[str, str, str, str, str]:
    entry_lo = round(price * 0.998, 2)
    entry_hi = round(price * 1.002, 2)

    atr = atr_20 if atr_20 > 0 else price * 0.02

    # BPS-continuous multipliers — both scale with score so R:R varies per ticker
    # stop_mult: 2.0 (bps=0) → 1.0 (bps=100) — tighter stop for stronger setups
    # t1_mult:   2.0 (bps=0) → 3.0 (bps=100) — higher target for stronger setups
    # t2_mult:   t1_mult * 2 — fixed 2× extension
    stop_mult = round(1.0 + ((100 - bps) / 100), 4)   # 1.0–2.0
    t1_mult   = round(2.0 + (bps / 100), 4)            # 2.0–3.0
    t2_mult   = round(t1_mult * 2, 4)

    stop = round(price - stop_mult * atr, 2)
    stop = max(stop, round(price * 0.90, 2))  # floor at 10% max loss
    risk = price - stop
    if risk <= 0:
        risk = price * 0.02

    t1 = round(price + t1_mult * atr, 2)
    t2 = round(price + t2_mult * atr, 2)
    rr = round((t1 - price) / risk, 2)

    return f"${entry_lo}-${entry_hi}", f"${stop}", f"${t1}", f"${t2}", f"{rr}:1"


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
    entry, stop, t1, t2, rr = _entry_stop_targets(price, tech.atr_20, total)

    # Relative strength vs SPY (20-day return ratio)
    rs_vs_spy: float | None = None
    try:
        from data.fetcher import _OHLCV_BATCH_CACHE
        spy_df = _OHLCV_BATCH_CACHE.get("SPY")
        if spy_df is not None and len(spy_df) >= 21:
            spy_ret = float(spy_df["Close"].iloc[-1]) / float(spy_df["Close"].iloc[-21]) - 1
            tkr_ret = float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-21]) - 1
            if abs(spy_ret) > 1e-6:
                rs_vs_spy = round(tkr_ret / abs(spy_ret), 3)
    except Exception:
        pass

    # Per-component technical breakdown for diagnosis
    _vol_pts  = 10 if tech.volume_ratio > 2.0 else 6 if tech.volume_ratio >= 1.5 else 3 if tech.volume_ratio >= 1.2 else 0
    _high_pts = 8 if tech.pct_from_52w_high >= -3.0 else 4 if tech.pct_from_52w_high >= -8.0 else 0
    _coil_pts = 7 if tech.volatility_contracting else 0
    _rsi_pts  = 8 if 55 <= tech.rsi_14 <= 75 else 4 if 50 <= tech.rsi_14 < 55 else 3 if 75 < tech.rsi_14 <= 80 else 0
    _macd_pts = 7 if tech.macd_bullish else (4 if "rising" in tech.macd_signal else 0)
    _ma_pts   = 5 if tech.above_key_mas else (3 if tech.above_20ma and tech.above_50ma else (1 if tech.above_20ma else 0))
    print(f"[TECH_SCORE] {ticker}: vol={_vol_pts} 52h={_high_pts} coil={_coil_pts} "
          f"rsi={_rsi_pts} macd={_macd_pts} ma={_ma_pts} -> subtotal={tech.total} "
          f"pattern={tech.pattern}({tech.pattern_score}pts) atr={tech.atr_20}")
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
            macd_histogram=round(_safe_float(tech.macd_histogram), 4),
            volatility_contracting=tech.volatility_contracting,
            pct_from_52w_high=round(_safe_float(tech.pct_from_52w_high), 2),
            ml_breakout_prob=round(_safe_float(ml_prob), 4),
        ),
        fundamentals=Fundamentals(
            eps_growth_yoy=fund.eps_growth_yoy,
            revenue_growth_yoy=fund.revenue_growth_yoy,
            peg_ratio=fund.peg_ratio,
            catalyst=fund.catalyst,
            sector=info.get("sector") or "Unknown",
        ),
        risk_flags=risk_flags,
        entry_zone=entry,
        stop_loss=stop,
        target_1=t1,
        target_2=t2,
        risk_reward=rr,
        timeframe="5-10 trading sessions",
        rs_vs_spy=rs_vs_spy,
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
            macd_histogram=0.0,
            volatility_contracting=False,
            pct_from_52w_high=0,
            ml_breakout_prob=0,
        ),
        fundamentals=Fundamentals(
            eps_growth_yoy="N/A",
            revenue_growth_yoy="N/A",
            peg_ratio=None,
            catalyst="Disqualified",
            sector="Unknown",
        ),
        risk_flags=flags,
        entry_zone="N/A",
        stop_loss="N/A",
        target_1="N/A",
        target_2="N/A",
        risk_reward="N/A",
        timeframe="N/A",
    )
