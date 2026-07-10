# TRACE: Candidate Release Browser Proof

## Decision

The local read-only review UI requires a browser smoke check in continuous integration. A TypeScript build alone does not prove that the generated review surface renders, stays local-only, or remains usable at a standard desktop viewport.

## Scope

The check builds `apps/legal-intake-budget`, serves its generated files from a loopback-only static server, and opens the result in headless Chromium. It fails on browser runtime errors, failed asset requests, external requests, an empty review surface, or horizontal overflow at 1440x960.

## Authority And Data Boundaries

The browser check reads generated UI files only. It does not call a backend, write to the Exception Lake, submit a budget, open a matter, invoke a model, use a connector, or load public or real-matter data. Its emitted JSON report is candidate-only validation evidence.

## Rationale

The intake vertical is not authorized to execute legal work. The review UI is valuable only if it makes blockers, evidence, and candidate-only status visible without silently creating a new runtime authority surface. Loopback-only browser proof catches accidental remote dependencies and client-side failures before owner review.

## Verification

Run the following from `apps/legal-intake-budget` after installing dependencies and Chromium:

```powershell
npm run build
npm run smoke:browser
```

The GitHub Actions workflow runs the same check on every pull request and push.
