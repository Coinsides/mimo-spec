import os, hashlib, gzip, base64, json, mimetypes, random, string
from datetime import datetime

INPUT_ROOT = r"C:\Mimo\mimo_data\Test\.mimo_samples"
OUTPUT_ROOT = os.path.join(INPUT_ROOT, "mimo")
ASSETS_ROOT = os.path.join(INPUT_ROOT, "assets")
ASSET_INDEX = os.path.join(ASSETS_ROOT, "asset_index.jsonl")

os.makedirs(OUTPUT_ROOT, exist_ok=True)
os.makedirs(ASSETS_ROOT, exist_ok=True)

TEXT_EXTS = {".md", ".txt", ".html", ".rtf"}
PDF_EXTS = {".pdf"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUD_EXTS = {".mp3", ".wav", ".m4a"}
VID_EXTS = {".mp4", ".mov", ".mkv", ".webm"}

# TEMP tools (can be swapped later)
USE_EASYOCR = True
USE_WHISPER = True
WHISPER_MODEL = "small"  # tiny/base/small/medium/large-v3
FFMPEG_BIN = "ffmpeg"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def gz_b64(s: str) -> str:
    data = s.encode("utf-8")
    comp = gzip.compress(data)
    return base64.b64encode(comp).decode("utf-8")


def safe_summary(text: str, limit=400):
    text = " ".join(text.strip().split())
    return text[:limit]


def rand4():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=4))


def load_pdf_text(path):
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(path)
        parts = []
        for p in reader.pages[:5]:
            t = p.extract_text() or ""
            parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""


def easyocr_text(path):
    if not USE_EASYOCR:
        return ""
    try:
        import easyocr  # type: ignore
        reader = easyocr.Reader(["en", "ch_sim"], gpu=False)
        results = reader.readtext(path, detail=0)
        return "\n".join(results)
    except Exception:
        return ""


def whisper_transcribe_audio(audio_path):
    if not USE_WHISPER:
        return ""
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path)
        text = "".join([seg.text for seg in segments])
        return text.strip()
    except Exception:
        return ""


def extract_audio_from_video(video_path, out_wav):
    # requires ffmpeg in PATH
    cmd = f'"{FFMPEG_BIN}" -y -i "{video_path}" -vn -ac 1 -ar 16000 "{out_wav}"'
    return os.system(cmd) == 0


def struct_data_from_table_csv(csv_text):
    # minimal struct_data for table-like text
    return {
        "json_gz_b64": gz_b64(json.dumps({
            "type": "table",
            "title": "",
            "source_pointer": "",
            "fields": [],
            "rows": [],
            "summary": "",
            "notes": "",
        }, ensure_ascii=False)),
        "csv_gz_b64": gz_b64(csv_text)
    }


