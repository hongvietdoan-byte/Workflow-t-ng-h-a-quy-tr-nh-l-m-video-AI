"""K1a "Lưu gói gửi" (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md, thẩm định lần 4 lỗ hổng #2).

What really left for the provider, kept on the job (`jobs.sent_package`, `end_frames.sent_package`) as JSON:
{prompt (the final text, byte for byte), negative, refs[] {param, role, label, path, file, sha256}, provider, model, params (every
other keyword/positional argument; names starting with '_' are the runner's notes and never sent; names that look like a secret are
dropped and listed in `redacted`), external_id, at, v: 1}.

The package is a LEDGER, never a gate: building it never raises (safe_build) — a picture that cannot be read gets sha256 null and a
warning, anything that is not JSON (Path, bytes, a provider object) becomes a string / a fingerprint. Long strings in params (a base64
picture) are kept as {len, sha256} only. Paths are kept the way the rest of the database keeps them: relative as given; an absolute
path inside the repository becomes relative to the repository root; another absolute path stays as it is."""
from __future__ import annotations

import datetime
import hashlib
import inspect
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

V = 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# argument → role of the file(s) it carries (None = the role comes from the reference dict / the runner's own list)
REF_PARAMS = {"image_path": "start_frame", "references": None, "image_references": None, "reference_video": "reference_video",
              "last_frame": "last_frame", "reference_only": None, "reference_audio": "reference_audio"}
PROMPT_PARAMS = ("prompt",)
NEGATIVE_PARAMS = ("negative_prompt", "negative")
SECRET_WORDS = ("token", "secret", "password", "passwd", "authorization", "cookie", "credential")
LONG_TEXT = 4000            # a param string longer than this (base64 picture …) is kept as {len, sha256}

# positional names when the provider's signature cannot be read (a test double `Mock()`): the order of the real adapters
POSITIONAL = {"image": ("prompt", "references"),
              "video": ("image_path", "prompt", "negative_prompt", "duration_sec", "model", "with_audio", "subjects",
                        "image_references", "reference_video"),
              "submit_final_from_sample": ("sample_external_id", "resolution")}


def _secret(name: str) -> bool:
    """A name that may carry a secret. 'plate_key' / 'prompt_key' (what a picture is / which tool) are not secrets."""
    low = str(name).lower().replace("-", "_")
    if low in ("key", "auth") or low.startswith("auth_") or low.endswith(("api_key", "apikey", "access_key", "secret_key", "private_key")):
        return True
    return any(w in low for w in SECRET_WORDS)


def _bind(fn, args: Sequence, kwargs: Dict, kind: str) -> Dict[str, Any]:
    """{parameter name: value} exactly as the call passed them (defaults NOT filled in: only what was sent)."""
    try:
        sig = inspect.signature(fn)
        if not any(p.kind == p.VAR_POSITIONAL for p in sig.parameters.values()):
            out = dict(sig.bind_partial(*args, **kwargs).arguments)
            for p in sig.parameters.values():          # **kw of the provider: its keys are what was sent, not one 'kw' dict
                if p.kind == p.VAR_KEYWORD and isinstance(out.get(p.name), dict):
                    out.update(out.pop(p.name))
            return out
    except (TypeError, ValueError):
        pass
    names = POSITIONAL.get(kind, ())
    out = {(names[i] if i < len(names) else f"arg{i}"): v for i, v in enumerate(args)}
    out.update(kwargs)
    return out


