# Practice Context

## Why practice context matters

The same words can imply different likely workflows depending on the firm and practice. An insurance-defense practice receives assignments from carriers. A plaintiff personal-injury practice receives help requests from individuals. A commercial-litigation practice receives direct corporate disputes.

Without context, the model may rank the wrong matter type. With uncontrolled context, it may force every source into the firm’s dominant practice. The design therefore uses context as a transparent prior, never as evidence.

## Context hierarchy

```text
firm profile
+ office profile
+ practice-group profile
+ client/referral-source profile
+ human-confirmed matter facts
+ run-specific restrictions
```

## Precedence

```text
observed source evidence
> human-confirmed matter facts
> client/referral-source profile
> practice-group profile
> firm defaults
```

Context cannot override a contradiction in the source. Human-confirmed facts are not model context; they are governed review artifacts.

## Profile fields

A practice profile may contain:

- profile ID, version, effective date, approver, and hash;
- offices and jurisdictions;
- active practices and default side;
- typical inbound source mix;
- matter-family priors;
- required intake fields;
- reporting or guideline source references;
- budget template IDs;
- synthetic or authorized rate references;
- escalation and approval rules.

## Private configuration

Real firm profiles must never be committed to this public/source-available repo. Future operational profiles should live in an approved private configuration store. Runs record only the resolved profile ID, version, and hash unless policy permits more.

## Learning

Human corrections may become `profile_change_candidate` evidence after repeated reviewed examples. They never silently change the profile.

## Counterfactual test

Run the same source under:

- synthetic insurance defense;
- synthetic plaintiff personal injury;
- synthetic commercial litigation.

Expected behavior:

- source segment hashes remain identical;
- observed evidence refs remain identical;
- candidate rankings may change;
- unknown remains available;
- human confirmation remains mandatory.
