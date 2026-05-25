import os
import requests

_WEBHOOK_URL = None


def _get_webhook() -> str:
    global _WEBHOOK_URL
    if _WEBHOOK_URL is None:
        _WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
    return _WEBHOOK_URL


def send_high_conviction_alerts(candidates: list) -> None:
    """POST embed to Discord for any ticker with BPS >= 75.
    Silently no-ops if DISCORD_WEBHOOK_URL is not set."""
    url = _get_webhook()
    if not url:
        return

    high = [c for c in candidates if getattr(c, "breakout_probability_score", 0) >= 75]
    if not high:
        return

    lines = []
    for c in high[:8]:
        ss = c.signal_summary
        rs_str = f" | RS {c.rs_vs_spy:+.2f}x SPY" if c.rs_vs_spy is not None else ""
        earn_warn = " ⚠ EARNINGS SOON" if "EARNINGS_WITHIN_5D" in (c.risk_flags or []) else ""
        lines.append(
            f"**{c.ticker}** BPS={c.breakout_probability_score} · {c.conviction}"
            f" · {ss.pattern} · RR={c.risk_reward}{rs_str}{earn_warn}"
        )

    payload = {
        "username": "BreakoutStocks Scanner",
        "avatar_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4c8.png",
        "embeds": [
            {
                "title": f"🚀 {len(high)} HIGH conviction setup{'s' if len(high) != 1 else ''} detected",
                "description": "\n".join(lines),
                "color": 0x22C55E,
                "footer": {"text": "BreakoutStocks · Auto Scan"},
            }
        ],
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code not in (200, 204):
            print(f"[DISCORD] Webhook returned {resp.status_code}: {resp.text[:120]}")
        else:
            print(f"[DISCORD] Sent alert for {[c.ticker for c in high]}")
    except Exception as e:
        print(f"[DISCORD] Failed to send: {e}")
