"""Sân khấu 3D v2 — V3 / K2: Director (Claude) viết dàn cảnh (`blocking`) + yêu cầu khung (`shot_specs`) cho MỘT cảnh
(docs/PHUONG_PHAP_SAN_KHAU_3D.md mục 3, 10). Code giải máy + đo (core/stage_solver, tools/stage_grid.py v2); không đạt → gửi lại cho
Director đúng lời khuyên của bộ giải / số đo Blender, tối đa 2 lượt Claude (docs/CHUAN_XAY_DUNG: gen lại phải đổi đầu vào, ≤ 2).

Mọi lời gọi qua sổ chi (llm_runner.tagged), có ước tính trước (cost.llm_estimate). Prompt: prompts/29_director_stage_specs.md.
"""
import json
import math
import os
from typing import Dict, List, Optional, Sequence

from . import llm_io
from . import stage_grid as sg
from . import stage_solver as ss

STAGE = "director_stage_specs"
PROMPT_FILE = "29_director_stage_specs.md"
MAX_ROUNDS = 2
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _r(v, n=2):
    return round(float(v), n)


def build_prompt(inputs: Dict, prev: Optional[Dict] = None, feedback: Sequence[str] = ()) -> str:
    """Đề bài: cách nghĩ (prompt 29) + căn cứ của cảnh. Lượt 2: kèm câu trả lời trước + kết quả kiểm của code (chỉ sửa shot hỏng)."""
    with open(os.path.join(_ROOT, "prompts", PROMPT_FILE), encoding="utf-8") as f:
        head = f.read()
    L = [head, "", "---", "", f"## Cảnh: {inputs.get('canh', '')}", ""]
    L.append(f"Khung hình dự án: {inputs.get('aspect', '9:16')}. Chỗ đứng chính (gốc O): {inputs.get('spot', '')}.")
    L += ["", "### Vật đã cố định (GIỮ NGUYÊN số)"]
    for o in inputs["fixed"]:
        L.append("- " + json.dumps(o, ensure_ascii=False))
    L += ["", "### Nhân vật (chiều cao hồ sơ, đứng)"]
    for p in inputs["people"]:
        L.append(f"- `{p['key']}` {p.get('label', '')}: H = {p['H']} m" + (f" — {p['note']}" if p.get("note") else ""))
    if inputs.get("floor"):
        L += ["", "### Sàn quanh vùng diễn (ô không đứng được / bậc)"] + [f"- {x}" for x in inputs["floor"]]
    L += ["", "### Kịch bản từng shot"]
    for s in inputs["shots"]:
        L.append(f"- **shot {s['shot']}** ({s.get('do_dai', '')}): {s.get('action', '')}")
        if s.get("ghi_chu_khung_cu"):
            L.append(f"  - ghi chú khung cũ (chỉ để hiểu ý, KHÔNG phải luật): {s['ghi_chu_khung_cu']}")
    if inputs.get("user_notes"):
        L += ["", "### Lời người dùng (ưu tiên cao nhất)"] + [f"- {x}" for x in inputs["user_notes"]]
    if inputs.get("refs"):
        L += ["", "### Tham chiếu"] + [f"- {x}" for x in inputs["refs"]]
    if prev is not None:
        L += ["", "---", "", "## Lượt sửa: câu trả lời trước của bạn", "```json", json.dumps(prev, ensure_ascii=False), "```", "",
              "### Code đã giải máy + đo trên sân khấu 3D — các shot CHƯA đạt (sửa dàn cảnh / yêu cầu của đúng các shot này; shot đã "
              "đạt giữ nguyên; không nới yêu cầu mà người dùng đã nói rõ)"] + [f"- {x}" for x in feedback]
        L.append("\nTrả lại TOÀN BỘ JSON (cả shot đã đạt), cùng định dạng.")
    return "\n".join(L)


