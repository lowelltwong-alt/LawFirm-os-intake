# Upfront Intake Integration Research

Status: public-research candidate, synthetic-only implementation guidance.

## What Was Researched

The product appears to be **Upfront(TM) New Business Intake & Conflicts by
Fulcrum GT**, not a generic intake form tool. Public sources describe it as a
new business intake, conflicts, risk, workflow, and ethical-screening platform
for law firms.

Publicly available sources used:

- Fulcrum GT Upfront product page:
  `https://fulcrumgt.com/solutions/upfront/`
- Legaltech Hub vendor profile:
  `https://www.legaltechnologyhub.com/vendors/upfront-by-fulcrum-gt/`
- Fulcrum GT Upfront brochure:
  `https://a.storyblok.com/f/102444/x/50e3547cd3/upfront-brochure.pdf`
- Fulcrum GT technology/integrations page:
  `https://fulcrumgt.com/solutions/technology/`
- Fulcrum GT SCREENS whitepaper:
  `https://knowledgebase.fulcrumgt.com/wp-content/uploads/2024/09/Upfront-Screens-Whitepaper.pdf`
- Fulcrum GT SCREENS announcement:
  `https://knowledgebase.fulcrumgt.com/fulcrum-gt-introduces-screens-to-reduce-law-firm-risks/`
- Fulcrum GT LinkedIn product post:
  `https://www.linkedin.com/posts/fulcrumgt_an-onboarding-truth-activity-7432132557573623808-cg4E`

## Publicly Supported Capability Map

The public materials support these Upfront-like capability assumptions:

- configurable intake forms and workflow administration;
- role-based workflows for attorneys, staff, risk teams, conflicts teams, and
  approval stakeholders;
- intake requests for new clients and matters;
- required-information capture at the start of intake;
- AML/KYC validation rules and compliance checks;
- risk scoring and client evaluation;
- external risk, sanctions, and compliance source integration;
- self-service, ad hoc, and full conflict searches launched during intake;
- conflict evaluation, attorney review, clearance tracking, interactive
  conflict reports, and traceable decision-making;
- intelligent labels, tagging, and relationship insights;
- a data warehouse or single-source-of-truth surface for finalized clients,
  matters, related parties, risk assessments, and client history;
- lateral-hire intake that can upload client/matter lists and convert approved
  items into full records;
- reporting dashboards for intake, conflicts, screens, clearance, workload, and
  turnaround metrics;
- mobile access for requests, tasks, approvals, and conflict searches;
- SCREENS ethical-wall workflows with access lists, notifications, audit logs,
  acknowledgments, dashboards, and downstream-system integration;
- integration with third-party PMS, DMS, LPM, case-management, risk, compliance,
  and analytics systems.

## What Is Not Publicly Proven

No public Upfront API reference, field-level export schema, webhook contract,
admin manual, request payload examples, output JSON examples, authentication
model, endpoint list, or event catalog was found in public search. Public
materials say Fulcrum Snap supports prebuilt integrations and APIs, but do not
publish an Upfront-specific API contract.

Therefore this repo must not assume:

- endpoint names;
- auth scheme;
- webhook names;
- canonical Upfront object IDs;
- field names used by a real firm tenant;
- conflict report structure;
- matter-number lifecycle;
- screen event lifecycle;
- write-back permissions.

Any real connector belongs to Orchestrator and requires vendor/firm-provided
documentation plus human approval.

## Candidate Upfront-Like Input Shape

If this repo needs to consume Upfront output later, expect a normalized source
bundle with these groups:

- request identity: intake request ID, status, request type, practice group,
  opened/updated timestamps, requester, responsible attorney, risk owner;
- channel metadata: portal, email, mobile, manual entry, imported file, lateral
  list, or API/import source;
- firm/future-system IDs: client ID, matter ID, request ID, conflict search ID,
  screen ID, workflow task IDs;
- external references: adjuster reference, carrier claim number, policy number,
  insured reference, incident/loss date, agency charge number, court/docket
  number, RFP/budget request ID, and sender email/thread IDs;
- parties and relationships: prospective client, represented entity, payer,
  carrier, insured, claimant, employee, employer, affiliate, individual
  supervisor, opposing counsel, requesting attorney, referring party, vendor,
  expert, agency, court, and unknown role alternatives;
- conflicts search seed: exact terms, aliases, normalized names, related-party
  graph, relationship types, source refs, and unresolved role candidates;
- risk/compliance: AML/KYC status, sanctions status, risk score, risk reasons,
  required approvals, clearance status, review comments;
- ethical screens: proposed screen reason, screened persons/groups, access list,
  acknowledgments, downstream systems, audit refs;
- attachments/source inventory: file names, MIME types, source IDs, hashes,
  duplicate groups, missing attachment states, unread/unparsable states, quoted
  history boundaries, and source offsets where available;
- workflow state: current step, assigned role, due date, approvals, rejects,
  deferrals, required next action, audit trail.

## Candidate Upfront-Like Output Shape We Should Produce If We Are Doing Its Job

Until real Upfront docs are supplied, this repo should produce an
`upfront_like_intake_output_candidate` that is intentionally narrower than a
real Upfront export:

