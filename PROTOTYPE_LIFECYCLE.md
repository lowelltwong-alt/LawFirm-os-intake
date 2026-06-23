# Prototype Lifecycle

Every generated or experimental artifact has an explicit lifecycle state.

```text
scratch
→ experiment
→ staged_candidate
→ reviewed_reference
→ promoted_contract (only in owning sibling repo)
→ deprecated
→ blocked
```

Existence does not imply trust, default use, or canon. This starter's schemas, profiles, worker manifests, prompts, and budget templates are `staged_candidate` or synthetic fixture artifacts unless stated otherwise.
