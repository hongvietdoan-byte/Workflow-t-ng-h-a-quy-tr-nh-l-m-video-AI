"""Mức tự động (đợt 3, 01/10): ONE choice over three existing settings of a project — who approves pictures/clips (operating_mode), the
automatic run's gates (bible / pilot / storyboard) and the QC policy. Nothing new is stored: the level is READ back from those three, so
changing any of them by hand (⚙ → Dự án → chi tiết, step 1 gates, step 2 QC policy) just shows as "Tùy chỉnh".

  all  Tôi duyệt hết      : people approve every picture/clip; the run stops at Bible, pilot and storyboard; strict QC.
  main Duyệt cổng chính   : the default of a new project — the run stops at Bible and storyboard; balanced QC.
  auto Tự chạy trong trần : Claude approves pictures by QC; the run does not stop at the Bible; it still stops at the storyboard unless
                            the QC has earned the right to skip it (feature `storyboard_auto_trust`, core/effectiveness.look_trust) —
                            money gates (locked project budget, trial cap) always apply.
"""
import json
from typing import Dict, Optional

from . import autopilot, qc_policy

LEVELS: Dict[str, Dict] = {
    "all": {"label": "Tôi duyệt hết", "mode": "human_qc", "policy": "strict",
            "gates": {"bible": True, "pilot": True, "storyboard": True},
            "desc": "Làm từng bước: mọi ảnh / clip chờ bạn duyệt. Chạy tự động: dừng ở Bible, mẫu thử và storyboard; QC mức Chặt (gen lại nhiều hơn)."},
    "main": {"label": "Duyệt cổng chính", "mode": "human_qc", "policy": "balanced",
             "gates": {"bible": True, "pilot": False, "storyboard": True},
             "desc": "Chạy tự động dừng ở Bible và storyboard (trước khi chi tiền video); QC mức Cân bằng. Mặc định của dự án mới."},
    "auto": {"label": "Tự chạy trong trần", "mode": "auto", "policy": "balanced",
             "gates": {"bible": False, "pilot": False, "storyboard": True},
             "desc": "Claude tự duyệt ảnh theo QC; không dừng ở Bible; vẫn dừng ở storyboard trừ khi QC đã đo đủ tin cậy để bỏ qua; "
                     "trần tiền (ngân sách khóa, đợt thử) luôn áp dụng."},
}


def current(p, pid: int) -> str:
    """'all' | 'main' | 'auto' | 'custom' from the project's real settings."""
    proj = p.project(pid)
    gates = autopilot.get_gates(p, pid)
    mode = proj["operating_mode"]
    try:
        saved = json.loads(proj["autopilot_saved_cfg"] or "null")
    except (ValueError, KeyError, IndexError, TypeError):
        saved = None
    if saved and saved.get("operating_mode"):           # the run switched the project to automatic QC; give back the person's choice
        mode = saved["operating_mode"]
    policy = qc_policy.current(proj)
    for key, lv in LEVELS.items():
        if (mode == lv["mode"] and policy == lv["policy"]
                and all(bool(gates.get(g)) == v for g, v in lv["gates"].items())):
            return key
    return "custom"


def apply(p, pid: int, key: str) -> None:
    if key not in LEVELS:
        raise ValueError(f"không có mức {key}")
    lv = LEVELS[key]
    if p.project(pid)["autopilot_saved_cfg"]:
        raise ValueError("đang chạy tự động — dừng hoặc đặt lại trước khi đổi mức")
    p.set_mode(pid, lv["mode"])
    qc_policy.apply(p, pid, lv["policy"])
    autopilot.set_gates(p, pid, dict(lv["gates"]))


def label(key: str) -> str:
    return LEVELS[key]["label"] if key in LEVELS else "Tùy chỉnh"
