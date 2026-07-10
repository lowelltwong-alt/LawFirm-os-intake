"""Deterministic residue scanner that emits only closed, non-sensitive reason codes."""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ResidueReasonCode(str, Enum):
    currency_or_rate_detected = "currency_or_rate_detected"
    specific_carrier_identifier_detected = "specific_carrier_identifier_detected"
    pii_detected = "pii_detected"
    privilege_or_work_product_detected = "privilege_or_work_product_detected"
    raw_source_blob_detected = "raw_source_blob_detected"
    free_text_signal_present = "free_text_signal_present"
    non_ascii_signal_detected = "non_ascii_signal_detected"


class ResidueScanResult(_StrictModel):
    scanner_version: Literal["ifc-residue-scanner-v1"] = "ifc-residue-scanner-v1"
    clean: bool
    reason_codes: tuple[ResidueReasonCode, ...]
    scanned_signal_count: int = Field(ge=0)
    raw_signal_values_included: Literal[False] = False

    @model_validator(mode="after")
    def result_is_consistent(self) -> "ResidueScanResult":
        if self.clean != (not self.reason_codes):
            raise ValueError("residue scanner clean flag is inconsistent")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("residue scanner reason codes must be unique")
        return self


_CURRENCY_OR_RATE = re.compile(
    r"(?:[$]|\b(?:usd|eur|gbp)\b|\brate\b|\bper\s+(?:hour|hr)\b|/\s*(?:hour|hr)\b|"
    r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b)",
    re.IGNORECASE,
)
_SPECIFIC_CARRIER = re.compile(
    r"\bcarrier[-_:](?!(?:tier|class|group|general|any)[-_:])[a-z0-9_-]+\b|"
    r"\bspecific[-_:]carrier\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"\b(?:\+?1[-. ]?)?(?:\(?\d{3}\)?[-. ]?)\d{3}[-. ]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PRIVILEGE = re.compile(
    r"\b(?:privileged|attorney[ -]?client|work[ -]?product|legal advice)\b", re.IGNORECASE
)
_MAX_SIGNAL_LENGTH = 240


def scan_residue(
    signals: tuple[str, ...],
    *,
    classify_as_free_text: bool = True,
    scope_confirmed_synthetic: bool = False,
) -> ResidueScanResult:
    """Scan strings without retaining or echoing values in the resulting evidence."""
    if scope_confirmed_synthetic is not True:
        raise ValueError("residue scanning requires explicitly confirmed synthetic scope")
    reasons: set[ResidueReasonCode] = set()
    for signal in signals:
        if classify_as_free_text and signal:
            reasons.add(ResidueReasonCode.free_text_signal_present)
        if len(signal) > _MAX_SIGNAL_LENGTH:
            reasons.add(ResidueReasonCode.raw_source_blob_detected)
        if not signal.isascii():
            reasons.add(ResidueReasonCode.non_ascii_signal_detected)
        if _CURRENCY_OR_RATE.search(signal):
            reasons.add(ResidueReasonCode.currency_or_rate_detected)
        if _SPECIFIC_CARRIER.search(signal):
            reasons.add(ResidueReasonCode.specific_carrier_identifier_detected)
        if _EMAIL.search(signal) or _PHONE.search(signal) or _SSN.search(signal):
            reasons.add(ResidueReasonCode.pii_detected)
        if _PRIVILEGE.search(signal):
            reasons.add(ResidueReasonCode.privilege_or_work_product_detected)
    return ResidueScanResult(
        clean=not reasons,
        reason_codes=tuple(sorted(reasons, key=lambda item: item.value)),
        scanned_signal_count=len(signals),
    )
