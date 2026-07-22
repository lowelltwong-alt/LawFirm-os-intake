# Public Gold Strategy — Training Legal-Budget ML Without Internal Firm Gold

Status: researched candidate strategy (web-verified 2026-07-21). Candidate-only.
Routed to DAD as a candidate mail packet for lesson processing.

## The essential question

"How do I train this with machine learning without an internal firm reference
point for gold budgets?" — the firm will not release budgets until the system is
delivered, so internal gold is structurally unavailable until after v1 ships.

## The answer in one paragraph

Court-adjudicated fee outcomes ARE the missing gold. US courts publicly
adjudicate the reasonableness of real law-firm budgets, hours, rates, and
phase allocations every week, and in large Chapter 11 cases law firms are
*required* to file actual budgets and staffing plans on the public docket.
A judge or fee examiner approving/cutting a fee application is a qualified,
independent human adjudication — exactly the semantic the DAD synthetic-silver
program requires of a gold anchor. You cannot get *your firm's* gold yet, but
you can get a *reference-class* gold corpus: real budgets and adjudicated
outcomes for matters like yours. Silver moves the corpus; this public gold
measures it; the firm's own data recalibrates it later (the "deliver first,
then recalibrate" unlock).

## Verified public gold sources (three tiers)

### Tier 1 — per-matter budget gold (the strongest find; verified)
**Large Chapter 11 fee applications under the UST Appendix B guidelines.**
For cases ≥$50M assets and ≥$50M liabilities (filed on/after 2013-11-01), the
DOJ US Trustee guidelines require: **budgets and staffing plans**, billing by
**project category** (Exhibit D summaries; UTBMS-aligned task codes),
**searchable electronic billing records**, rate disclosures and rate-increase
disclosures, and fee examiners in the largest cases who publish
budget-vs-actual analyses. Courts then adjudicate every dollar. Access is free
via CourtListener/RECAP and claims agents (Kroll, Stretto, Epiq host dockets).
This is real firm budget data, with actuals, with independent adjudication, on
the public record.
Academic precedent: the **LoPucki-Doherty professional-fees datasets are
public** (UCLA/UFL Bankruptcy Research Database) and back a published
**fee-prediction calculator** — regression models of professional fees from
public court files. Public-data legal-budget ML is not novel; it has a
published, peer-reviewed precedent with downloadable data.

### Tier 2 — phase/rate gold (litigation + insurance defense)
- **Fee-shifting award opinions** (§1988 civil rights, FLSA, ERISA, patent
  §285, Lanham, IDEA): courts adjudicate reasonable hours by phase, rates by
  market, and publish itemized cuts. Free full-text via CourtListener/GovInfo.
- **Class-action/securities lodestar petitions**: hours-by-timekeeper and
  phase declarations plus judicial lodestar cross-checks.
- **Published rate matrices**: USAO Attorney's Fees Matrix, Laffey Matrix —
  court-accepted rate schedules by experience band.
- **Insurance defense specifically:**
  - *Independent-counsel (Cumis-type) rate litigation*: courts adjudicate
    reasonable insurance-defense rates (published opinions; awards exceeding
    $700/hr have been upheld — the disputes themselves put carrier panel rates
    and defense billing guidelines on the record).
  - *Public-entity risk pools* (e.g., PRISM in California): publish defense
    counsel standards, billing guidelines, and rate structures as public
    agency documents.
  - *Bad-faith and coverage litigation*: defense billing records entered as
    exhibits; carrier billing guidelines produced in discovery and filed.
  - *Municipal/JPA defense spend*: invoices and rate schedules in public
    council agendas and via records requests.

### Tier 3 — distribution anchors (aggregate calibration)
- **NAIC Schedule P** defense-and-cost-containment (DCC/ALAE) aggregates by
  line of business from statutory filings — defense-cost ratios per premium
  and per claim for insurance-defense calibration.
- Public summaries of industry rate surveys (e.g., Real Rate Report/
  CounselLink trend releases); city attorney budgets; AG outside-counsel
  contracts.

## ML design without internal gold (reference-class approach)

