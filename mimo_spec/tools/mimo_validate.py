from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import sys
from pathlib import Path

import jsonschema
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# No hardcoded roots; pass --in explicitly.

REQUIRED_TOP_V1_0 = ["schema_version", "id", "meta", "summary", "pointer", "snapshot"]
REQUIRED_TOP_V1_1 = [
    "schema_version",
    "mu_id",
    "content_hash",
    "idempotency",
    "meta",
    "summary",
    "pointer",
    "snapshot",
    "links",
    "privacy",
    "provenance",
]

REQUIRED_META = [
    "time",
    "source",
    "group_id",
    "order",
    "span",
    "has_assets",
    "has_struct_data",
]

# Pointer+Locator v0.1 (new style)
LOCATOR_KINDS = {"line_range", "byte_range", "page_range", "time_range", "bbox"}


def err(code, path, msg):
    return {"code": code, "path": path, "msg": msg}


def validate_file(path: str) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [err("E_YAML", path, f"YAML parse error: {e}")], []

    if not isinstance(data, dict):
        return [err("E_YAML", path, "YAML root must be a mapping")], []

    sv = str(data.get("schema_version") or "")

    required = REQUIRED_TOP_V1_1 if sv == "1.1" else REQUIRED_TOP_V1_0
    for k in required:
        if k not in data:
            errors.append(err("E_REQUIRED", path, f"Missing: {k}"))

    # v1.1: enforce JSON Schema contract (when present)
    if sv == "1.1":
        schema_path = Path(__file__).resolve().parents[1] / "contracts" / "mu_v1_1.schema.json"
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            errors.append(err("E_SCHEMA", path, f"MU v1.1 schema validation failed: {e.message}"))
        except Exception as e:
            errors.append(err("E_SCHEMA", path, f"MU v1.1 schema validation failed: {e}"))

    if "meta" in data and not isinstance(data["meta"], dict):
        errors.append(err("E_TYPE", path, "meta must be dict"))
    if "pointer" in data and not isinstance(data["pointer"], list):
        errors.append(err("E_TYPE", path, "pointer must be list"))
    if "summary" in data and not isinstance(data["summary"], str):
        errors.append(err("E_TYPE", path, "summary must be string"))

    meta = data.get("meta", {}) if isinstance(data.get("meta", {}), dict) else {}

    for k in REQUIRED_META:
        if k not in meta:
            errors.append(err("E_REQUIRED", path, f"Missing meta: {k}"))

    # allow meta.source to be string (preferred). if dict, keep legacy tolerance.
    src = meta.get("source")
    if not (isinstance(src, str) or isinstance(src, dict)):
        errors.append(err("E_TYPE", path, "meta.source must be string (preferred) or dict (legacy)"))

    # asset consistency
    if meta.get("has_assets") is True and not meta.get("shared_assets"):
        warnings.append(err("W_ASSET", path, "has_assets=true but shared_assets empty"))
    if meta.get("has_struct_data") is True and "struct_data" not in data:
        warnings.append(err("W_STRUCT", path, "has_struct_data=true but struct_data missing"))

    if sv and str(sv) not in {"1.0", "1.1"}:
        warnings.append(err("W_SCHEMA", path, f"schema_version={sv} (expected 1.0 or 1.1)"))

    # snapshot minimal contract
    snap = data.get("snapshot")
    if isinstance(snap, dict):
        kind = snap.get("kind")
        codec = snap.get("codec")
        if kind not in {"text", "web", "audio", "image", "other"}:
            errors.append(err("E_SNAPSHOT", path, f"snapshot.kind invalid: {kind}"))
        if codec not in {"plain", "gz+b64"}:
            errors.append(err("E_SNAPSHOT", path, f"snapshot.codec invalid: {codec}"))

        src_ref = snap.get("source_ref")
        if not isinstance(src_ref, dict) or not src_ref.get("sha256") or not src_ref.get("uri"):
            errors.append(err("E_SNAPSHOT", path, "snapshot.source_ref must include uri + sha256"))

        payload = snap.get("payload")
        if not isinstance(payload, dict):
            errors.append(err("E_SNAPSHOT", path, "snapshot.payload must be dict"))
        else:
            if codec == "plain":
                if "text" not in payload or not isinstance(payload.get("text"), str):
                    errors.append(
                        err(
                            "E_SNAPSHOT",
                            path,
                            "snapshot.payload.text required for codec=plain",
                        )
                    )
            if codec == "gz+b64":
                b64 = payload.get("text_gz_b64")
                if not isinstance(b64, str):
                    errors.append(
                        err(
                            "E_SNAPSHOT",
                            path,
                            "snapshot.payload.text_gz_b64 required for codec=gz+b64",
                        )
                    )
                else:
                    try:
                        raw = gzip.decompress(base64.b64decode(b64.encode("utf-8")))
                        if len(raw) > 20_000:
                            warnings.append(
                                err(
                                    "W_SNAPSHOT",
                                    path,
                                    "snapshot text > 20KB; consider splitting MU",
                                )
                            )
                    except Exception:
                        errors.append(err("E_SNAPSHOT", path, "snapshot.payload not decodable"))

    # pointer checks
    ptrs = data.get("pointer")
    if isinstance(ptrs, list):
        for i, p in enumerate(ptrs):
            if not isinstance(p, dict):
                errors.append(err("E_POINTER", path, f"pointer[{i}] must be object"))
                continue

            # new style
            if "uri" in p or "sha256" in p or "locator" in p:
                if not p.get("uri") or not p.get("sha256") or not isinstance(p.get("locator"), dict):
                    errors.append(
                        err(
                            "E_POINTER",
                            path,
                            f"pointer[{i}] must include uri + sha256 + locator",
                        )
                    )
                else:
                    loc = p.get("locator") or {}
                    if loc.get("kind") not in LOCATOR_KINDS:
                        errors.append(
                            err(
                                "E_POINTER",
                                path,
                                f"pointer[{i}].locator.kind invalid: {loc.get('kind')}",
                            )
                        )
                    if loc.get("kind") == "line_range":
                        try:
                            s = int(loc.get("start"))
                            e = int(loc.get("end"))
                            if s < 1 or e < 1 or s > e:
                                errors.append(
                                    err(
                                        "E_LOCATOR",
                                        path,
                                        f"pointer[{i}].locator line_range invalid: start={loc.get('start')} end={loc.get('end')}",
                                    )
                                )
                        except Exception:
                            errors.append(
                                err(
                                    "E_LOCATOR",
                                    path,
                                    f"pointer[{i}].locator line_range invalid: start={loc.get('start')} end={loc.get('end')}",
                                )
                            )
            else:
                # legacy
                if p.get("path") and p.get("timestamp"):
                    warnings.append(
                        err(
                            "W_POINTER_LEGACY",
                            path,
                            f"pointer[{i}] uses legacy fields path/timestamp; prefer uri/sha256/locator",
                        )
                    )

    return errors, warnings


def iter_mimo_files(in_path: Path) -> list[Path]:
    if in_path.is_file() and in_path.suffix.lower() == ".mimo":
        return [in_path]
    files = [p for p in in_path.rglob("*.mimo") if p.is_file()]
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimo-validate")
    ap.add_argument("--in", dest="in_path", required=True, help="Input .mimo file or directory")
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_path)
    if not in_path.exists():
        print(f"missing input: {in_path}")
        return 1

    files = iter_mimo_files(in_path)
    checked = 0
    failed = 0
    warn_count = 0

    for p in files:
        checked += 1
        errs, warns = validate_file(str(p))
        for w in warns:
            warn_count += 1
            print(f"WARN: {p}\n  - {w['code']}: {w['msg']}")
        for e in errs:
            failed += 1
            print(f"ERROR: {p}\n  - {e['code']}: {e['msg']}")

    print(f"checked={checked} failed={failed} warnings={warn_count}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
