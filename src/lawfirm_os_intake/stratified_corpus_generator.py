"""DT4 — driver-stratified synthetic matter generator (generation-spec v2).

Implements `MEDICAL_MALPRACTICE_SYNTHETIC_MATTER_GENERATION_SPEC.md` intake-side
(world-maker remains the spec's eventual home; this module is self-contained for a
later lift-and-shift). It fixes the marathon's biggest measurement gap: **every
ground-truth driver level is rendered as observable evidence inside the
documents**, so driver recovery is genuinely testable downstream.

Design:

- **Deliberate stratification, not random draws.** The grid is subtype ×
  damages-severity × implicated-specialties × difficulty × 2 signal variants, with
  the contract's ``subtype_priors`` overriding pinned drivers (birth-injury/
  obstetric is forced catastrophic + 3-plus specialties — the hard/high-cost
  anchor). Remaining drivers derive from a per-case seeded RNG.
- **Observable evidence.** Each explicit driver level produces a concrete snippet
  (caption defendant count, expert-disclosure specialty list, demand-letter
  severity + life-care-plan language, scheduling-order deposition count and
  posture, discovery-request interrogatory sets and ESI volume, jurisdictional
  affidavit/panel sentences…) recorded in ``observable_driver_evidence`` and
  enforced verbatim-in-document by the model validator.
- **Dollars deterministic, never stated.** The budget is computed via
  ``build_explicit_canonical_profile`` + the DT2 canonical pricing engine; the
  documents never contain the computed total (validator-enforced). The demand
  letter states EXPOSURE, which is derived from the priced total and a seeded
  ratio kept inside the med-mal reference-class band [0.03, 0.40].
- **Anti-tautology + leak-proof holdout**, as in LW1: difficulty controls
  signal/distractor term density; the train/holdout split is a seeded hash of the
  case id, digest-frozen in the manifest. Regeneration is byte-identical
  (no timestamps anywhere in the artifacts).

All names, entities, and facts are invented; no real person, provider, or matter
is implied. Candidate-only, synthetic-only, ``reference_class_only``.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

from .canonical_pricing import build_canonical_priced_work_plan
from .driver_taxonomy import build_explicit_canonical_profile, load_driver_taxonomy
from .models import (
    RenderedMatterDocument,
    StratifiedCorpusManifest,
    StratifiedManifestEntry,
    StratifiedSyntheticMatter,
    _digest_str_list,
)
from .util import digest_json, load_json, write_json
from .workers import MATTER_SIGNALS

GENERATOR_VERSION = "stratified-corpus-generator.v0_1"
CORPUS_SEED = 20260726
LINE_ID = "medical_malpractice_defense"
STRATIFIED_CORPUS_DIR = "examples/synthetic/stratified"
HOLDOUT_PERCENT = 28

_SEVERITIES = ("minor", "serious", "catastrophic")
_SPECIALTY_LEVELS = ("1", "2", "3_plus")
_DIFFICULTIES = ("clear", "moderate", "hard")
_VARIANTS = (0, 1)

_SEVERITY_TO_STAKES = {"minor": "low", "serious": "medium", "catastrophic": "high"}
# Exposure bands per case_stakes level (minor units); chosen so the derived
# budget-to-exposure ratio lands inside the med-mal reference-class band.
_STAKES_EXPOSURE_BANDS = {
    "low": (80_000_000, 150_000_000),
    "medium": (200_000_000, 500_000_000),
    "high": (600_000_000, 1_200_000_000),
}

_SEVERITY_PHRASES = {
    "minor": "soft-tissue injuries with full recovery expected",
    "serious": "injuries requiring surgical intervention with disputed permanency",
    "catastrophic": "catastrophic injuries; a life-care plan will be submitted",
}
_THEORY_PHRASES = {
    "negligence": "sounding in negligence",
    "informed_consent": "sounding in lack of informed consent",
    "both": "sounding in negligence and lack of informed consent",
}
_POSTURE_PHRASES = {
    "low": "This matter is referred to early mediation.",
    "medium": "This matter proceeds on the standard case-management track.",
    "high": "A firm trial date has been set by the court.",
}
# Jurisdictional regimes: (affidavit_of_merit, screening_panel) with sentences.
_REGIMES = [
    ("Synthetic State A", "none", "none"),
    ("Synthetic State B", "required", "none"),
    ("Synthetic State C", "required", "mandatory"),
    ("Synthetic State D", "required", "waivable"),
]
_AFFIDAVIT_SENTENCES = {
    "none": "No affidavit of merit is required in this jurisdiction.",
    "required": "An affidavit of merit has been filed with the complaint.",
}
_PANEL_SENTENCES = {
    "none": "No pre-suit screening panel applies in this jurisdiction.",
    "waivable": "The parties have stipulated to waive the pre-suit screening panel.",
    "mandatory": "The mandatory pre-suit screening panel has issued its notice.",
}

_DEFENDANT_NAMES = [
    "Dr. Alice Hart",
    "Dr. Brian Osei",
    "Dr. Carla Mendez",
    "Dr. David Lin",
    "Dr. Elena Petrov",
]
_SPECIALTIES = ["obstetrics", "anesthesiology", "emergency medicine", "radiology"]


def _rng_for(case_id: str, seed: int) -> random.Random:
    return random.Random(f"{seed}:{case_id}")


def _holdout_split(case_id: str, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}:{case_id}".encode("utf-8")).hexdigest()
    return "holdout" if int(digest[:8], 16) % 100 < HOLDOUT_PERCENT else "train"


def _signal_terms(rng: random.Random, difficulty: str) -> tuple[list[str], list[str]]:
    medmal_terms = list(MATTER_SIGNALS[LINE_ID])
    other_families = sorted(k for k in MATTER_SIGNALS if k != LINE_ID)
    distractor_pool: list[str] = []
    for family in other_families[:2]:
        distractor_pool.extend(list(MATTER_SIGNALS[family])[:2])
    if difficulty == "clear":
        return medmal_terms[:3], []
    if difficulty == "moderate":
        return medmal_terms[:2], [distractor_pool[rng.randrange(len(distractor_pool))]]
    picks = rng.sample(range(len(distractor_pool)), 2)
    return medmal_terms[:1], [distractor_pool[i] for i in picks]


def _cells_for_subtype(subtype: str, priors: dict[str, str]) -> list[tuple[str, str]]:
    """Distinct (severity, specialties) cells after applying subtype priors."""

    cells: list[tuple[str, str]] = []
    for severity in _SEVERITIES:
        for specialties in _SPECIALTY_LEVELS:
            cell = (
                priors.get("damages_severity", severity),
                priors.get("implicated_specialties", specialties),
            )
            if cell not in cells:
                cells.append(cell)
    return cells


def _derive_levels(
    rng: random.Random, subtype: str, priors: dict[str, str], severity: str, specialties: str
) -> dict[str, str]:
    state, affidavit, panel = (
        _REGIMES[rng.randrange(len(_REGIMES))][0],
        None,
        None,
    )
    regime = next(r for r in _REGIMES if r[0] == state)
    affidavit, panel = regime[1], regime[2]
    levels = {
        "damages_severity": severity,
        "implicated_specialties": specialties,
        "case_stakes": _SEVERITY_TO_STAKES[severity],
        "defendant_provider_count": priors.get(
            "defendant_provider_count", rng.choice(["1", "2_3", "4_plus"])
        ),
        "causation_disputed": priors.get(
            "causation_disputed", rng.choice(["not_disputed", "disputed"])
        ),
        "medical_record_volume": priors.get(
            "medical_record_volume", rng.choice(["low", "medium", "high"])
        ),
        "theory_of_liability": priors.get(
            "theory_of_liability", rng.choice(["negligence", "both"])
        ),
        "deposition_burden": rng.choice(["none", "limited_3_5", "heavy_8_plus"]),
        "written_discovery_burden": rng.choice(["light", "moderate", "heavy"]),
        "ediscovery_volume": rng.choice(["none", "esi_no_disputes", "esi_with_disputes"]),
        "trial_likelihood": rng.choice(["low", "medium", "high"]),
        "appeal_likelihood": "low",
        "affidavit_of_merit": affidavit,
        "screening_panel": panel,
    }
    return levels


def _render_matter(
    case_id: str,
    subtype: str,
    difficulty: str,
    levels: dict[str, str],
    rng: random.Random,
    exposure_minor_units: int,
    state_name: str,
) -> tuple[list[RenderedMatterDocument], dict[str, str], list[str], list[str]]:
    signal_terms, distractor_terms = _signal_terms(rng, difficulty)

    provider_counts = {"1": 1, "2_3": rng.choice([2, 3]), "4_plus": rng.choice([4, 5])}
    n_defendants = provider_counts[levels["defendant_provider_count"]]
    defendants = ", ".join(_DEFENDANT_NAMES[:n_defendants])
    plural = "defendant" if n_defendants == 1 else "defendants"
    caption_evidence = f"names {n_defendants} physician {plural}"

    specialty_counts = {"1": 1, "2": 2, "3_plus": rng.choice([3, 4])}
    n_specialties = specialty_counts[levels["implicated_specialties"]]
    disclosed = ", ".join(f"one expert in {name}" for name in _SPECIALTIES[:n_specialties])
    expert_evidence = f"discloses {n_specialties} standard-of-care expert opinion(s)"

    severity_evidence = _SEVERITY_PHRASES[levels["damages_severity"]]
    theory_evidence = _THEORY_PHRASES[levels["theory_of_liability"]]
    stakes_evidence = f"demands ${exposure_minor_units // 100:,}"

    deposition_counts = {
        "none": 0,
        "limited_3_5": rng.choice([3, 4, 5]),
        "heavy_8_plus": rng.choice([8, 9, 10, 11]),
    }
    n_depositions = deposition_counts[levels["deposition_burden"]]
    deposition_evidence = f"the parties shall complete {n_depositions} depositions"

    interrogatory_sets = {"light": 1, "moderate": 2, "heavy": 4}[levels["written_discovery_burden"]]
    written_evidence = f"{interrogatory_sets} set(s) of interrogatories"

    gb = rng.choice([15, 40, 120, 300])
    esi_sentences = {
        "none": "The parties anticipate no ESI production.",
        "esi_no_disputes": f"ESI production of approximately {gb} GB is anticipated.",
        "esi_with_disputes": (
            f"ESI production of approximately {gb} GB is anticipated; "
            "two ESI disputes are pending before the court."
        ),
    }
    esi_evidence = esi_sentences[levels["ediscovery_volume"]]

    pages = {
        "low": rng.randint(200, 800),
        "medium": rng.randint(2000, 5000),
        "high": rng.randint(9000, 20000),
    }[levels["medical_record_volume"]]
    records_evidence = f"medical records comprising approximately {pages} pages"

    causation_sentences = {
        "not_disputed": "Causation is not separately contested by the defense.",
        "disputed": ("Defendants deny causation and will present a separate causation opinion."),
    }
    causation_evidence = causation_sentences[levels["causation_disputed"]]

    posture_evidence = _POSTURE_PHRASES[levels["trial_likelihood"]]
    affidavit_evidence = _AFFIDAVIT_SENTENCES[levels["affidavit_of_merit"]]
    panel_evidence = _PANEL_SENTENCES[levels["screening_panel"]]

    signal_sentence = "The complaint concerns " + "; ".join(signal_terms) + "."
    distractor_sentence = (
        ("The record also references " + "; ".join(distractor_terms) + ".")
        if distractor_terms
        else ""
    )

    documents = [
        RenderedMatterDocument(
            doc_type="complaint",
            text=(
                f"IN THE DISTRICT COURT OF {state_name.upper()}. Jane Roe, Plaintiff, "
                f"v. {defendants}, Defendants. This medical negligence action "
                f"{caption_evidence}, {theory_evidence}. {signal_sentence} "
                f"{distractor_sentence}"
            ).strip(),
        ),
        RenderedMatterDocument(
            doc_type="answer",
            text=(
                "Defendants generally deny the allegations. "
                f"{causation_evidence} All affirmative defenses are reserved."
            ),
        ),
        RenderedMatterDocument(
            doc_type="expert_disclosure",
            text=(f"Pursuant to the scheduling order, the defense {expert_evidence}: {disclosed}."),
        ),
        RenderedMatterDocument(
            doc_type="demand_letter",
            text=(
                f"Plaintiff {stakes_evidence} in full settlement. Plaintiff sustained "
                f"{severity_evidence}. Enclosed are {records_evidence}."
            ),
        ),
        RenderedMatterDocument(
            doc_type="scheduling_order",
            text=(
                f"Per the case-management conference, {deposition_evidence}. "
                f"{posture_evidence} {affidavit_evidence} {panel_evidence}"
            ),
        ),
        RenderedMatterDocument(
            doc_type="discovery_requests",
            text=(
                f"Plaintiff serves {written_evidence} and requests for production. {esi_evidence}"
            ),
        ),
    ]

    evidence = {
        "damages_severity": severity_evidence,
        "implicated_specialties": expert_evidence,
        "case_stakes": stakes_evidence,
        "defendant_provider_count": caption_evidence,
        "causation_disputed": causation_evidence,
        "medical_record_volume": records_evidence,
        "theory_of_liability": theory_evidence,
        "deposition_burden": deposition_evidence,
        "written_discovery_burden": written_evidence,
        "ediscovery_volume": esi_evidence,
        "trial_likelihood": posture_evidence,
        "appeal_likelihood": _POSTURE_PHRASES[levels["trial_likelihood"]],
        "affidavit_of_merit": affidavit_evidence,
        "screening_panel": panel_evidence,
    }
    # appeal_likelihood is pinned "low" for every matter; its evidence is the
    # posture sentence (no separate appellate signal exists pre-disposition).
    return documents, evidence, signal_terms, distractor_terms


def generate_stratified_corpus(
    *, repo_root: str | Path, seed: int = CORPUS_SEED
) -> tuple[list[StratifiedSyntheticMatter], StratifiedCorpusManifest]:
    root = Path(repo_root)
    contract = load_driver_taxonomy(root)
    subtype_priors: dict[str, dict[str, str]] = contract["lines"][LINE_ID]["subtype_priors"]

    matters: list[StratifiedSyntheticMatter] = []
    for subtype in sorted(subtype_priors):
        priors = subtype_priors[subtype]
        for severity, specialties in _cells_for_subtype(subtype, priors):
            for difficulty in _DIFFICULTIES:
                for variant in _VARIANTS:
                    case_id = f"strat-{subtype}-{severity}-{specialties}-{difficulty}-v{variant}"
                    rng = _rng_for(case_id, seed)
                    levels = _derive_levels(rng, subtype, priors, severity, specialties)
                    state_name = next(
                        r[0]
                        for r in _REGIMES
                        if r[1] == levels["affidavit_of_merit"]
                        and r[2] == levels["screening_panel"]
                    )

                    profile = build_explicit_canonical_profile(levels, repo_root=root)
                    plan = build_canonical_priced_work_plan(profile, repo_root=root)

                    # Exposure derived from the priced total and a seeded ratio so
                    # the budget-to-exposure ratio stays in the med-mal band; the
                    # exposure must also sit in its stakes level's band.
                    low, high = _STAKES_EXPOSURE_BANDS[levels["case_stakes"]]
                    floor = max(low, int(plan.total_dollars_minor_units / 0.38))
                    ceiling = max(floor, min(high, int(plan.total_dollars_minor_units / 0.04)))
                    exposure = floor + (
                        rng.randrange(ceiling - floor + 1) if ceiling > floor else 0
                    )

                    documents, evidence, signal_terms, distractor_terms = _render_matter(
                        case_id, subtype, difficulty, levels, rng, exposure, state_name
                    )
                    matters.append(
                        StratifiedSyntheticMatter(
                            case_id=case_id,
                            line_id=LINE_ID,
                            subtype=subtype,
                            difficulty=difficulty,  # type: ignore[arg-type]
                            explicit_driver_levels=levels,
                            observable_driver_evidence=evidence,
                            documents=documents,
                            signal_terms_used=signal_terms,
                            distractor_terms_used=distractor_terms,
                            exposure_minor_units=exposure,
                            profile_id=profile.profile_id,
                            plan_id=plan.plan_id,
                            canonical_total_minor_units=plan.total_dollars_minor_units,
                            contract_digest=plan.contract_digest,
                            holdout_split=_holdout_split(case_id, seed),  # type: ignore[arg-type]
                        )
                    )

    entries = [
        StratifiedManifestEntry(
            case_id=m.case_id,
            subtype=m.subtype,
            difficulty=m.difficulty,
            holdout_split=m.holdout_split,
            plan_id=m.plan_id,
        )
        for m in matters
    ]
    subtype_counts: dict[str, int] = {}
    difficulty_counts: dict[str, int] = {}
    for m in matters:
        subtype_counts[m.subtype] = subtype_counts.get(m.subtype, 0) + 1
        difficulty_counts[m.difficulty] = difficulty_counts.get(m.difficulty, 0) + 1
    corpus_digest = digest_json([m.model_dump(mode="json") for m in matters])
    manifest = StratifiedCorpusManifest(
        corpus_id="stratcorpus-" + corpus_digest.removeprefix("sha256:")[:16],
        generator_version=GENERATOR_VERSION,
        corpus_seed=seed,
        contract_digest=matters[0].contract_digest,
        case_count=len(matters),
        subtype_counts=subtype_counts,
        difficulty_counts=difficulty_counts,
        train_count=sum(1 for m in matters if m.holdout_split == "train"),
        holdout_count=sum(1 for m in matters if m.holdout_split == "holdout"),
        cases=entries,
        corpus_digest=corpus_digest,
        holdout_split_digest=_digest_str_list(
            sorted(f"{m.case_id}:{m.holdout_split}" for m in matters)
        ),
    )
    return matters, manifest


def freeze_stratified_corpus(repo_root: str | Path) -> StratifiedCorpusManifest:
    root = Path(repo_root)
    matters, manifest = generate_stratified_corpus(repo_root=root)
    out_dir = root / STRATIFIED_CORPUS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "matters.json", [m.model_dump(mode="json") for m in matters])
    write_json(out_dir / "manifest.json", manifest.model_dump(mode="json"))
    return manifest


def load_stratified_corpus(
    repo_root: str | Path,
) -> tuple[list[StratifiedSyntheticMatter], StratifiedCorpusManifest]:
    root = Path(repo_root)
    matters = [
        StratifiedSyntheticMatter.model_validate(raw)
        for raw in load_json(root / STRATIFIED_CORPUS_DIR / "matters.json")
    ]
    manifest = StratifiedCorpusManifest.model_validate(
        load_json(root / STRATIFIED_CORPUS_DIR / "manifest.json")
    )
    if digest_json([m.model_dump(mode="json") for m in matters]) != manifest.corpus_digest:
        raise ValueError("frozen stratified corpus does not match its manifest digest")
    return matters, manifest
