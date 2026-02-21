import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mimo_spec.tools.mimo_validate import validate_file


def _write(tmp_path, obj):
    p = tmp_path / "x.mimo"
    p.write_text(yaml.safe_dump(obj, allow_unicode=True), encoding="utf-8")
    return str(p)


def test_snapshot_gzb64_ok(tmp_path):
    mimo = {
        "schema_version": "1.1",
        "id": "mu_test",
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
    }
    path = _write(tmp_path, mimo)
    errors, warnings = validate_file(path)
    assert errors == []


def test_snapshot_missing_source_ref(tmp_path):
    mimo = {
        "schema_version": "1.1",
        "id": "mu_test",
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
        "pointer": [{"type": "file", "path": __file__, "timestamp": "2026-02-21T00:00:00Z"}],
        "snapshot": {
            "kind": "text",
            "codec": "gz+b64",
            "size_bytes": 2,
            "created_at": "2026-02-21T00:00:00Z",
            "payload": {"text_gz_b64": "H4sIAAAAAAAC/8vIBACsKpPYAgAAAA=="},
        },
    }
    path = _write(tmp_path, mimo)
    errors, warnings = validate_file(path)
    assert any(e["code"] in {"E_SNAPSHOT", "E_REQUIRED"} for e in errors)
