from data.fetcher import fetch_ohlcv
from scoring.bps_engine import score_ticker
from database import get_conn


def classify_ticker(row: dict) -> dict:
    ticker = row["ticker"]
    try:
        result = score_ticker(ticker)
    except Exception as e:
        return {"ticker": ticker, "status": "ERROR", "urgency": "LOW",
                "current_price": 0.0, "action": str(e), "updated_bps": 0, "notes": ""}

    bps = result.breakout_probability_score
    prev_status = row.get("last_status", "STILL_VALID")

    if bps >= 80 and prev_status in ("STILL_VALID", "WATCH", "PATTERN_EXTENDED"):
        status = "TRIGGERED"
        urgency = "HIGH"
        action = f"Enter long near {result.entry_zone}. Stop {result.stop_loss}. Scale 50/50."
    elif result.signal_summary.rsi_14 < 45:
        status = "BREAKING_DOWN"
        urgency = "HIGH"
        action = "RSI collapsed below 45. Cut position or wait for re-entry."
    elif bps < ((row.get("original_bps") or 65) - 15):
        status = "BREAKING_DOWN"
        urgency = "MEDIUM"
        action = f"BPS dropped to {bps}. Review stop {result.stop_loss}."
    else:
        status = "STILL_VALID"
        urgency = "LOW"
        action = "Setup intact. Monitor."

    conn = get_conn()
    conn.execute("UPDATE watchlist SET last_status=? WHERE ticker=?", (status, ticker))
    conn.commit()
    conn.close()

    try:
        current_price = float(fetch_ohlcv(ticker, period="1mo")["Close"].iloc[-1])
    except Exception:
        current_price = 0.0

    return {
        "ticker": ticker,
        "status": status,
        "urgency": urgency,
        "current_price": current_price,
        "action": action,
        "updated_bps": bps,
        "notes": f"Pattern: {result.signal_summary.pattern}. RSI: {result.signal_summary.rsi_14}",
    }


def run_watchlist_scan() -> list[dict]:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM watchlist").fetchall()]
    conn.close()
    return [classify_ticker(r) for r in rows]