def validate_answer(obj, inputs: Dict, marks: Optional[Dict] = None) -> Dict:
    """SchemaError (ask_json hỏi lại một lần) khi câu trả lời không dùng được: thiếu shot, khóa sai, vật cố định bị đổi số, nhịp /
    yêu cầu không qua `stage_solver.validate`."""
    if not isinstance(obj, dict) or not isinstance(obj.get("blocking"), dict) or not isinstance(obj.get("shot_specs"), list):
        raise llm_io.SchemaError("cần {blocking: {...}, shot_specs: [...]}")
    bl, specs = obj["blocking"], obj["shot_specs"]
    want = sorted(s["shot"] for s in inputs["shots"])
    got = sorted(s.get("shot") for s in specs if isinstance(s, dict))
    if got != want:
        raise llm_io.SchemaError(f"shot_specs phải có đúng các shot {want}, đang có {got}")
    errs: List[str] = []
    have = {o.get("key"): o for o in bl.get("objects", []) if isinstance(o, dict)}
    for f in inputs["fixed"]:
        o = have.get(f["key"])
        if o is None:
            errs.append(f"thiếu vật cố định '{f['key']}' trong blocking.objects")
            continue
        if f.get("at") and (not o.get("at") or math.dist(o["at"][:2], f["at"][:2]) > 0.01):
            errs.append(f"vật cố định '{f['key']}' bị đổi vị trí {o.get('at')} ≠ {f['at']}")
        for k in ("h", "d", "kind"):
            if k in f and o.get(k) != f[k]:
                errs.append(f"vật cố định '{f['key']}' bị đổi {k}: {o.get(k)} ≠ {f[k]}")
    # tư thế ngoài enum (vd 'nga', 'lying') trước đây bị giải im lặng như người đứng — rà Đợt 2 khi prompt 29 mở nga_ngua/nam.
    # Chỉ kiểm câu trả lời mới của Đạo diễn (blocking cũ đã lưu không bị chặn ở đây).
    from .shot_intent import TU_THE
    rows = [("objects", o) for o in bl.get("objects", []) if isinstance(o, dict)]
    rows += [(f"beats.{n}", ov) for n, b in (bl.get("beats") or {}).items() if isinstance(b, dict)
             for ov in b.values() if isinstance(ov, dict)]
    for where, o in rows:
        if o.get("tu_the") is not None and o["tu_the"] not in TU_THE:
            errs.append(f"{where}: tu_the '{o['tu_the']}' không thuộc {', '.join(TU_THE)}")
    if errs:
        raise llm_io.SchemaError("; ".join(errs[:6]))
    try:
        base = ss.objects_from_blocking(bl, marks)
    except (ValueError, KeyError, TypeError) as e:
        raise llm_io.SchemaError(f"blocking không dựng được: {e}") from e
    for s in specs:
        try:
            o = ss.objects_from_blocking(bl, marks, s["nhip"]) if s.get("nhip") else base
        except (ValueError, KeyError, TypeError) as e:
            errs.append(f"shot {s.get('shot')}: nhịp '{s.get('nhip')}' lỗi: {e}")
            continue
        if s.get("pov") and s["pov"] in o:
            o = {k: v for k, v in o.items() if k != s["pov"]}
        try:
            errs += [f"shot {s.get('shot')}: {e}" for e in ss.validate(s, o)]
        except (ValueError, KeyError, TypeError) as e:
            errs.append(f"shot {s.get('shot')}: {e}")
        if s.get("may"):
            errs += [f"shot {s.get('shot')}: {e}" for e in ss.move_errors(s["may"])]
        errs += [f"shot {s.get('shot')}: {e}" for e in overlap_errors(o)]
    if errs:
        raise llm_io.SchemaError("; ".join(dict.fromkeys(errs[:8])))
    return obj


