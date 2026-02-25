from __future__ import annotations

"""mimo-pack: generate MU (.mimo) files from raw inputs.

v0.2 goals (MVP-aligned):
- No hardcoded input/output paths.
- Stable group_id (derived from raw sha256).
- pointer uses pointer+locator shape (type/uri/sha256/locator).
- Stable mu_key (derived from raw_sha256 + locator + split).

This tool is intentionally minimal: text-like inputs only (md/txt/html/rtf).
"""

import argparse
import base64
import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

TEXT_EXTS = {".md", ".txt", ".html", ".rtf"}


def now_iso_z() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_prefixed(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def gz_b64(s: str) -> str:
    comp = gzip.compress(s.encode("utf-8"))
    return base64.b64encode(comp).decode("utf-8")


def safe_summary(text: str, limit: int = 400) -> str:
    text = " ".join(text.strip().split())
    return text[:limit]


@dataclass(frozen=True)
class SplitSpec:
    strategy: str
    window: int


def parse_split(s: str) -> SplitSpec:
    # Expect: line_window:400
    if not s:
        raise ValueError("--split is required (e.g. line_window:400)")
    if ":" not in s:
        raise ValueError("invalid split, expected line_window:<n>")
    strat, n = s.split(":", 1)
    strat = strat.strip()
    if strat != "line_window":
        raise ValueError("only split strategy supported in MVP: line_window")
    try:
        window = int(n)
    except Exception as e:
        raise ValueError("invalid split window") from e
    if window <= 0:
        raise ValueError("split window must be > 0")
    return SplitSpec(strategy=strat, window=window)


def compute_mu_key(*, raw_sha256: str, locator: dict, split: dict) -> str:
    seed = canonical_json({"raw_sha256": raw_sha256, "locator": locator, "split": split})
    return sha256_prefixed(seed.encode("utf-8"))


def compute_content_hash(*, schema_version: str, summary: str, snapshot: dict) -> str:
    seed = canonical_json(
        {
            "schema_version": schema_version,
            "summary": summary,
            "snapshot": {
                "kind": snapshot.get("kind"),
                "codec": snapshot.get("codec"),
                "payload": snapshot.get("payload"),
            },
        }
    )
    return sha256_prefixed(seed.encode("utf-8"))


def make_snapshot(*, source_uri: str, raw_sha256: str, text: str) -> dict:
    raw = text.encode("utf-8")
    return {
        "kind": "text",
        "codec": "gz+b64",
        "size_bytes": len(raw),
        "created_at": now_iso_z(),
        "source_ref": {"raw_id": f"sha256:{raw_sha256}", "uri": source_uri},
        "payload": {"text_gz_b64": gz_b64(text)},
        "meta": {},
    }


def vault_raw_uri(*, vault_id: str, raw_sha256: str, ext: str) -> str:
    # Mirror vault_ingest naming: vault://default/raw/YYYY/MM/<sha>.<ext>
    # We don't try to preserve original filenames.
    dt = datetime.now(timezone.utc)
    yyyy = dt.strftime("%Y")
    mm = dt.strftime("%m")
    ext = ext.lstrip(".") or "txt"
    return f"vault://{vault_id}/raw/{yyyy}/{mm}/{raw_sha256}.{ext}"


def iter_text_files(in_dir: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(in_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            files.append(p)
    return files


def read_text_best_effort(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_mimo(path: Path, mimo: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(mimo, f, allow_unicode=True, sort_keys=False)


def write_mu_v1_1(
    mimo_path: str,
    *,
    meta: dict,
    pointer: dict,
    summary: str,
    snapshot_text: str,
    struct_data=None,
    dedup: str = "skip",
    existing_mu_keys: set[str] | None = None,
) -> bool:
    """Backward-compatible helper used by older tests.

    This keeps the public API stable while the CLI evolves.
    """

    existing_mu_keys = existing_mu_keys or set()

    # legacy pointer may include path/timestamp; normalize if possible
    raw_path = pointer.get("path") if isinstance(pointer, dict) else None
    if isinstance(raw_path, str) and raw_path:
        raw_sha_hex = sha256_file_hex(Path(raw_path))
        uri = "file:///" + raw_path.replace("\\", "/")
    else:
        raw_sha_hex = "0" * 64
        uri = ""

    # best-effort locator
    locator = {"kind": "line_range", "start": 1, "end": max(1, len(snapshot_text.splitlines()))}
    split = {"strategy": "single", "index": 0, "total": 1, "window": 0}

    mu_key = compute_mu_key(raw_sha256=f"sha256:{raw_sha_hex}", locator=locator, split=split)
    if dedup == "skip" and mu_key in existing_mu_keys:
        return False

    snap = make_snapshot(source_uri=uri, raw_sha256=raw_sha_hex, text=snapshot_text)
    content_hash = compute_content_hash(schema_version="1.1", summary=summary, snapshot=snap)

    mu_id = meta.get("mu_id") or f"mu_{raw_sha_hex[:12]}_001"

    mimo = {
        "schema_version": "1.1",
        "mu_id": mu_id,
        "content_hash": content_hash,
        "idempotency": {"mu_key": mu_key},
        "meta": meta,
        "summary": summary,
        "pointer": [pointer],
        "snapshot": snap,
        "links": {"corrects": [], "supersedes": [], "duplicate_of": []},
        "privacy": {"level": "private", "redact": "none"},
        "provenance": {"tool": "mimo-pack", "tool_version": "0.2.0"},
    }

    if struct_data is not None:
        mimo["struct_data"] = struct_data

    write_mimo(Path(mimo_path), mimo)
    existing_mu_keys.add(mu_key)
    return True


def build_mus_for_file(
    *,
    raw_path: Path,
    out_dir: Path,
    source_kind: str,
    workspace_id: str | None,
    split_spec: SplitSpec,
    vault_id: str,
) -> int:
    text = read_text_best_effort(raw_path)
    lines = text.splitlines()

    raw_sha_hex = sha256_file_hex(raw_path)
    raw_sha = f"sha256:{raw_sha_hex}"

    # Stable group_id derived from raw sha256
    group_id = f"grp_{raw_sha_hex[:12]}"

    total = max(1, (len(lines) + split_spec.window - 1) // split_spec.window)

    written = 0
    for i in range(total):
        start = i * split_spec.window
        end = min(len(lines), (i + 1) * split_spec.window)
        # 1-indexed line numbers in locator
        locator = {"kind": "line_range", "start": start + 1, "end": end}
        split = {"strategy": split_spec.strategy, "index": i, "total": total, "window": split_spec.window}

        snippet_lines = lines[start:end]
        snippet = "\n".join(snippet_lines).strip() or "(empty)"

        uri = vault_raw_uri(vault_id=vault_id, raw_sha256=raw_sha_hex, ext=raw_path.suffix)
        pointer = {
            "type": "raw",
            "uri": uri,
            "sha256": raw_sha,
            "locator": locator,
        }

        meta: dict[str, Any] = {
            "time": now_iso_z(),
            "source": source_kind,
            "group_id": group_id,
            "order": i + 1,
            "span": total,
            "tags": [],
        }
        if workspace_id:
            meta["workspace_id"] = workspace_id
            meta["tags"].append(f"ws:{workspace_id}")

        mu_key = compute_mu_key(raw_sha256=raw_sha, locator=locator, split=split)
        snap = make_snapshot(source_uri=uri, raw_sha256=raw_sha_hex, text=snippet)

        summary = safe_summary(snippet)
        content_hash = compute_content_hash(schema_version="1.1", summary=summary, snapshot=snap)

        mu_id = f"mu_{group_id}_{i+1:03d}"
        mimo = {
            "schema_version": "1.1",
            "mu_id": mu_id,
            "content_hash": content_hash,
            "idempotency": {"mu_key": mu_key},
            "meta": meta,
            "summary": summary,
            "pointer": [pointer],
            "snapshot": snap,
            "links": {"corrects": [], "supersedes": [], "duplicate_of": []},
            "privacy": {"level": "private", "redact": "none"},
            "provenance": {
                "tool": "mimo-pack",
                "tool_version": "0.2.0",
                "model": "",
                "prompt_version": "",
            },
        }

        out_path = out_dir / f"{mu_id}.mimo"
        write_mimo(out_path, mimo)
        written += 1

    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimo-pack", description="Generate MU (.mimo) from raw inputs")
    ap.add_argument("--in", dest="in_dir", required=True, help="Input directory containing raw files")
    ap.add_argument("--out", dest="out_dir", required=True, help="Output directory for .mimo files")
    ap.add_argument("--source", default="file", choices=["chat", "file", "web", "pdf"], help="meta.source")
    ap.add_argument("--workspace", default=None, help="workspace_id (also adds tag ws:<id>)")
    ap.add_argument("--split", required=True, help="split strategy, e.g. line_window:400")
    ap.add_argument("--vault-id", default="default", help="vault id used in vault:// URIs")
    ap.add_argument("--dedup", default="skip", choices=["skip"], help="(MVP) dedup policy")

    ns = ap.parse_args(argv)

    in_dir = Path(ns.in_dir)
    out_dir = Path(ns.out_dir)
    if not in_dir.exists():
        raise SystemExit(f"missing input: {in_dir}")

    split_spec = parse_split(ns.split)

    files = iter_text_files(in_dir)
    if not files:
        print("no supported input files")
        return 0

    total_written = 0
    for f in files:
        total_written += build_mus_for_file(
            raw_path=f,
            out_dir=out_dir,
            source_kind=ns.source,
            workspace_id=ns.workspace,
            split_spec=split_spec,
            vault_id=ns.vault_id,
        )

    print(f"written_mus={total_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
