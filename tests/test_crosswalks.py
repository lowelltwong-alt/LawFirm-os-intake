import pytest

from lawfirm_os_intake.crosswalks import (
    audit_crosswalks,
    load_crosswalk,
    run_crosswalk_audit_report,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    Crosswalk,
    CrosswalkAuditReport,
    CrosswalkEntry,
    CrosswalkSourceProvenance,
)
from lawfirm_os_intake.util import load_json

FIXTURE_DIR = "fixtures/synthetic/crosswalks"
FIXTURES = [
    "l-and-e-matter-families-to-sali-lmss.json",
    "party-roles-to-sali-lmss.json",
    "budget-phase-task-expense-to-utbms-ledes.json",
    "rejection-families-to-ledes-error-dimensions.json",
]


def _path(repo_root, name):
    return repo_root / FIXTURE_DIR / name


def _all_crosswalks(repo_root):
    return [load_crosswalk(_path(repo_root, name)) for name in FIXTURES]


def _provenance(system="sali_lmss"):
    base = {
        "sali_lmss": {
            "source_url": "https://github.com/sali-legal/LMSS",
            "source_version_or_date": "LMSS.owl (candidate reference only)",
            "license_terms_note": "SALI LMSS; verify license before promotion.",
        },
        "utbms_ledes": {
            "source_url": "https://utbms.com/",
            "source_version_or_date": "UTBMS code sets (candidate reference only)",
            "license_terms_note": "UTBMS/LEDES; verify before promotion.",
        },
        "ledes_error_dimension": {
            "source_url": "https://ledes.org/",
            "source_version_or_date": "LEDES error dimensions (candidate reference only)",
            "license_terms_note": "LEDES; verify before promotion.",
        },
    }[system]
    return CrosswalkSourceProvenance(
        source_url=base["source_url"],
        source_version_or_date=base["source_version_or_date"],
        retrieved_at="2026-07-09T00:00:00Z",
        content_sha256=None,
        license_terms_note=base["license_terms_note"],
        review_status="candidate_unverified",
    )


def _entry(
    local_term,
    kind,
    target,
    system,
    confidence,
    provenance,
    *,
    candidate_only=True,
):
    return CrosswalkEntry(
        local_term=local_term,
        local_term_kind=kind,
        candidate_target=target,
        candidate_target_system=system,
        confidence=confidence,
        provenance=provenance,
        review_status="candidate_unverified",
        notes="synthetic test entry",
        candidate_only=candidate_only,
    )


def test_all_four_synthetic_crosswalks_load_and_validate(repo_root):
    crosswalks = _all_crosswalks(repo_root)
    assert len(crosswalks) == 4
    kinds = {cw.kind for cw in crosswalks}
    assert kinds == {
        "matter_family_to_sali",
        "party_role_to_sali",
        "budget_code_to_utbms_ledes",
        "rejection_family_to_ledes_error_dimension",
    }
    for cw in crosswalks:
        assert cw.candidate_only is True
        assert cw.not_promoted_canon is True
        assert cw.data_origin == "synthetic"


def test_crosswalk_round_trips_through_model_dump(repo_root):
    cw = load_crosswalk(_path(repo_root, "l-and-e-matter-families-to-sali-lmss.json"))
    rerun = Crosswalk.model_validate(cw.model_dump(mode="json"))
    assert rerun == cw