def write_asset_index(rec):
    with open(ASSET_INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def make_pointer(path):
    ts = datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
    # Legacy pointer for now (new pointer+locator will be introduced in P0-1 follow-ups)
    return {
        "type": "file",
        "path": path,
        "timestamp": ts,
    }


def make_snapshot(path: str, kind: str, text: str):
    # Snapshot v0.1: gzip+base64 payload, rooted by source_ref
    sha = "sha256:" + sha256_file(path)
    uri = "file://" + path
    raw = text.encode("utf-8")
    return {
        "kind": kind,
        "codec": "gz+b64",
        "size_bytes": len(raw),
        "created_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "source_ref": {"uri": uri, "sha256": sha},
        "payload": {"text_gz_b64": gz_b64(text)},
        "meta": {},
    }


def yaml_quote(s: str) -> str:
    # use single quotes; escape single quotes by doubling
    return "'" + s.replace("'", "''") + "'"


def write_mimo(mimo_path, schema_version, mu_id, meta, summary, pointer, snapshot_text, struct_data=None):
    lines = []
    lines.append(f"schema_version: {schema_version}")
    lines.append(f"id: {mu_id}")
    lines.append("meta:")
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"  {k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"  {k}: []")
            else:
                lines.append(f"  {k}:")
                for item in v:
                    lines.append(f"    - {yaml_quote(str(item))}")
        else:
            lines.append(f"  {k}: {yaml_quote(str(v))}")
    lines.append("summary: |")
    for ln in summary.splitlines() or [""]:
        lines.append(f"  {ln}")
    lines.append("pointer:")
    lines.append("  - type: file")
    lines.append(f"    path: {yaml_quote(pointer['path'])}")
    lines.append(f"    timestamp: {yaml_quote(pointer['timestamp'])}")

    # Snapshot v0.1
    snap = make_snapshot(pointer['path'], "text", snapshot_text)
    lines.append("snapshot:")
    lines.append(f"  kind: {yaml_quote(str(snap['kind']))}")
    lines.append(f"  codec: {yaml_quote(str(snap['codec']))}")
    lines.append(f"  size_bytes: {int(snap['size_bytes'])}")
    lines.append(f"  created_at: {yaml_quote(str(snap['created_at']))}")
    lines.append("  source_ref:")
    lines.append(f"    uri: {yaml_quote(str(snap['source_ref']['uri']))}")
    lines.append(f"    sha256: {yaml_quote(str(snap['source_ref']['sha256']))}")
    lines.append("  payload:")
    lines.append(f"    text_gz_b64: {yaml_quote(str(snap['payload']['text_gz_b64']))}")
    if struct_data:
        lines.append("struct_data:")
        lines.append(f"  json_gz_b64: {yaml_quote(struct_data['json_gz_b64'])}")
        lines.append(f"  csv_gz_b64: {yaml_quote(struct_data['csv_gz_b64'])}")

    with open(mimo_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def process_file(path):
    ext = os.path.splitext(path)[1].lower()
    base = os.path.basename(path)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    group_id = f"grp_{datetime.now().strftime('%Y%m%d')}_01_{rand4()}"

    pointer = make_pointer(path)

    # Text-like
    if ext in TEXT_EXTS or ext in PDF_EXTS:
        text = ""
        if ext in TEXT_EXTS:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif ext in PDF_EXTS:
            text = load_pdf_text(path)

        if not text:
            text = f"[PDF/文本未解析内容] 文件名: {base}"
        summary = safe_summary(text)

        # split into 5000-char chunks
        chunk_size = 5000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] or [""]
        total = len(chunks)
        for i, chunk in enumerate(chunks, start=1):
            mu_id = f"mu_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rand4()}"
            meta = {
                "time": ts,
                "source": "sample",
                "tags": [],
                "chains": [],
                "group_id": group_id,
                "order": f"{i}/{total}",
                "span": f"{(i-1)*chunk_size+1}-{min(i*chunk_size, len(text))}",
                "shared_assets": [],
                "has_assets": False,
                "has_struct_data": False,
                "source_filename": base,
            }
            out_name = f"{os.path.splitext(base)[0]}__{i:02d}.mimo"
            out_path = os.path.join(OUTPUT_ROOT, out_name)
            write_mimo(out_path, "1.0", mu_id, meta, summary, pointer, chunk)
        return

    # Media assets
    if ext in IMG_EXTS | AUD_EXTS | VID_EXTS:
        asset_id = "sha256_" + sha256_file(path)
        mime, _ = mimetypes.guess_type(path)
        size = os.path.getsize(path)

        ocr_text = ""
        transcript = ""
        if ext in IMG_EXTS:
            ocr_text = easyocr_text(path)
        elif ext in AUD_EXTS:
            transcript = whisper_transcribe_audio(path)
        elif ext in VID_EXTS:
            tmp_wav = os.path.join(ASSETS_ROOT, f"_tmp_{rand4()}.wav")
            if extract_audio_from_video(path, tmp_wav):
                transcript = whisper_transcribe_audio(tmp_wav)
                try:
                    os.remove(tmp_wav)
                except Exception:
                    pass

        # lightweight descriptions (TEMP): OCR/Transcript + file meta
        if ext in IMG_EXTS:
            caption = f"Image file: {base}; size={size} bytes; mime={mime or 'unknown'}."
            if ocr_text:
                caption += f" OCR: {safe_summary(ocr_text, 500)}"
            text_summary = caption
        elif ext in AUD_EXTS:
            caption = f"Audio file: {base}; size={size} bytes; mime={mime or 'unknown'}."
            if transcript:
                caption += f" Transcript: {safe_summary(transcript, 800)}"
            text_summary = caption
        else:
            caption = f"Video file: {base}; size={size} bytes; mime={mime or 'unknown'}."
            if transcript:
                caption += f" Transcript: {safe_summary(transcript, 800)}"
            text_summary = caption

        asset_rec = {
            "asset_id": asset_id,
            "type": "image" if ext in IMG_EXTS else ("audio" if ext in AUD_EXTS else "video"),
            "path": path,
            "meta": {"size_bytes": size, "mime": mime or "unknown", "ext": ext},
            "text_summary": text_summary,
        }
        write_asset_index(asset_rec)

        mu_id = f"mu_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rand4()}"
        meta = {
            "time": ts,
            "source": "sample",
            "tags": [],
            "chains": [],
            "group_id": group_id,
            "order": "1/1",
            "span": "1-1",
            "shared_assets": [asset_id],
            "has_assets": True,
            "has_struct_data": False,
            "source_filename": base,
        }
        out_name = f"{os.path.splitext(base)[0]}.mimo"
        out_path = os.path.join(OUTPUT_ROOT, out_name)
        write_mimo(out_path, "1.0", mu_id, meta, text_summary, pointer, "")
        return


def walk_inputs():
    for root, _, files in os.walk(INPUT_ROOT):
        if root.endswith("\\mimo") or root.endswith("\\assets"):
            continue
        for fn in files:
            path = os.path.join(root, fn)
            yield path


def main():
    # reset asset index for reproducibility
    if os.path.exists(ASSET_INDEX):
        os.remove(ASSET_INDEX)

    for path in walk_inputs():
        process_file(path)

    print("mimo-pack: done")


if __name__ == "__main__":
    main()
