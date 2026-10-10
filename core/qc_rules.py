"""Bảng luật kết luận của Tổ QC (docs/THIET_KE_TO_QC_2026-10-01.md mục 9) — code, not the model, turns answers into a verdict.

An answer per assertion: {"id", "answer": "true" | "false" | "unclear", "confidence": "high" | "medium" | "low", "note_vi", "fix_en",
"region"}. Code results (qc_measure): certain_ok / certain_fail / uncertain / not_measurable.
"""
from typing import Dict, List, Optional, Tuple

HIGH_RISK = {"asym", "headwear", "skill"}         # an "ok" on these when seen from behind / with a line still goes to the arbiter (10.1)

# GĐ3 01/10: the model SAW the right thing and concluded the wrong way (Kenta's arms on the wrong side of the frame; Maxim "buckle at the
# nape, no brim" judged "worn backwards"). So for these assertions the model only reports what it sees (fixed choices) and the code below
# turns it into true / false — the model's own `answer` is kept for comparison, never used.
_FRONT_OWN = {"image_left_of_body": "RIGHT", "image_right_of_body": "LEFT"}       # facing the camera: a mirror
_BACK_OWN = {"image_left_of_body": "LEFT", "image_right_of_body": "RIGHT"}        # back to the camera: same as the camera
_NEAR_OWN = {"profile_facing_image_right": "RIGHT", "profile_facing_image_left": "LEFT"}   # in profile the side toward the camera
_OTHER = {"LEFT": "RIGHT", "RIGHT": "LEFT"}
SIDE_CAN_BLOCK = False     # user 01/10: left/right from the model is never an automatic block until measured on a new project
CAP_BACKWARDS = {"strap_or_buckle_at_forehead", "brim_at_nape"}
CAP_FORWARD = {"brim_at_forehead", "strap_or_buckle_at_nape", "no_cap"}


def own_side(facing: str, seen_at: str) -> Optional[str]:
    """The person's OWN side (LEFT / RIGHT) a detail is on, from where it is seen in the picture and which way the person faces; None
    when the two do not fit together (image half with a profile, near/far with front/back) or one is not visible."""
    if facing == "front":
        return _FRONT_OWN.get(seen_at)
    if facing == "back":
        return _BACK_OWN.get(seen_at)
    near = _NEAR_OWN.get(facing)
    if near and seen_at == "near_side":
        return near
    if near and seen_at == "far_side":
        return _OTHER[near]
    return None


def observed(a: Dict, answer: Optional[Dict], code: Optional[Dict] = None) -> Tuple[Optional[Dict], Optional[str], str]:
    """(answer with `answer` decided by code, severity override or None, how it was decided) for an assertion with `observe`; the
    answer unchanged for the others."""
    kind = a.get("observe")
    if kind == "geo" and answer:
        # 10/10 (#24 shot 4 + 8): a 3D-stage geometry fact (core/stage_facts) — the model reports `geo_seen`, stage_facts judges;
        # missing / 'na' / not a choice = 'unsure' → vàng (said, never silent); đỏ = sure
        from . import stage_facts
        seen = answer.get("geo_seen")
        level = stage_facts.judge(a["fact"], seen)
        ans = dict(answer, model_answer=answer.get("answer"))
        how = f"khai hình học: {seen or 'thiếu'} · sự thật {a['fact']['id']} = {a['fact']['value']}"
        if level is None:
            ans.update(answer="true")
            return ans, None, how
        if level == "do":
            ans.update(answer="false", confidence="high")
            return ans, "block", how + " → sai chắc chắn"
        unsure = seen not in a["fact"]["options"] or seen == stage_facts.UNSURE
        if unsure:
            # rà kỹ 10/10 lỗi 2: 'unsure' hạ 'minor' thì frame_verdict vẫn 'pass' — im lặng. Giữ mức của mệnh đề (block) → 'unclear'
            # + block = 'doubt' (người xem), không bao giờ tự vẽ lại vì một khai không chắc
            ans.update(answer="unclear")
            return ans, None, how + " → không chắc, cần người xem"
        ans.update(answer="false")
        return ans, "minor", how + " → lệch, cần người xem"
    if not kind or not answer:
        return answer, None, ""
    ans = dict(answer, model_answer=answer.get("answer"))
    if kind == "side":
        facing, seen = answer.get("facing"), answer.get("seen_at")
        own = own_side(facing, seen)
        faces = ((code or {}).get("_faces") or {}).get("count")
        if a.get("cast_n") == 1 and faces is not None and ((facing == "back" and faces >= 1) or
                                                           (facing == "front" and faces == 0 and a.get("close"))):
            ans.update(answer="unclear")                                     # the face detector disagrees with the reported facing
            return ans, None, f"khai {facing} nhưng code thấy {faces} mặt"
        if own is None:
            ans.update(answer="unclear")
            return ans, None, f"khai: {facing} · {seen} → không suy ra được bên"
        ans.update(answer="true" if own == a["expected"] else "false")
        how = f"khai: {facing} · {seen} → bên {own} của chính người đó (cần {a['expected']})"
        if own != a["expected"] and not SIDE_CAN_BLOCK:        # GĐ3 01/10: the model places a detail on the right half of the
            return ans, "minor", "trái/phải — cần người xem (QC chưa đo được tin cậy) · " + how     # picture ~50 % of the time
        return ans, None, how
    if kind == "cap":
        marks = answer.get("cap_marks")
        ans.update(answer="true" if marks in CAP_BACKWARDS else ("false" if marks in CAP_FORWARD else "unclear"))
        return ans, None, f"khai mũ: {marks}"
    if kind == "count":
        extra = answer.get("extra_people")
        if extra == "none":
            ans.update(answer="true")
        elif extra in ("clear", "missing"):
            ans.update(answer="false")
        elif extra == "partial_or_background":                          # #8 323 / 326: labelled minor
            ans.update(answer="false")
            return ans, "minor", "khai: người thừa chỉ lộ một phần / mờ phía sau"
        return ans, None, f"khai số người: {extra}" if extra and extra != "na" else ""
    return answer, None, ""


