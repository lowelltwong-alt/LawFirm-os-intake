# Agent Run Ledger

Every meaningful run should record enough information to reconstruct what occurred without relying on a vendor dashboard or hidden model reasoning.

## Minimum fields

```yaml
run_id:
parent_run_id:
workflow_id:
step_index:
worker_id:
mode: explore | plan | build | validate | review | runtime
practice_profile_id:
practice_profile_version:
practice_profile_hash:
contract_pins:
input_artifact_refs:
source_scope:
allowed_tools:
permission_mode:
model_class:
provider_model_if_used:
prompt_ref:
prompt_version:
prompt_hash:
started_at:
ended_at:
status:
output_artifact_refs:
validation_results:
human_review_required:
human_decision_ref:
escalation_triggers:
prohibited_action_attempts:
result_class: proposal | validated_artifact | blocked | rejected | lesson_candidate
```

The starter emits a smaller JSONL event record; the fields above are the target platform contract.