def test_audit_passes_for_all_synthetic_crosswalks(repo_root):
    crosswalks = _all_crosswalks(repo_root)
    report = audit_crosswalks(crosswalks)
    assert isinstance(report, CrosswalkAuditReport)
    assert report.status == "passed", report.findings
    assert report.canonical_claim_count == 0
    assert report.candidate_only_violation_count == 0
    assert report.entries_missing_provenance_count == 0
    assert report.entries_missing_review_status_count == 0
    assert report.guessed_mapping_count == 0
    assert report.crosswalk_count == 4
    assert report.entry_count > 0
    assert report.mapped_entry_count > 0
    assert report.unmapped_entry_count > 0
    assert report.not_promoted_canon is True
    assert report.candidate_only is True
    assert report.acceptance_gate_status == "accepted_with_restrictions"
    assert report.unverified_pinned_target_count == 0
    assert report.candidate_target_prefix_violation_count == 0
    assert report.workflow_dependency_violation_count == 0
    assert report.not_authorized_for_canonical_use is True
    assert report.not_authorized_for_budget_logic is True
    assert report.not_authorized_for_rejection_logic is True
    assert (
        "not legal, billing, SALI, LEDES, UTBMS, or substrate canon"
        in (report.display_banner["warning"])
    )
    # The prohibited actions must explicitly forbid treating local crosswalks as canon.
    assert "do_not_treat_local_crosswalk_as_canonical" in report.prohibited_actions
    assert "do_not_use_crosswalks_as_budget_or_rejection_business_logic" in (
        report.prohibited_actions
    )


def test_no_local_crosswalk_can_be_treated_as_canonical():
    prov = _provenance("sali_lmss")
    entry = _entry("x", "matter_family", "sali_lmss_candidate:X", "sali_lmss", "medium", prov)
    cw = Crosswalk(
        crosswalk_id="xwalk-bad-canon",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[entry],
        candidate_only=True,
        not_promoted_canon=False,  # violation
        data_origin="synthetic",
    )
    report = audit_crosswalks([cw])
    assert report.status == "blocked"
    assert report.canonical_claim_count == 1
    ids = {f.finding_id for f in report.findings}
    assert "not_promoted_canon_must_be_true" in ids


def test_entry_missing_provenance_blocks():
    prov = _provenance("sali_lmss")
    bad_prov = prov.model_copy(update={"source_url": "   ", "license_terms_note": ""})
    entry = _entry("x", "matter_family", "sali_lmss_candidate:X", "sali_lmss", "medium", bad_prov)
    cw = Crosswalk(
        crosswalk_id="xwalk-bad-prov",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[entry],
    )
    report = audit_crosswalks([cw])
    assert report.status == "blocked"
    assert report.entries_missing_provenance_count == 1


def test_entry_missing_review_status_blocks():
    prov = _provenance("sali_lmss")
    bad_prov = prov.model_copy(update={"review_status": "unknown"})
    entry = _entry("x", "matter_family", "sali_lmss_candidate:X", "sali_lmss", "medium", bad_prov)
    cw = Crosswalk(
        crosswalk_id="xwalk-bad-review",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[entry],
    )
    report = audit_crosswalks([cw])
    assert report.status == "blocked"
    assert report.entries_missing_review_status_count == 1


def test_unmapped_terms_stay_explicit_not_guessed():
    prov = _provenance("sali_lmss")
    # Guessed target on an unmapped entry must block.
    guessed = CrosswalkEntry(
        local_term="broad_thing",
        local_term_kind="matter_family",
        candidate_target="sali_lmss_candidate:SomeGuess",
        candidate_target_system="unmapped",
        confidence="unknown",
        provenance=prov,
        review_status="candidate_unverified",
        notes="should not guess",
        candidate_only=True,
    )
    cw = Crosswalk(
        crosswalk_id="xwalk-guessed-unmapped",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[guessed],
    )
    report = audit_crosswalks([cw])
    assert report.status == "blocked"
    assert report.guessed_mapping_count >= 1
    ids = {f.finding_id for f in report.findings}
    assert "unmapped_entry_has_guessed_target" in ids

    # Correct explicit unknown passes.
    explicit = guessed.model_copy(
        update={"candidate_target": "unmapped", "candidate_target_system": "unmapped"}
    )
    cw_ok = cw.model_copy(update={"entries": [explicit], "crosswalk_id": "xwalk-explicit-unknown"})
    report_ok = audit_crosswalks([cw_ok])
    assert report_ok.status == "passed", report_ok.findings
    assert report_ok.unmapped_entry_count == 1


