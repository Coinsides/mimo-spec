import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mimo_spec.tools.mimo_validate import validate_file


def _write(tmp_path, obj):
    p = tmp_path / "x.mimo"
    p.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return str(p)


def _base_mu():
    return {
        "schema_version": "1.1",
        "mu_id": "mu_test",
        "content_hash": "sha256:" + "0" * 64,
        "idempotency": {"mu_key": "sha256:" + "0" * 64},
        "meta": {
            "time": "2026-02-21T00:00:00Z",
            "source": "test",
            "group_id": "g",
            "order": "1/1",
            "span": "1-1",
            "shared_assets": [],
            "has_assets": False,
            "has_struct_data": False,
        },
        "summary": "hi",
        "pointer": [{"type": "file", "path": __file__, "timestamp": "2026-02-21T00:00:00Z"}],
        "snapshot": {
            "kind": "text",
            "codec": "gz+b64",
            "size_bytes": 2,
            "created_at": "2026-02-21T00:00:00Z",
            "source_ref": {"uri": "file://" + __file__, "sha256": "sha256:" + "0" * 64},
            "payload": {"text_gz_b64": "H4sIAAAAAAAC/8vIBACsKpPYAgAAAA=="},
            "meta": {},
        },
        "links": {"corrects": [], "supersedes": [], "duplicate_of": []},
        "privacy": {"level": "private", "redact": "none", "pii": [], "share_policy": {"allow_snapshot": True, "allow_pointer": True}},
        "provenance": {"tool": "test", "tool_version": "0"},
    }


def test_corrects_ok(tmp_path):
    mu = _base_mu()
    mu["links"]["corrects"] = ["mu_old"]
    path = _write(tmp_path, mu)
    errors, warnings = validate_file(path)
    assert errors == []


def test_tombstone_ok(tmp_path):
    mu = _base_mu()
    mu["tombstone"] = {
        "target_mu_id": "mu_old",
        "created_at": "2026-02-21T00:00:00Z",
        "actor": "owner",
        "reason": "requested",
        "scope": "all",
        "retain_raw": True,
    }
    path = _write(tmp_path, mu)
    errors, warnings = validate_file(path)
    assert errors == []


def test_tombstone_bad_scope(tmp_path):
    mu = _base_mu()
    mu["tombstone"] = {
        "target_mu_id": "mu_old",
        "created_at": "2026-02-21T00:00:00Z",
        "actor": "owner",
        "reason": "requested",
        "scope": "nope",
        "retain_raw": True,
    }
    path = _write(tmp_path, mu)
    errors, warnings = validate_file(path)
    assert any(e["code"] == "E_SCHEMA" for e in errors)