def overlap_errors(objs: Dict[str, Dict]) -> List[str]:
    """Người đứng chồng lên đạo cụ trụ (giếng) mà không khai `in` → người nộm cắm vào thành, số đo vô nghĩa (V3 #24 lượt 2: yêu nữ
    'bám mép' đặt ở 0,73 m từ tâm giếng bán kính 0,75 không khai `in`). Người trong giếng thì phải nằm trong lòng giếng."""
    out = []
    for k, o in objs.items():
        if o["kind"] != "nguoi":
            continue
        for w in objs.values():
            if w["kind"] != "dao_cu" or w.get("shape") != "gieng":
                continue
            d = math.dist(o["xy"], w["xy"])
            if o.get("in") == w["key"]:
                if d > w["r"] - 0.15:
                    out.append(f"'{k}' khai trong '{w['key']}' nhưng cách tâm {d:.2f} m ≥ lòng giếng ({w['r'] - 0.15:.2f} m)")
            elif d < w["r"] + 0.2:
                out.append(f"'{k}' đứng chồng lên '{w['key']}' (cách tâm {d:.2f} m < {w['r'] + 0.2:.2f} m) — ở trong lòng thì khai "
                           f"\"in\": \"{w['key']}\", không thì đứng ra ngoài")
    return out


def feedback_from(solve: Optional[Dict], v2: Optional[Dict]) -> List[str]:
    """Câu gửi lại Director cho shot chưa đạt: ưu tiên số đo Blender (che khuất thật), không có thì lời khuyên của bộ giải."""
    out: List[str] = []
    done = set()
    for s in (v2 or {}).get("shots", []):
        b = s.get("best")
        if b and not b["ok"]:
            why = "; ".join(f"{k}: {v}" for k, v in b["check"]["why"].items())
            if b.get("end") and not b["end"]["check"]["ok"]:
                why += " | khung cuối: " + "; ".join(f"{k}: {v}" for k, v in b["end"]["check"]["why"].items())
            out.append(f"shot {s['shot']}: phương án tốt nhất ({b['tag']}) vẫn hỏng — {why}")
            done.add(s["shot"])
        elif not b:
            out.append(f"shot {s['shot']}: không có phương án máy nào")
            done.add(s["shot"])
    for s in (solve or {}).get("shots", []):
        if s["shot"] in done:
            continue
        if s.get("errors"):
            out.append(f"shot {s['shot']}: " + "; ".join(s["errors"]))
        elif s.get("advice"):
            out.append(f"shot {s['shot']}: " + "; ".join(s["advice"]))
    return out


def compare(hand: Dict, ai: Dict) -> List[Dict]:
    """So từng shot: đạt luật? máy (ô, cao, pitch) lệch bao nhiêu so với bản viết tay; thành phần chính giống / khác."""
    hs = {s["shot"]: s for s in hand.get("shots", [])}
    rows = []
    for s in ai.get("shots", []):
        h = hs.get(s["shot"])
        a_b, h_b = s.get("best"), (h or {}).get("best")
        row = {"shot": s["shot"], "ai_ok": bool(a_b and a_b["ok"]), "hand_ok": bool(h_b and h_b["ok"]),
               "ai_main": [c["vat"] for c in s["spec"]["thanh_phan"] if c.get("vai") == "chinh"],
               "hand_main": [] if not h else [c["vat"] for c in h["spec"]["thanh_phan"] if c.get("vai") == "chinh"],
               "ai_extra": {k: s["spec"].get(k) for k in ("pov", "may", "cao_m") if s["spec"].get(k)},
               "hand_extra": {} if not h else {k: h["spec"].get(k) for k in ("pov", "may", "cao_m") if h["spec"].get(k)}}
        if a_b and h_b:
            am, hm = a_b["m"], h_b["m"]
            row.update(cam_dist_m=_r(math.dist(am["at"], hm["at"])), yaw_diff=_r(abs((am["yaw"] - hm["yaw"] + 180) % 360 - 180), 1),
                       pitch_ai=_r(am["pitch"], 1), pitch_hand=_r(hm["pitch"], 1), cell_ai=am["cell"], cell_hand=hm["cell"])
        if a_b and not a_b["ok"]:
            row["ai_why"] = a_b["check"]["why"]
        rows.append(row)
    return rows
