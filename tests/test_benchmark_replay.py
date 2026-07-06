from lawfirm_os_intake.benchmarks import (
    BENCHMARK_REPLAY_REPORT_FILENAME,
    effective_benchmark_grade,
    run_benchmark_replay_audit,
)
from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import BenchmarkReplayReport, HumanConfirmation, RateBenchmarkCell
from lawfirm_os_intake.util import digest_json, load_json, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


SNAPSHOT_PATH = "examples/synthetic/benchmarks/synthetic-rate-benchmark-snapshot.json"


def _budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw_confirmation),
    )
    confirmation_path = tmp_path / "confirmation.json"
    write_json(confirmation_path, confirmation.model_dump(mode="json"))
    proposal, _run_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return proposal


def _hours_only_budget(tmp_path, repo_root):
    packet, _preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "hours-only-preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw_confirmation),
    )
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    profile["synthetic_hourly_rates"] = {}
    return build_budget_proposal(packet, confirmation, profile)


def test_benchmark_replay_accepts_valid_context_refs(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget["lines"][0]["estimate_basis"] = "benchmark_cell"
    budget["lines"][0]["estimate_basis_refs"] = ["benchmark-cell:nv:partner:p50:2026"]
    budget_path = tmp_path / "budget-with-benchmark-context.json"
    write_json(budget_path, budget)

    report, run_dir = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=repo_root / SNAPSHOT_PATH,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )
    persisted = BenchmarkReplayReport.model_validate(
        load_json(run_dir / BENCHMARK_REPLAY_REPORT_FILENAME)
    )

    assert report.status == "benchmark_replay_ready_for_review"
    assert persisted.snapshot_cell_count == 3
    assert persisted.failed_cell_check_count == 0
    assert persisted.failed_budget_line_check_count == 0
    assert persisted.missing_benchmark_ref_count == 0
    assert persisted.rate_laundering_attempt_count == 0
    assert persisted.benchmark_cells_used_as_rate_authority is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    first_line = persisted.budget_lines[0]
    assert first_line.rate_trace_status == "benchmark_context_ref_valid"
    assert first_line.rate_source in {"synthetic_profile", "authorized_profile"}


def test_benchmark_replay_cli_writes_ready_report(tmp_path, repo_root, capsys):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget_path = tmp_path / "budget.json"
    write_json(budget_path, budget)

    result = main(
        [
            "audit-benchmark-replay",
            "--budget-proposal",
            str(budget_path),
            "--benchmark-snapshot",
            str(repo_root / SNAPSHOT_PATH),
            "--out-dir",
            str(tmp_path / "benchmark-replay-cli"),
            "--as-of-date",
            "2026-07-06",
        ]
    )
    captured = capsys.readouterr().out
    persisted = load_json(tmp_path / "benchmark-replay-cli" / BENCHMARK_REPLAY_REPORT_FILENAME)

    assert result == 0
    assert "benchmark_replay_ready_for_review" in captured
    assert persisted["budget_submission_authorized"] is False
    assert persisted["lake_write_performed"] is False
    assert persisted["sqlite_write_performed"] is False


