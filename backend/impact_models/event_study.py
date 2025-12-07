from dataclasses import dataclass
from math import sqrt
from scipy.stats import norm
from typing import Optional
import numpy as np


@dataclass
class GroupPrior:
    """Historical statistics for a group of similar events"""
    event_type: str
    sector: str
    cap_bucket: str
    mu: float           # mean abnormal return (%)
    sigma: float        # std dev of abnormal returns (%)
    n: int              # number of historical events


def p_move(mu: float, sigma: float, T: float) -> float:
    """
    P(|R| > T) - Probability of absolute move exceeding threshold
    """
    if sigma <= 0:
        return 0.0
    z = (T - abs(mu)) / sigma
    return 2.0 * (1.0 - norm.cdf(abs(z)))


def p_up(mu: float, sigma: float, T: float) -> float:
    """
    P(R > T) - Probability of upward move exceeding threshold
    """
    if sigma <= 0:
        return 0.5
    z = (T - mu) / sigma
    return 1.0 - norm.cdf(z)


def p_down(mu: float, sigma: float, T: float) -> float:
    """
    P(R < -T) - Probability of downward move exceeding threshold
    """
    if sigma <= 0:
        return 0.5
    z = (-T - mu) / sigma
    return norm.cdf(z)


def make_group_key(event_type: str, sector: str, cap_bucket: str) -> tuple:
    """Returns group key for event categorization"""
    return (event_type, sector, cap_bucket)