1. **Two gold layers, different jobs.** (a) *Process gold* (already decided):
   reviewed synthetic output-state labels for workflow correctness. (b)
   *Reference-class dollar gold* (this strategy): public adjudicated fee
   outcomes for budget realism and calibration. They are complementary;
   neither claims to be firm pricing truth.
2. **Ingestion only through the roadmap §18 public-source gate chain**
   (methodology review → conversion review → red-team identity-reconstruction
   → cache custody). Extraction to structured phase/rate records with span-
   level provenance per the DAD provenance-record schema.
3. **Stratify and freeze a holdout.** Strata: forum, case family (restructuring
   / fee-shifting litigation / insurance-defense-adjacent), size band, era.
   The holdout is untouched: excluded from prompts, examples, tuning,
   threshold selection, and training (DAD non-negotiable #3). Temporal splits
   come free (filing years) — satisfying the repo's XGBoost precondition
   design (temporal splits, leakage checks).
4. **Calibrate silver against gold (S2).** The World Builder's synthetic
   budgets/actuals are calibrated so their *distributions* (phase shares, rate
   ranges, variance magnitudes, cut frequencies) match the public reference
   class per stratum — this is the DAD "gold-anchor calibration" that lifts
   silver from S1 to S2.
5. **Predict intervals, not points.** Quantile/conformal models for phase cost
   ranges, variance risk, and rejection risk, evaluated only on the frozen
   holdout, reported with uncertainty. The LoPucki-Doherty calculator is the
   baseline-challenger precedent (deterministic regression baseline first —
   matching the repo's stated XGBoost gate).
6. **Say the domain-shift truth.** Public per-matter budget gold is
   restructuring-skewed; insurance-defense per-matter budgets are rarer (rate
   litigation + risk pools + aggregates partially fill it). Treat public gold
   as a covariate-shifted reference class: measure the shift, present
   intervals, and never claim firm-level calibration until firm data exists.
   After delivery, firm data recalibrates the same pipeline (the handicap is
   temporary; the architecture is not).
7. **This satisfies the repo's training boundary.** "Training waits for
   governed reviewed historical outcomes" — public court-adjudicated outcomes,
   human-reviewed through the §18 gates and adjudicated for mapping by the
   owner, *are* governed reviewed historical outcomes for the reference class.

## First concrete increment (PR-sized)
Curate a **pilot anchor set (~30–50 outcomes)**: ~10 large Chapter 11 matters
with filed budgets + fee-examiner budget-vs-actual reports; ~20 fee-shifting
opinions with itemized hours/rates/cuts; ~5 insurance-defense rate
adjudications / risk-pool schedules. Extract to a versioned anchor schema with
span provenance; owner adjudicates the *mapping* (not the court's money);
freeze the holdout split; record a DAD release manifest. Then wire silver S2
calibration to it.

## DAD processing
This strategy is routed to DAD as a candidate mail packet (outbox, metadata +
pointer only) for screening and lesson processing; the DAD lesson-graph is
stale and should pick it up on its next regeneration. Candidate additions to
DAD research backlogs: the Tier 1–3 source families above for the
research-intake registry and the synthetic-silver program's gold-anchor lane.

## Sources (verified 2026-07-21)
- Federal Register: UST Appendix B guidelines (budgets/staffing plans/project
  categories): https://www.federalregister.gov/documents/2013/06/17/2013-14323/
- LoPucki BRD public professional-fees data: https://lopucki.law.ucla.edu/professional_fees.php
  and fee calculator: https://lopucki.law.ufl.edu/fee_calculator_prediction.php
- PRISM liability defense counsel standards: https://www.prismrisk.gov/about-prism/prism-documents/claims/standards/defense-counsel-standards/
- Independent-counsel rate adjudication: https://millerfriel.com/insurer-must-pay-counsel-rates-excess-700-per-hour/
  and ABA overview: https://www.americanbar.org/groups/litigation/resources/newsletters/insurance-coverage/independent-defense-counsel-rate-caps-guidelines-deductions-oh-my/
- Defense-cost/ALAE background: https://www.perrknight.com/2009/04/01/controlling-claims-costs-long-look-litigation-expenses/
