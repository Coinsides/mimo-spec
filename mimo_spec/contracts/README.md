# Contracts

This folder contains machine-readable contracts (JSON Schema, etc.) that define the stable on-disk data formats used by the MIMO toolchain.

## pointer_locator_v0_1.schema.json
Defines the **Pointer + Locator** structure used inside `.mimo` files.

## snapshot_v0_1.schema.json
Defines the **Snapshot** structure used inside `.mimo` files.

## mu_v1_1.schema.json
Defines the `.mimo` **Memory Unit (MU)** contract for schema_version **1.1**.

## id_dedup_v0_1.md
Defines the canonical hashing rules for `content_hash` and `idempotency.mu_key`, plus the dedup policy.

- Pointer: (type, uri, sha256)
- Locator: a media-agnostic coordinate system for backtracking into evidence.

Kinds:
- `line_range` (text)
- `byte_range`
- `page_range` (PDF)
- `time_range` (audio/video)
- `bbox` (images)
