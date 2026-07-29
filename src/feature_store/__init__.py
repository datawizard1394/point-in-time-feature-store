"""Synthetic point-in-time feature-store reference implementation."""

from .engine import build_offline_features, materialize_online, parity_report
from .models import Observation, Transaction

__all__ = [
    "Observation",
    "Transaction",
    "build_offline_features",
    "materialize_online",
    "parity_report",
]

__version__ = "0.1.0"
