(mimo-spec)

## Scope
This repo is: MU (.mimo) spec + pack/validate/extract tools.
Do NOT add memory-system orchestrator code here unless explicitly requested.

## Priorities
1) Backward compatibility of `.mimo` format (schema_version).
2) Deterministic behavior & idempotency.
3) Cross-platform paths (no hard-coded C:\ paths).
4) Minimal dependencies.

## Coding rules
- Prefer `pathlib` and relative paths.
- CLI must accept `--input`, `--output`, `--assets`, `--config` (no global constants).
- Any format change requires updating docs and bumping schema_version.
- Keep PRs small.

## Tests
- Add pytest tests for pack/validate/extract using small fixtures in-repo.
- Provide commands:
  - python -m pytest -q
