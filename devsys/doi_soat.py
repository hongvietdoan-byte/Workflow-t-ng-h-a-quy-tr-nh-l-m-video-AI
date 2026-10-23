"""Đối soát chỉ đọc giữa màu sơ đồ, sổ lỗi và trạng thái việc kế hoạch."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from . import pipeline_maps

KINDS = ("LOI", "LONG", "THIEU", "LECH", "KHONG_VIEC")
DONE = set(pipeline_maps.DONE)
COLOR_NAMES = {"xanh": "xanh", "vang": "vàng", "do": "đỏ", "tim": "tím", "xam": "xám"}


def _stage_id(value: object) -> Optional[str]:
    """Đưa cả khâu con như L3b về khâu chính L3."""
    text = str(value or "")
    if len(text) >= 2 and text[0] == "L" and text[1].isdigit():
        index = 2
        while index < len(text) and text[index].isdigit():
            index += 1
        return text[:index]
    return None


def _task_pairs(row: Mapping, plan_status: Optional[Mapping[str, str]] = None) -> List[Dict[str, str]]:
    raw = row.get("tasks")
    if raw is None:
        raw = (row.get("inputs") or {}).get("plan") if isinstance(row.get("inputs"), Mapping) else None
    if raw is None:
        raw = row.get("plan")
    if isinstance(raw, Mapping):
        pairs = raw.items()
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        pairs = ((item.get("id"), item.get("status", "?")) for item in raw if isinstance(item, Mapping))
    else:
        pairs = ()
    authoritative = plan_status or {}
    result = []
    for task_id, raw_status in pairs:
        task_id = str(task_id or "").strip()
        if not task_id:
            continue
        status = authoritative.get(task_id, raw_status)
        result.append({"id": task_id, "status": str(status or "?")})
    return sorted(result, key=lambda item: item["id"])


def _open_errors(row: Mapping, errors: Optional[Iterable[Mapping]] = None,
                 plan_status: Optional[Mapping[str, str]] = None) -> List[Dict]:
    source = errors if errors is not None else row.get("open_errors") or []
    allowed_stages = {_stage_id(value) for value in (row.get("khau") or [])}
    row_stage = _stage_id(row.get("id"))
    if row_stage:
        allowed_stages.add(row_stage)
    out = []
    authoritative = plan_status or {}
    for error in source:
        if not isinstance(error, Mapping):
            continue
        status = str(error.get("status") or "UNKNOWN").upper()
        if status in {"VERIFIED", "WONT_FIX"}:
            continue
        error_stage = _stage_id(error.get("stage"))
        if errors is not None and error_stage not in allowed_stages:
            continue
        item = dict(error)
        task_id = str(item.get("plan_task") or "").strip()
        item["plan_task"] = task_id or None
        item["plan_task_status"] = authoritative.get(task_id, item.get("plan_task_status", "?")) if task_id else None
        out.append(item)
    return sorted(out, key=lambda item: str(item.get("id") or ""))


def classify_row(row: Mapping) -> List[str]:
    """Trả loại cảnh báo của một dòng; không thay đổi dữ liệu đầu vào."""
    color = str(row.get("color") or "xam").lower()
    tasks = _task_pairs(row)
    errors = _open_errors(row)
    kinds: Set[str] = set()

    if errors:
        kinds.add("LOI")
    if color == "vang":
        kinds.add("LONG")
    if color == "do":
        kinds.add("THIEU")

    # Sơ đồ còn đỏ/vàng sau khi toàn bộ việc liên kết đã xong là lệch kế hoạch.
    if color in {"do", "vang"} and tasks and all(item["status"] == "✅" for item in tasks):
        kinds.add("LECH")
    # Màu xanh nhưng có ít nhất một việc chưa xong là lệch theo chiều ngược lại.
    if color == "xanh" and any(item["status"] not in DONE for item in tasks):
        kinds.add("LECH")

    if color in {"do", "vang"} and not tasks:
        kinds.add("KHONG_VIEC")
    if any(not error.get("plan_task") for error in errors):
        kinds.add("KHONG_VIEC")
    return [kind for kind in KINDS if kind in kinds]


def _evidence_for(row: Mapping, errors: Sequence[Mapping]) -> List[str]:
    evidence = []
    for value in row.get("why") or []:
        if str(value).strip():
            evidence.append(str(value).strip())
    for error in errors:
        source = str(error.get("source_document") or "").strip()
        refs = error.get("evidence") or []
        if isinstance(refs, str):
            refs = [refs]
        for ref in refs:
            item = " · ".join(part for part in (source, str(ref).strip()) if part)
            if item:
                evidence.append(item)
    return list(dict.fromkeys(evidence)) or [f"devsys/pipeline_maps.json:{row.get('id', 'không rõ mã')}"]


def _proposal(row: Mapping, kinds: Sequence[str], errors: Sequence[Mapping]) -> Dict[str, str]:
    stages = [_stage_id(value) for value in (row.get("khau") or [])]
    stage = _stage_id(row.get("id")) or next((item for item in stages if item), "")
    tasks = _task_pairs(row)
    active_tasks = [task for task in tasks if task["status"] not in DONE]
    reasons = []
    if "LOI" in kinds:
        reasons.append("còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật")
    if "LONG" in kinds:
        reasons.append("khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động)")
    if "THIEU" in kinds:
        reasons.append("sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu")
    if "LECH" in kinds:
        reasons.append("trạng thái kế hoạch và màu/bằng chứng hiện tại chưa khớp")
    if "KHONG_VIEC" in kinds:
        reasons.append("khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp")
    if errors:
        reasons.append("mã lỗi: " + ", ".join(str(error.get("id") or "không rõ mã") for error in errors))
    if active_tasks:
        title = f"Tiếp tục {active_tasks[0]['id']} và chốt tiêu chí cho {row.get('id', 'khâu chưa rõ')}"
    elif "LOI" in kinds and not set(kinds).intersection({"LONG", "THIEU", "LECH", "KHONG_VIEC"}):
        ids = ", ".join(str(error.get("id") or "lỗi chưa rõ mã") for error in errors)
        title = f"Xác minh lỗi mở bằng bằng chứng chạy thật: {ids or row.get('id', 'khâu chưa rõ')}"
    elif "KHONG_VIEC" in kinds or not tasks:
        title = f"Bổ sung việc vào plan cho {row.get('id', 'khâu chưa rõ')}"
    else:
        title = f"Bổ sung việc xử lý phần còn lệch ở {row.get('id', 'khâu chưa rõ')}"
    return {
        "title": title,
        "stage": stage,
        "reason": "; ".join(reasons) or "kiểm tra lại liên kết giữa sơ đồ, lỗi và kế hoạch",
        "evidence": "; ".join(_evidence_for(row, errors)),
    }


def _rows_from_model(model: Mapping) -> List[Dict]:
    result = []
    for row in (model.get("khau") or {}).get("rows") or []:
        item = dict(row)
        if isinstance(item.get("label"), (list, tuple)):
            item["label"] = " · ".join(str(value) for value in item["label"] if value)
        item["kind"] = "khâu"
        item["khau"] = item.get("khau") or [item.get("id")]
        result.append(item)
    for row in (model.get("dashboard") or {}).get("cells") or []:
        item = dict(row)
        item["kind"] = "ô Dashboard"
        result.append(item)
    for row in (model.get("truong") or {}).get("nodes") or []:
        item = dict(row)
        item["kind"] = "nút trường"
        result.append(item)
    return result


def build_reconciliation(model: Mapping, errors: Iterable[Mapping],
                         plan_status: Optional[Mapping[str, str]] = None) -> Dict:
    """Dựng báo cáo từ snapshot đầu vào; tuyệt đối không ghi kế hoạch hay trạng thái lỗi."""
    status_map = dict(plan_status or {})
    all_errors = [dict(error) for error in errors if isinstance(error, Mapping)]
    rows = []
    stage_kinds: Dict[str, Set[str]] = {}
    for source in _rows_from_model(model):
        tasks = _task_pairs(source, status_map)
        source["tasks"] = tasks
        item_errors = _open_errors(source, all_errors, status_map)
        source["open_errors"] = item_errors
        source["open_error_ids"] = [str(error.get("id") or "") for error in item_errors if error.get("id")]
        source["types"] = classify_row(source)
        source["proposal"] = _proposal(source, source["types"], item_errors) if source["types"] else None
        rows.append(source)
        related = {_stage_id(value) for value in (source.get("khau") or [])}
        own_stage = _stage_id(source.get("id"))
        if own_stage:
            related.add(own_stage)
        for stage in related - {None}:
            stage_kinds.setdefault(stage, set()).update(source["types"])

    summary = {kind: sum(kind in kinds for kinds in stage_kinds.values()) for kind in KINDS}
    return {"rows": rows, "summary": summary, "plan_changed": False,
            "stages_counted": len(stage_kinds), "warnings": list(model.get("warnings") or [])}


def render_markdown(report: Mapping, generated_on: Optional[str] = None) -> str:
    """Render bản xuất thuần văn bản, không thực hiện cập nhật dữ liệu nguồn."""
    date = generated_on or __import__("datetime").date.today().isoformat()
    summary = report.get("summary") or {kind: 0 for kind in KINDS}
    lines = [f"# Đối soát khâu ↔ kế hoạch — {date}", "", "Báo cáo chỉ đọc; không tự cập nhật kế hoạch hoặc sổ lỗi.", "",
             "## Tổng hợp số khâu có vấn đề", "", "| Loại | Số khâu |", "|---|---:|"]
    lines.extend(f"| {kind} | {int(summary.get(kind, 0) or 0)} |" for kind in KINDS)
    lines += ["", "## Chi tiết từng khâu, ô và nút", ""]
    for row in report.get("rows") or []:
        types = row.get("types") or []
        kinds_text = ", ".join(types) if types else "Không có cảnh báo phân loại"
        color = COLOR_NAMES.get(str(row.get("color") or ""), str(row.get("color") or "chưa rõ"))
        lines += [f"### {row.get('id', 'không rõ mã')} — {row.get('label', '')}", "",
                  f"- Loại dòng: {row.get('kind', 'không rõ')}", f"- Màu: {color}",
                  f"- Khâu liên quan: {', '.join(str(v) for v in row.get('khau') or []) or 'chưa gắn'}",
                  f"- Phân loại: {kinds_text}"]
        why = row.get("why") or []
        if why:
            lines.append("- Lý do: " + " · ".join(str(value).replace("\n", " ") for value in why))
        tasks = row.get("tasks") or []
        if tasks:
            lines.append("- Việc kế hoạch: " + ", ".join(f"{task['id']} ({task['status']})" for task in tasks))
        errors = row.get("open_errors") or []
        if errors:
            lines.append("- Lỗi đang mở: " + ", ".join(
                f"{error.get('id', 'mã?')} — {error.get('title', '')} [{error.get('status', 'UNKNOWN')}]"
                f" → {error.get('plan_task') or 'chưa gắn việc'}"
                for error in errors))
        proposal = row.get("proposal")
        if proposal:
            lines += [f"- Việc đề xuất thêm vào plan: **{proposal.get('title', '')}**",
                      f"- Khâu đề xuất: {proposal.get('stage') or 'chưa xác định'}",
                      f"- Lý do đề xuất: {proposal.get('reason', '')}",
                      f"- Bằng chứng: {proposal.get('evidence', '')}"]
        lines.append("")
    warnings = report.get("warnings") or []
    if warnings:
        lines += ["## Cảnh báo nguồn", ""] + [f"- {warning}" for warning in warnings] + [""]
    return "\n".join(lines).rstrip() + "\n"


def write_markdown(path: os.PathLike | str, text: str) -> str:
    """Tạo đúng file đích do caller yêu cầu, không ghi đè bản báo cáo có sẵn."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(str(text))
    return str(target)
