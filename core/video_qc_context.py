"""QC clip hiểu ngữ cảnh shot (người dùng 08/10, dự án #24).

Vì sao: QC clip chỉ nhận Character Lock của `characters` + motion prompt, không biết (a) nhân vật có nhiều dạng / biến hình giữa
clip — shot 7 #24 "biến hình từ dạng 1 sang dạng 2": nét gạch chéo truyện tranh trên mặt (đúng hồ sơ YÊU NỮ TÀ LINH DẠNG 2) bị chấm
"identity/style break"; (b) hiệu ứng chủ ý của kịch bản — shot 9 "màn hình nhòe, nhấp nháy, nhiễu sóng như mất kết nối": QC phạt
"jerks" / artifacts 0,30 (tiêu chí chặn cứng) dù nhiễu là ý đồ. Job 592/594 bị loại + xếp gen lại.

Ở đây (thuần dữ liệu, không gọi model):
- `shot_characters`: mọi nhân vật của shot = `characters` + tên dự án nhắc trong câu hành động/ý đồ + các DẠNG khác của cùng nhân vật
  khi shot có biến hình (dạng sau biến hình thường không nằm trong `characters`).
- `profiles_block`: mô tả hồ sơ (characters.description) từng nhân vật, nhóm theo dạng.
- `intent_block`: câu hành động / trạng thái cuối / ý đồ cảm xúc / motion (EN) + chỉ dẫn: hiệu ứng, biến hình, glitch kịch bản yêu
  cầu không phải lỗi.
- `intended_effects` / `soft_criteria`: nhận diện BẰNG CODE (từ chữ trong hành động / motion) shot có nhiễu chủ ý → `artifacts` không
  chặn cứng (pipeline.apply_qc `soft`).
"""
import json
import re
from typing import Dict, Iterable, List, Optional, Tuple

NOISE_WORDS = ("glitch", "nhiễu", "nhấp nháy", "nhòe", "mất kết nối", "mất tín hiệu", "flicker", "signal loss", "lost connection",
               "distortion", "static noise", "tv static", "full-frame static", "nhiễu sóng", "chớp giật", "vhs", "datamosh")
"""Chữ cho biết kịch bản CỐ Ý làm nhiễu / nhấp nháy / méo hình (so khớp không phân biệt hoa thường, trên câu hành động + motion).
Không có "static" trần: motion prompt nào cũng có "camera static"."""
TRANSFORM_WORDS = ("biến hình", "hóa thành", "hoá thành", "biến thành", "chuyển dạng", "lột xác", "transform", "morph", "shapeshift",
                   "từ dạng", "sang dạng", "from form", "into form", "to form")
"""Chữ cho biết nhân vật đổi dạng giữa clip (không có "dạng 2" trần: tên nhân vật "... DẠNG 2" không phải biến hình)."""
SOFT_WHEN_NOISE = ("artifacts",)
"""Tiêu chí chặn cứng KHÔNG chặn cứng ở shot có nhiễu chủ ý (vẫn tính vào điểm trung bình, vẫn ghi lỗi QC thấy)."""
_FORM = re.compile(r"\s*[-–(]?\s*(?:DẠNG|DANG|FORM|PHASE|GIAI ĐOẠN)\s*\d+\s*\)?\s*$", re.IGNORECASE)
_INTENT_KEYS = ("action", "text", "end_state", "action_peak", "transition_in", "transition_out")


def _intent_text(data: Dict, motion_prompt: Optional[str]) -> str:
    """Mọi chữ nói shot làm gì (không lấy âm thanh / ánh sáng: "noise" của tiếng không phải hình)."""
    parts = [str(data.get(k) or "") for k in _INTENT_KEYS]
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    parts += [str(en.get("action") or ""), str(en.get("end_state") or "")]
    perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    parts += [str(perf.get(k) or "") for k in ("face", "body", "timing", "motive")]
    parts.append(motion_prompt or "")
    return " ".join(p for p in parts if p).lower()


