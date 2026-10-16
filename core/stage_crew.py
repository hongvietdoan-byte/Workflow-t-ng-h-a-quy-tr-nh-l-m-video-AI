"""Sân khấu 3D CHIA VAI (cờ `stage_crew`, kế hoạch docs/KE_HOACH_CHIA_VAI_SAN_KHAU_2026-10-16.md — người dùng duyệt 16/10).

Gốc: #31 shot 10 — một vai "Đạo diễn kiêm Quay phim" viết cả dàn cảnh lẫn khung; Kelly đứng giữa máy và xe nôi (237 % khung), máy chúc
−6,5° trái ý "nhìn lên, chỉ thấy tay" của ghi chú khung Quay phim — bộ kiểm vẫn ĐẠT vì không ai so khung đo được với ý đồ. Không đặt luật
cấm cứng (che để chuyển cảnh là ý đồ hợp lệ): mỗi vai KHAI ý đồ, code lập BẢNG ĐỐI CHIẾU "đã khai ↔ đo được" (chỉ sự thật số), vai tự
kết luận.

Luồng (máy trạng thái `state`, dùng chung cho API và ngoại tuyến):
  dao_dien (dàn cảnh + ý đồ nhịp + shot_nhip) → quay_phim (đặt máy) → [đo K3 + K4] → quay_phim_duyet (khop / sua_may /
  de_nghi_doi_cho / giu_lech, ≤ MAX_REVIEWS lượt) → (có đề nghị, một lần) dao_dien_tra_loi (Đạo diễn thắng) → duyet (Đạo diễn, hoặc
  NGƯỜI DÙNG khi cờ stage_crew_user_approve — #31) → xong.
Module này không gọi Blender / API: `measure(bl, specs)` do core/stage_auto đưa vào.
"""
import copy
import json
import math
import os
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import llm_io
from . import stage_director as sd
from . import stage_solver as ss

FLAG = "stage_crew"
USER_APPROVE = "stage_crew_user_approve"
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = {                       # vai → (khâu sổ chi, đề bài)
    "dao_dien": ("director_stage_blocking", "29a_director_blocking.md"),
    "quay_phim": ("dp_stage_specs", "29b_dp_stage_specs.md"),
    "quay_phim_duyet": ("dp_stage_review", "29c_dp_stage_review.md"),
    "dao_dien_tra_loi": ("director_stage_blocking", "29a_director_blocking.md"),
    "duyet": ("director_stage_approve", "29d_director_stage_approve.md"),
}
MAX_REVIEWS = 2
KET_LUAN = ("khop", "sua_may", "de_nghi_doi_cho", "giu_lech")
CHE = ("chuyen_canh", "tien_canh", "qua_vai", "khac")
DP_NOTE = "ghi chú khung của Quay phim (ý đồ của BẠN lúc chia shot — làm theo; đổi thì ghi lý do vào y_do_khung)"
DIRECTOR_NOTE = "ghi chú khung của Quay phim (đọc để chừa chỗ cho máy — không phải luật dàn cảnh)"
DIRECTOR_RULES = "\n".join([
    "### Luật code kiểm dàn cảnh (sai thì bị trả lại)",
    "- `shot_nhip` có MỌI shot của kịch bản, nhịp phải có trong `beats` (hoặc \"\" = vị trí gốc `objects`).",
    "- Mọi nhân vật ở dòng 'nhân vật' của shot có mặt (không `hidden`) ở nhịp của shot.",
    "- Nhịp của shot = trạng thái ĐẦU shot: người bị hạ TRONG shot còn ĐỨNG ở nhịp của shot đó; ngã / nằm ở nhịp của shot sau.",
    "- Người không đứng chồng lên đạo cụ / trong giếng mà không khai `in`.",
])
UP_WORDS = re.compile(r"nhìn lên|ngước|từ dưới lên|looking up|low[- ]angle", re.I)
DOWN_WORDS = re.compile(r"nhìn xuống|từ trên xuống|looking down|high[- ]angle|top[- ]down|bird", re.I)
PERSON_R = 0.25


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def user_approves() -> bool:
    from . import features
    try:
        return features.on(USER_APPROVE)
    except KeyError:
        return False


def new_state(fp: str) -> Dict:
    return {"fp": fp, "phase": "dao_dien", "reviews": 0, "asked": False, "returned": False, "blocking": None, "specs": None,
            "measure": None, "n_measure": 0, "verdicts": {}, "keep": {}, "requests": [], "replies": [], "notes": [], "unresolved": {},
            "history": []}


# ---- đề bài ------------------------------------------------------------------------------------------------------------------
def _head(name: str) -> str:
    with open(os.path.join(_ROOT, "prompts", name), encoding="utf-8") as f:
        return f.read()


