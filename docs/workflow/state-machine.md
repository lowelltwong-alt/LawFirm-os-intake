# State Machine

```mermaid
stateDiagram-v2
    [*] --> raw_received
    raw_received --> data_origin_validated
    data_origin_validated --> source_inventory_complete
    source_inventory_complete --> segmentation_complete
    segmentation_complete --> party_candidates_ready
    party_candidates_ready --> matter_candidates_ready
    matter_candidates_ready --> deadline_gap_candidates_ready
    deadline_gap_candidates_ready --> evidence_review_complete
    evidence_review_complete --> human_intake_review_required
    human_intake_review_required --> human_intake_confirmed
    human_intake_review_required --> needs_more_information
    human_intake_review_required --> human_only
    human_intake_confirmed --> conflict_seed_ready
    conflict_seed_ready --> budget_preconditions_checked
    budget_preconditions_checked --> budget_proposal_ready
    budget_proposal_ready --> human_budget_review_required
    human_budget_review_required --> blocked_pending_conflicts_and_engagement
```

## Protected transitions

Only an authorized human may create:

- `human_intake_confirmed`
- `declined_or_referred`
- future `human_budget_approved`
- future `conflicts_cleared`
- future `engagement_authorized`
- future `matter_opening_approved`

See `workflow/prohibited-transitions.yaml`.
