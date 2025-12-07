import math


def compute_confidence(
    n: int,
    sigma: float,
    sigma_market: float = 2.0,
    n0: int = 50,
    alpha: float = 0.7,
) -> float:
    """
    Returns confidence in [0, 1].
    - n: number of historical events in the group
    - sigma: std dev of group abnormal returns
    - sigma_market: typical 1-day market volatility in %
    - n0: prior pseudo-count
    - alpha: penalty scale for noisy groups
    """
    if n <= 0:
        return 0.0
    conf_raw = n / (n + n0)
    noise_penalty = math.exp(-alpha * (sigma / sigma_market))
    return max(0.0, min(1.0, conf_raw * noise_penalty))
