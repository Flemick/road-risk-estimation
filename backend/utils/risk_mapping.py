def risk_category(probability: float) -> str:
    """
    Convert model probability (0–1) into risk level.
    """

    # Safety-oriented thresholds
    if probability < 0.25:
        return "Low"
    elif probability < 0.55:
        return "Medium"
    else:
        return "High"


def risk_score(probability: float) -> float:
    """
    Convert probability to percentage score (0–100)
    for UI display or coloring.
    """
    return round(probability * 100, 2)