# Codex Build Packet — Learning-vs-Leakage Solutions (Opus draft)

## 0. Status & how to read this

- **status:** candidate; author: Opus; date: 2026-07-08; **synthetic-only, deploy behind existing gates.**
- Companion kernels (read first): `cross-matter-noninterference-kernel.opus-draft.md`, `bounded-leakage-calibration-kernel.opus-draft.md`, `learning-vs-leakage-hard-kernels.opus-draft.md`.
- This packet turns those kernels into **buildable components with research basis, file targets, tests, dependency gates, and a PR order.** Codex deploys the *machinery + synthetic fixtures*; **no component may run on real client/matter data** — each fails closed to synthetic/hours-only until the Phase-2 approvals (privacy, counsel, data-owner, Substrate governance) exist. Mirrors Mock Trial `probabilistic_calibration_boundary.md`.

## 1. The honest research verdict

| # | Problem | Established research that solves / bounds it | Verdict |
|---|---|---|---|
| P1 | Bounded-leakage calibration | **Differential privacy**: Dwork-McSherry-Nissim-Smith 2006 (calibrating noise to sensitivity); Dwork-Roth 2014 (monograph); Gaussian mechanism; **zCDP** Bun-Steinke 2016 / **RDP** Mironov 2017 (composition); **DP-ERM/objective perturbation** Chaudhuri-Monteleoni-Sarwate 2011; **functional mechanism** Zhang 2012; **DP-SGD** Abadi 2016. Reconstruction/differencing: Dinur-Nissim 2003. Membership inference: Shokri 2017. | **SOLVED** — reduce to DP; our kernel applies it. Only ε-choice + small-n utility remain (policy). |
| P2 | Qualitative-rule disclosure budget | k-anonymity Sweeney 2002; l-diversity Machanavajjhala 2007; t-closeness Li 2007. **Critiques that confirm the residue:** composition attacks Ganta 2008; de-anonymization Narayanan-Shmatikov 2008 (auxiliary knowledge defeats k-anon). DP-for-text (metric-DP) exists but utility for rules is poor. | **PARTIALLY / OPEN** — no clean formal bound vs a strong adversary. Best available = generalization + suppression + **declared adversary** + human sign-off. Research *confirms* our honesty flag. |
| #3 | Positional/issue-conflict laundering | **Brewer-Nash 1989 "The Chinese Wall Security Policy"** — the classic formal access model for conflict-of-interest, directly applicable. + ABA Model Rules 1.6/1.9/1.7/1.18/1.10; ABA Formal Op. 512 (2024, generative AI). | **SOLVED pattern** (Brewer-Nash) + **legal policy** (ABA). We build the wall; counsel sets adversity. |
| #4 | Evidentiary durability across model death | Evidence law: **FRE 901(b)(9)** (process producing accurate result), **FRE 902(13)/(14)** (self-authenticating machine/records, 2017). Provenance: **C2PA**; **model cards** Mitchell 2019; **datasheets** Gebru 2018; **RFC 3161** trusted timestamp. LLM inference is non-reproducible (known). | **SOLVED reframed** — authenticate the *process*, don't reproduce the *model*. Seal the deterministic wrapper + attestation. |
| #5 | Retroactive screen after human decision | **Machine unlearning**: Cao-Yang 2015; **SISA** Bourtoule 2021 (shard→rebuild only affected). Information-flow lineage: Denning 1976; Myers-Liskov DLM. The "already-influenced-a-human" part is remediation/disclosure, not CS. | **PARTIALLY** — unlearning + lineage bound the *machine* blast radius; human residue stays policy. |
| #6 | Holdout taint under screening | **The reusable holdout** (Dwork-Feldman-Hardt-Pitassi-Reingold-Roth, *Science* 2015) — DP keeps a validation set valid under adaptive reuse; SISA rebuilds only tainted shards. | **SOLVED** — DP-Thresholdout holdout + shard rebuild. |
| #7 | Prove zero residue crossing DAD | **Information-flow control**: noninterference Goguen-Meseguer 1982; lattice model Denning 1976; decentralized labels Myers-Liskov. + structured-IR (closes free-text) + DLP-style scan. | **SOLVED pattern** — typed labels + structured IR + scanner; free-text carries no signal. |

