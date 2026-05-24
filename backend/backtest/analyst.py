import numpy as np


def evaluate_signals(signals: list[dict]) -> dict:
    if not signals:
        return {"total_signals": 0, "error": "no signals found"}

    outcomes = []
    for s in signals:
        prices = s["price_data_after_signal"]
        entry = s["entry_price"]
        stop = s["stop_loss"]
        t1 = s["target_1"]
        t2 = s["target_2"]

        outcome = "STILL_OPEN"
        exit_price = prices[-1] if prices else entry
        days = len(prices)

        for d, p in enumerate(prices):
            if p <= stop:
                outcome = "STOPPED_OUT"
                exit_price = stop
                days = d + 1
                break
            if p >= t2:
                outcome = "HIT_T2"
                exit_price = t2
                days = d + 1
                break
            if p >= t1:
                outcome = "HIT_T1"
                exit_price = t1
                days = d + 1
                break

        ret = (exit_price - entry) / entry * 100
        signal_clean = {k: v for k, v in s.items() if k != "price_data_after_signal"}
        outcomes.append({**signal_clean, "outcome": outcome,
                         "actual_return_pct": round(ret, 2), "days_to_resolution": days})

    total = len(outcomes)
    winners = [o for o in outcomes if o["outcome"] in ("HIT_T1", "HIT_T2")]
    losers = [o for o in outcomes if o["outcome"] == "STOPPED_OUT"]

    win_rate = len(winners) / total
    stop_rate = len(losers) / total
    avg_win = float(np.mean([o["actual_return_pct"] for o in winners])) if winners else 0.0
    avg_loss = float(np.mean([o["actual_return_pct"] for o in losers])) if losers else 0.0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss
    pf_denom = abs(avg_loss * len(losers))
    profit_factor = abs(avg_win * len(winners) / pf_denom) if pf_denom > 0 else 999.0

    returns = [o["actual_return_pct"] for o in outcomes]
    sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0.0

    cum, peak, max_dd = 0.0, 0.0, 0.0
    for r in returns:
        cum += r
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)

    return {
        "total_signals": total,
        "win_rate_t1": round(win_rate, 3),
        "stop_out_rate": round(stop_rate, 3),
        "avg_return_winners_pct": round(avg_win, 2),
        "avg_return_losers_pct": round(avg_loss, 2),
        "expectancy_per_trade_pct": round(expectancy, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_days_to_resolution": round(float(np.mean([o["days_to_resolution"] for o in outcomes])), 1),
        "signals": outcomes,
    }