def dp_book() -> List[str]:
    """Bộ nguyên tắc Quay phim (knowledge/roles/dp.md + bổ sung Kelly / KLD theo cờ) — cùng sách vai Quay phim ở Tầng B."""
    from . import knowledge, prompts
    return [prompts.role_text("dp.md"), *knowledge.kelly_blocks("dp"), *knowledge.kld_blocks("dp")]


def _js(v) -> str:
    return "```json\n" + json.dumps(v, ensure_ascii=False) + "\n```"


def prompt_for(state: Dict, inputs: Dict, table: Optional[Dict[int, List[str]]] = None, extra: Sequence = (),
               cache_break: str = "") -> str:
    """Đề bài của vai đang tới lượt (`state.phase`). `table` = bảng đối chiếu của lần đo cuối; `extra` = dòng thêm (ảnh clay, chú thích
    màu…) cho lượt duyệt. `cache_break` (API: llm_runner.CACHE_BREAK) tách phần cố định (cách nghĩ + sách vai) để cache."""
    from . import knowledge
    phase = state["phase"]
    if phase not in ROLES:
        raise ValueError(f"không có đề bài cho bước '{phase}'")
    L = [_head(ROLES[phase][1])]
    if phase in ("quay_phim", "quay_phim_duyet"):
        L += ["", "## Bộ nguyên tắc Quay phim", *dp_book()]
    L += [x for b in knowledge.p24_blocks() for x in ("", b)]
    if cache_break:
        L.append(cache_break)
    if phase in ("dao_dien", "dao_dien_tra_loi"):
        L += sd.scene_facts(inputs, auto_rules=DIRECTOR_RULES, note_label=DIRECTOR_NOTE)
    else:
        L += sd.scene_facts(inputs, note_label=DP_NOTE)
    if phase != "dao_dien":
        L += ["", "## Dàn cảnh của Đạo diễn", _js(state["blocking"])]
    if phase in ("quay_phim_duyet", "duyet"):
        L += ["", "## Yêu cầu khung của Quay phim (hiện tại)", _js(state["specs"])]
    if phase in ("quay_phim_duyet", "duyet") and table:
        L += ["", "## Bảng đối chiếu \"đã khai ↔ đo được\" (số đo Blender lần cuối — chỉ sự thật, không phán)"]
        for shot in sorted(table):
            L.append(f"- **shot {shot}**")
            L += [f"  - {x}" for x in table[shot]]
    if extra:
        L += [""] + list(extra)
    if state.get("replies"):
        L += ["", "## Đạo diễn đã trả lời đề nghị dời người (Đạo diễn thắng khi từ chối)", _js(state["replies"])]
    if state.get("notes"):
        L += ["", "## Trả lại từ lượt duyệt chốt (ý đồ cần đạt)", _js(state["notes"])]
    if phase == "quay_phim_duyet" and state.get("verdicts"):
        L += ["", "## Kết luận lượt duyệt trước của bạn", _js(state["verdicts"])]
    if phase == "dao_dien_tra_loi":
        L += ["", "## Đề nghị dời người của Quay phim", _js(state["requests"]), "",
              "**Lượt này trả JSON theo khuôn dưới (THAY khuôn trả lời ở đầu đề bài)**: trả lời MỖI đề nghị (đồng ý → sửa `beats` "
              "theo; từ chối → lý do) và trả lại TOÀN BỘ dàn cảnh (kể cả phần không đổi):",
              _js({"tra_loi": [{"shot": 10, "dong_y": True, "ly_do": "…"}], "blocking": {"objects": "…", "beats": "…",
                                                                                 "shot_nhip": "…"}})]
    if phase == "duyet":
        L += ["", "## Kết luận tự duyệt của Quay phim", _js(state.get("verdicts") or {})]
    return "\n".join(L)


# ---- bộ kiểm từng vai ------------------------------------------------------------------------------------------------------
def _schema(errs: List[str]) -> None:
    if errs:
        raise llm_io.SchemaError("; ".join(dict.fromkeys(errs[:8])))


def shot_nhip_of(bl: Dict) -> Dict[int, str]:
    return {int(k): (v or "") for k, v in (bl.get("shot_nhip") or {}).items()}


