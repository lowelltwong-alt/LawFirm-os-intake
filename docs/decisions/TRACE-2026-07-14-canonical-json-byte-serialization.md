# TRACE: Canonical JSON Byte Serialization

## Decision

Write JSON and JSONL artifacts with explicit LF newlines on every platform.

## Why

Hash-bound UI fixtures were generated on Windows with CRLF bytes but committed
with LF normalization. The local Rust manifest then matched the working-tree
bytes while a Linux/GitHub checkout correctly found hash drift. Hashes must bind
the same bytes in local validation, GitHub review, and a future owner runtime.

## Verification

`tests/test_util_serialization.py` rejects CRLF output for JSON and JSONL.
The checked UI fixtures and Rust manifest are regenerated after this change and
must pass the source-hash and snapshot-coherence gates on the final committed
bytes.
