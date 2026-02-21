import os, gzip, base64, json
import yaml
from collections import defaultdict

INPUT_ROOT = r"C:\Mimo\mimo_data\Test\.mimo_samples\mimo"
OUT_ROOT = r"C:\Mimo\mimo_data\Test\.mimo_samples\reconstructed"

os.makedirs(OUT_ROOT, exist_ok=True)


def b64_gz_decode(s: str) -> str:
    data = base64.b64decode(s.encode("utf-8"))
    return gzip.decompress(data).decode("utf-8", errors="ignore")


def load_mimo(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return yaml.safe_load(f)


def group_key(meta):
    return meta.get("group_id", "ungrouped")


def order_key(meta):
    # order like "2/7" or span like "1-5000"
    ords = meta.get("order", "1/1")
    try:
        return int(str(ords).split("/")[0])
    except Exception:
        span = meta.get("span", "0-0")
        try:
            return int(str(span).split("-")[0])
        except Exception:
            return 0


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _read_lines(pth: str):
    with open(pth, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


def resolve_pointer_snippet(pointer: dict) -> str | None:
    """Minimal pointer.resolve() for text evidence.

    Supports:
    - legacy pointer: {path: <file>, ...} with locator.kind=line_range
    - new pointer: {uri: file://...} or {uri: <plain path>} with locator.kind=line_range

    Does NOT yet resolve vault:// URIs (handled by memory_system via manifest).
    """
    loc = pointer.get("locator")
    if not isinstance(loc, dict) or loc.get("kind") != "line_range":
        return None
    start = loc.get("start")
    end = loc.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        return None

    # pick path
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
    # slice is 1-indexed inclusive
    snippet = "".join(lines[start - 1 : end])
    return snippet


def main():
    groups = defaultdict(list)
    index = []

    for root, _, files in os.walk(INPUT_ROOT):
        for fn in files:
            if not fn.endswith(".mimo"):
                continue
            path = os.path.join(root, fn)
            data = load_mimo(path)
            meta = data.get("meta", {})
            gid = group_key(meta)
            groups[gid].append((path, data))

    for gid, items in groups.items():
        # sort by order/span
        items.sort(key=lambda x: order_key(x[1].get("meta", {})))

        # reconstruct text snapshots
        snapshots = []
        summaries = []
        pointers = []
        snippets = []
        assets_md = []
        struct_json = None
        struct_csv = None

        # filename preference: source_filename -> group_id
        filename = None

        for path, data in items:
            meta = data.get("meta", {})
            if not filename:
                filename = meta.get("source_filename")
            summaries.append(data.get("summary", ""))
            ps = data.get("pointer", [])
            pointers.extend(ps)
            # Try to resolve text snippets when locator is present (minimal v0.1)
            if isinstance(ps, list):
                for p in ps:
                    if isinstance(p, dict):
                        snip = resolve_pointer_snippet(p)
                        if snip:
                            snippets.append(snip)

            snap = data.get("snapshot_gz_b64")
            if snap:
                snapshots.append(b64_gz_decode(snap))

            # struct_data
            if data.get("struct_data"):
                sd = data["struct_data"]
                if sd.get("json_gz_b64"):
                    try:
                        struct_json = b64_gz_decode(sd["json_gz_b64"])
                    except Exception:
                        pass
                if sd.get("csv_gz_b64"):
                    try:
                        struct_csv = b64_gz_decode(sd["csv_gz_b64"])
                    except Exception:
                        pass

            # assets (text_summary lives in asset index; here use summary as fallback)
            if meta.get("has_assets"):
                assets_md.append(f"- {os.path.basename(path)}: {data.get('summary','')}")

        base = filename or gid
        base = os.path.splitext(base)[0]

        # write reconstructed text
        if snapshots:
            out_txt = os.path.join(OUT_ROOT, f"{base}.txt")
            write_text(out_txt, "".join(snapshots))

        # write extracted evidence snippets (if any)
        if snippets:
            out_snip = os.path.join(OUT_ROOT, f"{base}.snippets.txt")
            write_text(out_snip, "\n\n---\n\n".join(snippets))

        # write assets description
        if assets_md:
            out_md = os.path.join(OUT_ROOT, f"{base}.md")
            write_text(out_md, "# Assets Summary\n" + "\n".join(assets_md))

        # write struct_data
        if struct_json:
            write_text(os.path.join(OUT_ROOT, f"{base}.json"), struct_json)
        if struct_csv:
            write_text(os.path.join(OUT_ROOT, f"{base}.csv"), struct_csv)

        index.append({
            "group_id": gid,
            "count": len(items),
            "out_text": f"{base}.txt" if snapshots else None,
            "out_assets": f"{base}.md" if assets_md else None,
            "out_json": f"{base}.json" if struct_json else None,
            "out_csv": f"{base}.csv" if struct_csv else None,
        })

    with open(os.path.join(OUT_ROOT, "index.jsonl"), "w", encoding="utf-8") as f:
        for rec in index:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("mimo-extract: done")


if __name__ == "__main__":
    main()