def validate_blocking(obj, inputs: Dict, marks: Optional[Dict] = None) -> Dict:
    """Vai Đạo diễn: {blocking: {objects, beats, beat_intent, shot_nhip, axis, s0}, can_hoi}. Kiểm phần dàn cảnh dùng chung
    (sd.blocking_errors) + mọi shot có nhịp + người kịch bản có mặt ở nhịp + hạ trong shot còn đứng + không chồng đạo cụ."""
    if not isinstance(obj, dict) or not isinstance(obj.get("blocking"), dict):
        raise llm_io.SchemaError("cần {blocking: {...}}")
    bl = obj["blocking"]
    try:
        sn = shot_nhip_of(bl)
    except (ValueError, TypeError, AttributeError):
        raise llm_io.SchemaError("shot_nhip phải là {\"<số shot>\": \"<nhịp>\"}")
    errs = sd.blocking_errors(bl, inputs)
    _schema(errs)
    want = sorted(s["shot"] for s in inputs["shots"])
    if sorted(sn) != want:
        raise llm_io.SchemaError(f"shot_nhip phải có đúng các shot {want}, đang có {sorted(sn)}")
    beats = bl.get("beats") or {}
    info = {s["shot"]: s for s in inputs["shots"]}
    prev = None
    for shot in want:
        nhip = sn[shot]
        if nhip and nhip not in beats:
            errs.append(f"shot {shot}: nhịp '{nhip}' không có trong beats")
            continue
        try:
            objs = ss.objects_from_blocking(bl, marks, nhip or None)
        except (ValueError, KeyError, TypeError) as e:
            errs.append(f"shot {shot}: nhịp '{nhip}' lỗi: {e}")
            continue
        errs += [f"shot {shot}: {e}" for e in sd.overlap_errors(objs)]
        sh = info[shot]
        now = sd._state(bl, nhip or None)
        for k in sh.get("nhan_vat") or []:
            if k not in now:
                errs.append(f"shot {shot}: nhân vật `{k}` bị ẩn / không có ở nhịp `{nhip}` mà kịch bản có")
        if sd.kill_in_shot(str(sh.get("action") or "")):
            before = sd._state(bl, prev) if prev is not None else sd._state(bl, None)
            for k in sh.get("nhan_vat") or []:
                if k in before and (now.get(k) or {}).get("tu_the") in sd.LYING and (before.get(k) or {}).get("tu_the") not in sd.LYING:
                    errs.append(f"shot {shot}: `{k}` bị hạ TRONG shot này nên ở nhịp `{nhip}` (khung ĐẦU) phải còn đứng")
        prev = nhip or None
    _schema(errs)
    return obj


def _with_nhip(specs: List[Dict], bl: Dict) -> List[Dict]:
    sn = shot_nhip_of(bl)
    out = []
    for s in specs:
        s = dict(s)
        if isinstance(s.get("shot"), int) and s["shot"] in sn:
            if sn[s["shot"]]:
                s["nhip"] = sn[s["shot"]]
            else:
                s.pop("nhip", None)
        out.append(s)
    return out


def validate_specs(obj, inputs: Dict, bl: Dict, marks: Optional[Dict] = None) -> Dict:
    """Vai Quay phim: {shot_specs: [...]}. Nhịp do Đạo diễn chọn (code gắn theo shot_nhip — Quay phim không đổi được); `che` trong enum
    và có lý do; rồi bộ kiểm đầy đủ của câu trả lời ghép (sd.validate_answer: khung, luật kịch bản, K3)."""
    if not isinstance(obj, dict) or not isinstance(obj.get("shot_specs"), list):
        raise llm_io.SchemaError("cần {shot_specs: [...]}")
    errs = [] if obj.get("s0") in (None, "left", "right") else [f"s0 '{obj.get('s0')}' phải là left / right"]
    for s in obj["shot_specs"]:
        for c in (s.get("thanh_phan") or []) if isinstance(s, dict) else []:
            if isinstance(c, dict) and c.get("che") is not None:
                if c["che"] not in CHE:
                    errs.append(f"shot {s.get('shot')}: `{c.get('vat')}` che '{c['che']}' không thuộc {', '.join(CHE)}")
                elif not str(c.get("ly_do") or "").strip():
                    errs.append(f"shot {s.get('shot')}: `{c.get('vat')}` khai che mà không có ly_do")
    _schema(errs)
    specs = _with_nhip(obj["shot_specs"], bl)
    blv = {k: v for k, v in bl.items() if k != "s0"}
    if obj.get("s0"):
        blv["s0"] = obj["s0"]
    sd.validate_answer({"blocking": copy.deepcopy(blv), "shot_specs": specs}, inputs, marks)
    obj["shot_specs"] = specs
    return obj


