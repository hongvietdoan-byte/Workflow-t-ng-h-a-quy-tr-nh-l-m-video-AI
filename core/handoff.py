"""V3.1 M6.2 handoff contract, JSONL shadow only.

This branch provides the JSONL writer contract only; it has no production
caller yet. Callers must pass a pinned snapshot. The module does not query or
mutate production tables, invoke builders/providers, or alter the handoff flow.
The package projection accepts M2.6 sent-package JSON (including M1.9 replay
output). Revision shape is validated but not fetched or verified against M2.5
write_guard. With the flag off, ``record`` returns before validation or I/O.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional

FLAG = "crew_handoff_shadow"
SCHEMA_VERSION = 1
FILENAME = "handoffs.jsonl"
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")

_DEPENDENCY_KEYS = {"kind", "rel_path", "sha256", "revision", "asset_id", "input_hash", "source"}
_PRODUCT_KEYS = {"path", "sha256", "kind", "job_id", "id", "revision"}
_QC_KEYS = {"id", "status", "path", "sha256"}


class HandoffInputError(ValueError):
    """Input does not contain a complete, safe handoff snapshot."""


def enabled() -> bool:
    from . import features

    return features.on(FLAG)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise HandoffInputError(f"{name} phải là số nguyên dương")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise HandoffInputError(f"{name} phải là số nguyên không âm")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffInputError(f"{name} phải là chuỗi không rỗng")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    value = _text(value, name)
    if not _SHA256.fullmatch(value):
        raise HandoffInputError(f"{name} phải là SHA-256 đủ 64 ký tự hex")
    return value.lower()


def _canonical_path(value: Any, name: str) -> str:
    path = _text(value, name)
    if "\\" in path:
        raise HandoffInputError(f"{name} phải dùng dấu / theo M2.6 rel_path")
    from .sent_package import rel_path

    if rel_path(path) != path:
        raise HandoffInputError(f"{name} chưa ở dạng chuẩn M2.6 rel_path")
    if not os.path.isabs(path) and ".." in path.split("/"):
        raise HandoffInputError(f"{name} không được đi ra ngoài thư mục gốc qua ..")
    return path


def _simple_rows(value: Any, name: str, allowed: set, required: set) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        raise HandoffInputError(f"{name} phải là danh sách")
    rows: List[Dict[str, Any]] = []
    for index, row in enumerate(value):
        label = f"{name}[{index}]"
        if not isinstance(row, dict):
            raise HandoffInputError(f"{label} phải là object")
        keys = set(row)
        if not all(isinstance(key, str) for key in keys):
            raise HandoffInputError(f"{label} có tên trường không hợp lệ")
        extra = keys - allowed
        missing = required - keys
        if extra:
            raise HandoffInputError(f"{label} có trường ngoài hợp đồng: {', '.join(sorted(extra))}")
        if missing:
            raise HandoffInputError(f"{label} thiếu trường: {', '.join(sorted(missing))}")
        clean = dict(row)
        for key, item in clean.items():
            if item is None:
                raise HandoffInputError(f"{label}.{key} thiếu giá trị")
            if isinstance(item, (dict, list, tuple, set, bytes, bytearray)):
                raise HandoffInputError(f"{label}.{key} phải là giá trị đơn giản")
            if not isinstance(item, (str, int, float, bool)):
                raise HandoffInputError(f"{label}.{key} không phải dữ liệu JSON đơn giản")
        try:
            json.dumps(clean, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise HandoffInputError(f"{label} không thể ghi JSON an toàn") from exc
        rows.append(clean)
    return rows


def _dependencies(value: Any) -> List[Dict[str, Any]]:
    rows = _simple_rows(value, "dependencies", _DEPENDENCY_KEYS, {"kind"})
    for index, row in enumerate(rows):
        label = f"dependencies[{index}]"
        row["kind"] = _text(row["kind"], f"{label}.kind")
        if not any(key in row for key in ("rel_path", "revision", "asset_id", "input_hash")):
            raise HandoffInputError(f"{label} cần rel_path, revision, asset_id hoặc input_hash")
        if "rel_path" in row:
            row["rel_path"] = _canonical_path(row["rel_path"], f"{label}.rel_path")
        if "sha256" in row:
            row["sha256"] = _digest(row["sha256"], f"{label}.sha256")
        if "revision" in row:
            row["revision"] = _nonnegative_int(row["revision"], f"{label}.revision")
        if "asset_id" in row:
            row["asset_id"] = _positive_int(row["asset_id"], f"{label}.asset_id")
        if "input_hash" in row:
            row["input_hash"] = _text(row["input_hash"], f"{label}.input_hash")
        if "source" in row:
            row["source"] = _text(row["source"], f"{label}.source")
    return rows


def _revision(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"scene_rev", "byd_v", "fields"}:
        raise HandoffInputError("revision phải có scene_rev, byd_v và fields từ snapshot nguồn")
    fields = value["fields"]
    if not isinstance(fields, dict) or not all(isinstance(key, str) and key.strip() for key in fields):
        raise HandoffInputError("revision.fields phải là object tên trường → revision")
    return {
        "scene_rev": _nonnegative_int(value["scene_rev"], "revision.scene_rev"),
        "byd_v": _nonnegative_int(value["byd_v"], "revision.byd_v"),
        "fields": {key: _nonnegative_int(rev, f"revision.fields.{key}") for key, rev in fields.items()},
    }


def dependencies_from_package(package: Any) -> List[Dict[str, Any]]:
    """Project M2.6 sent-package refs into immutable dependency records.

    ``package`` may be the JSON returned by M2.6 or the byte/string replay
    returned by M1.9's golden builder. Missing paths or hashes fail closed.
    """
    if isinstance(package, bytes):
        try:
            package = package.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HandoffInputError("sent_package không phải UTF-8 JSON") from exc
    if isinstance(package, str):
        try:
            package = json.loads(package)
        except ValueError as exc:
            raise HandoffInputError("sent_package JSON không hợp lệ") from exc
    if not isinstance(package, dict) or not isinstance(package.get("refs"), list):
        raise HandoffInputError("sent_package thiếu refs theo M2.6")
    deps = []
    for index, ref in enumerate(package["refs"]):
        if not isinstance(ref, dict):
            raise HandoffInputError(f"sent_package.refs[{index}] phải là object")
        kind = ref.get("role") or ref.get("param")
        dep = {
            "kind": _text(kind, f"sent_package.refs[{index}].kind"),
            "rel_path": _canonical_path(ref.get("path"), f"sent_package.refs[{index}].path"),
            "sha256": _digest(ref.get("sha256"), f"sent_package.refs[{index}].sha256"),
            "source": "sent_package",
        }
        if ref.get("asset_id") is not None:
            dep["asset_id"] = _positive_int(ref["asset_id"], f"sent_package.refs[{index}].asset_id")
        deps.append(dep)
    return deps


def _root(data_dir: Any) -> str:
    if not isinstance(data_dir, (str, os.PathLike)):
        raise HandoffInputError("data_dir phải là đường dẫn tuyệt đối")
    raw = os.fspath(data_dir)
    if not os.path.isabs(raw):
        raise HandoffInputError("data_dir phải là đường dẫn tuyệt đối")
    return os.path.realpath(os.path.abspath(raw))


def _file_path(data_dir: Any, project_id: Any) -> str:
    root = _root(data_dir)
    pid = _positive_int(project_id, "project_id")
    path = os.path.realpath(os.path.abspath(os.path.join(root, str(pid), "crew", FILENAME)))
    try:
        if os.path.normcase(os.path.commonpath((root, path))) != os.path.normcase(root):
            raise HandoffInputError("đường dẫn JSONL nằm ngoài data_dir")
    except ValueError as exc:
        raise HandoffInputError("đường dẫn JSONL không cùng ổ đĩa với data_dir") from exc
    return path


def record(*, data_dir: str, project_id: int, scene_id: int, shot_no: int,
           from_role: str, to_role: str, revision: Dict[str, Any],
           dependencies: List[Dict[str, Any]], products: List[Dict[str, Any]],
           qc_evidence: List[Dict[str, Any]], approval_state: str,
           handoff_id: Optional[str] = None, at: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Append one pinned handoff row; flag OFF is a zero-I/O no-op."""
    if not enabled():
        return None

    pid = _positive_int(project_id, "project_id")
    sid = _positive_int(scene_id, "scene_id")
    number = _positive_int(shot_no, "shot_no")
    sender = _text(from_role, "from_role")
    recipient = _text(to_role, "to_role")
    rev = _revision(revision)
    deps = _dependencies(dependencies)
    product_rows = _simple_rows(products, "products", _PRODUCT_KEYS, {"path", "sha256"})
    if not product_rows:
        raise HandoffInputError("products phải có ít nhất một sản phẩm")
    for index, product in enumerate(product_rows):
        product["path"] = _canonical_path(product["path"], f"products[{index}].path")
        product["sha256"] = _digest(product["sha256"], f"products[{index}].sha256")
        for key in ("kind",):
            if key in product:
                product[key] = _text(product[key], f"products[{index}].{key}")
        for key in ("job_id", "id"):
            if key in product:
                product[key] = _positive_int(product[key], f"products[{index}].{key}")
        if "revision" in product:
            product["revision"] = _nonnegative_int(product["revision"], f"products[{index}].revision")

    qc_rows = _simple_rows(qc_evidence, "qc_evidence", _QC_KEYS, {"id"})
    for index, evidence in enumerate(qc_rows):
        evidence["id"] = _text(evidence["id"], f"qc_evidence[{index}].id")
        if "status" in evidence:
            evidence["status"] = _text(evidence["status"], f"qc_evidence[{index}].status")
        if "path" in evidence:
            evidence["path"] = _canonical_path(evidence["path"], f"qc_evidence[{index}].path")
        if "sha256" in evidence:
            evidence["sha256"] = _digest(evidence["sha256"], f"qc_evidence[{index}].sha256")

    state = _text(approval_state, "approval_state")
    event_id = _text(handoff_id, "handoff_id") if handoff_id is not None else str(uuid.uuid4())
    timestamp = at or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    timestamp = _text(timestamp, "at")
    try:
        parsed = _dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HandoffInputError("at phải là thời điểm ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HandoffInputError("at phải có múi giờ")

    row = {
        "schema_version": SCHEMA_VERSION,
        "handoff_id": event_id,
        "created_at": timestamp,
        "project_id": pid,
        "scene_id": sid,
        "shot_no": number,
        "from_role": sender,
        "to_role": recipient,
        "revision": rev,
        "dependencies": deps,
        "products": product_rows,
        "qc_evidence": qc_rows,
        "approval_state": state,
    }
    try:
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise HandoffInputError("handoff không thể ghi JSON an toàn") from exc

    path = _file_path(data_dir, pid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded)
    return row


def latest(data_dir: str, project_id: int, scene_id: int, *,
           from_role: Optional[str] = None, to_role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the newest recorded matching handoff for one project/shot."""
    pid = _positive_int(project_id, "project_id")
    sid = _positive_int(scene_id, "scene_id")
    source = _text(from_role, "from_role") if from_role is not None else None
    target = _text(to_role, "to_role") if to_role is not None else None
    path = _file_path(data_dir, pid)
    try:
        stream = open(path, encoding="utf-8")
    except FileNotFoundError:
        return None
    selected = None
    with stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise HandoffInputError(f"JSONL hỏng tại dòng {line_number}") from exc
            if not isinstance(row, dict) or row.get("schema_version") != SCHEMA_VERSION:
                raise HandoffInputError(f"schema JSONL không hợp lệ tại dòng {line_number}")
            if row.get("project_id") != pid or row.get("scene_id") != sid:
                continue
            if source is not None and row.get("from_role") != source:
                continue
            if target is not None and row.get("to_role") != target:
                continue
            selected = row
    return selected
