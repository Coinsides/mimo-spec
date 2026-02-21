import os, sys, gzip, base64, json
import yaml
import jsonschema

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

INPUT_ROOT = r"C:\Mimo\mimo_data\Test\.mimo_samples\mimo"

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
REQUIRED_META = ["time", "source", "group_id", "order", "span", "has_assets", "has_struct_data"]

# Pointer+Locator v0.1 (new style)
LOCATOR_KINDS = {"line_range", "byte_range", "page_range", "time_range", "bbox"}


def err(code, path, msg):
    return {"code": code, "path": path, "msg": msg}


def validate_file(path):
    errors = []
    warnings = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [err("E_YAML", path, f"YAML parse error: {e}")], []

    sv = str(data.get("schema_version") or "")

    # required top-level
    required = REQUIRED_TOP_V1_1 if sv == "1.1" else REQUIRED_TOP_V1_0
    for k in required:
        if k not in data:
            errors.append(err("E_REQUIRED", path, f"Missing: {k}"))

    # v1.1: enforce JSON Schema contract (when present)
    if sv == "1.1":
        schema_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "mu_v1_1.schema.json")
        schema_path = os.path.normpath(schema_path)
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            jsonschema.validate(instance=data, schema=schema)
        except Exception as e:
            errors.append(err("E_SCHEMA", path, f"MU v1.1 schema validation failed: {e}"))

    # type checks
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

    # rule consistency
    if meta.get("has_assets") is True and not meta.get("shared_assets"):
        warnings.append(err("W_ASSET", path, "has_assets=true but shared_assets empty"))
    if meta.get("has_struct_data") is True and "struct_data" not in data:
        warnings.append(err("W_STRUCT", path, "has_struct_data=true but struct_data missing"))

        # schema_version strategy (v0.1 tooling still accepts 1.0 and 1.1)
    if sv and str(sv) not in {"1.0", "1.1"}:
        warnings.append(err("W_SCHEMA", path, f"schema_version={sv} (expected 1.0 or 1.1)"))

    # snapshot minimal contract (P0-A / Snapshot v0.1)
    snap = data.get("snapshot")
    if isinstance(snap, dict):
        kind = snap.get("kind")
        codec = snap.get("codec")
        if kind not in {"text", "web", "audio", "image", "other"}:
            errors.append(err("E_SNAPSHOT", path, f"snapshot.kind invalid: {kind}"))
        if codec not in {"plain", "gz+b64"}:
            errors.append(err("E_SNAPSHOT", path, f"snapshot.codec invalid: {codec}"))

        # must be rooted
        src = snap.get("source_ref")
        if not isinstance(src, dict) or not src.get("sha256") or not src.get("uri"):
            errors.append(err("E_SNAPSHOT", path, "snapshot.source_ref must include uri + sha256"))

        # payload decodability
        payload = snap.get("payload")
        if not isinstance(payload, dict):
            errors.append(err("E_SNAPSHOT", path, "snapshot.payload must be dict"))
        else:
            if codec == "plain":
                if "text" not in payload or not isinstance(payload.get("text"), str):
                    errors.append(err("E_SNAPSHOT", path, "snapshot.payload.text required for codec=plain"))
            if codec == "gz+b64":
                b64 = payload.get("text_gz_b64")
                if not isinstance(b64, str):
                    errors.append(err("E_SNAPSHOT", path, "snapshot.payload.text_gz_b64 required for codec=gz+b64"))
                else:
                    try:
                        raw = gzip.decompress(base64.b64decode(b64.encode("utf-8")))
                        # 20KB hard cap (can be tuned later)
                        if len(raw) > 20 * 1024:
                            errors.append(err("E_SNAPSHOT", path, f"snapshot payload too large: {len(raw)} bytes (cap=20480)"))
                    except Exception as e:
                        errors.append(err("E_SNAPSHOT", path, f"snapshot payload not decodable: {e}"))
    else:
        errors.append(err("E_REQUIRED", path, "Missing: snapshot"))

    def _validate_locator(i, loc):
        if not isinstance(loc, dict):
            errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator must be dict"))
            return
        kind = loc.get("kind")
        if kind not in LOCATOR_KINDS:
            errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator.kind invalid: {kind}"))
            return
        # kind-specific required fields + sanity
        if kind in {"line_range", "byte_range", "time_range"}:
            if "start" not in loc or "end" not in loc:
                errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator missing start/end"))
                return
            try:
                if float(loc["start"]) > float(loc["end"]):
                    errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator start>end"))
            except Exception:
                errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator start/end not comparable"))
        elif kind == "page_range":
            if not ("page" in loc or ("page_start" in loc and "page_end" in loc)):
                errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator requires page or page_start/page_end"))
        elif kind == "bbox":
            for k in ("x", "y", "w", "h"):
                if k not in loc:
                    errors.append(err("E_LOCATOR", path, f"pointer[{i}].locator missing {k}"))

    # pointer minimal fields (support legacy + new style)
    if isinstance(data.get("pointer"), list):
        for i, p in enumerate(data["pointer"]):
            if not isinstance(p, dict):
                errors.append(err("E_POINTER", path, f"pointer[{i}] must be dict"))
                continue

            # New style: type/uri/sha256/locator
            if "uri" in p or "locator" in p:
                for k in ("type", "uri", "sha256", "locator"):
                    if k not in p:
                        errors.append(err("E_POINTER", path, f"pointer[{i}] missing {k} (new style)"))
                _validate_locator(i, p.get("locator"))

            # Legacy style: type/path/timestamp
            else:
                if "type" not in p or "path" not in p or "timestamp" not in p:
                    errors.append(err("E_POINTER", path, f"pointer[{i}] missing type/path/timestamp (legacy style)"))
                else:
                    warnings.append(err("W_POINTER_LEGACY", path, f"pointer[{i}] uses legacy fields path/timestamp; prefer uri/sha256/locator"))

    return errors, warnings


def main():
    total = 0
    failed = 0
    warn = 0
    for root, _, files in os.walk(INPUT_ROOT):
        for fn in files:
            if not fn.endswith(".mimo"):
                continue
            total += 1
            path = os.path.join(root, fn)
            errors, warnings = validate_file(path)
            if errors:
                failed += 1
                print(f"FAIL: {path}")
                for e in errors:
                    print(f"  - {e['code']}: {e['msg']}")
            if warnings:
                warn += 1
                print(f"WARN: {path}")
                for w in warnings:
                    print(f"  - {w['code']}: {w['msg']}")

    print(f"checked={total} failed={failed} warnings={warn}")


if __name__ == "__main__":
    main()