def validate_review(obj, state: Dict, inputs: Dict, marks: Optional[Dict] = None) -> Dict:
    """Vai Quay phim tự duyệt: MỌI shot một kết luận; sửa máy → đặc tả mới qua bộ kiểm đầy đủ; đề nghị dời người cần vật + lý do."""
    if not isinstance(obj, dict) or not isinstance(obj.get("shots"), list):
        raise llm_io.SchemaError("cần {shots: [{shot, ket_luan, ...}]}")
    if not all(isinstance(r, dict) for r in obj["shots"]):
        raise llm_io.SchemaError("mỗi phần tử của shots phải là object {shot, ket_luan, ...}")
    want = sorted(s["shot"] for s in inputs["shots"])
    got = sorted(r.get("shot") for r in obj["shots"])
    if got != want:
        raise llm_io.SchemaError(f"shots phải có đúng các shot {want}, đang có {got}")
    errs = []
    keys = {o.get("key") for o in state["blocking"].get("objects") or [] if o.get("kind") == "nguoi"}   # rà 16/10: chỉ dời NGƯỜI
    new_specs = {s["shot"]: s for s in state["specs"]}
    for r in obj["shots"]:
        k = r.get("ket_luan")
        if k not in KET_LUAN:
            errs.append(f"shot {r['shot']}: ket_luan '{k}' không thuộc {', '.join(KET_LUAN)}")
            continue
        if k != "khop" and not str(r.get("ly_do") or "").strip():
            errs.append(f"shot {r['shot']}: {k} cần ly_do")
        if k == "sua_may":
            sp = r.get("shot_spec")
            if not isinstance(sp, dict) or sp.get("shot") != r["shot"]:
                errs.append(f"shot {r['shot']}: sua_may cần shot_spec đầy đủ cùng số shot")
            else:
                new_specs[r["shot"]] = sp
        if r.get("lan_do") is not None and r.get("lan_do") not in ((state.get("shot_hist") or {}).get(str(r["shot"])) or []):
            errs.append(f"shot {r['shot']}: lan_do '{r.get('lan_do')}' không phải một lần đo của shot này "
                        f"({', '.join((state.get('shot_hist') or {}).get(str(r['shot'])) or [])})")
        if r.get("lan_do") is not None and k not in ("khop", "giu_lech"):
            errs.append(f"shot {r['shot']}: lan_do chỉ dùng với khop / giu_lech")
        if r.get("bo_luat"):
            if k != "giu_lech" or not isinstance(r["bo_luat"], list):
                errs.append(f"shot {r['shot']}: bo_luat là danh sách mã luật, chỉ dùng với giu_lech (kèm ly_do)")
            elif any(str(c).split(":")[-1].startswith("P1") for c in r["bo_luat"]):
                errs.append(f"shot {r['shot']}: không miễn được P1 (máy trong tường / ngoài vùng đi tới được)")
        if k == "de_nghi_doi_cho":
            if r.get("vat") not in keys:
                errs.append(f"shot {r['shot']}: chỉ đề nghị dời NGƯỜI có trong dàn cảnh ('{r.get('vat')}' không phải — vật cố định Đạo "
                            "diễn không dời được; đổi máy hoặc giu_lech)")
            if r.get("goi_y_at") is not None and not (isinstance(r["goi_y_at"], list) and len(r["goi_y_at"]) == 2):
                errs.append(f"shot {r['shot']}: goi_y_at phải là [x, y]")
    _schema(errs)
    if obj.get("s0") not in (None, "left", "right"):
        raise llm_io.SchemaError(f"s0 '{obj.get('s0')}' phải là left / right")
    if any(r["ket_luan"] == "sua_may" for r in obj["shots"]) or obj.get("s0"):
        validate_specs({"shot_specs": [new_specs[s] for s in want], "s0": obj.get("s0") or state.get("s0")}, inputs, state["blocking"],
                       marks)
    return obj


def validate_reply(obj, state: Dict, inputs: Dict, marks: Optional[Dict] = None) -> Dict:
    """Đạo diễn trả lời đề nghị: mỗi đề nghị một câu (đồng ý / từ chối + lý do) + toàn bộ dàn cảnh (qua validate_blocking)."""
    if not isinstance(obj, dict) or not isinstance(obj.get("tra_loi"), list):
        raise llm_io.SchemaError("cần {tra_loi: [...], blocking: {...}}")
    asked = sorted(r["shot"] for r in state["requests"])
    got = sorted(r.get("shot") for r in obj["tra_loi"] if isinstance(r, dict))
    errs = [] if got == asked else [f"tra_loi phải trả lời đúng các shot {asked}, đang có {got}"]
    errs += [f"shot {r.get('shot')}: cần dong_y (true/false) + ly_do" for r in obj["tra_loi"]
             if not isinstance(r.get("dong_y"), bool) or not str(r.get("ly_do") or "").strip()]
    _schema(errs)
    validate_blocking(obj, inputs, marks)
    try:                                                  # rà 16/10: dàn cảnh mới phải còn hợp với đặc tả máy hiện có (Quay phim sửa sau)
        validate_specs({"shot_specs": copy.deepcopy(state["specs"]), "s0": state.get("s0")}, inputs, obj["blocking"], marks)
    except llm_io.SchemaError as e:
        raise llm_io.SchemaError(f"dàn cảnh mới làm đặc tả máy hiện có không còn hợp lệ — {e}") from e
    return obj


