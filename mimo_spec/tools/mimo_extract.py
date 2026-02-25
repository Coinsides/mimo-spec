from __future__ import annotations

"""mimo-extract: reconstruct snapshots/assets from .mimo files.

This tool should not assume any fixed directories.
Pass paths explicitly.

Note: vault:// resolution is intentionally handled by `mimobrain_memory_system`
(via manifests), not by this repo.
"""

import argparse
import base64
import gzip
import json
import os
from collections import defaultdict
from pathlib import Path

import yaml


def b64_gz_decode(s: str) -> str:
    data = base64.b64decode(s.encode("utf-8"))
    return gzip.decompress(data).decode("utf-8", errors="ignore")


def load_mimo(path: str | Path):
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8", errors="ignore"))


def group_key(meta: dict) -> str:
    return str(meta.get("group_id") or "ungrouped")


def order_key(meta: dict) -> int:
    ords = meta.get("order", "1/1")
    try:
        return int(str(ords).split("/")[0])
    except Exception:
        span = meta.get("span", "0-0")
        try:
            return int(str(span).split("-")[0])
        except Exception:
            return 0


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_lines(pth: str) -> list[str]:
    with open(pth, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def resolve_pointer_snippet(pointer: dict) -> str | None:
    """Minimal pointer.resolve() for text evidence.

    Supports:
    - legacy pointer: {path: <file>, ...} with locator.kind=line_range
    - new pointer: {uri: file://...} or {uri: <plain path>} with locator.kind=line_range

    Does NOT resolve vault:// URIs.
    """

    loc = pointer.get("locator")
    if not isinstance(loc, dict) or loc.get("kind") != "line_range":
        return None
    start = loc.get("start")
    end = loc.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        return None

    pth = pointer.get("path")
    if not pth:
        uri = pointer.get("uri")
        if isinstance(uri, str) and uri.startswith("file://"):
            pth = uri[len("file://") :]
        elif isinstance(uri, str) and (uri.startswith("vault://") or uri.startswith("http")):
            return None
        else:
            pth = uri

    if not pth or not isinstance(pth, str) or not os.path.exists(pth):
        return None

    lines = _read_lines(pth)
    return "".join(lines[start - 1 : end])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mimo-extract")
    ap.add_argument("--in", dest="in_path", required=True, help="Input .mimo directory")
    ap.add_argument(
        "--out",
        dest="out_dir",
        required=True,
        help="Output directory for reconstructed artifacts",
    )
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_path)
    out_root = Path(ns.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    groups: dict[str, list[tuple[Path, dict]]] = defaultdict(list)

    for p in sorted(in_path.rglob("*.mimo")):
        data = load_mimo(p)
        if not isinstance(data, dict):
            continue
        meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
        gid = group_key(meta)
        groups[gid].append((p, data))

    index: list[dict] = []

    for gid, items in groups.items():
        items.sort(key=lambda x: order_key(x[1].get("meta", {}) if isinstance(x[1], dict) else {}))

        summaries: list[str] = []
        pointers: list[dict] = []
        snippets: list[str] = []

        filename = None
        for path, data in items:
            meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
            if not filename:
                filename = meta.get("source_filename")
            summaries.append(str(data.get("summary") or ""))

            ps = data.get("pointer") or []
            if isinstance(ps, list):
                for p in ps:
                    if isinstance(p, dict):
                        pointers.append(p)
                        sn = resolve_pointer_snippet(p)
                        if sn:
                            snippets.append(sn)

        base = filename or gid
        out_dir = out_root / base
        out_dir.mkdir(parents=True, exist_ok=True)

        write_text(out_dir / "summary.txt", "\n\n".join(summaries))
        write_text(out_dir / "snippets.txt", "\n\n".join(snippets))
        (out_dir / "pointers.json").write_text(
            json.dumps(pointers, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        index.append({"group_id": gid, "out_dir": str(out_dir)})

    (out_root / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
