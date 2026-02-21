import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mimo_spec.tools.mu_hash import canonical_json, sha256_prefixed
from mimo_spec.tools import mimo_pack


def test_canonical_json_is_stable():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonical_json(a) == canonical_json(b)


def test_sha256_prefixed_format():
    h = sha256_prefixed(b"x")
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64


def test_dedup_skip(tmp_path):
    # Arrange: make two identical MUs and ensure the second is skipped
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    meta = {
        "time": "2026-02-21T00:00:00Z",
        "source": "test",
        "group_id": "g",
        "order": "1/1",
        "span": "1-1",
        "shared_assets": [],
        "has_assets": False,
        "has_struct_data": False,
    }
    pointer = {"type": "file", "path": __file__, "timestamp": "2026-02-21T00:00:00Z"}

    # First write
    p1 = out_dir / "a.mimo"
    ok1 = mimo_pack.write_mu_v1_1(str(p1), meta=meta, pointer=pointer, summary="hi", snapshot_text="hi", dedup="skip", existing_mu_keys=set())
    assert ok1 is True

    # Load mu_key from first
    data = yaml.safe_load(p1.read_text(encoding="utf-8"))
    mu_key = data["idempotency"]["mu_key"]

    # Second write with existing mu_key
    p2 = out_dir / "b.mimo"
    ok2 = mimo_pack.write_mu_v1_1(str(p2), meta=meta, pointer=pointer, summary="hi", snapshot_text="hi", dedup="skip", existing_mu_keys={mu_key})
    assert ok2 is False
    assert not p2.exists()