- it must carry source refs, hashes, and exact support for every observed fact;
- it may propose candidate matter links but cannot finalize a matter link;
- it may carry external/internal references but cannot infer they are unique;
- it must distinguish sender identity from matter identity;
- it must preserve unknown role alternatives instead of collapsing them;
- it must create conflict-search seeds, not conflict conclusions;
- it must record risk/compliance/screen candidates, not approvals;
- it must record blocked/missing facts for budget readiness;
- it must surface candidate Exception Lake labels for unresolved matching,
  missing IDs, duplicate sources, conflicting references, and source ambiguity;
- it must never create or submit client, matter, budget, screen, conflict,
  billing, court, or Lake records.

See `examples/synthetic/upfront/upfront-like-intake-output.example.json`.

The local compatibility report currently exposes only a candidate request ID,
request channel, typed external-reference counts, and unknown-reference counts.
It validates observed external references against the source inventory; these are
not vendor field names, real object IDs, or an API guarantee.

## Document-To-Matter Matching Problem

The user's specific risk is real: the same adjuster or carrier contact may send
multiple documents for multiple unrelated cases, sometimes before the firm has
an official matter number. The system must avoid over-linking.

Candidate deterministic signal classes:

- strong positive signals: official matter number, Upfront request ID, conflict
  search ID, carrier claim number, policy number, court docket, agency charge
  number, unique insured/claimant pair, incident/loss date, same attachment hash
  already assigned to a candidate request;
- medium signals: exact party pair, exact opposing counsel, exact caption,
  same adjuster reference, thread ID with consistent subject/reference, same
  policy and insured;
- weak/context signals: sender email, carrier name, general practice area,
  vague subject line, repeated template language, forwarding chain;
- negative signals: different claimant/employee, different insured/employer,
  different loss/employment date, different docket/agency number, conflicting
  carrier reference, same sender with different subject/reference, attachment
  hashes belonging to another candidate.

Required uncertainty states:

- `unmatched_new_candidate`: no known request/matter candidate is strong enough;
- `linked_high_evidence_candidate`: enough source-bound identifiers agree, but
  still needs human confirmation before matter opening;
- `ambiguous_multiple_candidates`: more than one candidate has plausible support;
- `conflicting_identifiers`: strong identifiers disagree;
- `insufficient_identifiers`: only weak sender/thread/practice signals exist;
- `requires_sender_followup`: missing claim/reference/party facts must be
  requested from the sender;
- `requires_human_linking_review`: reviewer must confirm or split documents.

Candidate Exception Lake labels for future owner review:

- `source_matter_link_ambiguous`;
- `multiple_possible_matters_same_sender`;
- `missing_official_matter_number`;
- `unresolved_sender_internal_reference`;
- `conflicting_external_reference`;
- `source_attachment_unlinked`;
- `source_thread_cross_matter_risk`;
- `document_cluster_split_required`;
- `document_cluster_merge_candidate`.

## Roadmap Slice

Implement `matter-linking-preflight` before any real Upfront connector:

1. Add synthetic source bundles where one adjuster sends documents for two
   unrelated cases with overlapping carrier names and no official matter number.
   Initial fixture and deterministic audit: `lawfirm-os-intake
   audit-matter-linking-preflight --input
   examples/synthetic/upfront/upfront-like-intake-output.example.json --out-dir
   <dir>`.
2. Add synthetic bundles where a later email supplies a carrier claim number or
   Upfront-like request ID that resolves the cluster. Initial fixture:
   `examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json`.
3. Add deterministic matching candidate contracts with source-bound signal
   evidence, negative evidence, and explicit uncertainty state.
4. Add human review artifact to confirm, split, merge, mark unknown, or request
   more information. Local candidate command added:
   `lawfirm-os-intake record-matter-linking-review-outcome
   --matter-linking-preflight-report <dir>/matter_linking_preflight_report.json
   --outcome examples/synthetic/upfront/matter-linking-review-confirm-split.outcome.json
   --out-dir <dir>`.
5. Add dry-run Lake mapping candidates for unresolved matching and follow-up.
6. Add UI panels for unmatched/ambiguous/conflicting clusters and the recorded
   matter-linking review outcome.
7. Add an aggregate QA gate that replays the required matter-linking holdouts,
   including ambiguous same-sender/multi-case input, resolved follow-up split
   candidates, weak-only blocked packets, resolved single candidates, and
   conflicting external identifiers:
   `lawfirm-os-intake audit-matter-linking-qa-gate --repo-root . --out-dir
   <dir>`.
8. Keep all real Upfront API work out of intake until Orchestrator receives a
   reviewed vendor contract.

## Acceptance Tests For That Slice

- same sender plus same carrier but different claimant/insured must not merge;
- same claim number plus same party pair may become a high-evidence candidate;
- conflicting claim numbers must block linking;
- no official matter number must remain explicit;
- weak signals alone must route to human review or sender follow-up;
- every match signal must carry source refs and hashes;
- prompt-injection text inside an email cannot force a link;
- duplicate attachments collapse by hash but do not collapse matters by
  themselves;
- output remains local JSON only, candidate-only, no connector, no Lake/SQLite
  write, no matter opening, and no conflict conclusion.
