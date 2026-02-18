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
            pointers.extend(data.get("pointer", []))

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
