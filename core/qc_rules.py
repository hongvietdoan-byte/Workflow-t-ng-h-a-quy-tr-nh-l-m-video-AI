"""Bảng luật kết luận của Tổ QC (docs/THIET_KE_TO_QC_2026-10-01.md mục 9) — code, not the model, turns answers into a verdict.

An answer per assertion: {"id", "answer": "true" | "false" | "unclear", "confidence": "high" | "medium" | "low", "note_vi", "fix_en",
"region"}. Code results (qc_measure): certain_ok / certain_fail / uncertain / not_measurable.
"""
from typing import Dict, List, Optional

HIGH_RISK = {"asym", "headwear", "skill"}         # an "ok" on these when seen from behind / with a line still goes to the arbiter (10.1)


def assertion_result(a: Dict, answer: Optional[Dict], code: Optional[Dict]) -> Dict:
    """{"state": ok / fail / unclear, "severity", "why", "arbiter": reason or None} for one assertion."""
    cs = (code or {}).get("status")
    ans = (answer or {}).get("answer")
    conf = (answer or {}).get("confidence") or "low"
    sev = a["severity_if_false"]
    if a["how"] == "code":                                           # code only (size…): the code result is the answer
        if cs == "certain_fail":
            return {"state": "fail", "severity": sev, "why": (code or {}).get("note", ""), "arbiter": None}
        return {"state": "ok" if cs == "certain_ok" else "unclear", "severity": sev, "why": (code or {}).get("note", ""), "arbiter": None}
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
    results = {a["id"]: assertion_result(a, answers.get(a["id"]), code.get(a["id"])) for a in assertions}
    fails = [a for a in assertions if results[a["id"]]["state"] == "fail"]
    unclear_block = [a for a in assertions if results[a["id"]]["state"] == "unclear" and a["severity_if_false"] == "block"]
    arbiter = sorted({f"{a['id']}: {results[a['id']]['arbiter']}" for a in assertions if results[a["id"]]["arbiter"]})
    if any(a["severity_if_false"] == "block" for a in fails):
        verdict = "block"
    elif unclear_block:
        verdict = "doubt"
    elif fails:
        verdict = "minor"
    else:
        verdict = "pass"
    return {"verdict": verdict, "arbiter": arbiter, "results": results,
            "fails": [{"id": a["id"], "type": a["type"], "subject": a["subject"], "claim_vi": a["claim_vi"],
                       "severity": a["severity_if_false"], "why": results[a["id"]]["why"],
                       "fix_en": (answers.get(a["id"]) or {}).get("fix_en", "")} for a in fails]}
