import sys
from pathlib import Path

import yaml

# Make repo importable without installation
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mimo_spec.tools.mimo_validate import validate_file


def _write(tmp_path, obj):
    p = tmp_path / "x.mimo"
    p.write_text(yaml.safe_dump(obj, allow_unicode=True), encoding="utf-8")
    return str(p)


def test_pointer_new_style_ok(tmp_path):
    mimo = {
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
            "has_assets": False,
            "has_struct_data": False,
        },
        "summary": "hi",
        "links": {"corrects": [], "supersedes": [], "duplicate_of": []},
        "privacy": {"level": "private", "redact": "none", "pii": [], "share_policy": {"allow_snapshot": True, "allow_pointer": True}},
        "provenance": {"tool": "test", "tool_version": "0"},
        "pointer": [
            {
                "type": "raw",
                "uri": "vault://default/raw/2026/02/21/a.txt",
                "sha256": "sha256:" + "0" * 64,
                "locator": {"kind": "line_range", "start": 1, "end": 2},
            }
        ],
        "snapshot": {
            "kind": "text",
            "codec": "gz+b64",
            "size_bytes": 2,
            "created_at": "2026-02-21T00:00:00Z",
            "source_ref": {"uri": "vault://default/raw/2026/02/21/a.txt", "sha256": "sha256:" + "0" * 64},
            "payload": {"text_gz_b64": "H4sIAAAAAAAC/8vIBACsKpPYAgAAAA=="},
            "meta": {},
        },
    }
    path = _write(tmp_path, mimo)
    errors, warnings = validate_file(path)
    assert errors == []


def test_pointer_new_style_bad_locator(tmp_path):
    mimo = {
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
            "has_assets": False,
            "has_struct_data": False,
        },
        "summary": "hi",
        "links": {"corrects": [], "supersedes": [], "duplicate_of": []},
        "privacy": {"level": "private", "redact": "none", "pii": [], "share_policy": {"allow_snapshot": True, "allow_pointer": True}},
        "provenance": {"tool": "test", "tool_version": "0"},
        "pointer": [
            {
                "type": "raw",
                "uri": "vault://default/raw/2026/02/21/a.txt",
                "sha256": "sha256:" + "0" * 64,
                "locator": {"kind": "line_range", "start": 3, "end": 2},
            }
        ],
        "snapshot": {
            "kind": "text",
            "codec": "gz+b64",
            "size_bytes": 2,
            "created_at": "2026-02-21T00:00:00Z",
            "source_ref": {"uri": "vault://default/raw/2026/02/21/a.txt", "sha256": "sha256:" + "0" * 64},
            "payload": {"text_gz_b64": "H4sIAAAAAAAC/8vIBACsKpPYAgAAAA=="},
            "meta": {},
        },
    }
    path = _write(tmp_path, mimo)
    errors, warnings = validate_file(path)
    assert any(e["code"] == "E_LOCATOR" for e in errors)
