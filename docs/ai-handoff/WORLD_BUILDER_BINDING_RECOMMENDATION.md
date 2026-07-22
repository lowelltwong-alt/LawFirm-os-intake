# World Builder — recommendation + candidate adapter binding

Decision context: you want the World Builder as a **separate, modular
workspace/repo** that works *with* Law Firm Sim and can build *other* law-firm-
document worlds. This resolves DAD's `adapter:world-builder` (`target_unresolved`)
toward a **new dedicated repo**, not a fold-in to intake or Law Firm Sim.
Candidate only — the hub-registry edit and repo creation are yours to apply.

## Recommendation: a new `lawfirm-synthetic-world-builder` repo

Role and relationships (keeps every DAD authority boundary intact):

- **Law Firm Sim = deterministic truth kernel.** The World Builder does NOT own
  world truth. Per the DAD synthetic-silver contract, its generators are
  **proposal-only JobManifest/JobResult workers** on top of the Sim kernel, which
  keeps sole ownership of canonical state and its G0–G2 gates. That is how it
  "works with the law firm sim thing."
- **Modular = pluggable "worlds."** Each world is a synthetic law-firm-document
  corpus family (e.g. intake bundles, litigation artifacts, carrier
  correspondence, employment records). A world-definition interface + pluggable
  generators / deterministic validators / judges lets you add worlds without
  touching the others.
- **Emits the DAD record contracts.** Every corpus produces
  `synthetic-silver-provenance-record` (per item) and
  `synthetic-silver-release-manifest` (per release). Corpus content lives in this
  repo (factory plane); DAD only holds the contract.
- **Feeds LawFirm-os-intake as a consumer.** Intake→budget ingests World
  Builder-generated synthetic intake docs — this is Phase 1 of the intake plan.
- **Its own DAD enrollment.** New repo → its own wave + approval id → then
  `adapter:world-builder` is bound and active.

Layering: `Law Firm Sim (kernel/authority)` → `World Builder (modular factory,
proposal-only)` → `LawFirm-os-intake (consumer + its own silver factory for
budget outputs)`; `DAD` holds the contract for all of them.

## Candidate `adapter:world-builder` entry (apply in the hub registry when the repo exists)

Replace the `target_unresolved` entry in
`04_Digital_Assett_Directory/registry/synthetic-silver-program-registry.json`:

```json
{
  "adapter_id": "adapter:world-builder",
  "target": "LawFirm Synthetic World Builder (modular corpus factory)",
  "target_repo": "lawfirm-synthetic-world-builder",
  "mode": "sovereignty_child_pointer",
  "write_policy": "dad_never_writes",
  "notes": "Separate modular repo. Builds multiple law-firm-document 'worlds' as proposal-only JobManifest/JobResult producers on top of the Law Firm Sim deterministic kernel, which retains sole world-truth authority and its G0-G2 gates. Emits synthetic-silver provenance records and release manifests. Feeds LawFirm-os-intake as a synthetic-intake consumer. Requires its own DAD enrollment wave before the pointer is active."
}
```

Also update the program doc adapter table and remove the research-backlog line
"Confirm the World Builder target repository identity and bind
adapter:world-builder or retire it."

## Next steps (yours / Fable's plan to sequence)
1. Create the `lawfirm-synthetic-world-builder` repo (scaffold: world-definition
   interface, one example world, deterministic validators, DAD front-door files).
2. Enroll it in DAD (own wave + approval id).
3. Apply the adapter entry above in the hub.
4. Build the first world; feed it into intake→budget (Phase 1).

The **gold anchor** decision is deferred to Fable (see the planning brief).