def validate_approve(obj, inputs: Dict) -> Dict:
    if not isinstance(obj, dict) or not isinstance(obj.get("duyet"), bool):
        raise llm_io.SchemaError("cần {duyet: true|false, tra_lai: [...]}")
    if not obj["duyet"]:
        want = {s["shot"] for s in inputs["shots"]}
        bad = [r for r in obj.get("tra_lai") or [] if not isinstance(r, dict) or r.get("shot") not in want
               or not str(r.get("y_do") or "").strip()]
        if bad or not obj.get("tra_lai"):
            raise llm_io.SchemaError("duyet=false cần tra_lai: [{shot (của cảnh), y_do}]")
    return obj


def validator(state: Dict, inputs: Dict, marks: Optional[Dict] = None) -> Callable[[Dict], Dict]:
    p = state["phase"]
    if p == "dao_dien":
        return lambda o: validate_blocking(o, inputs, marks)
    if p == "quay_phim":
        return lambda o: validate_specs(o, inputs, state["blocking"], marks)
    if p == "quay_phim_duyet":
        return lambda o: validate_review(o, state, inputs, marks)
    if p == "dao_dien_tra_loi":
        return lambda o: validate_reply(o, state, inputs, marks)
    if p == "duyet":
        return lambda o: validate_approve(o, inputs)
    raise ValueError(f"bước '{p}' không nhận câu trả lời")


# ---- bảng đối chiếu (0 USD, chỉ sự thật) ---------------------------------------------------------------------------------
def _bearing(a, b) -> float:
    return math.atan2(b[0] - a[0], b[1] - a[1])


def _pitch_word(p: float) -> str:
    return "ngửa" if p > 2 else ("chúc" if p < -2 else "ngang")


