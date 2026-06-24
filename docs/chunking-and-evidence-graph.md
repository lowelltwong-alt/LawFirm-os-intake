# Provenance-Preserving Segmentation and Evidence Graph

## Terminology

The starter uses **segmentation** rather than generic token chunking. Structural parent units are preserved first; token subdivision may occur later beneath those units.

## Email segmentation

Preserve:

- message boundary;
- From/To/Cc/Date/Subject headers;
- current message body;
- quoted prior messages;
- signatures;
- attachment references;
- source offsets and hashes.

Quoted history must not be treated as newly authored content.

## Legal document segmentation

Preserve:

- document identity;
- pages;
- headings and subheadings;
- paragraphs;
- tables;
- exhibit references;
- signature blocks;
- attachments;
- parent-child structure.

## No semantic smuggling

Segmentation may preserve observed structure. It may not decide:

- privilege or work product;
- responsiveness;
- represented client;
- adverse-party status;
- legal issue or cause of action;
- evidentiary weight;
- deadline legal effect;
- matter type;
- budget phase applicability.

Those remain candidates or human decisions.

## Required segment fields

```yaml
segment_id:
source_id:
parent_segment_id:
segment_type:
sequence:
start_offset:
end_offset:
sha256:
text:
```

## Required evidence ref fields

Every source-bound evidence reference must be self-contained enough to verify against the cited segment:

```yaml
source_id:
segment_id:
start_offset:
end_offset:
sha256:
```

The strict preflight validator rejects a ref if its source ID, offsets, or hash do not match the segment ID it cites.

The Python reference ingestion boundary writes `ingestion_result.json` with one segment-level evidence ref per segment. A future Rust ingestion adapter must match this artifact before it can replace the Python path.

## Evidence graph

The graph links:

```text
source → segment → candidate → human confirmation → conflict seed/budget proposal
```

Node and edge status must distinguish:

- source evidence;
- candidate;
- human confirmed;
- runtime evidence;
- proposal;
- seed-only search inputs;
- structured evidence;
- canonical reference.

The budget-stage graph also links:

```text
source -> conflict search term -> conflict seed
source/structured ref -> budget support -> budget proposal
human confirmation -> review outcome
source -> party role candidate -> party candidate
```

## Why no graph database yet

A JSON graph is inspectable, portable, and sufficient for the first workflow. Introduce a graph database or GraphRAG only when evaluation shows a real bottleneck in relationship traversal, entity resolution, or multi-document retrieval.

## Chunking quality tests

- exact offset/hash preservation;
- `ingestion_result.json` parity for inventory, coverage summary, segments, and segment evidence refs;
- evidence refs match cited segment offsets and hashes;
- every party-role candidate has packet-bound evidence refs;
- quoted email separation;
- attachment inventory completeness;
- non-target text identity after transformations;
- no candidate without evidence ref;
- no hidden role or legal-status field in segment records.