def test_benchmark_replay_blocks_missing_context_ref(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget["lines"][0]["estimate_basis"] = "benchmark_cell"
    budget["lines"][0]["estimate_basis_refs"] = ["benchmark-cell:missing"]
    budget_path = tmp_path / "budget-missing-benchmark-context.json"
    write_json(budget_path, budget)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=repo_root / SNAPSHOT_PATH,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    assert report.status == "blocked_by_benchmark_replay"
    assert report.failed_budget_line_check_count == 1
    assert report.missing_benchmark_ref_count == 1
    assert report.budget_lines[0].rate_trace_status == "benchmark_context_missing"
    assert report.budget_lines[0].missing_benchmark_refs == ["benchmark-cell:missing"]


def test_benchmark_replay_blocks_rejected_context_ref(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget["lines"][0]["estimate_basis"] = "benchmark_cell"
    budget["lines"][0]["estimate_basis_refs"] = ["benchmark-cell:nv:partner:p50:2026"]
    budget_path = tmp_path / "budget-rejected-benchmark-context.json"
    write_json(budget_path, budget)
    snapshot = load_json(repo_root / SNAPSHOT_PATH)
    snapshot["cells"][0]["human_grading_status"] = "rejected"
    _refresh_pinned_hash(snapshot)
    snapshot_path = tmp_path / "snapshot-rejected-cell.json"
    write_json(snapshot_path, snapshot)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=snapshot_path,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    assert report.status == "blocked_by_benchmark_replay"
    assert report.missing_benchmark_ref_count == 1
    rejected_cell = next(
        cell
        for cell in report.cells
        if cell.benchmark_cell_id == "benchmark-cell:nv:partner:p50:2026"
    )
    assert rejected_cell.status == "ignored"
    assert "benchmark_cell_rejected" in rejected_cell.issue_codes


def test_benchmark_replay_blocks_snapshot_hash_mismatch(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget_path = tmp_path / "budget.json"
    write_json(budget_path, budget)
    snapshot = load_json(repo_root / SNAPSHOT_PATH)
    snapshot["cells"][0]["value"] = 999.0
    snapshot_path = tmp_path / "snapshot-hash-mismatch.json"
    write_json(snapshot_path, snapshot)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=snapshot_path,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    assert report.status == "blocked_by_benchmark_replay"
    assert _check(report, "benchmark_snapshot_hash_matches_content").status == "failed"


def test_benchmark_replay_refuses_real_negotiated_rate_snapshot(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget_path = tmp_path / "budget.json"
    write_json(budget_path, budget)
    snapshot = load_json(repo_root / SNAPSHOT_PATH)
    snapshot["contains_real_negotiated_rates"] = True
    _refresh_pinned_hash(snapshot)
    snapshot_path = tmp_path / "snapshot-real-rates.json"
    write_json(snapshot_path, snapshot)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=snapshot_path,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    assert report.status == "blocked_by_benchmark_replay"
    assert _check(report, "benchmark_snapshot_real_rates_refused").status == "failed"
    assert "benchmark_snapshot_invalid" in report.candidate_exception_lake_labels


def test_benchmark_replay_refuses_carrier_panel_candidate_cell(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget["lines"][0]["estimate_basis"] = "benchmark_cell"
    budget["lines"][0]["estimate_basis_refs"] = ["benchmark-cell:nv:partner:p50:2026"]
    budget_path = tmp_path / "budget-carrier-panel-context.json"
    write_json(budget_path, budget)
    snapshot = load_json(repo_root / SNAPSHOT_PATH)
    snapshot["cells"][0]["benchmark_type"] = "carrier_panel_candidate"
    _refresh_pinned_hash(snapshot)
    snapshot_path = tmp_path / "snapshot-carrier-panel-candidate.json"
    write_json(snapshot_path, snapshot)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=snapshot_path,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    refused_cell = next(
        cell
        for cell in report.cells
        if cell.benchmark_cell_id == "benchmark-cell:nv:partner:p50:2026"
    )
    assert report.status == "blocked_by_benchmark_replay"
    assert report.failed_cell_check_count == 1
    assert report.missing_benchmark_ref_count == 1
    assert refused_cell.status == "failed"
    assert "benchmark_cell_carrier_panel_candidate_refused" in refused_cell.issue_codes


def test_benchmark_replay_blocks_benchmark_cell_rate_laundering(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget["lines"][0]["rate_source"] = "benchmark_cell"
    budget["calculation_report"]["rate_sources"] = ["benchmark_cell"]
    budget_path = tmp_path / "budget-launder-attempt.json"
    write_json(budget_path, budget)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=repo_root / SNAPSHOT_PATH,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    assert report.status == "blocked_by_benchmark_replay"
    assert report.rate_laundering_attempt_count == 2
    assert _check(report, "no_benchmark_cell_as_rate_source").status == "failed"
    assert any(
        line.rate_trace_status == "benchmark_launder_attempt" for line in report.budget_lines
    )


def test_benchmark_replay_keeps_hours_only_budget_from_using_benchmark_rates(
    tmp_path,
    repo_root,
):
    budget = _hours_only_budget(tmp_path, repo_root).model_dump(mode="json")
    budget_path = tmp_path / "hours-only-budget.json"
    write_json(budget_path, budget)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=repo_root / SNAPSHOT_PATH,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    assert budget["pricing_status"] == "hours_only"
    assert budget["total_proposed_budget"] is None
    assert all(line["hourly_rate"] is None for line in budget["lines"])
    assert report.status == "benchmark_replay_ready_for_review"
    assert report.rate_laundering_attempt_count == 0
    assert all(line.rate_trace_status == "hours_only_no_rate" for line in report.budget_lines)


def test_benchmark_replay_ignores_low_confidence_cells_without_blocking(
    tmp_path,
    repo_root,
):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget_path = tmp_path / "budget.json"
    write_json(budget_path, budget)
    snapshot = load_json(repo_root / SNAPSHOT_PATH)
    snapshot["cells"][0]["grade"] = "C"
    _refresh_pinned_hash(snapshot)
    snapshot_path = tmp_path / "snapshot-weak-grade.json"
    write_json(snapshot_path, snapshot)

    report, _ = run_benchmark_replay_audit(
        budget_proposal_path=budget_path,
        benchmark_snapshot_path=snapshot_path,
        out_dir=tmp_path / "benchmark-replay",
        as_of_date="2026-07-06",
    )

    weak_cell = next(
        cell
        for cell in report.cells
        if cell.benchmark_cell_id == "benchmark-cell:nv:partner:p50:2026"
    )
    assert report.status == "benchmark_replay_ready_for_review"
    assert weak_cell.status == "ignored"
    assert weak_cell.effective_grade == "C"
    assert weak_cell.band_flag_authorized is False


def test_benchmark_effective_grade_downgrades_stale_a_grade():
    cell = RateBenchmarkCell(
        benchmark_cell_id="cell:stale",
        jurisdiction="NV",
        role="partner",
        experience_band="senior",
        year=2023,
        percentile="p50",
        value=450,
        benchmark_type="synthetic_candidate",
        source_url="https://example.invalid/synthetic",
        retrieved_at="2026-07-06T00:00:00Z",
        observation_period_end="2023-12-31",
        page_sha256="sha256:" + "d" * 64,
        quote_span="synthetic span",
        license_note="synthetic",
        proxy_bias_note="proxy only",
        grade="A",
        human_grading_status="reviewed",
    )

    assert effective_benchmark_grade(cell, "2026-07-06")[0] == "B"
    assert effective_benchmark_grade(cell, "2028-03-01")[0] == "C"


def _refresh_pinned_hash(snapshot):
    body = dict(snapshot)
    body.pop("pinned_hash", None)
    snapshot["pinned_hash"] = digest_json(body)


def _check(report, check_id):
    return next(check for check in report.checks if check.check_id == check_id)