def compare_table(inputs: Dict, specs: List[Dict], v2: Dict, keep: Optional[Dict] = None,
                  post: Optional[Dict[int, str]] = None) -> Dict[int, List[str]]:
    """{shot: [dòng sự thật]}: cỡ khai ↔ cỡ đo của MỌI thành phần (cả vai phụ), % thấy, góc khai / chữ trong ý đồ ↔ pitch đo, độ cao,
    ống + khoảng cách, vật đứng GIỮA máy và thứ chính, kết quả Blender, luật kịch bản (post_checks), ý đồ che đã khai, ảnh clay."""
    info = {s["shot"]: s for s in inputs.get("shots") or []}
    spec_of = {s["shot"]: s for s in specs}
    out: Dict[int, List[str]] = {}
    for sh in sorted(v2.get("shots") or [], key=lambda x: x["shot"]):
        n = sh["shot"]
        sp = spec_of.get(n) or sh.get("spec") or {}
        b = sh.get("best") or {}
        m = b.get("m") or {}
        rows: List[str] = []
        if not m:
            out[n] = ["không có phương án máy nào đo được"]
            continue
        objs = sh.get("objs") or {}
        at = m.get("at") or [0, 0, 0]
        mains = [c["vat"] for c in sp.get("thanh_phan") or [] if c.get("vai") == "chinh"]
        rows.append(f"máy: cỡ khai `{sp.get('co')}` · ống {m.get('lens') or '?'} mm · cao {m.get('cam_above_floor_m')} m trên sàn "
                    f"(khai `{sp.get('do_cao')}`" + (f", cao_m {sp['cao_m']}" if sp.get("cao_m") is not None else "") + ")"
                    + (f" · máy chạy {sp['may'].get('kieu')} {sp['may'].get('m')} m" if sp.get("may") else ""))
        text = " ".join(str(x or "") for x in (sp.get("muc_dich"), sp.get("y_do_khung"), (info.get(n) or {}).get("ghi_chu_khung_cu")))
        hint = "nhìn lên" if UP_WORDS.search(text) else ("nhìn xuống" if DOWN_WORDS.search(text) else "")
        p = float(m.get("pitch") or 0.0)
        rows.append(f"góc: khai `{sp.get('goc') or '(trống)'}`" + (f" · chữ trong ý đồ / ghi chú: '{hint}'" if hint else "")
                    + f" · pitch đo {p:+.1f}° ({_pitch_word(p)})")
        for c in sp.get("thanh_phan") or []:
            k = c.get("vat")
            o = (m.get("obj") or {}).get(k) or {}
            ob = objs.get(k) or {}
            d = math.dist(at[:2], ob["xy"]) if ob.get("xy") else None
            want = f", khai co_pct {c['co_pct'][0]}–{c['co_pct'][1]} %" if isinstance(c.get("co_pct"), list) and len(c["co_pct"]) == 2 else ""
            row = (f"`{k}` ({c.get('vai')}{want}{', vùng ' + str(c['vung']) if c.get('vung') else ''}): đo cỡ {o.get('size_pct', 0):g} % "
                   f"khung, thấy {o.get('seen_pct', 0):g} %" + (f", cách máy {d:.2f} m" if d is not None else ""))
            if c.get("che"):
                row += f" · ĐÃ KHAI che `{c['che']}`: {c.get('ly_do')}"
            elif c.get("ly_do"):
                row += f" · ý đồ: {c['ly_do']}"
            rows.append(row)
        for k in mains:
            ok_ = objs.get(k) or {}
            if not ok_.get("xy"):
                continue
            dk = math.dist(at[:2], ok_["xy"])
            bk = _bearing(at, ok_["xy"])
            for j, oj in objs.items():
                if j == k or oj.get("kind") == "moc" or not oj.get("xy"):
                    continue
                dj = math.dist(at[:2], oj["xy"])
                if dj >= dk or dj < 0.05:
                    continue
                r = PERSON_R if oj.get("kind") == "nguoi" else float(oj.get("r") or 0.3)
                diff = abs((_bearing(at, oj["xy"]) - bk + math.pi) % (2 * math.pi) - math.pi)
                # rà 16/10: xét cả chiều cao — vật thấp dưới đường nhìn từ máy tới tâm thứ chính thì không chắn
                tz = float(ok_.get("z") or 0.0) + float(ok_.get("H") or ok_.get("h") or 1.0) / 2
                sight = float(at[2] if len(at) > 2 else 1.5) + (tz - float(at[2] if len(at) > 2 else 1.5)) * dj / dk
                top = float(oj.get("z") or 0.0) + float(oj.get("H") or oj.get("h") or 1.7)
                if diff < math.atan2(r, dj) + 0.05 and top > sight - 0.05:
                    rows.append(f"`{j}` đứng GIỮA máy và `{k}` trên mặt sàn (cách máy {dj:.2f} m, `{k}` cách {dk:.2f} m)")
        why = [f"{a}: {w}" for a, w in ((b.get("check") or {}).get("why") or {}).items()]
        if not b.get("c1_ok", True):                      # như feedback_from: hỏng chỉ vì vượt trục thì 'why' trống
            why.append(f"C1: máy ở phía khác trục 180° so với s0 `{(sp or {}).get('s0') or 'của cảnh'}` — đổi phía máy / vùng, hoặc "
                       "`cross_ok: true` + lý do nếu cố ý")
        e = b.get("end") or {}
        if e and not (e.get("check") or {}).get("ok", True):   # máy chạy: khung CUỐI hỏng (ca thử #31 shot 11: 'HỎNG —' trống)
            why.append("khung cuối: " + "; ".join(f"{a}: {w}" for a, w in ((e.get("check") or {}).get("why") or {}).items()))
        rows.append("Blender: " + ("ĐẠT luật khung" if b.get("ok") else "HỎNG — " + "; ".join(why)))
        if post and n in post:
            rows.append(f"luật kịch bản: {post[n]}")
        if (keep or {}).get(str(n)) or (keep or {}).get(n):
            rows.append(f"Quay phim đã giữ lệch có chủ ý: {(keep or {}).get(str(n)) or (keep or {}).get(n)}")
        if b.get("clay"):
            rows.append(f"ảnh clay: {b['clay']}")
        out[n] = rows
    for n in spec_of:                                     # rà 16/10: shot không có trong số đo — nói rõ, không bỏ im lặng
        out.setdefault(n, ["không có số đo Blender cho shot này"])
    return out


# ---- máy trạng thái ----------------------------------------------------------------------------------------------------------
MeasureFn = Callable[[Dict, List[Dict]], Tuple[str, Dict]]


def measure_blocking(state: Dict) -> Dict:
    """Dàn cảnh gửi đo: của Đạo diễn + phía máy s0 của QUAY PHIM (tối ưu 16/10: s0 thuộc Quay phim — ca thử shot 10–11 Đạo diễn chọn s0
    ngược ghi chú khung → C1 hỏng cả hai shot)."""
    bl = {k: v for k, v in state["blocking"].items() if k != "s0"}
    if state.get("s0"):
        bl["s0"] = state["s0"]
    return bl


