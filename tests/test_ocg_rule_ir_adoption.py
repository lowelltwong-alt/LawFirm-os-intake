from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.guidelines import build_carrier_compliant_projection, load_carrier_guideline
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.ocg_rule_ir import (
    build_ocg_rule_ir_adoption_report,
    load_ocg_rule_ir,
    run_ocg_rule_ir_adoption_report,
)
from lawfirm_os_intake.util import load_json, write_json
from lawfirm_os_intake.workflow import run_preflight


RULE_IR_FIXTURE = "fixtures/synthetic/ocg/shared-rule-ir/harbor-point-alpha.ocg-rule-ir.json"


def _budget(repo_root, tmp_path):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = HumanConfirmation.model_validate(raw_confirmation)
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    return build_budget_proposal(packet, confirmation, profile)


def _budget_projection_and_rule_ir(repo_root, tmp_path):
    budget = _budget(repo_root, tmp_path)
    guideline_path = repo_root / "config/synthetic-carrier-guideline.yaml"
    guideline = load_carrier_guideline(guideline_path)
    projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref=str(guideline_path.relative_to(repo_root)).replace("\\", "/"),
        carrier_id=str(guideline.get("default_carrier_id", "synthetic-carrier-a")),
    )
    assert projection is not None
    rule_ir = load_ocg_rule_ir(repo_root / RULE_IR_FIXTURE)
    return budget, projection, rule_ir


