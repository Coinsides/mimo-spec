import hashlib
import json


def sha256_hex(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_prefixed(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


def canonical_json(obj) -> str:
    # stable json for hashing
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