def reset_measures(state: Dict) -> None:
    """Dàn cảnh hoặc phía máy s0 đổi → mọi số đo cũ (lịch sử, máy lần trước, khóa, lần bị bác) không còn đúng (rà 16/10)."""
    for k in ("accepted", "shot_hist", "cam_xy", "rejected", "measure_errors", "waive"):
        state[k] = {}


def _measure(state: Dict, measure: MeasureFn, only=None) -> None:
    """K3 + K4 cho các shot `only` (None = mọi shot). Tối ưu 16/10: (1) chỉ đo lại shot đổi — số đo ghép THEO SHOT (`shot_measure`), mỗi
    shot nhớ mọi lần đo (`shot_hist`) để chốt lần tốt nhất; (2) shot đo lại được gắn `_near` = máy lần đo trước → bộ giải ưu tiên cùng
    phía (ca thử m4: khai cross_ok làm máy nhảy ra sau lưng Kelly), trừ khi Quay phim ghi `doi_phia: true`."""
    specs = []
    for sp in state["specs"]:
        if only is not None and sp["shot"] not in only:
            continue
        sp = dict(sp)
        near = (state.get("cam_xy") or {}).get(str(sp["shot"]))
        if near and not sp.get("doi_phia"):
            sp["_near"] = near
        specs.append(sp)
    rel, v2 = measure(measure_blocking(state), specs)
    got = set()
    for sh in (v2 or {}).get("shots") or []:
        k = str(sh["shot"])
        got.add(k)
        state.setdefault("shot_measure", {})[k] = rel
        state.setdefault("shot_hist", {}).setdefault(k, []).append(rel)
        at = (((sh.get("best") or {}).get("m") or {}).get("at"))
        if at:
            state.setdefault("cam_xy", {})[k] = list(at[:2])
    for sp in specs:                                     # rà 16/10: shot được đo mà bộ giải không ra phương án → KHÔNG dùng lặng số đo cũ
        k = str(sp["shot"])
        if k not in got:
            (state.get("shot_measure") or {}).pop(k, None)
            state.setdefault("measure_errors", {})[k] = f"lần đo {rel}: bộ giải không đặt được máy cho đặc tả này"
        else:
            (state.get("measure_errors") or {}).pop(k, None)
    if not state.get("s0") and (v2 or {}).get("s0"):     # rà 16/10: s0 trống → lấy phía bộ giải chọn ở lần đo đầy đủ, đo một phần chấm C1
        state["s0"] = v2["s0"]                           # cùng phía (không để bộ giải tự chọn lại theo shot đầu của tập con)
    for sp in state["specs"]:                            # doi_phia chỉ áp một lần đo
        if (only is None or sp["shot"] in only) and sp.get("doi_phia"):
            sp.pop("doi_phia", None)
    state["measure"] = rel
    if only is None:
        state["full_measure"] = rel
    state["n_measure"] += 1


def ingest(state: Dict, obj: Dict, measure: MeasureFn, source: str = "") -> Dict:
    """Nhận câu trả lời ĐÃ QUA bộ kiểm của vai đang tới lượt → bước sau. `measure(bl, specs)` chạy K3 + K4, trả (thư mục lượt đo
    tương đối, v2)."""
    work = copy.deepcopy(state)                          # rà 16/10: đo lỗi giữa chừng → state gốc nguyên vẹn (không mất lượt duyệt)
    _ingest(work, obj, measure, source)
    state.clear()
    state.update(work)
    return state