def _hits(text: str, words: Iterable[str]) -> List[str]:
    return [w for w in words if w in text]


def intended_effects(data: Dict, motion_prompt: Optional[str] = None) -> Dict[str, List[str]]:
    """{"noise": [chữ khớp], "transform": [chữ khớp]} — hiệu ứng chủ ý đọc từ câu hành động + motion prompt."""
    text = _intent_text(data, motion_prompt)
    return {"noise": _hits(text, NOISE_WORDS), "transform": _hits(text, TRANSFORM_WORDS)}


def soft_criteria(data: Dict, motion_prompt: Optional[str] = None) -> Tuple[str, ...]:
    """Tiêu chí không chặn cứng cho clip này: `artifacts` khi kịch bản cố ý làm nhiễu / nhấp nháy / méo hình."""
    return SOFT_WHEN_NOISE if intended_effects(data, motion_prompt)["noise"] else ()


def base_name(name: str) -> str:
    """'YÊU NỮ TÀ LINH DẠNG 2' → 'YÊU NỮ TÀ LINH' (tên không có dạng giữ nguyên)."""
    return _FORM.sub("", str(name or "")).strip().upper()


def shot_characters(conn, project_id: int, data: Dict, motion_prompt: Optional[str] = None) -> List[str]:
    """Nhân vật của shot: `characters` + tên dự án nhắc trong câu hành động/ý đồ + (shot có biến hình) mọi dạng khác của cùng nhân
    vật. Giữ thứ tự: `characters` trước."""
    names = [str(n) for n in (data.get("characters") or []) if n]
    project = [r["name"] for r in conn.execute("SELECT name FROM characters WHERE project_id=? ORDER BY id", (project_id,))]
    text = _intent_text(data, motion_prompt)
    out = list(names)
    for n in project:
        if n not in out and n.lower() in text:
            out.append(n)
    if intended_effects(data, motion_prompt)["transform"]:
        bases = {base_name(n) for n in out}
        out += [n for n in project if n not in out and base_name(n) in bases and base_name(n) != n.upper()]
    return out


