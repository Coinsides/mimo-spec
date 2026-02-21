# ID & Dedup v0.1 (P0-E)

This document defines the **canonical hashing** rules used for MU v1.1:
- `idempotency.mu_key` (dedup key)
- `content_hash` (content identity)

## Goals
- Prevent library pollution (duplicate MUs)
- Support sync/repair and future migrations
- Keep hashing deterministic and testable

## Hash format
All hashes are stored as:
- `sha256:<64-hex>`

## Canonicalization
All objects hashed MUST be serialized as canonical JSON:
- UTF-8
- `sort_keys=true`
- no whitespace (`separators=(",", ":")`)

## mu_id
- `mu_id` is **NOT** idempotent.
- It is a stable reference / filename-friendly identifier.

## idempotency.mu_key (v0.1)
Purpose: detect "same source, same slice".

Current v0.1 seed (as implemented in `mimo_pack.py`):
```json
{
  "pointer": {"type":"file","path":"...","timestamp":"..."},
  "group_id": "...",
  "order": "...",
  "span": "..."
}
```
Hash:
- `sha256(canonical_json(seed))`

Notes:
- This will likely evolve to a stricter seed based on `pointer+locator+raw_id/span` once the full pointer.resolve + vault manifest is in place.

## content_hash (v0.1)
Purpose: detect "same MU content" (for sync integrity / near-dup detection).

Seed:
```json
{
  "schema_version": "1.1",
  "summary": "...",
  "snapshot": {
    "kind": "text",
    "codec": "gz+b64",
    "payload": {"text_gz_b64": "..."}
  }
}
```

## Dedup policy (mimo-pack)
`mimo-pack` supports:
- `--dedup=skip` (default): if `mu_key` already exists in output, skip writing a new MU.
- `--dedup=alias` (not implemented yet)
- `--dedup=versioned` (not implemented yet)
