"""V3.1 M4.3 (C-M43, cloud-C 20/10) — logic XUYÊN SHOT chế độ SHADOW: chỉ ghi, KHÔNG chặn gen, không đổi QC, không gọi model (0 USD).
Cờ `continuity_shadow` (mặc định TẮT: không dựng, không ghi gì).

Theo thiết kế M3.4 (docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md mục 5) ở mức ĐỌC: tầng *expected* tính lại từ dữ liệu shot (BYĐ + chữ),
không lưu; tầng *observed* = phát hiện của QC logic chuỗi Claude (core/sequence_logic, cờ `qc_sequence_logic`) nếu đã chạy; *resolved* (người
duyệt, M4.7) chưa có. Đồ thị phụ thuộc theo thực thể: cạnh `shot_i --(thực thể, thuộc tính)--> shot_j` giữa 2 shot LIỀN cùng nhóm
`sequence` khi thuộc tính giữ nguyên; thuộc tính đổi mà chữ shot sau không nói lý do → finding REVIEW (người xem — có thể là ý đồ).

  vật cầm      BYĐ v2 `vat[{vat, nguoi, cach: cam}]` (v1 chuỗi không có người cầm → không suy) — G51 "súng biến mất", G52
  dạng         core/character_forms.for_shot (Kho style khai dạng) — G37 / #31 shot 30 (bóng mờ → thực tại: đổi ĐÚNG ý đồ → chỉ REVIEW)
  hướng khung  chữ tiếng Anh nói rõ hướng trên khung ("left to right", "towards frame-left"…) — G41; không chữ → không đoán

Observed (Claude) có lỗi ở shot i → mọi shot j phụ thuộc i qua cạnh → `can_xem` (KHÔNG tự gen lại — M5.1 quyết).
Ghi `<data_dir>/<pid>/qc_set/sequence/continuity_shadow.json` (findings theo trường M4.1: qc_code QC-L13-CONTINUITY…)."""
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

FLAG = "continuity_shadow"
QC_VERSION = "continuity_shadow@1"

# hướng trên KHUNG — chỉ chữ tiếng Anh viết rõ (prompt video / motion_en); "left"/"right" một mình không đọc (trái của ai?)
_LTR = re.compile(r"\bfrom (?:frame[- ])?left to (?:frame[- ])?right\b|\btowards? frame[- ]right\b|\bframe[- ]right ?ward\b|"
                  r"\b(?:runs?|moves?|walks?|travels?|goes|crosses|heads?) (?:to(?:wards?)? )?(?:the )?frame[- ]right\b", re.I)
_RTL = re.compile(r"\bfrom (?:frame[- ])?right to (?:frame[- ])?left\b|\btowards? frame[- ]left\b|\bframe[- ]left ?ward\b|"
                  r"\b(?:runs?|moves?|walks?|travels?|goes|crosses|heads?) (?:to(?:wards?)? )?(?:the )?frame[- ]left\b", re.I)
# chữ nói lý do đổi: quay lại / vòng lại / máy đổi phía / thả, ném, mất vật / biến hình
_TURN = re.compile(r"\bturns? (?:a)?round\b|\bu-?turn\b|\breverses?\b|\bdoubles? back\b|\bquay (?:lại|đầu|người)\b|vòng lại|"
                   r"\breverse angle\b|góc ngược", re.I)
_LOSE = re.compile(r"\bdrops?\b|\bthrows?\b|\btosses?\b|\blets? go\b|\bholsters?\b|\bputs? (?:it |the \w+ )?(?:down|away)\b|\bloses?\b|"
                   r"\bhands? (?:it|the \w+) (?:to|over)\b|đánh rơi|\bthả\b|\bném\b|cất (?:súng|vũ khí)|làm rơi|\bmất\b", re.I)
_SHIFT = re.compile(r"\btransforms?\b|\bturns? into\b|\bchanges? (?:back|into|form)\b|\breturns? to (?:reality|normal)\b|biến (?:hình|thành)|"
                    r"trở về|về thực tại|hiện nguyên hình", re.I)


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _text(data: Dict, motion: str = "") -> str:
    from . import prop_lock
    parts = [prop_lock.shot_text(data), motion]
    m = data.get("motion_en")
    if isinstance(m, dict):
        parts += [str(v) for v in m.values() if isinstance(v, str)]
    return " ".join(p for p in parts if p)