def assertion_result(a: Dict, answer: Optional[Dict], code: Optional[Dict]) -> Dict:
    """{"state": ok / fail / unclear, "severity", "why", "arbiter": reason or None} for one assertion."""
    answer, sev_override, derived = observed(a, answer, code)
    res = _assertion_result(a, answer, code, sev_override)
    if derived:
        res["why"] = (derived + (" — " + res["why"] if res["why"] else "")).strip()
    return res


def _assertion_result(a: Dict, answer: Optional[Dict], code: Optional[Dict], sev_override: Optional[str]) -> Dict:
    cs = (code or {}).get("status")
    ans = (answer or {}).get("answer")
    conf = (answer or {}).get("confidence") or "low"
    sev = sev_override or a["severity_if_false"]
    if a["how"] == "code":                                           # code only (size…): the code result is the answer
        if cs == "certain_fail":
            return {"state": "fail", "severity": sev, "why": (code or {}).get("note", ""), "arbiter": None}
        return {"state": "ok" if cs == "certain_ok" else "unclear", "severity": sev, "why": (code or {}).get("note", ""), "arbiter": None}
    if ans is None and cs in ("certain_ok", "certain_fail"):         # nobody was asked (a role not running) — the code is sure
        return {"state": "fail" if cs == "certain_fail" else "ok", "severity": sev, "why": (code or {}).get("note", ""),
                "arbiter": "xác nhận chặn" if cs == "certain_fail" and sev == "block" else None}
    if ans is None:
        return {"state": "unclear", "severity": sev, "why": "chuyên viên không trả lời mệnh đề này",
                "arbiter": "không trả lời" if sev == "block" else None}
    if cs in ("certain_ok", "certain_fail") and ans in ("true", "false") and (cs == "certain_ok") != (ans == "true"):
        return {"state": "unclear", "severity": sev, "why": f"code ({cs}) ≠ chuyên viên ({ans})", "arbiter": "code ≠ chuyên viên"}
    if ans == "false":
        if conf == "low" and sev == "block":
            return {"state": "unclear", "severity": sev, "why": answer.get("note_vi", ""), "arbiter": "sai nhưng độ chắc thấp"}
        return {"state": "fail", "severity": sev, "why": answer.get("note_vi", ""), "arbiter": "xác nhận chặn" if sev == "block" else None}
    if ans == "unclear":
        return {"state": "unclear", "severity": sev, "why": answer.get("note_vi", ""), "arbiter": "không rõ" if sev == "block" else None}
    risky = a["type"] in HIGH_RISK and a.get("view") == "behind" and sev == "block"
    return {"state": "ok", "severity": sev, "why": "", "arbiter": "đạt nhưng rủi ro cao (quay lưng)" if risky else None}


def frame_verdict(assertions: List[Dict], answers: Dict[str, Dict], code: Dict[str, Dict]) -> Dict:
    """Mục 9.2: {"verdict": block / minor / pass / doubt, "arbiter": [reasons], "results": {id: result}, "fails": [...]}. 'block'
    here is a proposal: it waits for the arbiter before any money is spent redrawing."""
    results = {a["id"]: assertion_result(a, answers.get(a["id"]), dict(code.get(a["id"]) or {}, _faces=code.get("_faces")))
               for a in assertions}
    fails = [a for a in assertions if results[a["id"]]["state"] == "fail"]
    unclear_block = [a for a in assertions if results[a["id"]]["state"] == "unclear" and results[a["id"]]["severity"] == "block"]
    arbiter = sorted({f"{a['id']}: {results[a['id']]['arbiter']}" for a in assertions if results[a["id"]]["arbiter"]})
    if any(results[a["id"]]["severity"] == "block" for a in fails):
        verdict = "block"
    elif unclear_block:
        verdict = "doubt"
    elif fails:
        verdict = "minor"
    else:
        verdict = "pass"
    return {"verdict": verdict, "arbiter": arbiter, "results": results,
            "fails": [{"id": a["id"], "type": a["type"], "subject": a["subject"], "claim_vi": a["claim_vi"],
                       "severity": results[a["id"]]["severity"], "why": results[a["id"]]["why"],
                       "fix_en": (answers.get(a["id"]) or {}).get("fix_en", "")} for a in fails]}
