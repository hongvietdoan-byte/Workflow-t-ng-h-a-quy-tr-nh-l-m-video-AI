"""Sân khấu 3D v2 — V3 / K2: Director (Claude) viết dàn cảnh (`blocking`) + yêu cầu khung (`shot_specs`) cho MỘT cảnh
(docs/PHUONG_PHAP_SAN_KHAU_3D.md mục 3, 10). Code giải máy + đo (core/stage_solver, tools/stage_grid.py v2); không đạt → gửi lại cho
Director đúng lời khuyên của bộ giải / số đo Blender, tối đa 2 lượt Claude (docs/CHUAN_XAY_DUNG: gen lại phải đổi đầu vào, ≤ 2).

Mọi lời gọi qua sổ chi (llm_runner.tagged), có ước tính trước (cost.llm_estimate). Prompt: prompts/29_director_stage_specs.md.
"""
import copy
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
    from . import knowledge
    L = [head] + [x for b in knowledge.p24_blocks() for x in ("", b)]     # 11/10 cờ p24_lessons (TẮT → prompt y cũ)
    L += ["", "---", "", f"## Cảnh: {inputs.get('canh', '')}", ""]
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
        if s.get("nhan_vat") is not None:                 # 16/10 sân khấu tự động: dữ kiện shot của kịch bản — code kiểm theo
            cd = s.get("cho_dung") or {}
            L.append(f"  - **nhân vật PHẢI có trong khung**: {', '.join(f'`{k}`' for k in s['nhan_vat']) or '(không)'}"
                     + (f" · chỗ đứng `{cd.get('ten')}`" + (f" tại ({cd['at'][0]:+.2f}, {cd['at'][1]:+.2f}) so với O" if cd.get("at") else "")
                        if cd.get("ten") else "")
                     + (f" · cỡ kịch bản `{s['co_kich_ban']}`" if s.get("co_kich_ban") else "")
                     + (f" · góc `{s['goc_kich_ban']}`" if s.get("goc_kich_ban") else "")
                     + (f" · máy `{s['may_kich_ban']}`" if s.get("may_kich_ban") else ""))
    if inputs.get("auto"):
        L += ["", AUTO_RULES]
    if inputs.get("user_notes"):
        L += ["", "### Lời người dùng (ưu tiên cao nhất)"] + [f"- {x}" for x in inputs["user_notes"]]
    if inputs.get("refs"):
        L += ["", "### Tham chiếu"] + [f"- {x}" for x in inputs["refs"]]
    if prev is not None:
        L += ["", "---", "", "## Lượt sửa: câu trả lời trước của bạn", "```json", json.dumps(prev, ensure_ascii=False), "```", "",
              "### Code đã giải máy + đo trên sân khấu 3D — các shot CHƯA đạt (sửa dàn cảnh / yêu cầu của đúng các shot này; shot đã "
              "đạt giữ nguyên; không nới yêu cầu mà người dùng đã nói rõ)"] + [f"- {x}" for x in feedback]
        L.append("\nTrả lại TOÀN BỘ JSON (cả shot đã đạt), cùng định dạng.")
    from .director_blockout import append_prompt
    return append_prompt("\n".join(L), inputs)


