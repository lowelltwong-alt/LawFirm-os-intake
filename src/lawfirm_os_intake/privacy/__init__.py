"""Synthetic-only, candidate-only CAL-DP primitives.

These utilities are local evaluation scaffolds. They are not a production privacy
implementation and make no formal production privacy claim.
"""

from .dp_mechanism import (
    GaussianMechanism,
    GaussianRelease,
    SyntheticReplaySeed,
    SyntheticPrivacyScope,
    clip_l2,
)
from .zcdp_ledger import (
    SYNTHETIC_RESET_POLICY_PLACEHOLDER,
    ZCDPBudgetExceeded,
    ZCDPLedger,
    ZCDPReport,
    zcdp_to_epsilon_delta,
)

__all__ = [
    "GaussianMechanism",
    "GaussianRelease",
    "SyntheticReplaySeed",
    "SyntheticPrivacyScope",
    "SYNTHETIC_RESET_POLICY_PLACEHOLDER",
    "ZCDPBudgetExceeded",
    "ZCDPLedger",
    "ZCDPReport",
    "clip_l2",
    "zcdp_to_epsilon_delta",
]
