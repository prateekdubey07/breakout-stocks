from typing import Tuple, List


def apply_risk_filters(info: dict, fundamental_flags: List[str]) -> Tuple[bool, List[str], float]:
    """
    Returns (disqualified, risk_flags, bps_penalty).
    disqualified=True forces BPS to 0.
    bps_penalty subtracted before conviction tier assignment.
    """
    flags = list(fundamental_flags)
    penalty = 0.0

    avg_vol = info.get("avg_volume") or 0
    short_pct = info.get("short_pct_float") or 0

    # Hard disqualifiers
    if avg_vol < 500_000:
        return True, ["AVG_VOLUME_TOO_LOW"], 0.0
    if short_pct > 0.25:
        return True, ["SHORT_INTEREST_HIGH"], 0.0

    # Yellow flags
    if "EARNINGS_WITHIN_5D" in flags:
        penalty += 15
        flags.append("YELLOW_EARNINGS_BINARY_RISK")

    return False, flags, penalty