def validate_answer(obj, inputs: Dict, marks: Optional[Dict] = None) -> Dict:
    """SchemaError (ask_json hỏi lại một lần) khi câu trả lời không dùng được: thiếu shot, khóa sai, vật cố định bị đổi số, nhịp /
    yêu cầu không qua `stage_solver.validate`."""
    if not isinstance(obj, dict) or not isinstance(obj.get("blocking"), dict) or not isinstance(obj.get("shot_specs"), list):
        raise llm_io.SchemaError("cần {blocking: {...}, shot_specs: [...]}")
    bl, specs = obj["blocking"], obj["shot_specs"]
    # 16/10 chạy thật #31 cảnh 4 (lượt 2 hỏng vì "thiếu vật cố định 'moc'"): vật cố định ĐÃ có tọa độ / mốc từ K1 là dữ kiện của code —
    # thiếu thì code tự thêm (không bắt Đạo diễn chép lại, không tốn lượt hỏi lại). Đạo cụ chưa có `at` vẫn phải do Đạo diễn đặt.
    objs_ = bl.setdefault("objects", []) if isinstance(bl.get("objects", []), list) else None
    if objs_ is not None:
        keys_ = {o.get("key") for o in objs_ if isinstance(o, dict)}
        for f in inputs.get("fixed") or []:
            if f.get("key") not in keys_ and (f.get("kind") == "moc" or f.get("at")):
                objs_.append(copy.deepcopy({k: v for k, v in f.items() if k != "source"}) | {"source": f.get("source") or "code: vật cố định"})
    want = sorted(s["shot"] for s in inputs["shots"])
    got = sorted(s.get("shot") for s in specs if isinstance(s, dict))
    if got != want:
        raise llm_io.SchemaError(f"shot_specs phải có đúng các shot {want}, đang có {got}")
    errs: List[str] = []
    have = {o.get("key"): o for o in bl.get("objects", []) if isinstance(o, dict)}
    if inputs.get("auto"):                               # sân khấu tự động: đạo cụ chỉ từ Kho (kích thước có nguồn), không tự thêm
        given = {f["key"] for f in inputs["fixed"]}
        for k, o in have.items():
            if o.get("kind") not in ("nguoi", "moc") and k not in given:
                errs.append(f"vật '{k}' ({o.get('kind')}) không có trong danh sách vật cố định — chỉ dùng đạo cụ được cho, không tự thêm")
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
    if inputs.get("auto"):
        errs += script_rules(bl, specs, inputs)
    if errs:
        raise llm_io.SchemaError("; ".join(dict.fromkeys(errs[:8])))
    from .director_blockout import enabled, issues_for
    if enabled(inputs):
        problems = issues_for(obj, inputs)
        red = [i for i in problems if i['muc']=='do']
        if red:
            raise llm_io.SchemaError('; '.join(f"{i['path']}: {i['loi']}" for i in red))
    return obj


def _sig(spec: Dict):
    main = next((c for c in spec.get("thanh_phan") or [] if c.get("vai") == "chinh"), {}) or {}
    return (spec.get("co"), sg.fold(spec.get("do_cao") or "ngang"), sg.fold(spec.get("goc") or "ngang"), main.get("vat"),
            str(main.get("vung") or ""), str(main.get("thay") or ""), bool(spec.get("may")), spec.get("pov"))


def off_frame(spec: Dict) -> set:
    """Nhân vật Đạo diễn khai NGOÀI khung có lý do (kịch bản: người nói ngoài hình, người nghe ở CU…): `ngoai_khung: [{vat, _ly_do}]`."""
    return {e.get("vat") for e in spec.get("ngoai_khung") or [] if isinstance(e, dict) and str(e.get("_ly_do") or "").strip()}


AUTO_RULES = chr(10).join([
    "### Luật code kiểm (sân khấu tự động — sai thì bị trả lại)",
    "- Mọi nhân vật ở dòng 'nhân vật PHẢI có trong khung' của shot: ghi vào `thanh_phan` (`chinh` hoặc `phu`), có mặt ở nhịp của "
    "shot, và code ĐO thấy ≥ 15 % thân trong khung (đầu hoặc cuối khi máy chạy). Kịch bản cho phép một người ở ngoài khung (người "
    'nói ngoài hình, người nghe ở cận) → khai `"ngoai_khung": [{"vat": "<khóa>", "_ly_do": "…"}]` trong shot đó. '
    'Shot POV: `"pov": "<người cầm máy>"` (được miễn).',
    "- `co` = cỡ kịch bản.",
    "- Hai shot liền nhau cùng chỗ đứng phải là hai máy khác nhau (đổi độ cao / góc / vùng / hướng thấy); cố ý giữ ĐÚNG khung shot "
    'trước (cắt tại chỗ) → ghi `"cung_khung": true` + lý do trong `muc_dich`.',
])