def direction(text: str) -> Optional[str]:
    """'ltr' / 'rtl' khi chữ nói rõ MỘT hướng trên khung; cả hai hoặc không có → None (không đoán)."""
    ltr, rtl = bool(_LTR.search(text or "")), bool(_RTL.search(text or ""))
    return "ltr" if ltr and not rtl else "rtl" if rtl and not ltr else None


def held(data: Dict) -> Dict[str, Set[str]]:
    """{NGƯỜI: {VẬT}} từ BYĐ v2 (cach = cam). v1 (chuỗi) không có người cầm → {} (không suy)."""
    from . import shot_intent
    out: Dict[str, Set[str]] = {}
    for v in shot_intent.vat_items(data.get("byd")):
        if isinstance(v, dict) and str(v.get("cach") or "").lower() in ("cam", "cầm") and v.get("nguoi") and v.get("vat"):
            out.setdefault(str(v["nguoi"]).strip().upper(), set()).add(str(v["vat"]).strip().upper())
    return out


def _cast(data: Dict) -> Set[str]:
    return {str(c).strip().upper() for c in data.get("characters") or [] if str(c).strip()}


def _finding(code: str, registry: List[str], shots: Tuple[int, int], entity: str, why: str, evidence: Dict) -> Dict:
    return {"qc_code": code, "error_type": "L13", "registry_ids": registry, "severity": "REVIEW", "evidence_type": "metadata",
            "evidence": {"shots": list(shots), "entity": entity, **evidence}, "confidence": None, "confidence_calibration": None,
            "intent_exception": None, "actionability": {"layer": "byd", "auto_ok": False}, "source_refs": ["core/continuity_shadow.py"],
            "why": why}


def build(rows: List[Dict], forms_of=None) -> Dict:
    """rows: [{idx, sequence, data, motion}] theo thứ tự phim. forms_of(data) -> {NGƯỜI: tên dạng}. → {edges, findings, unknown}."""
    edges, findings, unknown = [], [], []
    for a, b in zip(rows, rows[1:]):
        if a.get("sequence") != b.get("sequence"):
            continue                                            # khác nhóm liên tục: không có kỳ vọng giữ nguyên
        pair = (a["idx"], b["idx"])
        da, db = a.get("data") or {}, b.get("data") or {}
        ta, tb = _text(da, a.get("motion") or ""), _text(db, b.get("motion") or "")
        both = sorted(_cast(da) & _cast(db))
        ha, hb = held(da), held(db)
        b_has_byd_vat = isinstance(db.get("byd"), dict) and "vat" in db["byd"]
        for who in both:
            for thing in sorted(ha.get(who, set())):
                if thing in hb.get(who, set()):
                    edges.append({"from": pair[0], "to": pair[1], "entity": who, "attribute": "cam", "value": thing})
                elif not b_has_byd_vat:
                    unknown.append({"shots": list(pair), "entity": who, "ly_do": f"shot {pair[1]} chưa có BYĐ vat — không biết {thing} còn cầm"})
                elif not _LOSE.search(ta + " " + tb):
                    findings.append(_finding("QC-L13-CONTINUITY", ["P31-G51", "P31-G52"], pair, who,
                                             f"{who} cầm {thing} ở shot {pair[0]} nhưng shot {pair[1]} (liền sau) không còn — chữ không nói thả/ném",
                                             {"attribute": "cam", "before": thing, "after": None}))
        if forms_of is not None:
            fa, fb = forms_of(da), forms_of(db)
            for who in both:
                if fa.get(who) == fb.get(who):
                    if fa.get(who):
                        edges.append({"from": pair[0], "to": pair[1], "entity": who, "attribute": "dang", "value": fa[who]})
                elif not _SHIFT.search(ta + " " + tb):
                    findings.append(_finding("QC-L13-CONTINUITY", ["P31-G37"], pair, who,
                                             f"{who} đổi dạng giữa shot {pair[0]} ({fa.get(who) or 'thường'}) và {pair[1]} "
                                             f"({fb.get(who) or 'thường'}) — xác nhận đúng ý đồ", {"attribute": "dang", "before": fa.get(who),
                                                                                                  "after": fb.get(who)}))
        dir_a, dir_b = direction(ta), direction(tb)
        if dir_a and dir_b and len(both) == 1:                  # một người: hướng của ai rõ ràng
            if dir_a == dir_b:
                edges.append({"from": pair[0], "to": pair[1], "entity": both[0], "attribute": "huong_khung", "value": dir_a})
            elif not _TURN.search(tb):
                findings.append(_finding("QC-L13-CONTINUITY", ["P31-G41"], pair, both[0],
                                         f"{both[0]} đi {'trái→phải' if dir_a == 'ltr' else 'phải→trái'} ở shot {pair[0]} rồi ngược lại ở shot "
                                         f"{pair[1]} (liền sau) — vượt trục 180° nếu không có quay lại / máy đổi phía",
                                         {"attribute": "huong_khung", "before": dir_a, "after": dir_b}))
    return {"edges": edges, "findings": findings, "unknown": unknown}


