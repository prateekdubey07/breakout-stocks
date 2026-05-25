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


# Normalize yfinance/Alpaca/FinViz sector strings → standard GICS-like buckets
_SECTOR_MAP = {
    # Tech variants
    "Electronic Technology": "Technology",
    "Semiconductors": "Technology",
    "Software Application": "Technology",
    "Software Infrastructure": "Technology",
    "Internet Content & Information": "Technology",
    "Consumer Electronics": "Technology",
    "Technology Services": "Technology",
    "Information Technology": "Technology",
    "IT Services": "Technology",
    "Software": "Technology",
    # Communication
    "Interactive Media & Services": "Communication Services",
    "Telecommunications": "Communication Services",
    "Media": "Communication Services",
    # Consumer
    "Retail Trade": "Consumer Cyclical",
    "Consumer Durables": "Consumer Cyclical",
    "Consumer Discretionary": "Consumer Cyclical",
    "Consumer Non-Durables": "Consumer Defensive",
    "Consumer Staples": "Consumer Defensive",
    # Healthcare
    "Health Technology": "Healthcare",
    "Health Services": "Healthcare",
    "Health Care": "Healthcare",
    "Biotechnology": "Healthcare",
    "Pharmaceuticals": "Healthcare",
    # Financial
    "Finance": "Financial Services",
    "Financial": "Financial Services",
    "Financials": "Financial Services",
    "Banks": "Financial Services",
    "Insurance": "Financial Services",
    # Industrials
    "Producer Manufacturing": "Industrials",
    "Process Industries": "Industrials",
    "Transportation": "Industrials",
    "Commercial Services": "Industrials",
    # Energy / Materials
    "Basic Materials": "Materials",
    "Minerals": "Materials",
}


def compute_fundamental_score(info: dict) -> FundamentalScore:
    score = 0.0
    flags = []
    catalyst_parts = []

    eps_g = info.get("eps_growth_yoy")
    rev_g = info.get("revenue_growth_yoy")
    peg = info.get("peg_ratio")
    forward_pe = info.get("forward_pe")
    market_cap = info.get("market_cap") or 0
    short_pct = info.get("short_pct_float") or 0
    raw_sector = info.get("sector") or "Unknown"
    sector = _SECTOR_MAP.get(raw_sector, raw_sector)  # normalize non-standard names

    # EPS growth (max 8 pts)
    if eps_g is not None:
        if eps_g > 0.30:
            score += 8
            catalyst_parts.append(f"EPS growth {eps_g*100:.0f}% YoY")
        elif eps_g >= 0.15:
            score += 5
            catalyst_parts.append(f"EPS growth {eps_g*100:.0f}% YoY")
        elif eps_g >= 0.0:
            score += 2

    # Revenue growth (max 6 pts)
    if rev_g is not None:
        if rev_g > 0.20:
            score += 6
            catalyst_parts.append(f"Rev growth {rev_g*100:.0f}% YoY")
        elif rev_g >= 0.08:
            score += 3

    # Forward PE (max 4 pts)
    if forward_pe and forward_pe > 0:
        if forward_pe < 20:
            score += 4
        elif forward_pe <= 30:
            score += 2

    # PEG ratio (max 2 pts)
    if peg and peg < 1.5:
        score += 2
        catalyst_parts.append(f"PEG {peg:.2f}")

    # Market cap (max 3 pts)
    if market_cap > 100_000_000_000:
        score += 3
    elif market_cap > 10_000_000_000:
        score += 2

    # Short interest (max 4 pts) — short_pct_float is 0-1 decimal
    if short_pct < 0.03:
        score += 4
    elif short_pct < 0.07:
        score += 2

    # Sector (max 3 pts) — uses normalized sector (already mapped via _SECTOR_MAP above)
    _TIER1 = {"Technology", "Communication Services", "Consumer Cyclical", "Financial Services"}
    _TIER2 = {"Healthcare", "Industrials", "Energy"}
    if sector in _TIER1:
        score += 3
        catalyst_parts.append(f"{sector} tailwind")
    elif sector in _TIER2:
        score += 2

    # Next earnings timing
    next_earnings = info.get("next_earnings")
    if next_earnings:
        days_to_earnings = (next_earnings - time.time()) / 86400
        if 14 <= days_to_earnings <= 28:
            score += 2
            catalyst_parts.append(f"Earnings in {days_to_earnings:.0f}d")
        elif 0 < days_to_earnings < 5:
            flags.append("EARNINGS_WITHIN_5D")

    eps_str = f"{eps_g*100:.0f}%" if eps_g is not None else "N/A"
    rev_str = f"{rev_g*100:.0f}%" if rev_g is not None else "N/A"

    print(f"[FUND_SCORE] total={min(score, 35.0):.1f} | "
          f"eps={eps_g}({eps_str}) rev={rev_g}({rev_str}) "
          f"pe={forward_pe} peg={peg} mktcap={market_cap:.2e} "
          f"short={short_pct:.4f} sector={raw_sector!r}->{sector!r}")

    return FundamentalScore(
        total=min(score, 35.0),
        eps_growth_yoy=eps_str,
        revenue_growth_yoy=rev_str,
        peg_ratio=round(peg, 2) if peg else None,
        catalyst=" + ".join(catalyst_parts) if catalyst_parts else "No catalyst identified",
        flags=flags,
    )
