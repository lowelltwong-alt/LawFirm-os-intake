# TRACE: Skills Registry Specialist Review

## Context

The remaining-roadmap report names Skills Registry specialist review as an
owner-gated follow-up. The repo already has predeclared worker YAML files,
prompt files, and prompt registry hashes, but a generic owner-adoption packet is
too coarse for supply-chain review. Skills Registry needs a worker-by-worker
view of prompt hashes, context scope, tool authority, schema refs, declared
harness coverage, human gates, revocation owner, and frontier-adjudicator
boundaries.

## Decision

Add `build-skills-registry-specialist-review`.

The command consumes:

- `skill-agent-manifest.json`;
- `agents/*.yaml`;
- declared `harnesses/*.yaml`;
- `prompts/registry.yaml`;
- local schema refs under `schemas/`.

It writes:

- `skills_registry_specialist_review_report.json`;
- `skills_registry_specialist_review_report.md`;
- `skills_registry_specialist_candidates.jsonl`;
- per-worker JSON/Markdown packets under `skills_registry_specialist_packets/`.

The command also makes candidate metadata explicit in the seven agent YAMLs:
prompt refs, schema refs, empty allowed-tool lists, human gate requirement, and
Skills Registry revocation owner.

## Boundary

The report is local candidate metadata for Skills Registry owner review only. It
does not promote skills, create trust records, add dynamic agents, enable model
providers, approve real data, create issues, open PRs, write sibling repos,
promote canon, admit Lake/SQLite records, perform external writes, or apply
learning.

## Red-Team Notes

- A prompt hash and clean metadata are not a promoted skill trust record.
- Frontier adjudication is the highest-risk specialist and must remain
  bounded-packet-only, no-tools, and human-gated.
- Tool authority must stay deny-by-default because a promoted specialist could
  otherwise become a connector or external-action bypass.
- Metadata gaps must block review readiness instead of being hidden by prose.

## Validation Plan

- Current manifest, worker YAML, declared harness refs, prompt registry, prompt
  files, and schema refs produce seven ready specialist candidates and fourteen
  per-worker packet files.
- Removing schema metadata in a copied test surface blocks the affected worker.
- Prompt hash drift in a copied test surface blocks the affected worker.
- Removing a declared harness in a copied test surface blocks the report.
- CLI output proves no skill promotion, trust-record creation, dynamic agent,
  provider enablement, real-data approval, GitHub write, sibling-repo write,
  Lake/SQLite write, external write, or silent learning.
