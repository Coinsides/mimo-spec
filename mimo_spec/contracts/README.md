# Contracts

This folder contains machine-readable contracts (JSON Schema, etc.) that define the stable on-disk data formats used by the MIMO toolchain.

## pointer_locator_v0_1.schema.json
Defines the **Pointer + Locator** structure used inside `.mimo` files.

- Pointer: (type, uri, sha256)
- Locator: a media-agnostic coordinate system for backtracking into evidence.

Kinds:
- `line_range` (text)
- `byte_range`
- `page_range` (PDF)
- `time_range` (audio/video)
- `bbox` (images)
