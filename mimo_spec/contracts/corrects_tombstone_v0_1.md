# CORRECTS & Tombstone v0.1 (P0-B)

This document defines the **append-only correction** and **tombstone deletion marker** contracts for MU v1.1.

## Goals
- Corrections must be **append-only** (never edit old MU files)
- Deletions must be **traceable** (no silent disappearance)

## 1) CORRECTS (links.corrects)
- A correction is represented by a **new MU** that points to the old MU via:
  - `links.corrects: ["<old_mu_id>"]`
- Resolution rule (system-side): when an MU is corrected, prefer the newest correction in normal mode.

## 2) Tombstone (tombstone object)
A tombstone is represented as an object stored inside a MU:

```yaml
tombstone:
  target_mu_id: "mu_..."
  created_at: "2026-02-21T00:00:00Z"
  actor: "owner"
  reason: "..."
  scope: "all"  # all|public_exports_only|injection_only
  retain_raw: true
```

Notes:
- Tombstone is **append-only**: create a new MU containing tombstone instead of deleting anything.
- System-side enforcement (memory_system): tombstoned MU should not be used in normal retrieval/injection.

## Compatibility
- MU v1.1 adds optional field `tombstone`.
- Existing tools should treat tombstone MUs as valid MUs.
