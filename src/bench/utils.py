import hashlib
import json

from bench.templates import Method, Task


def hash_serializable(object: Task | Method) -> str:
    if not hasattr(object, "_hash"):
        m = hashlib.sha256()
        m.update(object.name().encode())
        m.update(json.dumps(object.encode(), sort_keys=True, ensure_ascii=True).encode())
        setattr(object, "_hash", m.hexdigest()[:8])
    return getattr(object, "_hash")
