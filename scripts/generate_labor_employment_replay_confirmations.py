from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.models import (  # noqa: E402
    ConfirmedParty,
    EvidenceRef,
    HumanConfirmation,
    SourceBundle,
)
from lawfirm_os_intake.segmenter import segment_bundle  # noqa: E402
from lawfirm_os_intake.util import digest_json, load_json, write_json  # noqa: E402


FIXTURE_ROOT = ROOT / "examples" / "synthetic" / "labor-employment"
SOURCE_ROOT = FIXTURE_ROOT / "executable-fixtures"
REPLAY_ROOT = FIXTURE_ROOT / "replay-inputs"

CASE_SPECS = {
    "discrimination-harassment-clean": {
        "family": "discrimination_harassment",
        "decision_term": "discrimination",
        "parties": [
            ("Maya Reed", "adverse_party"),
            ("Cedar Loom Manufacturing LLC", "prospective_represented_client"),
        ],
    },
    "wage-hour-clean": {
        "family": "wage_hour_flsa_state",
        "decision_term": "wage/hour",
        "parties": [
            ("Nora Alvarez", "adverse_party"),
            ("Riverbend Packaging LLC", "prospective_represented_client"),
        ],
    },
    "class-collective-clean": {
        "family": "class_collective_paga_representative",
        "decision_term": "class and collective",
        "parties": [
            ("Maya Chen", "adverse_party"),
            ("Atlas Retail Services LLC", "prospective_represented_client"),
        ],
    },
    "epli-carrier-clean": {
        "family": "epli_carrier_assignment",
        "decision_term": "EPLI",
        "parties": [
            ("Granite Shield EPLI", "insurance_carrier"),
            ("Granite Shield EPLI", "payer"),
            ("ClaimsBridge Administrators", "third_party_administrator"),
            ("Brightline Foods Inc.", "prospective_represented_client"),
            ("Talia Nguyen", "adverse_party"),
            ("Stone & Hart", "opposing_counsel"),
        ],
    },
}


def _evidence_ref(segment) -> EvidenceRef:
    signature = digest_json(
        {
            "source_id": segment.source_id,
            "start_offset": segment.start_offset,
            "end_offset": segment.end_offset,
            "sha256": segment.sha256,
        }
    )
    return EvidenceRef(
        source_id=segment.source_id,
        segment_id="segment_anchor_" + signature[len("sha256:") : len("sha256:") + 16],
        start_offset=segment.start_offset,
        end_offset=segment.end_offset,
        sha256=segment.sha256,
    )


def _first_ref_containing(segments, term: str) -> EvidenceRef:
    lowered = term.casefold()
    for segment in segments:
        if lowered in segment.text.casefold():
            return _evidence_ref(segment)
    raise ValueError(f"synthetic replay source has no segment containing {term!r}")


def _build_confirmation(case_id: str, spec: dict[str, object]) -> HumanConfirmation:
    source_path = SOURCE_ROOT / f"le-{case_id}.source-bundle.json"
    budget_path = REPLAY_ROOT / case_id / "legal_budget_proposal.json"
    bundle = SourceBundle.model_validate(load_json(source_path))
    budget = load_json(budget_path)
    segments = segment_bundle(bundle)
    confirmed_parties = [
        ConfirmedParty(
            name=name,
            confirmed_role=role,
            evidence_refs=[_first_ref_containing(segments, name)],
        )
        for name, role in spec["parties"]
    ]
    return HumanConfirmation(
        confirmation_id=budget["confirmation_id"],
        preflight_packet_id=budget["preflight_packet_id"],
        status="confirmed",
        confirmed_inbound_event="prospective_matter_intake",
        confirmed_matter_family=spec["family"],
        confirmed_representation_posture=budget["representation_posture"],
        confirmed_parties=confirmed_parties,
        reviewer_id="synthetic-human-review-fixture",
        reviewed_at="2026-07-18T12:00:00Z",
        notes=(
            "Synthetic POC confirmation fixture only. This is not a real human review, "
            "conflict clearance, engagement decision, matter opening, or budget approval."
        ),
        decision_evidence_refs=[_first_ref_containing(segments, str(spec["decision_term"]))],
    )


def build_confirmations() -> dict[str, HumanConfirmation]:
    return {case_id: _build_confirmation(case_id, spec) for case_id, spec in CASE_SPECS.items()}


def main() -> int:
    for case_id, confirmation in build_confirmations().items():
        target = REPLAY_ROOT / case_id / "human_confirmation.json"
        write_json(target, confirmation.model_dump(mode="json"))
        print(target.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
