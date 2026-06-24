from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import build_conflict_seed, run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def test_conflict_seed_emits_normalized_grouped_terms(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    seed = build_conflict_seed(packet, _confirmation(packet, repo_root))
    groups = {term.group for term in seed.normalized_search_terms}
    assert "prospective_represented_client" in groups
    assert "instructing_source" in groups
    assert all(
        term.normalized_term == term.normalized_term.casefold()
        for term in seed.normalized_search_terms
    )
    assert all(term.evidence_refs for term in seed.normalized_search_terms)
    assert seed.conclusion == "no_conflict_conclusion"


def test_budget_has_ranges_calculation_report_and_review_form(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    assert budget.calculation_report is not None
    assert budget.calculation_report.total_hours > 0
    assert all(line.estimated_hours_min is not None for line in budget.lines)
    assert all(line.estimated_hours_max is not None for line in budget.lines)
    assert all(line.rate_is_synthetic for line in budget.lines)
    review_text = (budget_dir / "legal_budget_review_form.md").read_text(encoding="utf-8")
    assert "## Budget Lines" in review_text
    assert "rate source: synthetic_profile" in review_text
    assert "synthetic rate: True" in review_text
    assert "evidence: syn-email-001/" in review_text
    assert "] sha=sha256:" in review_text
    assert "## Evidence-Bound Budget Supports" in review_text
    assert "## Submission Boundary" in review_text
    assert "Approval state: proposed_for_human_review" in review_text
    assert "Client/carrier submission authorized: False" in review_text
    assert "Human budget review remains required" in review_text


def test_hours_only_report_preserves_no_rate_invention(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    profile["synthetic_hourly_rates"] = {}
    budget = build_budget_proposal(packet, _confirmation(packet, repo_root), profile)
    assert budget.pricing_status == "hours_only"
    assert budget.calculation_report is not None
    assert budget.calculation_report.unpriced_line_count == len(budget.lines)
    assert budget.total_proposed_budget is None
