# TRACE-2026-06-24 - Structured Model Adapter Guard

## Situation

The CLI already accepted `--adapter structured-model`, but the selected adapter only produced a ledger note. That was too thin for the v1.0 goal because a future provider boundary needs visible proof of prompt hashes, model/tool budget, denied tools, typed-output requirements, independent critic use, human gates, and deterministic baseline authority.

## Decision

Add `ModelAdapterReport` and write `model_adapter_report.json` for every preflight run.

For `structured-model`, the report is a dry-run guard artifact:

- no provider call;
- no model calls allowed;
- no external tools allowed;
- no network access;
- no external writes;
- no raw payload externalization;
- not approved for real data;
- typed JSON only under exported schemas;
- prompt hashes loaded from `prompts/registry.yaml`;
- zero-call model/tool budget;
- explicit tool denylist;
- independent critic and human confirmation required;
- deterministic workers remain authoritative.

The report is referenced from the preflight packet, run ledger, review package manifest, review package completeness checks, and final matter-opening review package.

## Non-decision

This does not add a provider SDK, call a model, call the network, write externally, approve real-data use, replace deterministic workers, bypass the independent critic, bypass human review, clear conflicts, accept engagement, open matters, docket deadlines, submit budgets, or promote a canonical platform schema.

## Authority impact

This is a local intake adapter-guard artifact. Orchestrator remains the future runtime owner for model/tool routing and prompt authority. Semantic Substrate remains the authority for promoted schemas and governance. Skills Registry remains the authority for promoted skill trust.

## Alternatives rejected

- Leave the adapter as a ledger note: rejected because provider boundaries need typed, reviewable guard evidence.
- Add a real provider call now: rejected because the repo is synthetic-only and no governance decision has approved provider/data posture.
- Hide adapter state in CLI output only: rejected because budget-stage review needs the adapter boundary carried forward.

## Risks and rollback

The main risk is another preflight artifact and required review-package section. That is acceptable because adapter authority is safety-critical. Rollback removes the model, report builder, packet ref, manifest key, completeness requirement, review section, schema export, tests, and docs while keeping deterministic execution unchanged.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 1 file reformatted, then 50 files left unchanged on rerun
- `python -m pytest tests/test_model_adapter_report.py tests/test_review_package.py tests/test_review_package_completeness.py tests/test_north_star_demo.py tests/test_cli_demo.py -q` - passed
- `python scripts/export_schemas.py` - exported 24 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 72 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 50 files already formatted
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

Remaining before merge:

- pushed-branch CI.
