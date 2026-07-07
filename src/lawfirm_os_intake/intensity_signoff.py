from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable

from .budget import build_budget_proposal
from .confirmation import bind_confirmation_to_packet_evidence
from .context import load_profile
from .drivers import (
    build_effective_intensity_multiplier_policy,
    load_driver_policy,
    resolve_case_drivers,
)
from .models import (
    HumanConfirmation,
    IntensityNormalizationDemoTotal,
    IntensityNormalizationFamilySignoff,
    IntensityNormalizationMultiplierRow,
    IntensityNormalizationSignoffGateCheck,
    IntensityNormalizationSignoffGateReport,
    IntensityNormalizationSignoffReport,
)
from .rates import load_rate_card, resolve_role_rates
from .util import digest_json, load_json, now_iso, write_json
from .workflow import run_preflight

DEFAULT_SIGNOFF_PATH = Path("docs/governance/intensity_normalization_signoff.json")


@dataclass(frozen=True)
class IntensitySignoffDemoCase:
    demo_case_id: str
    input_path: Path
    confirmation_path: Path


def _stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{prefix}_{sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _repo_root_from_policy(policy_path: Path) -> Path:
    for parent in [policy_path.parent, *policy_path.parents]:
        if (parent / "examples" / "synthetic").is_dir() and (parent / "context").is_dir():
            return parent
    return Path.cwd()


def _resolve_repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _find_repo_file(start: Path, ref: str) -> Path | None:
    for parent in [start, *start.parents]:
        candidate = parent / ref
        if candidate.is_file():
            return candidate
    return None


def _default_demo_cases(repo_root: Path) -> list[IntensitySignoffDemoCase]:
    specs = [
        (
            "carrier-assignment-medmal",
            "examples/synthetic/inbound/carrier-assignment-medmal.json",
            "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json",
        ),
        (
            "carrier-assignment-auto-bi",
            "examples/synthetic/inbound/carrier-assignment-auto-bi.json",
            "examples/synthetic/confirmations/carrier-assignment-auto-bi.confirmation-template.json",
        ),
    ]
    cases: list[IntensitySignoffDemoCase] = []
    for case_id, input_ref, confirmation_ref in specs:
        input_path = repo_root / input_ref
        confirmation_path = repo_root / confirmation_ref
        if input_path.is_file() and confirmation_path.is_file():
            cases.append(
                IntensitySignoffDemoCase(
                    demo_case_id=case_id,
                    input_path=input_path,
                    confirmation_path=confirmation_path,
                )
            )
    return cases


def parse_demo_case(value: str, repo_root: str | Path = ".") -> IntensitySignoffDemoCase:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3 or any(not part for part in parts):
        raise ValueError("--demo-case must be formatted as case_id,input_path,confirmation_path")
    root = Path(repo_root)
    return IntensitySignoffDemoCase(
        demo_case_id=parts[0],
        input_path=_resolve_repo_path(root, parts[1]),
        confirmation_path=_resolve_repo_path(root, parts[2]),
    )


def _policy_with_normalization(policy: dict[str, Any], mode: str) -> dict[str, Any]:
    result = deepcopy(policy)
    intensity_policy = result.setdefault("intensity_multiplier_policy", {})
    if not isinstance(intensity_policy, dict):
        raise ValueError("intensity_multiplier_policy must be a mapping")
    intensity_policy["normalization"] = mode
    return result


def _policy_mode(policy: dict[str, Any]) -> str:
    intensity_policy = policy.get("intensity_multiplier_policy", {})
    if not isinstance(intensity_policy, dict):
        return "raw"
    return str(intensity_policy.get("normalization", "raw"))


def _phase_ids(template: dict[str, Any], raw_intensity_policy: dict[str, Any]) -> list[str]:
    phases = {
        str(phase.get("phase_id"))
        for phase in template.get("phases", [])
        if isinstance(phase, dict) and phase.get("phase_id") is not None
    }
    effects = raw_intensity_policy.get("effects", {})
    if isinstance(effects, dict):
        for value_effects in effects.values():
            if not isinstance(value_effects, dict):
                continue
            for effect in value_effects.values():
                if isinstance(effect, dict):
                    phases.update(str(phase_id) for phase_id in effect.get("phase_ids", []))
    return sorted(phases)


def _raw_multiplier_for_phase(
    effects_by_driver: dict[str, Any],
    driver_id: str,
    tier: str | None,
    phase_id: str,
) -> float:
    if tier is None:
        return 1.0
    driver_effects = effects_by_driver.get(driver_id)
    if not isinstance(driver_effects, dict):
        return 1.0
    effect = driver_effects.get(str(tier))
    if not isinstance(effect, dict):
        return 1.0
    phase_ids = [str(item) for item in effect.get("phase_ids", [])]
    if phase_ids and phase_id not in phase_ids:
        return 1.0
    return float(effect.get("multiplier", 1.0))


def _effective_multiplier_for_phase(effect: dict[str, Any], phase_id: str) -> float:
    phase_ids = [str(item) for item in effect.get("phase_ids", [])]
    if phase_ids and phase_id not in phase_ids:
        return 1.0
    by_phase = effect.get("effective_multipliers_by_phase", {})
    if isinstance(by_phase, dict) and phase_id in by_phase:
        return float(by_phase[phase_id])
    if "effective_multiplier" in effect:
        return float(effect["effective_multiplier"])
    return float(effect.get("multiplier", 1.0))


def _default_products(
    intensity_policy: dict[str, Any],
    family_defaults: dict[str, Any],
    phase_ids: Iterable[str],
) -> dict[str, float]:
    effects = intensity_policy.get("effects", {})
    if not isinstance(effects, dict):
        return {phase_id: 1.0 for phase_id in phase_ids}
    products: dict[str, float] = {}
    for phase_id in phase_ids:
        product = 1.0
        for driver_id in effects:
            product *= _effective_multiplier_for_phase(
                effects.get(driver_id, {}).get(str(family_defaults.get(driver_id)), {}),
                phase_id,
            )
        products[phase_id] = round(product, 4)
    return products


def _multiplier_rows(
    *,
    matter_family: str,
    raw_intensity_policy: dict[str, Any],
    effective_intensity_policy: dict[str, Any],
    baseline_by_driver: dict[str, str],
) -> list[IntensityNormalizationMultiplierRow]:
    raw_effects = raw_intensity_policy.get("effects", {})
    effective_effects = effective_intensity_policy.get("effects", {})
    if not isinstance(raw_effects, dict) or not isinstance(effective_effects, dict):
        return []
    rows: list[IntensityNormalizationMultiplierRow] = []
    for driver_id, value_effects in sorted(effective_effects.items()):
        if not isinstance(value_effects, dict):
            continue
        baseline_tier = baseline_by_driver.get(str(driver_id))
        for tier, effect in sorted(value_effects.items()):
            if not isinstance(effect, dict):
                continue
            for phase_id in [str(item) for item in effect.get("phase_ids", [])]:
                rows.append(
                    IntensityNormalizationMultiplierRow(
                        matter_family=matter_family,
                        driver_id=str(driver_id),
                        tier=str(tier),
                        phase_id=phase_id,
                        baseline_tier=baseline_tier,
                        raw_multiplier=float(
                            effect.get("raw_multiplier", effect.get("multiplier", 1.0))
                        ),
                        baseline_raw_multiplier=_raw_multiplier_for_phase(
                            raw_effects,
                            str(driver_id),
                            baseline_tier,
                            phase_id,
                        ),
                        effective_multiplier=_effective_multiplier_for_phase(effect, phase_id),
                    )
                )
    return rows


def _resolve_role_rate_schedule(
    *,
    profile: dict[str, Any],
    profile_path: Path,
    confirmation: HumanConfirmation,
):
    rate_card_ref = profile.get("rate_card_ref")
    if not rate_card_ref:
        return resolve_role_rates(profile=profile, confirmation=confirmation)
    card_path = _find_repo_file(profile_path.parent, str(rate_card_ref))
    if card_path is None:
        return resolve_role_rates(profile=profile, confirmation=confirmation)
    return resolve_role_rates(
        profile=profile,
        confirmation=confirmation,
        rate_card=load_rate_card(card_path),
    )


def _demo_totals(
    *,
    repo_root: Path,
    before_policy: dict[str, Any],
    after_policy: dict[str, Any],
    profile_records: list[tuple[Path, dict[str, Any]]],
    demo_cases: list[IntensitySignoffDemoCase],
) -> list[IntensityNormalizationDemoTotal]:
    totals: list[IntensityNormalizationDemoTotal] = []
    with TemporaryDirectory(prefix="lawfirm_os_intake_intensity_signoff_") as temp:
        temp_root = Path(temp)
        for case in demo_cases:
            packet, _run_dir = run_preflight(
                case.input_path,
                profile_records[0][0],
                temp_root / case.demo_case_id / "preflight",
            )
            confirmation_payload = load_json(case.confirmation_path)
            confirmation_payload["preflight_packet_id"] = packet.packet_id
            confirmation = bind_confirmation_to_packet_evidence(
                packet,
                HumanConfirmation.model_validate(confirmation_payload),
            )
            profile_record = next(
                (
                    record
                    for record in profile_records
                    if confirmation.confirmed_matter_family in record[1].get("budget_templates", {})
                ),
                profile_records[0],
            )
            profile_path, profile = profile_record
            rate_resolution = _resolve_role_rate_schedule(
                profile=profile,
                profile_path=profile_path,
                confirmation=confirmation,
            )
            before_drivers = resolve_case_drivers(packet, confirmation, profile, before_policy)
            after_drivers = resolve_case_drivers(packet, confirmation, profile, after_policy)
            before_budget = build_budget_proposal(
                packet,
                confirmation,
                profile,
                case_drivers=before_drivers,
                rate_resolution=rate_resolution,
            )
            after_budget = build_budget_proposal(
                packet,
                confirmation,
                profile,
                case_drivers=after_drivers,
                rate_resolution=rate_resolution,
            )
            before_total = before_budget.total_proposed_budget
            after_total = after_budget.total_proposed_budget
            delta = (
                round(after_total - before_total, 2)
                if before_total is not None and after_total is not None
                else None
            )
            delta_percent = (
                round((delta / before_total) * 100, 2)
                if delta is not None and before_total not in (None, 0)
                else None
            )
            totals.append(
                IntensityNormalizationDemoTotal(
                    demo_case_id=case.demo_case_id,
                    matter_family=str(confirmation.confirmed_matter_family),
                    input_ref=_display_path(case.input_path, repo_root),
                    confirmation_ref=_display_path(case.confirmation_path, repo_root),
                    pricing_status_before=before_budget.pricing_status,
                    pricing_status_after=after_budget.pricing_status,
                    total_proposed_budget_before=before_total,
                    total_proposed_budget_after=after_total,
                    subtotal_fees_before=before_budget.subtotal_fees,
                    subtotal_fees_after=after_budget.subtotal_fees,
                    subtotal_expenses_before=before_budget.subtotal_expenses,
                    subtotal_expenses_after=after_budget.subtotal_expenses,
                    contingency_amount_before=before_budget.contingency_amount,
                    contingency_amount_after=after_budget.contingency_amount,
                    delta_amount=delta,
                    delta_percent=delta_percent,
                    before_case_driver_profile_id=before_drivers.case_driver_profile_id,
                    after_case_driver_profile_id=after_drivers.case_driver_profile_id,
                )
            )
    return totals


def build_intensity_normalization_signoff_report(
    *,
    policy_path: str | Path,
    practice_profile_paths: list[str | Path],
    demo_cases: list[IntensitySignoffDemoCase] | None = None,
    generated_at: str | None = None,
) -> IntensityNormalizationSignoffReport:
    policy_path = Path(policy_path)
    repo_root = _repo_root_from_policy(policy_path)
    policy = load_driver_policy(policy_path)
    before_policy = _policy_with_normalization(policy, "raw")
    after_policy = _policy_with_normalization(policy, "baseline_relative")
    generated_at = generated_at or now_iso()
    profile_records = [
        (Path(profile_path), load_profile(profile_path)) for profile_path in practice_profile_paths
    ]
    if not profile_records:
        raise ValueError("at least one practice profile is required")
    demo_cases = demo_cases if demo_cases is not None else _default_demo_cases(repo_root)
    demo_totals = _demo_totals(
        repo_root=repo_root,
        before_policy=before_policy,
        after_policy=after_policy,
        profile_records=profile_records,
        demo_cases=demo_cases,
    )
    totals_by_family: dict[str, list[IntensityNormalizationDemoTotal]] = {}
    for total in demo_totals:
        totals_by_family.setdefault(total.matter_family, []).append(total)

    raw_intensity_policy = before_policy.get("intensity_multiplier_policy", {})
    after_intensity_policy = after_policy.get("intensity_multiplier_policy", {})
    per_family: list[IntensityNormalizationFamilySignoff] = []
    for profile_path, profile in profile_records:
        templates = profile.get("budget_templates", {})
        if not isinstance(templates, dict):
            continue
        for matter_family, template in sorted(templates.items()):
            if not isinstance(template, dict):
                continue
            family_defaults = before_policy.get("matter_family_defaults", {}).get(matter_family)
            if not isinstance(family_defaults, dict):
                continue
            effective_policy, baseline_by_driver = build_effective_intensity_multiplier_policy(
                after_intensity_policy,
                matter_family=str(matter_family),
                profile=profile,
                family_defaults=family_defaults,
            )
            phase_ids = _phase_ids(template, raw_intensity_policy)
            baseline_source = (
                "template_declaration"
                if isinstance(template.get("baseline_intensity"), dict)
                and bool(template.get("baseline_intensity"))
                else "family_defaults"
            )
            per_family.append(
                IntensityNormalizationFamilySignoff(
                    matter_family=str(matter_family),
                    template_id=str(template.get("template_id", "unknown")),
                    baseline_source=baseline_source,
                    baseline_by_driver=baseline_by_driver,
                    per_phase_default_product_before=_default_products(
                        raw_intensity_policy,
                        family_defaults,
                        phase_ids,
                    ),
                    per_phase_default_product_after=_default_products(
                        effective_policy,
                        family_defaults,
                        phase_ids,
                    ),
                    effective_multiplier_table=_multiplier_rows(
                        matter_family=str(matter_family),
                        raw_intensity_policy=raw_intensity_policy,
                        effective_intensity_policy=effective_policy,
                        baseline_by_driver=baseline_by_driver,
                    ),
                    demo_totals=totals_by_family.get(str(matter_family), []),
                )
            )

    payload_for_id = {
        "policy_sha256_after": digest_json(after_policy),
        "profile_paths": [str(path) for path, _profile in profile_records],
        "generated_at": generated_at,
    }
    return IntensityNormalizationSignoffReport(
        signoff_id=_stable_id("intensitysignoff", payload_for_id),
        generated_at=generated_at,
        status="preview_requires_human_approval",
        policy_id=str(policy.get("policy_id", "unknown")),
        policy_version_before=str(policy.get("version", "0.1")),
        policy_version_after=f"{policy.get('version', '0.1')}+baseline_relative",
        policy_sha256_before=digest_json(before_policy),
        policy_sha256_after=digest_json(after_policy),
        per_family=per_family,
        decision_required=(
            "Human owner must approve or reject the baseline_relative policy flip after "
            "reviewing before/after default products and demo budget totals."
        ),
    )


def render_intensity_normalization_signoff_markdown(
    report: IntensityNormalizationSignoffReport,
) -> str:
    decision_heading = (
        "Decision" if report.status == "approved_for_baseline_relative" else "Decision Required"
    )
    title = (
        "# Intensity Normalization Approved Signoff"
        if report.status == "approved_for_baseline_relative"
        else "# Intensity Normalization Signoff Preview"
    )
    lines = [
        title,
        "",
        f"- Signoff ID: `{report.signoff_id}`",
        f"- Status: `{report.status}`",
        f"- Policy: `{report.policy_id}`",
        f"- Mode before: `{report.normalization_mode_before}`",
        f"- Mode after: `{report.normalization_mode_after}`",
        f"- Requires human approval: `{str(report.requires_human_approval).lower()}`",
        "- Candidate-only, synthetic-only, and not authorized for client submission.",
        "",
        f"## {decision_heading}",
        "",
        report.decision_required,
        "",
    ]
    for family in report.per_family:
        lines.extend(
            [
                f"## {family.matter_family}",
                "",
                f"- Template: `{family.template_id}`",
                f"- Baseline source: `{family.baseline_source}`",
                f"- Baseline tiers: `{json.dumps(family.baseline_by_driver, sort_keys=True)}`",
                "",
                "| Phase | Default Product Before | Default Product After |",
                "|---|---:|---:|",
            ]
        )
        for phase_id in sorted(family.per_phase_default_product_before):
            lines.append(
                "| "
                f"{phase_id} | "
                f"{family.per_phase_default_product_before[phase_id]:.4f} | "
                f"{family.per_phase_default_product_after.get(phase_id, 1.0):.4f} |"
            )
        if family.demo_totals:
            lines.extend(["", "| Demo Case | Before | After | Delta |", "|---|---:|---:|---:|"])
            for total in family.demo_totals:
                before = (
                    f"{total.total_proposed_budget_before:.2f}"
                    if total.total_proposed_budget_before is not None
                    else "hours-only"
                )
                after = (
                    f"{total.total_proposed_budget_after:.2f}"
                    if total.total_proposed_budget_after is not None
                    else "hours-only"
                )
                delta = f"{total.delta_amount:.2f}" if total.delta_amount is not None else "n/a"
                lines.append(f"| {total.demo_case_id} | {before} | {after} | {delta} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_intensity_normalization_signoff_report(
    *,
    policy_path: str | Path,
    practice_profile_paths: list[str | Path],
    out_path: str | Path,
    markdown_out_path: str | Path | None = None,
    demo_cases: list[IntensitySignoffDemoCase] | None = None,
    generated_at: str | None = None,
) -> IntensityNormalizationSignoffReport:
    report = build_intensity_normalization_signoff_report(
        policy_path=policy_path,
        practice_profile_paths=practice_profile_paths,
        demo_cases=demo_cases,
        generated_at=generated_at,
    )
    write_json(out_path, report.model_dump(mode="json"))
    if markdown_out_path is not None:
        target = Path(markdown_out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_intensity_normalization_signoff_markdown(report), encoding="utf-8")
    return report


def validate_intensity_normalization_signoff_gate(
    *,
    policy_path: str | Path,
    signoff_path: str | Path | None = None,
    report_out: str | Path | None = None,
) -> IntensityNormalizationSignoffGateReport:
    policy_path = Path(policy_path)
    policy = load_driver_policy(policy_path)
    mode = _policy_mode(policy)
    if mode not in {"raw", "baseline_relative"}:
        raise ValueError(f"unsupported intensity normalization mode: {mode}")
    checks: list[IntensityNormalizationSignoffGateCheck] = []
    signoff: IntensityNormalizationSignoffReport | None = None
    signoff_ref = str(signoff_path) if signoff_path is not None else None

    if mode == "raw":
        checks.append(
            IntensityNormalizationSignoffGateCheck(
                check_id="raw_mode_needs_no_signoff",
                status="passed",
                message="raw intensity normalization is behavior-preserving and needs no signoff",
            )
        )
    else:
        if signoff_path is None:
            checks.append(
                IntensityNormalizationSignoffGateCheck(
                    check_id="baseline_relative_requires_signoff",
                    status="failed",
                    message=(
                        "baseline_relative intensity normalization changes headline totals "
                        "and requires an approved signoff artifact"
                    ),
                    blocking_refs=[str(policy_path), str(DEFAULT_SIGNOFF_PATH)],
                )
            )
        else:
            signoff = IntensityNormalizationSignoffReport.model_validate(load_json(signoff_path))
            if signoff.status != "approved_for_baseline_relative":
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_approved_status",
                        status="failed",
                        message="signoff artifact is present but not approved for baseline_relative",
                        blocking_refs=[str(signoff_path)],
                    )
                )
            else:
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_approved_status",
                        status="passed",
                        message="signoff artifact is approved for baseline_relative",
                    )
                )
            if not signoff.approved_by or not signoff.approved_at:
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_human_fields",
                        status="failed",
                        message="approved signoff requires approved_by and approved_at",
                        blocking_refs=[str(signoff_path)],
                    )
                )
            else:
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_human_fields",
                        status="passed",
                        message="approved_by and approved_at are populated",
                    )
                )
            policy_hash = digest_json(policy)
            if signoff.policy_sha256_after != policy_hash:
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_policy_hash_matches",
                        status="failed",
                        message="signoff policy_sha256_after does not match the active policy",
                        blocking_refs=[str(signoff_path), str(policy_path)],
                    )
                )
            else:
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_policy_hash_matches",
                        status="passed",
                        message="signoff policy hash matches active baseline_relative policy",
                    )
                )
            if signoff.policy_id != str(policy.get("policy_id", "unknown")):
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_policy_id_matches",
                        status="failed",
                        message="signoff policy_id does not match the active policy",
                        blocking_refs=[str(signoff_path), str(policy_path)],
                    )
                )
            else:
                checks.append(
                    IntensityNormalizationSignoffGateCheck(
                        check_id="signoff_policy_id_matches",
                        status="passed",
                        message="signoff policy_id matches active policy",
                    )
                )

    status = "failed" if any(check.status == "failed" for check in checks) else "passed"
    report = IntensityNormalizationSignoffGateReport(
        status=status,
        policy_id=str(policy.get("policy_id", "unknown")),
        policy_version=str(policy.get("version", "0.1")),
        normalization_mode=mode,  # type: ignore[arg-type]
        signoff_required=mode == "baseline_relative",
        signoff_ref=signoff_ref,
        signoff_status=signoff.status if signoff is not None else None,
        checks=checks,
    )
    if report_out is not None:
        write_json(report_out, report.model_dump(mode="json"))
    return report