def test_high_confidence_unverified_mapped_entry_is_a_guessed_mapping():
    prov = _provenance("utbms_ledes")
    entry = _entry(
        "E310",
        "task_id",
        "utbms_ledes_candidate:task-L310-family-document-discovery",
        "utbms_ledes",
        "high",  # high confidence while candidate_unverified -> guessed
        prov,
    )
    cw = Crosswalk(
        crosswalk_id="xwalk-high-conf-unverified",
        kind="budget_code_to_utbms_ledes",
        target_system="utbms_ledes",
        source_provenance=prov,
        entries=[entry],
    )
    report = audit_crosswalks([cw])
    assert report.status == "blocked"
    assert report.guessed_mapping_count == 1
    ids = {f.finding_id for f in report.findings}
    assert "guessed_mapping_high_confidence_unverified" in ids


def test_unverified_mapped_entry_must_keep_candidate_target_prefix():
    prov = _provenance("sali_lmss")
    entry = _entry(
        "employment_litigation_defense",
        "matter_family",
        "EmploymentLitigation",
        "sali_lmss",
        "medium",
        prov,
    )
    cw = Crosswalk(
        crosswalk_id="xwalk-prefix-violation",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[entry],
    )

    report = audit_crosswalks([cw])

    assert report.status == "blocked"
    assert report.acceptance_gate_status == "blocked"
    assert report.candidate_target_prefix_violation_count == 1
    ids = {f.finding_id for f in report.findings}
    assert "unverified_candidate_target_prefix_violation" in ids


def test_unverified_sali_iri_or_utbms_code_blocks_as_pinned_target():
    sali_prov = _provenance("sali_lmss")
    utbms_prov = _provenance("utbms_ledes")
    sali_entry = _entry(
        "employment_litigation_defense",
        "matter_family",
        "https://lmss.sali.org/R123456",
        "sali_lmss",
        "medium",
        sali_prov,
    )
    utbms_entry = _entry("E310", "task_id", "L310", "utbms_ledes", "low", utbms_prov)
    report = audit_crosswalks(
        [
            Crosswalk(
                crosswalk_id="xwalk-pinned-sali",
                kind="matter_family_to_sali",
                target_system="sali_lmss",
                source_provenance=sali_prov,
                entries=[sali_entry],
            ),
            Crosswalk(
                crosswalk_id="xwalk-pinned-utbms",
                kind="budget_code_to_utbms_ledes",
                target_system="utbms_ledes",
                source_provenance=utbms_prov,
                entries=[utbms_entry],
            ),
        ]
    )

    assert report.status == "blocked"
    assert report.unverified_pinned_target_count == 2
    assert report.candidate_target_prefix_violation_count == 2
    assert {f.finding_id for f in report.findings} >= {
        "unverified_pinned_standard_target",
        "unverified_candidate_target_prefix_violation",
    }


def test_human_reviewed_pinned_target_is_allowed_only_as_review_evidence():
    prov = _provenance("sali_lmss").model_copy(update={"review_status": "human_reviewed"})
    entry = _entry(
        "employment_litigation_defense",
        "matter_family",
        "https://lmss.sali.org/R123456",
        "sali_lmss",
        "high",
        prov,
    ).model_copy(update={"review_status": "human_reviewed"})
    cw = Crosswalk(
        crosswalk_id="xwalk-reviewed-pinned",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[entry],
    )

    report = audit_crosswalks([cw])

    assert report.status == "passed", report.findings
    assert report.acceptance_gate_status == "accepted_with_restrictions"
    assert report.unverified_pinned_target_count == 0
    assert report.not_authorized_for_canonical_use is True