def dependents(edges: List[Dict], idx: int) -> List[int]:
    """Các shot phụ thuộc shot `idx` (đi theo cạnh, bắc cầu) — lệch ở idx → các shot này 'cần xem'."""
    out, todo = [], [idx]
    while todo:
        cur = todo.pop()
        for e in edges:
            if e["from"] == cur and e["to"] not in out:
                out.append(e["to"])
                todo.append(e["to"])
    return sorted(out)


def observed(result: Optional[Dict]) -> List[Dict]:
    """Phát hiện của QC logic chuỗi Claude (sequence_logic.last_result) → finding M4.1 (vlm, REVIEW)."""
    out = []
    for g, obj in ((result or {}).get("sequences") or {}).items():
        for it in obj.get("issues") or []:
            if not isinstance(it, dict) or it.get("idx") is None:
                continue
            out.append({"qc_code": "QC-L13-CONTINUITY", "error_type": "L13", "registry_ids": ["P31-G52"], "severity": "REVIEW",
                        "evidence_type": "vlm", "evidence": {"shots": [it["idx"]], "sequence": g, "problem": it.get("problem"),
                                                             "fix": it.get("fix")},
                        "confidence": None, "confidence_calibration": None, "intent_exception": None,
                        "actionability": {"layer": "video", "auto_ok": False, "fix_en": it.get("fix")},
                        "source_refs": ["core/sequence_logic.py:check"], "why": str(it.get("problem") or "")})
    return out


def rows_of(p, project_id: int) -> List[Dict]:
    from .sequence_logic import _group
    out = []
    for r in p.conn.execute("SELECT s.id, s.idx, s.data, m.motion_prompt FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id "
                            "WHERE s.project_id=? ORDER BY s.idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        out.append({"idx": r["idx"], "sequence": _group(d), "data": d, "motion": r["motion_prompt"] or ""})
    return out


def result_path(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "qc_set", "sequence", "continuity_shadow.json")


def run(p, project_id: int, data_dir: str, claude_result: Optional[Dict] = None) -> Optional[Dict]:
    """Cờ bật: dựng expected + đồ thị, gắn observed (Claude) + 'cần xem', ghi tệp; trả bản ghi. Cờ tắt → None. Không bao giờ ném lỗi."""
    if not enabled():
        return None
    try:
        from . import character_forms
        rows = rows_of(p, project_id)
        res = build(rows, lambda d: {w: f.get("form") for w, f in character_forms.for_shot(p.conn, project_id, d).items()})
        obs = observed(claude_result)
        need = {}
        for f in obs:
            for s in f["evidence"]["shots"]:
                for j in dependents(res["edges"], s):
                    need.setdefault(j, []).append(s)
        rec = {"qc_version": QC_VERSION, "mode": "shadow", "scope": "sequence", "project_id": project_id,
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "expected": res["findings"], "observed": obs,
               "edges": res["edges"], "unknown": res["unknown"], "can_xem": {str(k): sorted(set(v)) for k, v in need.items()}}
        path = result_path(data_dir, project_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        return rec
    except Exception as e:  # noqa: BLE001 - shadow never touches the real run: said in diag
        try:
            from . import diag
            diag.record(p.conn, "video", "warn", f"logic xuyên shot (shadow) lỗi ({type(e).__name__}: {e})", "continuity_shadow", project_id)
        except Exception:  # noqa: BLE001
            pass
        return None