def _description(conn, project_id: int, name: str) -> str:
    try:
        row = conn.execute("SELECT description FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    except Exception:  # noqa: BLE001 - old schema without a description column
        return ""
    return str((row["description"] if row is not None else None) or "").strip()


def profiles_block(conn, project_id: int, names: List[str]) -> str:
    """Hồ sơ (mô tả) từng nhân vật của shot; nhân vật nhiều dạng ghi rõ đây là CÙNG một nhân vật ở các dạng khác nhau."""
    if not names:
        return ""
    groups: Dict[str, List[str]] = {}
    for n in names:
        groups.setdefault(base_name(n), []).append(n)
    rows = []
    for n in names:
        desc = _description(conn, project_id, n)
        rows.append(f"- **{n}**" + (f": {desc}" if desc else " (chưa có mô tả hồ sơ — chấm theo Character Lock)"))
    multi = [f"- {b}: " + " → ".join(v) for b, v in groups.items() if len(v) > 1]
    out = ("# Hồ sơ nhân vật trong shot (đúng hồ sơ = KHÔNG phải lỗi; nhân vật chỉ được nhắc ở hành động có thể ở ngoài khung)\n"
           + "\n".join(rows))
    if multi:
        out += ("\n\nCùng một nhân vật ở nhiều dạng (đổi dạng giữa clip là đúng kịch bản; mỗi khung chấm `identity` theo hồ sơ của "
                "DẠNG đang hiện ở khung đó — nét vẽ / màu / hiệu ứng riêng của một dạng không phải \"lệch kiểu vẽ\"):\n" + "\n".join(multi))
    return out


def intent_block(data: Dict, motion_prompt: Optional[str] = None) -> str:
    """Hành động + ý đồ của shot và chỉ dẫn chấm hiệu ứng chủ ý."""
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    intent = {k: v for k, v in {"action": data.get("action") or data.get("text"), "action_en": en.get("action"),
                                "end_state": data.get("end_state") or en.get("end_state"), "action_peak": data.get("action_peak"),
                                "emotional_intent": data.get("emotional_intent"), "why": data.get("why"),
                                "transition_in": data.get("transition_in")}.items() if v}
    if not intent:
        return ""
    fx = intended_effects(data, motion_prompt)
    lines = ["# Hành động & ý đồ của shot (kịch bản / Đạo diễn)", "```json", json.dumps(intent, ensure_ascii=False, indent=1), "```",
             "Hiệu ứng, biến hình, glitch, nhiễu mà kịch bản YÊU CẦU ở trên là ý đồ, KHÔNG phải lỗi: không trừ điểm vì chúng. Chỉ "
             "chấm lỗi khi hiệu ứng làm sai ý đồ (thiếu hẳn, sai chỗ, che mất hành động chính) hoặc có lỗi khác ngoài hiệu ứng."]
    if fx["transform"]:
        lines.append("Shot có BIẾN HÌNH (" + ", ".join(fx["transform"]) + "): nhân vật đổi ngoại hình giữa clip là đúng; so từng khung "
                     "với hồ sơ của dạng trước / dạng sau, không coi khác biệt giữa hai dạng là lỗi `identity`.")
    if fx["noise"]:
        lines.append("Shot có NHIỄU CHỦ Ý (" + ", ".join(fx["noise"]) + "): nhấp nháy, nhòe, méo hình, nhiễu sóng, giật khung do hiệu "
                     "ứng là ý đồ — không trừ `artifacts` / `physics` vì chúng (máy: `artifacts` không chặn cứng ở shot này). Vẫn "
                     "chấm méo tay/mặt, người sai, vật tự sinh ở phần hình không bị nhiễu che.")
    return "\n".join(lines)


def note_case(conn, job, data: Dict, motion_prompt: Optional[str], scores: Dict, threshold: Optional[float],
              issues: Optional[str]) -> bool:
    """Sổ kinh nghiệm (core/experience): shot có hiệu ứng chủ ý (biến hình / nhiễu) mà QC vẫn trừ `identity` / `artifacts` / `physics`
    dưới ngưỡng → ghi một ca `kind=intended_effect` (outcome false_alarm, CHƯA người xác nhận — confirmed_by trống) để các khâu đọc
    lại và người xác nhận dần (#24 job 592/594: biến hình dạng 1→2 bị chấm "style break", nhiễu mất kết nối bị chấm artifacts 0,30).
    True = đã ghi ca mới. Không bao giờ chặn quyết định QC."""
    fx = intended_effects(data, motion_prompt)
    if not (fx["noise"] or fx["transform"]) or threshold is None:
        return False
    watched = ("artifacts", "physics") if fx["noise"] else ()
    watched += ("identity",) if fx["transform"] else ()
    low = {k: v for k, v in (scores or {}).items() if k in watched and isinstance(v, (int, float)) and v < threshold}
    if not low:
        return False
    try:
        from . import experience
        ctx = experience.job_context(conn, job["id"])
        words = ", ".join(fx["transform"] + fx["noise"])
        return experience.record(
            conn, key=f"intended_effect:{job['id']}", stage="video", outcome="false_alarm", kind="intended_effect",
            note=(f"Clip #{job['id']}: kịch bản yêu cầu hiệu ứng ({words}) nhưng QC trừ "
                  + ", ".join(f"{k} {v:.2f}" for k, v in low.items())
                  + " — dễ là báo nhầm (hiệu ứng chủ ý không phải lỗi); chờ người xác nhận. QC ghi: " + (issues or "")[:300]),
            source="qc_video", project_id=job["project_id"], job_id=job["id"], shot=ctx["shot"], subjects=ctx["subjects"],
            view=ctx["view"])
    except Exception:  # noqa: BLE001 - the notebook is evidence, it never stops the decision
        return False