def rel_path(path: str) -> str:
    """The path as the database keeps it (see module doc); separators always '/'."""
    p = str(path)
    if os.path.isabs(p):
        try:
            rp = os.path.relpath(p, ROOT)
            if not rp.startswith(".."):
                p = rp
        except ValueError:                     # another drive (Windows): keep it absolute
            pass
    return p.replace("\\", "/")


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _jsonable(value: Any, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) > LONG_TEXT:
            return {"len": len(value), "sha256": hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()}
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        b = bytes(value)
        return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
    if isinstance(value, os.PathLike):
        return rel_path(os.fspath(value))
    if depth > 6:
        return f"<{type(value).__name__}>"
    if isinstance(value, dict):
        return {str(k): ("<redacted>" if _secret(k) else _jsonable(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v, depth + 1) for v in value]
    return f"<{type(value).__name__}>"         # a provider object / anything else: its kind only (no repr: may hold a secret)


def _meta_index(meta: Optional[Iterable[Dict]]) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for m in meta or []:
        if isinstance(m, dict) and m.get("file"):
            out.setdefault(str(m["file"]), m)
    return out


def _one_ref(param: str, item: Any, role: Optional[str], meta: Dict[str, Dict], warns: List[str]) -> Optional[Dict]:
    extra: Dict[str, Any] = {}
    label = None
    if isinstance(item, dict):
        path = item.get("path") or item.get("file") or item.get("url")
        label = item.get("label")
        role = item.get("role") or role
        extra = {k: _jsonable(v) for k, v in item.items() if k not in ("path", "file", "url", "label", "role") and not _secret(k)}
    elif isinstance(item, (str, os.PathLike)):
        path = os.fspath(item)
    else:
        return None
    if not path:
        return None
    path = str(path)
    base = os.path.basename(path)
    known = meta.get(base) or {}
    ref: Dict[str, Any] = {"param": param, "role": role or known.get("role") or param, "label": label or known.get("label"),
                           "path": rel_path(path), "file": base, "sha256": None}
    if known.get("plate_key"):
        ref["plate_key"] = known["plate_key"]
    if path.startswith(("http://", "https://")):
        ref["url"] = True                      # not a local file: nothing to fingerprint (not an error)
    else:
        try:
            ref["sha256"] = sha256_of(path)
        except Exception as e:  # noqa: BLE001 - a ledger: an unreadable picture is said, never stops the send
            warns.append(f"gói gửi: không tính được sha256 của {rel_path(path)} ({type(e).__name__}: {e}) — ghi sha null")
    if extra:
        ref["extra"] = extra
    return ref


def build(fn, args: Sequence, kwargs: Dict, *, kind: str, provider: Any, external_id: Any, model: Optional[str] = None,
          meta: Optional[Iterable[Dict]] = None, call: str = "submit", extra: Optional[Dict] = None) -> Tuple[str, List[str]]:
    """(JSON text of the package, warnings). `fn` is the provider method really called with (args, kwargs)."""
    warns: List[str] = []
    bound = _bind(fn, tuple(args or ()), dict(kwargs or {}), call if call in POSITIONAL else kind)
    index = _meta_index(meta)
    prompt = next((bound[k] for k in PROMPT_PARAMS if k in bound), None)
    negative = next((bound[k] for k in NEGATIVE_PARAMS if k in bound), None)
    refs: List[Dict] = []
    params: Dict[str, Any] = {}
    redacted: List[str] = []
    for name, value in bound.items():
        if name in PROMPT_PARAMS or name in NEGATIVE_PARAMS or str(name).startswith("_"):
            continue
        if _secret(name):
            redacted.append(name)
            continue
        if name in REF_PARAMS and value:
            items = value if isinstance(value, (list, tuple)) else [value]
            for item in items:
                r = _one_ref(name, item, REF_PARAMS[name], index, warns)
                if r is not None:
                    refs.append(r)
                else:
                    params.setdefault(name, []).append(_jsonable(item))
            continue
        params[name] = _jsonable(value)
    pkg: Dict[str, Any] = {
        "v": V, "call": call,
        "prompt": prompt if isinstance(prompt, str) or prompt is None else _jsonable(prompt),
        "negative": negative if isinstance(negative, str) or negative is None else _jsonable(negative),
        "refs": refs, "provider": str(getattr(provider, "name", "") or type(provider).__name__),
        "model": model if model is not None else (bound.get("model") if isinstance(bound.get("model"), str) else None),
        "params": params, "external_id": None if external_id is None else str(external_id),
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    if redacted:
        pkg["redacted"] = sorted(redacted)
    if extra:
        pkg.update({k: _jsonable(v) for k, v in extra.items()})
    return json.dumps(pkg, ensure_ascii=False, default=str), warns


def safe_build(*a, **kw) -> Tuple[Optional[str], List[str]]:
    """build() that never raises: (None, [why]) when the package itself could not be made — the send goes on regardless."""
    try:
        return build(*a, **kw)
    except Exception as e:  # noqa: BLE001 - the package is a ledger, never a gate
        return None, [f"không ghi được gói gửi ({type(e).__name__}: {e}) — job vẫn gửi, sent_package để trống"]


def draft_of(conn, sample_external_id: str) -> Dict[str, Any]:
    """N1 'nâng từ nháp': the draft job behind a final made from its sample, and the prompt that draft really sent (if kept)."""
    out: Dict[str, Any] = {"from_sample": str(sample_external_id)}
    row = conn.execute("SELECT id, model, sent_package FROM jobs WHERE external_id=? ORDER BY id LIMIT 1",
                       (str(sample_external_id),)).fetchone()
    if row is not None:
        out["draft_job_id"] = row["id"]
        out["draft_model"] = row["model"]
        try:
            prior = json.loads(row["sent_package"]) if row["sent_package"] else None
        except (TypeError, ValueError):
            prior = None
        if isinstance(prior, dict):
            out["draft_prompt"] = prior.get("prompt")
            out["draft_refs"] = prior.get("refs")
    return out