def test_crosswalks_cannot_be_used_as_budget_or_rejection_business_logic(tmp_path):
    src = tmp_path / "src" / "lawfirm_os_intake"
    src.mkdir(parents=True)
    (src / "budget.py").write_text(
        "from lawfirm_os_intake.crosswalks import load_crosswalk\n"
        "def build_budget():\n"
        "    return load_crosswalk('fixtures/synthetic/crosswalks/example.json')\n",
        encoding="utf-8",
    )
    prov = _provenance("utbms_ledes")
    entry = _entry(
        "E310",
        "task_id",
        "utbms_ledes_candidate:task-family-L3xx-discovery",
        "utbms_ledes",
        "low",
        prov,
    )
    cw = Crosswalk(
        crosswalk_id="xwalk-business-logic",
        kind="budget_code_to_utbms_ledes",
        target_system="utbms_ledes",
        source_provenance=prov,
        entries=[entry],
    )

    report = audit_crosswalks([cw], repo_root=tmp_path)

    assert report.status == "blocked"
    assert report.workflow_dependency_violation_count == 1
    assert "crosswalk_used_as_business_logic_dependency" in {
        finding.finding_id for finding in report.findings
    }


def test_human_reviewed_high_confidence_entry_is_allowed():
    prov = _provenance("sali_lmss")
    entry = _entry(
        "employment_litigation_defense",
        "matter_family",
        "sali_lmss_candidate:EmploymentLitigation",
        "sali_lmss",
        "high",
        prov,
    )
    entry = entry.model_copy(update={"review_status": "human_reviewed"})
    cw = Crosswalk(
        crosswalk_id="xwalk-reviewed",
        kind="matter_family_to_sali",
        target_system="sali_lmss",
        source_provenance=prov,
        entries=[entry],
    )
    report = audit_crosswalks([cw])
    assert report.status == "passed", report.findings


def test_data_origin_non_synthetic_blocks():
    prov = _provenance("sali_lmss")
    entry = _entry("x", "matter_family", "sali_lmss_candidate:X", "sali_lmss", "medium", prov)
    # Direct construction with a disallowed literal must raise.
    with pytest.raises(Exception):
        Crosswalk(
            crosswalk_id="xwalk-bad-origin-2",
            kind="matter_family_to_sali",
            target_system="sali_lmss",
            source_provenance=prov,
            entries=[entry],
            data_origin="public_reference",  # type: ignore[arg-type]
        )


def test_run_crosswalk_audit_report_writes_artifacts(tmp_path, repo_root):
    paths = [str(_path(repo_root, name)) for name in FIXTURES]
    crosswalks, report, run_dir = run_crosswalk_audit_report(paths, tmp_path)
    assert report.status == "passed", report.findings
    assert (run_dir / "crosswalk_audit_report.json").exists()
    persisted = CrosswalkAuditReport.model_validate(
        load_json(run_dir / "crosswalk_audit_report.json")
    )
    assert persisted.status == "passed"
    assert persisted.acceptance_gate_status == "accepted_with_restrictions"
    assert persisted.display_banner["accepted_with_restrictions"] is True
    assert persisted.report_id == report.report_id
    assert (run_dir / "run_ledger.jsonl").exists()


def test_cli_crosswalk_audit_fails_closed_when_gate_blocks(tmp_path, capsys):
    prov = _provenance("utbms_ledes")
    entry = _entry("E310", "task_id", "L310", "utbms_ledes", "low", prov)
    cw = Crosswalk(
        crosswalk_id="xwalk-cli-blocked",
        kind="budget_code_to_utbms_ledes",
        target_system="utbms_ledes",
        source_provenance=prov,
        entries=[entry],
    )
    path = tmp_path / "blocked-crosswalk.json"
    path.write_text(cw.model_dump_json(indent=2), encoding="utf-8")

    exit_code = main(
        [
            "crosswalk-audit",
            "--crosswalk",
            str(path),
            "--out-dir",
            str(tmp_path / "audit"),
        ]
    )
    payload = load_json(tmp_path / "audit" / "crosswalk_audit_report.json")
    captured = capsys.readouterr().out

    assert exit_code == 2
    assert payload["status"] == "blocked"
    assert payload["unverified_pinned_target_count"] == 1
    assert '"acceptance_gate_status": "blocked"' in captured
