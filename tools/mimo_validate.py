import os, sys
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

INPUT_ROOT = r"C:\Mimo\mimo_data\Test\.mimo_samples\mimo"

REQUIRED_TOP = ["schema_version", "id", "meta", "summary", "pointer", "snapshot_gz_b64"]
REQUIRED_META = ["time", "source", "group_id", "order", "span", "has_assets", "has_struct_data"]


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

    # required top-level
    for k in REQUIRED_TOP:
        if k not in data:
            errors.append(err("E_REQUIRED", path, f"Missing: {k}"))

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

    # schema_version strategy
    sv = data.get("schema_version")
    if sv and str(sv) != "1.0":
        warnings.append(err("W_SCHEMA", path, f"schema_version={sv} (expected 1.0)"))

    # pointer minimal fields
    if isinstance(data.get("pointer"), list):
        for i, p in enumerate(data["pointer"]):
            if not isinstance(p, dict):
                errors.append(err("E_POINTER", path, f"pointer[{i}] must be dict"))
                continue
            if "type" not in p or "path" not in p or "timestamp" not in p:
                errors.append(err("E_POINTER", path, f"pointer[{i}] missing type/path/timestamp"))

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
