"""Ghi các phát hiện giám sát CHẶN/LỚN vào bản kế hoạch được chỉ định.

Hàm này chỉ sửa file kế hoạch được caller truyền vào. Ứng dụng giám sát phải
chỉ truyền đường dẫn `chinh` trong devsys/plans.json sau khi đã xác nhận đó là
kế hoạch nằm trong repo; tests luôn dùng file tạm.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import plan_progress


class PlanWriterError(ValueError):
    """Finding không đủ dữ kiện hoặc file kế hoạch không đúng cấu trúc an toàn."""


_AXIS = {
    "direction": "direction", "đúng hướng": "direction", "dung huong": "direction",
    "errors": "errors", "lỗi": "errors", "loi": "errors", "lỗi / lỗ hổng": "errors",
    "dashboard": "dashboard", "dashboard theo mốc": "dashboard",
}
_SEVERITY = {"chan": "CHẶN", "chặn": "CHẶN", "lon": "LỚN", "lớn": "LỚN",
             "nho": "NHỎ", "nhỏ": "NHỎ"}
_EVIDENCE_RE = re.compile(r"^(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+:\d+(?::\d+)?$")
_M9_RE = re.compile(r"^\s*- \[(?: |x|X)\] M9\.(\d+) · ")
_MARKER_RE = re.compile(r"\[(GS-[0-9a-f]{12})\]")


def _single_line(value, field: str, limit: int = 180) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    text = text.replace("·", ",").strip()
    if not text:
        raise PlanWriterError(f"thiếu {field}")
    return text[:limit]


def _axis(value) -> str:
    key = " ".join(str(value or "").strip().lower().replace("_", " ").split())
    if key not in _AXIS:
        raise PlanWriterError("axis phải thuộc đúng hướng / lỗi / dashboard")
    return _AXIS[key]


def _severity(value) -> str:
    key = str(value or "").strip().lower()
    if key not in _SEVERITY:
        raise PlanWriterError("severity phải là CHẶN, LỚN hoặc NHỎ")
    return _SEVERITY[key]


def _evidence(finding: Dict) -> str:
    raw = finding.get("evidence")
    items = [raw] if isinstance(raw, str) else raw if isinstance(raw, (list, tuple)) else []
    for item in items:
        text = str(item or "").strip().replace("\\", "/")
        if _EVIDENCE_RE.fullmatch(text):
            path_part = text.rsplit(":", 1)[0]
            if all(part not in {".", ".."} for part in path_part.split("/")):
                return text
    raise PlanWriterError("phát hiện CHẶN/LỚN cần bằng chứng file:dòng")


def finding_id(finding: Dict) -> str:
    """Mã ổn định theo trục + file:dòng + loại phát hiện; không phụ thuộc câu chữ AI."""
    axis = _axis(finding.get("axis"))
    evidence = _evidence(finding)
    kind = _single_line(finding.get("type"), "type", 80).lower()
    digest = hashlib.sha256(f"{axis}|{evidence}|{kind}".encode("utf-8")).hexdigest()[:12]
    return "GS-" + digest


def _run_info(finding: Dict) -> Tuple[str, int, str]:
    raw_date = finding.get("observed_on") or date.today().isoformat()
    try:
        run_date = date.fromisoformat(str(raw_date)).isoformat()
    except ValueError:
        raise PlanWriterError("observed_on phải theo YYYY-MM-DD") from None
    try:
        run_no = int(finding.get("run_no", 1))
    except (TypeError, ValueError):
        raise PlanWriterError("run_no phải là số nguyên dương") from None
    if run_no < 1:
        raise PlanWriterError("run_no phải là số nguyên dương")
    return run_date, run_no, f"GIÁM SÁT {run_date} (#{run_no})"


def _m9_bounds(lines: Sequence[str]) -> Tuple[int, int, int]:
    heads = [i for i, line in enumerate(lines) if re.match(r"^###\s+M9(?:\s|—|$)", line)]
    if len(heads) != 1:
        raise PlanWriterError("cần đúng một mục ### M9 trong kế hoạch")
    start = heads[0]
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^##\s+|^###\s+", lines[i])), len(lines))
    journals = [i for i, line in enumerate(lines) if re.match(r"^##\s+6\.\s+Nhật ký\s*$", line)]
    if len(journals) != 1 or journals[0] < end:
        raise PlanWriterError("cần mục ## 6. Nhật ký sau mục M9")
    return start, end, journals[0]


def _validate_findings(findings: Iterable[Dict]) -> Tuple[List[Dict], List[Dict]]:
    write, report_only, seen = [], [], set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise PlanWriterError("mỗi finding phải là object")
        severity = _severity(finding.get("severity"))
        if severity == "NHỎ":
            report_only.append(dict(finding))
            continue
        axis = _axis(finding.get("axis"))
        evidence = _evidence(finding)
        kind = _single_line(finding.get("type"), "type", 80)
        key = finding_id(finding)
        if key in seen:
            continue
        seen.add(key)
        task_id = str(finding.get("task_id") or "").strip()
        if not task_id or not re.fullmatch(r"[A-Z]+\d*(?:\.\d+)?", task_id):
            raise PlanWriterError(f"phát hiện {key} cần task_id hợp lệ để ghi chú việc bị ảnh hưởng")
        title = _single_line(finding.get("title") or finding.get("reason"), "title/reason")
        source = _single_line(finding.get("source") or evidence, "source", 100)
        run_date, run_no, run_tag = _run_info(finding)
        weight = finding.get("weight", 2)
        try:
            weight = int(weight)
        except (TypeError, ValueError):
            raise PlanWriterError("weight phải là 1, 2 hoặc 3") from None
        if weight not in (1, 2, 3):
            raise PlanWriterError("weight phải là 1, 2 hoặc 3")
        write.append({**finding, "axis": axis, "severity": severity, "evidence_ref": evidence, "type": kind,
                      "finding_id": key, "task_id": task_id, "title": title, "source_text": source,
                      "run_date": run_date, "run_no": run_no, "run_tag": run_tag, "weight": weight})
    return write, report_only


def _append_observation(line: str, tag: str, note: str, marker: str) -> str:
    observation = f"{tag} [{marker}]: {note}"
    if observation in line:
        return line
    if marker in line and tag in line:
        return line
    return line.rstrip() + " · " + observation


def _atomic_write(path: Path, text: str) -> None:
    mode = path.stat().st_mode
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, mode)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        backup = path.with_name(f"{path.name}.giam-sat.{stamp}.bak")
        shutil.copy2(path, backup)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def apply_findings(plan_path: str, findings: Iterable[Dict]) -> Dict:
    """Ghi finding CHẶN/LỚN idempotent vào kế hoạch; NHỎ chỉ trả trong `report_only`.

    `run_no` và `observed_on` là metadata của lần giám sát; cùng finding/lần chạy
    có thể áp dụng lặp mà không tạo thêm dòng hay ghi chú trùng.
    """
    path = Path(plan_path)
    if not path.is_file():
        raise PlanWriterError("không tìm thấy file kế hoạch")
    original = path.read_text(encoding="utf-8")
    findings_to_write, report_only = _validate_findings(findings)
    if not findings_to_write:
        return {"changed": False, "written": 0, "report_only": report_only, "backup": None}
    lines = original.splitlines()
    m9_start, m9_end, journal = _m9_bounds(lines)

    task_lines: Dict[str, List[int]] = {}
    for i, line in enumerate(lines):
        match = plan_progress.TASK_RE.match(line)
        if match:
            task_lines.setdefault(match.group("id"), []).append(i)
    for finding in findings_to_write:
        matches = task_lines.get(finding["task_id"], [])
        if len(matches) != 1:
            raise PlanWriterError(f"task_id {finding['task_id']} phải khớp đúng một dòng TASK_RE trong kế hoạch")

    m9_by_marker = {}
    max_m9 = -1
    for i in range(m9_start + 1, m9_end):
        match = _M9_RE.match(lines[i])
        if match:
            max_m9 = max(max_m9, int(match.group(1)))
            for marker in _MARKER_RE.findall(lines[i]):
                m9_by_marker[marker] = i

    changed_ids, new_rows, task_notes = [], [], {}
    for finding in findings_to_write:
        marker = finding["finding_id"]
        tag = finding["run_tag"]
        note = finding["title"]
        existing = m9_by_marker.get(marker)
        if existing is None:
            max_m9 += 1
            tid = f"M9.{max_m9}"
            row = (f"- [ ] {tid} · {finding['axis']} — {finding['title']} · nặng:{finding['weight']} · ⬜ · "
                   f"{tag} {finding['source_text']} [{marker}]")
            new_rows.append(row)
            m9_by_marker[marker] = -1  # subsequent duplicates in the same input reuse this row
            changed_ids.append(marker)
        else:
            row = lines[existing]
            updated = _append_observation(row, tag, note, marker)
            if updated != row:
                lines[existing] = updated
                changed_ids.append(marker)
        task_index = task_lines[finding["task_id"]][0]
        note_line = _append_observation(lines[task_index], tag, note, marker)
        if note_line != lines[task_index]:
            task_notes[task_index] = note_line

    for index, updated in task_notes.items():
        lines[index] = updated
    if new_rows:
        lines[m9_end:m9_end] = new_rows

    # One nhật ký row per monitor run. Re-running the same run updates that row,
    # while a later run remains a separate observation.
    journal += len(new_rows)
    runs: Dict[Tuple[str, int], List[str]] = {}
    for finding in findings_to_write:
        runs.setdefault((finding["run_date"], finding["run_no"]), []).append(finding["finding_id"])
    journal_lines = []
    for (run_date, run_no), ids in sorted(runs.items()):
        run_marker = f"[GIAM-SAT-RUN:{run_date}:{run_no}]"
        labels = ", ".join(sorted(set(ids)))
        row = f"- {run_date}: GIÁM SÁT (#{run_no}) — {len(set(ids))} phát hiện CHẶN/LỚN: {labels} {run_marker}"
        prior = next((i for i, line in enumerate(lines) if run_marker in line), None)
        if prior is None:
            journal_lines.append(row)
        else:
            lines[prior] = row
    if journal_lines:
        lines[journal + 1:journal + 1] = journal_lines

    updated_text = "\n".join(lines) + ("\n" if original.endswith(("\n", "\r")) else "")
    changed = updated_text != original
    backup_path = None
    if changed:
        _atomic_write(path, updated_text)
        backups = sorted(path.parent.glob(path.name + ".giam-sat.*.bak"), key=lambda p: p.stat().st_mtime_ns)
        backup_path = str(backups[-1]) if backups else None
    return {"changed": changed, "written": len(findings_to_write), "report_only": report_only,
            "finding_ids": changed_ids, "backup": backup_path}