def script_rules(bl: Dict, specs: List[Dict], inputs: Dict) -> List[str]:
    """16/10 (#31 cảnh 4, người dùng 'chưa được'): luật theo KỊCH BẢN của từng shot (sân khấu tự động, inputs.auto):
    (1) mọi nhân vật của shot (`nhan_vat`) có trong `thanh_phan` (chinh / phu) và có mặt ở nhịp của shot — Đạo diễn không được bỏ
        người cho máy dễ đạt (lượt sửa r2 đã bỏ 3 địch ở shot 15);
    (2) `co` = cỡ của kịch bản khi kịch bản ghi cỡ hợp lệ;
    (3) hai shot liền nhau cùng chỗ đứng không được cùng cỡ + độ cao + góc + bố cục thứ chính (shot 17 / 18 ra cùng một máy)."""
    out: List[str] = []
    info = {s["shot"]: s for s in inputs.get("shots") or []}
    ordered = sorted((s for s in specs if isinstance(s, dict) and s.get("shot") in info), key=lambda s: s["shot"])
    prev = None
    for s in ordered:
        sh = info[s["shot"]]
        want = sh.get("nhan_vat") or []
        roles = {c.get("vat"): c.get("vai") for c in s.get("thanh_phan") or [] if isinstance(c, dict)}
        try:
            present = set(ss.beat_raw(bl, s.get("nhip"))) if s.get("nhip") else set(ss.beat_raw(bl))
        except (ValueError, KeyError, TypeError):
            present = set()
        ngoai = off_frame(s)
        for k in want:
            if k == s.get("pov") or k in ngoai:
                continue
            if roles.get(k) not in ("chinh", "phu"):
                out.append(f"shot {s['shot']}: nhân vật `{k}` của kịch bản phải có trong thanh_phan (chinh/phu) — không bỏ người")
            elif k not in present:
                out.append(f"shot {s['shot']}: nhân vật `{k}` bị ẩn / không có ở nhịp `{s.get('nhip')}` mà kịch bản có")
        co = str(sh.get("co_kich_ban") or "").upper().split(" ")[0].split("(")[0].strip()
        if co in sg.FRAMING and s.get("co") != co:
            out.append(f"shot {s['shot']}: cỡ `{s.get('co')}` khác cỡ kịch bản `{co}` — giữ cỡ kịch bản")
        if prev is not None:
            same_spot = (info[prev["shot"]].get("cho_dung") or {}).get("ten") == (sh.get("cho_dung") or {}).get("ten")
            if same_spot and _sig(prev) == _sig(s) and not s.get("cung_khung"):
                out.append(f"shot {s['shot']}: trùng cỡ + độ cao + góc + bố cục với shot {prev['shot']} cùng chỗ đứng — đổi độ cao / "
                           "góc / vùng / hướng thấy để hai shot là hai máy khác nhau")
        prev = s
    return out


def overlap_errors(objs: Dict[str, Dict]) -> List[str]:
    """Người đứng chồng lên đạo cụ trụ (giếng) mà không khai `in` → người nộm cắm vào thành, số đo vô nghĩa (V3 #24 lượt 2: yêu nữ
    'bám mép' đặt ở 0,73 m từ tâm giếng bán kính 0,75 không khai `in`). Người trong giếng thì phải nằm trong lòng giếng."""
    out = []
    for k, o in objs.items():
        if o["kind"] != "nguoi":
            continue
        for w in objs.values():
            if w["kind"] == "dao_cu" and w.get("shape") == "dao_cu" and math.dist(o["xy"], w["xy"]) < w["r"] + 0.15:
                # 15/10 sân khấu tự động: đạo cụ Kho (khối trụ) — người không đứng trong khối
                out.append(f"'{k}' đứng chồng lên đạo cụ '{w['key']}' (cách tâm {math.dist(o['xy'], w['xy']):.2f} m < "
                           f"{w['r'] + 0.15:.2f} m) — đứng ra ngoài khối")
                continue
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
    from . import features
    if features.on("p24_lessons"):               # 11/10: nhịp sau động tác di chuyển (VÀNG của solve_scene) — trong 2 lượt đã ước tính
        out += [f"dàn cảnh: {w['msg']}" for w in (solve or {}).get("continuity") or []
                if w.get("part") == "vi_tri_sau_di_chuyen"]   # lỗi của code (loi_kiem) không gửi Đạo diễn — không tốn thêm lượt
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
