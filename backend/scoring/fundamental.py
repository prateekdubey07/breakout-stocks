from dataclasses import dataclass, field
from typing import List
import time


@dataclass
class FundamentalScore:
    total: float
    eps_growth_yoy: str
    revenue_growth_yoy: str
    peg_ratio: float | None
    catalyst: str
    flags: List[str] = field(default_factory=list)


def compute_fundamental_score(info: dict) -> FundamentalScore:
    score = 0.0
    flags = []
    catalyst_parts = []

    eps_g = info.get("eps_growth_yoy")
    rev_g = info.get("revenue_growth_yoy")
    peg = info.get("peg_ratio")

    if eps_g and eps_g > 0.20:
        score += 8
        catalyst_parts.append(f"EPS growth {eps_g*100:.0f}% YoY")
    if rev_g and rev_g > 0.15:
        score += 6
        catalyst_parts.append(f"Rev growth {rev_g*100:.0f}% YoY")

    # Approximate earnings beat via positive EPS growth
    if eps_g and eps_g > 0.10:
        score += 4

    if peg and peg < 1.5:
        score += 4

    # Catalyst: next earnings timing
    next_earnings = info.get("next_earnings")
    if next_earnings:
        days_to_earnings = (next_earnings - time.time()) / 86400
        if 14 <= days_to_earnings <= 28:
            score += 2
            catalyst_parts.append(f"Earnings in {days_to_earnings:.0f}d")
        elif 0 < days_to_earnings < 5:
            flags.append("EARNINGS_WITHIN_5D")

    eps_str = f"{eps_g*100:.0f}%" if eps_g else "N/A"
    rev_str = f"{rev_g*100:.0f}%" if rev_g else "N/A"

    return FundamentalScore(
        total=min(score, 35.0),
        eps_growth_yoy=eps_str,
        revenue_growth_yoy=rev_str,
        peg_ratio=round(peg, 2) if peg else None,
        catalyst=" + ".join(catalyst_parts) if catalyst_parts else "No catalyst identified",
        flags=flags,
    )
