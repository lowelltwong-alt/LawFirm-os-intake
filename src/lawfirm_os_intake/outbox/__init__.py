"""Synthetic-only, candidate-only IFC evidence for the intake outbox."""

from .crossing_proof import (
    CrossingProof,
    CrossingRequest,
    build_crossing_proof,
    crossing_request_digest,
)
from .label_lattice import SensitivityLabel, join_labels
from .residue_scanner import ResidueReasonCode, ResidueScanResult, scan_residue

__all__ = [
    "CrossingProof",
    "CrossingRequest",
    "ResidueReasonCode",
    "ResidueScanResult",
    "SensitivityLabel",
    "build_crossing_proof",
    "crossing_request_digest",
    "join_labels",
    "scan_residue",
]
