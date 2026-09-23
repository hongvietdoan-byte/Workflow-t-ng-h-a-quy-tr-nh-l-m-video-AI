"""QC policy: one choice instead of six separate knobs (threshold, automatic reject floor, automatic fix, retries, review zone).

Each preset writes the underlying project columns, so the QC code (Pipeline.apply_qc, autoqc, autopilot) is unchanged; "custom"
keeps whatever the person set by hand. Hard criteria (data/qc_checklist.json `hard_floor`) apply in every preset.
"""
from typing import Dict, Optional

PRESETS: Dict[str, Dict] = {
    "strict": {"label": "Chặt", "threshold": 0.88, "reject_floor": 0.55, "autofix": 1, "max_retry": 3,
               "note": "Ảnh dưới 0,88 được Claude tự gen lại tối đa 3 lần rồi mới đến bạn; hợp với cảnh quan trọng, tốn credit hơn."},
    "balanced": {"label": "Cân bằng", "threshold": 0.82, "reject_floor": 0.5, "autofix": 1, "max_retry": 2,
                 "note": "Ảnh dưới 0,82 được tự gen lại tối đa 2 lần; phần lớn dự án nên dùng mức này."},
    "saver": {"label": "Tiết kiệm credit", "threshold": 0.75, "reject_floor": 0.4, "autofix": 0, "max_retry": 1,
              "note": "Không tự gen lại: Claude chỉ chấm điểm gợi ý, ảnh rất tệ (< 0,4) mới bị loại; bạn tự quyết phần còn lại."},
}
CUSTOM = "custom"


def current(project_row) -> str:
    try:
        value = project_row["qc_policy"]
    except (KeyError, IndexError):
        value = None
    return value if value in PRESETS else CUSTOM


def apply(p, project_id: int, key: str) -> None:
    if key == CUSTOM:
        p.set_project_field(project_id, "qc_policy", CUSTOM)
        return
    preset = PRESETS[key]
    p.set_threshold(project_id, preset["threshold"])
    p.set_reject_floor(project_id, preset["reject_floor"])
    p.set_qc_autofix(project_id, bool(preset["autofix"]))
    p.set_max_retry(project_id, preset["max_retry"])
    p.set_project_field(project_id, "qc_policy", key)


def describe(project_row) -> str:
    """One plain sentence of what happens to a picture, from the project's actual settings."""
    th = project_row["qc_auto_pass_threshold"]
    floor: Optional[float] = project_row["qc_reject_floor"]
    retry = project_row["max_retry_count"]
    auto = project_row["operating_mode"] == "auto"
    fix = bool(project_row["qc_autofix"])
    who = "Claude tự duyệt ảnh đạt" if auto else "ảnh đạt vẫn chờ bạn duyệt"
    if auto or fix:
        low = f"ảnh dưới {th:.2f} được tự gen lại tối đa {retry} lần (mỗi lần tốn credit), sau đó chờ bạn"
    else:
        low = "ảnh dưới ngưỡng chỉ được gắn điểm gợi ý" + (f", dưới {floor:.2f} thì bị loại" if floor is not None else "")
    return f"Ngưỡng đạt {th:.2f}: {who}; {low}. Tiêu chí chặn cứng (đúng nhân vật, tay/mặt, chân chạm đất) luôn áp dụng."