def test_ocg_shared_rule_ir_fixture_is_read_only_candidate(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    before = budget.model_dump(mode="json")

    report = build_ocg_rule_ir_adoption_report(budget, projection, rule_ir)

    assert budget.model_dump(mode="json") == before
    assert report.status == "accepted_as_read_only_candidate", report.findings
    assert report.acceptance_gate_status == "accepted_with_restrictions"
    assert report.source_owner == "LawFirm-os-semantic-substrate"
    assert report.rule_count == 6
    assert report.impact_line_count == 6
    assert report.candidate_rule_id_count == 6
    assert report.canonical_rule_id_violation_count == 0
    assert report.read_only_violation_count == 0
    assert report.rewrite_budget_violation_count == 0
    assert report.real_guideline_or_rate_violation_count == 0
    assert report.proposed_total_before == budget.total_proposed_budget
    assert report.proposed_total_after == budget.total_proposed_budget
    assert report.carrier_compliant_total == projection.compliant_total
    assert report.projection_total_delta == projection.total_delta
    assert report.proposed_budget_preserved is True
    assert report.projection_rewrites_budget is False
    assert "budget rewrite" in report.display_banner["warning"]
    assert "do_not_author_canonical_ocg_rule_ids_in_intake" in report.prohibited_actions
    buckets = {line.impact_bucket for line in report.impact_lines}
    assert {
        "rate_cap_delta",
        "expense_cap_delta",
        "contingency_delta",
        "staffing_delta",
        "preapproval_dry_run",
        "metadata_only",
    } <= buckets


def test_ocg_ir_blocks_non_substrate_or_writable_source(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    bad = rule_ir.model_copy(
        update={
            "source_owner": "LawFirm-os-intake",
            "read_only_consumption": False,
            "not_promoted_canon": False,
        }
    )

    report = build_ocg_rule_ir_adoption_report(budget, projection, bad)

    assert report.status == "blocked"
    assert report.source_owner_violation_count == 1
    assert report.read_only_violation_count == 1
    assert {finding.finding_id for finding in report.findings} >= {
        "ocg_ir_source_owner_not_substrate",
        "ocg_ir_not_read_only",
        "ocg_ir_claims_canonical_authority",
    }


def test_ocg_ir_blocks_canonical_rule_ids_and_budget_rewrites(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    bad_rule = rule_ir.rules[0].model_copy(
        update={
            "rule_id": "ocg:real-looking-rule-001",
            "candidate_only": False,
            "not_canonical_rule_id": False,
            "rewrites_budget": True,
        }
    )
    bad = rule_ir.model_copy(update={"rules": [bad_rule, *rule_ir.rules[1:]]})

    report = build_ocg_rule_ir_adoption_report(budget, projection, bad)

    assert report.status == "blocked"
    assert report.canonical_rule_id_violation_count == 1
    assert report.rewrite_budget_violation_count == 1
    assert {finding.finding_id for finding in report.findings} >= {
        "canonical_or_unprefixed_ocg_rule_id",
        "ocg_rule_claims_non_candidate_authority",
        "ocg_rule_attempts_budget_rewrite",
    }


def test_ocg_ir_blocks_real_guideline_or_rate_material(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    bad_rule = rule_ir.rules[0].model_copy(
        update={"no_real_guideline_text": False, "no_real_rate_value": False}
    )
    bad = rule_ir.model_copy(
        update={
            "no_real_guidelines": False,
            "no_real_rates": False,
            "contains_real_carrier_data": True,
            "rules": [bad_rule, *rule_ir.rules[1:]],
        }
    )

    report = build_ocg_rule_ir_adoption_report(budget, projection, bad)

    assert report.status == "blocked"
    assert report.real_guideline_or_rate_violation_count == 2
    assert {finding.finding_id for finding in report.findings} >= {
        "ocg_ir_contains_real_guideline_or_rate_material",
        "ocg_rule_contains_real_guideline_or_rate_material",
    }


def test_ocg_ir_blocks_projection_budget_mismatch(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    bad_projection = projection.model_copy(
        update={"proposed_total": (budget.total_proposed_budget or 0) + 1}
    )

    report = build_ocg_rule_ir_adoption_report(budget, bad_projection, rule_ir)

    assert report.status == "blocked"
    assert report.budget_projection_mismatch_count == 1
    assert {finding.finding_id for finding in report.findings} >= {
        "projection_proposed_total_mismatch"
    }


def test_ocg_rule_ir_cli_writes_report_and_fails_closed(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    budget_path = tmp_path / "budget.json"
    projection_path = tmp_path / "projection.json"
    good_rule_ir_path = tmp_path / "good-rule-ir.json"
    bad_rule_ir_path = tmp_path / "bad-rule-ir.json"
    write_json(budget_path, budget.model_dump(mode="json"))
    write_json(projection_path, projection.model_dump(mode="json"))
    write_json(good_rule_ir_path, rule_ir.model_dump(mode="json"))
    write_json(
        bad_rule_ir_path,
        rule_ir.model_copy(update={"read_only_consumption": False}).model_dump(mode="json"),
    )

    exit_code = main(
        [
            "adopt-ocg-rule-ir",
            "--budget-proposal",
            str(budget_path),
            "--carrier-projection",
            str(projection_path),
            "--ocg-rule-ir",
            str(good_rule_ir_path),
            "--out-dir",
            str(tmp_path / "good-run"),
        ]
    )
    assert exit_code == 0
    saved = load_json(tmp_path / "good-run" / "ocg_rule_ir_adoption_report.json")
    assert saved["status"] == "accepted_as_read_only_candidate"
    assert saved["not_authorized_for_client_submission"] is True

    blocked_exit_code = main(
        [
            "adopt-ocg-rule-ir",
            "--budget-proposal",
            str(budget_path),
            "--carrier-projection",
            str(projection_path),
            "--ocg-rule-ir",
            str(bad_rule_ir_path),
            "--out-dir",
            str(tmp_path / "bad-run"),
        ]
    )
    assert blocked_exit_code == 2
    blocked = load_json(tmp_path / "bad-run" / "ocg_rule_ir_adoption_report.json")
    assert blocked["status"] == "blocked"
    assert blocked["read_only_violation_count"] == 1


def test_ocg_rule_ir_runner_returns_local_candidate_report(repo_root, tmp_path):
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    budget_path = tmp_path / "budget.json"
    projection_path = tmp_path / "projection.json"
    rule_ir_path = tmp_path / "rule-ir.json"
    write_json(budget_path, budget.model_dump(mode="json"))
    write_json(projection_path, projection.model_dump(mode="json"))
    write_json(rule_ir_path, rule_ir.model_dump(mode="json"))

    loaded_rule_ir, report, run_dir = run_ocg_rule_ir_adoption_report(
        budget_path,
        projection_path,
        rule_ir_path,
        tmp_path / "run",
    )

    assert loaded_rule_ir == rule_ir
    assert report.status == "accepted_as_read_only_candidate"
    assert (run_dir / "ocg_rule_ir_adoption_report.json").is_file()
    assert (run_dir / "run_ledger.jsonl").is_file()
