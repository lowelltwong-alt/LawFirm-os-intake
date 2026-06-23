# Repository Role

## Role statement

`LawFirm-os-intake` is the **vertical reference implementation, evaluation harness, and workflow specification** for prospective-matter intake through legal budget proposal.

It demonstrates how the five LawFirm OS platform repos cooperate on one bounded value stream.

## This repo owns

- the end-to-end intake-to-budget state machine;
- vertical acceptance criteria;
- synthetic practice profiles and fixtures;
- specialist worker manifests and prompt contracts;
- counterfactual practice-context tests;
- escalation rules specific to intake;
- public-data source catalog and test plan;
- synthetic/adversarial evaluation suites;
- cross-repo contract tests;
- a runnable local reference flow;
- graduation criteria for promoting reusable components into sibling repos.

## This repo does not own

- canonical party-role or matter taxonomies;
- canonical schemas after promotion;
- firm-wide model or tool routing;
- general approval doctrine;
- Exception Lake storage contracts;
- production legal retrieval;
- reusable skill trust decisions;
- production connectors;
- the general orchestration runtime.

## Graduation model

A component starts here as `candidate` or `fixture`. It may be promoted only through the owning sibling repo:

- schema/registry/governance → Semantic Substrate;
- runtime gate/adapter/workflow engine → Orchestrator;
- event/audit/learning record → Exception Lake;
- reusable specialist skill → Skills Registry;
- public/legal source adapter and context bundle → Legal Knowledge Runtime.

This repo then pins the promoted contract and removes or clearly deprecates the local candidate copy.