def _ingest(state: Dict, obj: Dict, measure: MeasureFn, source: str) -> None:
    p = state["phase"]
    state["history"].append({"phase": p, "source": source})
    if obj.get("can_hoi"):
        state["can_hoi"] = obj["can_hoi"]
    if p == "dao_dien":
        state["blocking"] = obj["blocking"]
        state["phase"] = "quay_phim"
    elif p == "quay_phim":
        state["specs"] = obj["shot_specs"]
        state["s0"] = obj.get("s0")
        _measure(state, measure)
        state["phase"] = "quay_phim_duyet"
    elif p == "quay_phim_duyet":
        state["reviews"] += 1
        specs = {s["shot"]: s for s in state["specs"]}
        changed, requests = set(), []
        acc = state.setdefault("accepted", {})
        for r in obj["shots"]:
            n = r["shot"]
            state["verdicts"][str(n)] = dict({k: v for k, v in r.items() if k != "shot_spec"},
                                             measure=(state.get("shot_measure") or {}).get(str(n)))
            state["keep"].pop(str(n), None)
            state["unresolved"].pop(str(n), None)
            if r["ket_luan"] in ("khop", "giu_lech") and (state.get("shot_measure") or {}).get(str(n)):
                # tối ưu 16/10: khóa lần đo đã duyệt — sửa sau không làm lùi; `lan_do` = chọn một lần đo TRƯỚC của shot (ca thử: m1
                # đúng ý hơn lần sửa sau)
                acc[str(n)] = r.get("lan_do") or state["shot_measure"][str(n)]
            state.setdefault("waive", {}).pop(str(n), None)
            if r["ket_luan"] == "giu_lech" and r.get("bo_luat"):
                state["waive"][str(n)] = [str(c) for c in r["bo_luat"]]
            if r["ket_luan"] == "sua_may":
                specs[n] = _with_nhip([r["shot_spec"]], state["blocking"])[0]
                changed.add(n)
                acc.pop(str(n), None)
                cur = (state.get("shot_measure") or {}).get(str(n))
                if cur:                                          # rà 16/10: lần đo bị Quay phim bác không được chốt lại sau
                    state.setdefault("rejected", {}).setdefault(str(n), []).append(cur)
            elif r["ket_luan"] == "giu_lech":
                state["keep"][str(n)] = r["ly_do"]
            elif r["ket_luan"] == "de_nghi_doi_cho":
                if state["asked"]:                       # một lần hỏi Đạo diễn mỗi cảnh — sau đó Quay phim làm với chỗ đứng đó
                    state["unresolved"][str(n)] = f"Quay phim vẫn đề nghị dời `{r.get('vat')}` sau khi đã hỏi Đạo diễn: {r['ly_do']}"
                else:
                    requests.append({k: r.get(k) for k in ("shot", "vat", "goi_y_at", "ly_do")})
        state["specs"] = [specs[k] for k in sorted(specs)]
        state["notes"] = []
        if obj.get("s0") and obj["s0"] != state.get("s0"):       # Quay phim đổi phía máy cả cảnh → đo lại mọi shot
            state["s0"] = obj["s0"]
            reset_measures(state)
            changed = set(specs)
            _measure(state, measure)
        elif changed:
            _measure(state, measure, only=changed)
        if requests:
            state["requests"], state["asked"] = requests, True
            state["phase"] = "dao_dien_tra_loi"
        elif changed and state["reviews"] < MAX_REVIEWS:
            state["phase"] = "quay_phim_duyet"
        else:
            if changed:                                  # sửa ở lượt duyệt cuối: chưa tự duyệt lại — người duyệt chốt xem
                for r in obj["shots"]:
                    if r["ket_luan"] == "sua_may":
                        state["verdicts"][str(r["shot"])]["chua_duyet_lai"] = True
            state["phase"] = "duyet"
    elif p == "dao_dien_tra_loi":
        state["replies"] = obj["tra_loi"]
        if json.dumps(obj["blocking"], sort_keys=True) != json.dumps(state["blocking"], sort_keys=True):
            state["blocking"] = obj["blocking"]
            state["specs"] = _with_nhip(state["specs"], state["blocking"])
            reset_measures(state)                                # chỗ đứng đổi → số đo cũ (và máy lần trước) không còn đúng
            _measure(state, measure)
        state["requests"] = []
        # rà 16/10: sau câu trả lời của Đạo diễn Quay phim LUÔN có một lượt duyệt (dời người → sửa máy theo; từ chối → làm với chỗ
        # đứng đó / giữ lệch) — có chặn: chỉ hỏi Đạo diễn một lần mỗi cảnh
        state["reviews"] = min(state["reviews"], MAX_REVIEWS - 1)
        state["phase"] = "quay_phim_duyet"
    elif p == "duyet":
        if obj.get("duyet"):
            state["phase"] = "xong"
            state["approved_by"] = source or "dao_dien"
        elif not state["returned"]:
            state["returned"] = True
            state["notes"] = obj["tra_lai"]
            for r in obj["tra_lai"]:                             # rà 16/10: shot bị trả lại không còn khóa lần đo cũ
                (state.get("accepted") or {}).pop(str(r["shot"]), None)
            state["reviews"] = min(state["reviews"], MAX_REVIEWS - 1)       # một lượt tự duyệt nữa cho đúng các ý đồ bị trả lại
            state["phase"] = "quay_phim_duyet"
        else:
            for r in obj["tra_lai"]:
                state["unresolved"][str(r["shot"])] = f"duyệt chốt trả lại lần 2: {r['y_do']}"
            state["phase"] = "xong"
            state["approved_by"] = source or "dao_dien"
    else:
        raise ValueError(f"bước '{p}' đã xong")


def colour_lines(colours: Dict[str, str]) -> List[str]:
    return ["## Màu người nộm trong ảnh clay"] + [f"- {c} = {n}" for c, n in colours.items()] if colours else []
