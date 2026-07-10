"""Strict, synthetic-only structured IR for qualitative lesson candidates."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


Dimension = Literal[
    "carrier", "jurisdiction", "matter_type", "role", "issue_family", "threshold_band"
]
AtomClass = Literal["operational", "strategy"]
RuleClaimCode = Literal["candidate_review_default", "candidate_review_escalated"]
ContextCode = Literal[
    "applies_matching_operational_context",
    "not_for_strategy_or_unknown_context",
    "danger_overgeneralized_candidate_rule",
]
AdversaryCapability = Literal[
    "knows_reviewed_universe",
    "knows_all_but_target_support",
    "combines_published_lessons",
]

DIMENSION_ORDER: tuple[Dimension, ...] = (
    "carrier",
    "jurisdiction",
    "matter_type",
    "role",
    "issue_family",
    "threshold_band",
)


class LessonAtom(_StrictModel):
    dimension: Dimension
    value: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_:-]+$")
    atom_class: AtomClass

    @model_validator(mode="after")
    def value_is_not_whitespace(self) -> "LessonAtom":
        if not self.value.strip():
            raise ValueError("lesson atom value must not be whitespace")
        return self

    @property
    def policy_key(self) -> str:
        return f"{self.dimension}:{self.value}"


class LessonClaim(_StrictModel):
    before_code: RuleClaimCode
    after_code: RuleClaimCode

    @model_validator(mode="after")
    def codes_must_describe_a_change(self) -> "LessonClaim":
        if self.before_code == self.after_code:
            raise ValueError("lesson claim before_code and after_code must differ")
        return self


class SyntheticPolicyPlaceholders(_StrictModel):
    """Human-set inputs for synthetic fixtures, never production policy defaults."""

    policy_label: str = Field(min_length=1)
    k_qual: int = Field(ge=1)
    k_support: int = Field(ge=1)
    minimum_sensitive_outcome_diversity: int = Field(ge=1)
    adversary_model: str = Field(min_length=1, pattern=r"^[a-z0-9_:-]+$")
    adversary_capabilities: tuple[AdversaryCapability, ...] = Field(min_length=1)
    allowed_claim_codes: tuple[RuleClaimCode, ...] = Field(min_length=1)
    allowed_context_codes: tuple[ContextCode, ...] = Field(min_length=1)
    strategy_atom_keys: tuple[str, ...]

    @model_validator(mode="after")
    def policy_is_explicit_and_closed(self) -> "SyntheticPolicyPlaceholders":
        if not self.policy_label.strip() or not self.adversary_model.strip():
            raise ValueError("synthetic policy placeholders require nonblank labels")
        normalized_label = self.policy_label.casefold()
        if "synthetic" not in normalized_label or "placeholder" not in normalized_label:
            raise ValueError("policy_label must explicitly identify a synthetic policy placeholder")
        normalized_adversary = self.adversary_model.casefold()
        if "synthetic" not in normalized_adversary or "placeholder" not in normalized_adversary:
            raise ValueError("adversary_model must be a closed synthetic placeholder identifier")
        if len(set(self.allowed_claim_codes)) != len(self.allowed_claim_codes):
            raise ValueError("allowed claim codes must be unique")
        if len(set(self.allowed_context_codes)) != len(self.allowed_context_codes):
            raise ValueError("allowed context codes must be unique")
        if len(set(self.adversary_capabilities)) != len(self.adversary_capabilities):
            raise ValueError("adversary capabilities must be unique")
        if len(set(self.strategy_atom_keys)) != len(self.strategy_atom_keys):
            raise ValueError("strategy atom keys must be unique")
        if any(not key.strip() or ":" not in key for key in self.strategy_atom_keys):
            raise ValueError("strategy atom keys must use dimension:value form")
        return self


class LessonIR(_StrictModel):
    lesson_id: str = Field(min_length=1, pattern=r"^synthetic-[a-z0-9-]+$")
    data_class: Literal["synthetic_fixture"]
    runtime_scope: Literal["synthetic_candidate"]
    candidate_only: Literal[True]
    atoms: tuple[LessonAtom, ...] = Field(min_length=1)
    claim: LessonClaim
    applies_when: tuple[ContextCode, ...] = Field(min_length=1)
    does_not_apply_when: tuple[ContextCode, ...] = Field(min_length=1)
    danger_if_misapplied: ContextCode
    support_matter_ids: tuple[str, ...] = Field(min_length=1)
    support_count: int = Field(ge=1)
    free_text: str | None

    @model_validator(mode="after")
    def candidate_is_exactly_scoped_and_unambiguous(self) -> "LessonIR":
        if not self.lesson_id.strip():
            raise ValueError("lesson_id must not be whitespace")
        if len({atom.dimension for atom in self.atoms}) != len(self.atoms):
            raise ValueError("a lesson may contain at most one atom per dimension")
        if len(set(self.support_matter_ids)) != len(self.support_matter_ids):
            raise ValueError("support matter IDs must be unique")
        if any(not matter_id.strip() for matter_id in self.support_matter_ids):
            raise ValueError("support matter IDs must not be whitespace")
        if any(
            not matter_id.startswith("synthetic-") or not matter_id.replace("-", "").isalnum()
            for matter_id in self.support_matter_ids
        ):
            raise ValueError("support matter IDs must use closed synthetic identifiers")
        if self.support_count != len(self.support_matter_ids):
            raise ValueError("support_count must equal the number of unique support matter IDs")
        return self

    def validate_against_policy(self, policy: SyntheticPolicyPlaceholders) -> None:
        if self.claim.before_code not in policy.allowed_claim_codes:
            raise ValueError("lesson before_code is not allowed by the supplied synthetic policy")
        if self.claim.after_code not in policy.allowed_claim_codes:
            raise ValueError("lesson after_code is not allowed by the supplied synthetic policy")
        contexts = (*self.applies_when, *self.does_not_apply_when, self.danger_if_misapplied)
        if any(code not in policy.allowed_context_codes for code in contexts):
            raise ValueError("lesson context code is not allowed by the supplied synthetic policy")

    def free_text_is_signal_free(self) -> bool:
        """Free text is advisory only; nonempty text cannot enter disclosure evaluation."""
        return self.free_text is None or not self.free_text.strip()