**Bottom line:** P1, #4, #6, #7 have solid solutions; #3, #5 have a solid formal pattern + a policy remainder; **P2 is the one genuinely without a formal guarantee** — the literature (Ganta, Narayanan-Shmatikov) proves the limit, so we deploy the best-effort control and *label it honestly*.

## 2. Global constraints for Codex (do not violate)

- Candidate-only; reuse **`reviewed_learning_gate`** as the single promotion chokepoint (extend, don't fork); **no auto-promotion**; learning = versioned diff citing sources.
- **Fail closed on real data:** every component detects real/privileged/gated inputs and refuses (reuse existing real-data guards); default path = synthetic/hours-only.
- **Dependency gate:** any OSS DP/privacy library goes through the DAD `review-lane` + license/security/privacy review **before import**. Ship the **homegrown fallback first** (below), propose the library second with profiling evidence.
- Deterministic + replayable; secrets (DP seeds) never in git; MCP-first for any surface, file fallback declared.
- Respect `GOVERNANCE_BOUNDARY.md` promotion targets (schema→Substrate, gate→Orchestrator, correction→Exception Lake, worker→Skills Registry, evidence adapter→LKR).

## 3. Components to build

### CAL-DP — Differentially private calibration engine  (solves P1)
- **Research:** DP + zCDP + sufficient-statistic perturbation (§1 P1).
- **Build:** `src/lawfirm_os_intake/privacy/dp_mechanism.py` (Gaussian mechanism on clipped sufficient stats; homegrown ~150 LOC, no dep), `privacy/zcdp_ledger.py` (ρ accountant, group-size aware, durable JSONL), `calibration/estimators.py` (expfam reduction + `clip_norm`), `calibration/lomo.py` (dominance screen), `calibration/leakage_proof.py` (`CalibrationLeakageProof`), `calibration/reconstruction_test.py` (strong all-but-one-matter adversary).
- **Fork:** aggregate-only (≥K, no dominance, differencing-guarded) → DP (formal (ε,δ)) → **FAIL_CLOSED stay-synthetic** when noise>signal. Per `bounded-leakage-calibration-kernel` §6.
- **Gate:** `reviewed_learning_gate` refuses a calibrated parameter without a valid proof + approval_id.
- **Tests:** `tests/test_dp_mechanism.py`, `test_zcdp_ledger.py`, `test_calibration_leakage.py` — fixtures: aggregate-clean, dominance-route-dp, dp-epsilon-bound, group-privacy, utility-floor, budget-exhausted (holdout), lomo-negative (holdout), differencing (holdout), determinism.
- **DO NOT:** publish per-matter fits; present DP numbers as exact; use basic composition as accountant; account per-matter when a client/affiliate group is larger; run on non-synthetic data.
- **Library (gated, later):** OpenDP / Google-DP / Tumult Analytics as reviewed replacement for the homegrown mechanism.

### QRD — Qualitative-rule disclosure control  (best-effort P2; labeled honestly)
- **Research:** k-anon/l-diversity/t-closeness + their auxiliary-knowledge limits (§1 P2).
- **Build:** `src/lawfirm_os_intake/lessons/lesson_ir.py` (closed-vocab typed atoms; **free_text is advisory, never a signal**), `lessons/generalization_lattice.py` (reviewed hierarchy per dim; deterministic minimal climb), `lessons/kanon_universe.py` (anonymity_set over the reviewed matter universe; unknown⇒fail closed), `lessons/privilege_partition.py` (operational vs strategy; strategy⇒**block, not generalize**), `lessons/disclosure_proof.py` (`LessonDisclosureProof` with explicit `adversary_model`), `lessons/differencing.py` (cross-lesson suppression).
- **Tests:** `tests/test_lesson_disclosure.py` — kanon-generalize, suppress, privilege-block, differencing (holdout), freetext-lint (holdout), determinism.
- **DO NOT:** let free_text carry meaning; generalize a strategy atom; publish without a stated adversary model; **claim a formal privacy guarantee** — output must carry `guarantee: bounded_reident_under_declared_adversary`.

### CHW — Chinese-Wall conflict gate on lessons  (solves #3 pattern)
- **Research:** **Brewer-Nash 1989**; ABA 1.9/1.7/1.10.
- **Build:** `src/lawfirm_os_intake/conflicts/adversity_graph.py` (matters/clients → conflict-of-interest classes; reviewed edges only, no inference), `conflicts/chinese_wall.py` (a promoted lesson records its provenance CoI-classes; **refuses to fire when the consuming matter is adverse to any provenance matter's class** — Brewer-Nash "no read across a wall you've been on the other side of"), `conflicts/wall_proof.py`.
- **Gate:** lesson retrieval/firing checks the wall; block + Exception Lake candidate on violation.
- **Tests:** `tests/test_chinese_wall.py` — same-side-ok, cross-wall-block, imputation (firm-wide), unreviewed-edge-holds.
- **DO NOT:** infer adversity from similarity; auto-clear a conflict; treat firm-wide imputation as optional. **[COUNSEL owns the adversity classes.]**

### EVID — Durable evidentiary object  (solves #4 reframed)
- **Research:** FRE 901(b)(9)/902(13)/(14); C2PA; model cards; RFC 3161.
- **Build:** `src/lawfirm_os_intake/evidence/decision_record.py` — seals per AI-assisted judgment: input hashes, prompt hash, **model+provider+version+params**, output, **human reviewer attestation** (who reviewed *what* — the output, explicitly not the reasoning), producer manifest (script SHA), RFC-3161-style trusted timestamp ref, `review_scope: output_only`. `evidence/authenticate.py` (verify the seal at challenge time without the model).
- **Key stance:** authenticate the **process**, not reproduce the **model** — the object must be defensible when the model is gone.
- **Tests:** `tests/test_decision_record.py` — seal round-trip; tamper detection; verify-without-model; missing-attestation blocks.
- **DO NOT:** claim reproducibility of model reasoning; store raw privileged inputs in the record (hashes + refs only). **[COUNSEL: is output-only human attestation a defensible standard? confirm before real use.]**

### UNLRN — Retroactive unlearning + blast-radius lineage  (solves #5/#6 machine layer)
- **Research:** SISA Bourtoule 2021; Cao-Yang 2015; **reusable holdout** Dwork 2015; DLM lineage.
- **Build:** `src/lawfirm_os_intake/unlearning/shards.py` (SISA-style: calibration corpus sharded by matter so walling a matter rebuilds **only its shard**, cheap re-derive — reuses CAL-DP), `unlearning/lineage.py` (provenance graph: which rules/reports/decisions cited a now-walled matter → `screen_tainted` set = the blast radius), `holdout/thresholdout.py` (DP-validated reusable holdout so validation survives adaptive reuse *and* re-sharding).
- **Ties to:** `cross-matter-noninterference-kernel` §7 (supersede-not-delete) and CAL-DP (bounded ε already caps pre-screen leakage).
- **Tests:** `tests/test_unlearning.py` — shard-rebuild-only-affected; lineage blast-radius exact; thresholdout stays valid after re-shard; supersede-not-delete.
- **DO NOT:** delete raw evidence; rebuild a holdout from walled data; reuse a DP seed on re-derive. Human residue (already-made decisions) → route to disclosure policy, not code.

### IFC — Cross-boundary zero-residue proof  (solves #7)
- **Research:** noninterference Goguen-Meseguer 1982; Denning lattice 1976; Myers-Liskov DLM.
- **Build:** `src/lawfirm_os_intake/outbox/label_lattice.py` (sensitivity labels public<candidate<internal<privileged), `outbox/residue_scanner.py` (deny currency/carrier-name/rate/PII/privilege patterns + require structured-IR; **free-text fields rejected as signal**), `outbox/crossing_proof.py` (a DAD-bound lesson gets a `CrossingProof` asserting: structured-IR only, label≤candidate, scanner-clean, `LessonDisclosureProof` attached). Closes the `dad-learning-process-audit.md` D2 payload-schema gap.
- **Tests:** `tests/test_outbox_crossing.py` — clean-crosses, currency-blocked, carrier-name-blocked, freetext-signal-blocked, label-too-high-blocked.
- **DO NOT:** send raw rows/secrets/long source blobs; rely on agent discipline instead of the scanner.

## 4. PR sequence (deployable order)

1. **PR-LL1** CAL-DP homegrown mechanism + ledger + LOMO + proof + gate wire + fixtures. (foundation; UNLRN/QRD reuse it)
2. **PR-LL2** QRD LessonIR + generalization + k-anon + privilege partition + proof.
3. **PR-LL3** IFC label lattice + residue scanner + crossing proof (closes D2). *(depends QRD)*
4. **PR-LL4** CHW adversity graph + Chinese-Wall gate. *(counsel classes required)*
5. **PR-LL5** EVID decision record + authenticate.
6. **PR-LL6** UNLRN shards + lineage + thresholdout. *(depends CAL-DP)*
7. **PR-LL7** (gated) propose reviewed DP library (OpenDP/Tumult) to replace the homegrown mechanism, with profiling evidence + license/security/privacy review.

Each PR: synthetic fixtures green, `reviewed_learning_gate` still blocks promotion without proof+approval, real-data path fails closed, postflight with red-team + lesson-scout lanes.

## 5. Counsel / human policy inputs (block real-data use, not the build)

- **P1:** ε/ρ cap, reset policy, protected unit (matter|client|affiliate group), whether DP-noised numbers are presentable, whether *any* real-outcome calibration is allowed pre-pilot.
- **P2:** K_qual/K_support, the **declared adversary model**, which dims are `strategy`-class.
- **#3:** the adversity/CoI classes and firm-wide imputation rule (ABA 1.9/1.10).
- **#4:** whether output-only human attestation is an evidentiarily defensible standard.
- **#5/#6:** disclosure/remediation obligation when a screened signal already reached a human decision; retention of raw walled evidence.

## 6. What Codex must NOT deploy

- No component enabled on real client/matter/carrier/privileged data — synthetic fixtures only until the approvals above exist (mirrors `probabilistic_calibration_boundary.md`).
- No OSS privacy dependency imported before its review-lane + license/security/privacy pass.
- No auto-promotion, no silent learning, no bypass of `reviewed_learning_gate`, no deletion of append-only evidence, no network/external action from intake.
- QRD must not advertise a formal privacy guarantee it does not have.

## 7. Primary references (verify currency before citing externally)

DP: Dwork-McSherry-Nissim-Smith 2006; Dwork-Roth 2014; Bun-Steinke 2016 (zCDP); Mironov 2017 (RDP); Chaudhuri-Monteleoni-Sarwate 2011; Abadi et al. 2016 (DP-SGD). Reconstruction/MI: Dinur-Nissim 2003; Shokri et al. 2017. k-anon family + limits: Sweeney 2002; Machanavajjhala 2007; Li 2007; Ganta et al. 2008; Narayanan-Shmatikov 2008. Conflict model: Brewer-Nash 1989. IFC: Goguen-Meseguer 1982; Denning 1976; Myers-Liskov (DLM). Unlearning/holdout: Cao-Yang 2015; Bourtoule et al. 2021 (SISA); Dwork et al. 2015 (reusable holdout, Science). Provenance/records: FRE 901(b)(9), 902(13)/(14); C2PA; Mitchell et al. 2019 (model cards); Gebru et al. 2018 (datasheets); RFC 3161. Ethics: ABA Model Rules 1.6/1.9/1.7/1.18/1.10; ABA Formal Op. 512 (2024). Libraries: OpenDP, Google DP, IBM diffprivlib, Opacus, Tumult Analytics.
