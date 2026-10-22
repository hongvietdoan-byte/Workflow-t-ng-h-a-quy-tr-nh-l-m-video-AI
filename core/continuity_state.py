"""V3.1 M3.4 (C-M34, cloud-C 20/10) — continuity_state expected / observed / resolved + đồ thị phụ thuộc, chế độ SHADOW: chỉ ghi tệp,
mức REVIEW, KHÔNG chặn gen, không đổi QC, không gọi model (0 USD). Cờ `continuity_state` (mặc định TẮT: không dựng, không ghi gì).
Thiết kế: docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md mục 5.

  expected   tính lại từ BYĐ (shot_intent) giữa 2 shot LIỀN cùng nhóm `sequence` — không lưu riêng:
               cam       `vat[{vat, nguoi, cach: cam}]`: giữ / MẤT / ĐỔI TAY (chữ nói thả, ném, đưa → không phải lỗi)
               tu_the    `hanh_dong[ai].ket_thuc` (hoặc nhịp cuối có) shot trước ↔ `bat_dau` shot sau (chữ nói đứng dậy, ngã… → không)
               noi       `noi_chon.kho_id` hai shot liền cùng nhóm khác nhau
               huong_khung  đọc như M4.3 (core/continuity_shadow.direction — chỉ chữ nói rõ hướng trên khung)
  observed   QC shadow đã ghi: M4.2 `qc_shadow/video_qc.jsonl` (theo job → shot) + M4.3 `continuity_shadow.json` "observed" (Claude)
  resolved   người duyệt (override M4.7 / C3-4) — chưa có: luôn None

Lệch quan sát ở shot i → mọi shot phụ thuộc i qua cạnh (thuộc tính giữ nguyên) → `can_xem` (KHÔNG tự gen lại — M5.1 quyết).
core/continuity_shadow.py chỉ được ĐỌC (hàm đọc chữ / hướng / vật cầm / đồ thị), không gọi build/run của nó.
Ghi `<data_dir>/<pid>/world/continuity_state.json`."""
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import continuity_shadow

FLAG = "continuity_state"
QC_VERSION = "continuity_state@1"

_POSE = re.compile(r"\b(?:gets?|stands?|springs?|jumps?|climbs?|pulls? (?:himself|herself|themselves)) up\b|\brises?\b|\bfalls?\b|"
                   r"\bcollapses?\b|\bslumps?\b|\bdrops? to\b|\blies? down\b|\bsits?(?: down)?\b|\bkneels?\b|\bcrouch(?:es)?\b|"
                   r"\bknocked down\b|đứng (?:dậy|lên)|bật dậy|ngồi (?:dậy|xuống)|\bngã\b|\bgục\b|nằm xuống|\bquỳ\b|\bbò dậy\b", re.I)


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _finding(attribute: str, registry: List[str], shots, entity: str, why: str, before, after, kind: Optional[str] = None) -> Dict:
    ev = {"shots": list(shots), "entity": entity, "attribute": attribute, "before": before, "after": after}
    if kind:
        ev["kind"] = kind
    return {"qc_code": "QC-L13-CONTINUITY", "error_type": "L13", "registry_ids": registry, "severity": "REVIEW", "evidence_type": "metadata",
            "evidence": ev, "confidence": None, "confidence_calibration": None, "intent_exception": None,
            "actionability": {"layer": "byd", "auto_ok": False}, "source_refs": ["core/continuity_state.py"], "why": why}


def _byd(data: Dict) -> Dict:
    from . import shot_intent                      # V3.1 M2.1: đọc BYĐ qua adapter
    return shot_intent.byd_of(data) or {}


def _holder(data: Dict) -> Dict[str, str]:
    """{VẬT: NGƯỜI cầm} (BYĐ v2; v1 chuỗi không có người → không có)."""
    out = {}
    for who, things in continuity_shadow.held(data).items():
        for t in things:
            out[t] = who
    return out


def _poses(data: Dict) -> Dict[str, Dict[str, Optional[str]]]:
    """{NGƯỜI: {"dau": tư thế đầu, "cuoi": tư thế cuối}} từ BYĐ hanh_dong (thiếu nhịp sau → cuối = đầu)."""
    out = {}
    for h in _byd(data).get("hanh_dong") or []:
        if not isinstance(h, dict) or not h.get("ai"):
            continue
        beats = [h.get(n) for n in ("bat_dau", "dinh", "ket_thuc") if isinstance(h.get(n), dict) and h[n].get("tu_the")]
        if beats:
            out[str(h["ai"]).strip().upper()] = {"dau": beats[0]["tu_the"], "cuoi": beats[-1]["tu_the"]}
    return out


def _place(data: Dict):
    nc = _byd(data).get("noi_chon")
    return nc.get("kho_id") if isinstance(nc, dict) else None


def build(rows: List[Dict], observed: Optional[List[Dict]] = None) -> Dict:
    """rows: [{idx, sequence, data, motion}] theo thứ tự phim (như continuity_shadow.rows_of). observed: finding M4.1 có evidence.shots.
    → {states, edges, findings, unknown, can_xem}."""
    states: Dict[tuple, Dict] = {}
    edges, findings, unknown = [], [], []

    def state(shot, entity, attribute, expected):
        states.setdefault((shot, entity, attribute), {"shot": shot, "entity": entity, "attribute": attribute, "expected": expected,
                                                      "observed": [], "resolved": None, "status": "khop"})
        return states[(shot, entity, attribute)]

    for r in rows:
        d = r.get("data") or {}
        for thing, who in _holder(d).items():
            state(r["idx"], who, "cam", thing)
        for who, pose in _poses(d).items():
            state(r["idx"], who, "tu_the", pose)
        if _place(d) is not None:
            state(r["idx"], "_NOI", "noi", _place(d))
    for a, b in zip(rows, rows[1:]):
        if a.get("sequence") != b.get("sequence"):
            continue                                            # khác nhóm liên tục: không có kỳ vọng giữ nguyên
        pair = (a["idx"], b["idx"])
        da, db = a.get("data") or {}, b.get("data") or {}
        ta = continuity_shadow._text(da, a.get("motion") or "")
        tb = continuity_shadow._text(db, b.get("motion") or "")
        words = ta + " " + tb
        cast_b = continuity_shadow._cast(db)
        both = sorted(continuity_shadow._cast(da) & cast_b)
        ha, hb = _holder(da), _holder(db)
        b_has_vat = "vat" in _byd(db)
        for thing, who in sorted(ha.items()):
            if who not in cast_b:
                continue                                        # người cầm không còn trong khung: không kỳ vọng
            if hb.get(thing) == who:
                edges.append({"from": pair[0], "to": pair[1], "entity": who, "attribute": "cam", "value": thing})
            elif not b_has_vat:
                unknown.append({"shots": list(pair), "entity": who, "ly_do": f"shot {pair[1]} chưa có BYĐ vat — không biết {thing} còn cầm"})
                state(pair[1], who, "cam", None)["status"] = "chua_ro"
            elif continuity_shadow._LOSE.search(words):
                continue                                        # chữ nói thả / ném / đưa: đổi theo ý đồ
            elif thing in hb:
                findings.append(_finding("cam", ["P31-G51", "P31-G52"], pair, who,
                                         f"{thing} đổi tay: {who} cầm ở shot {pair[0]}, {hb[thing]} cầm ở shot {pair[1]} (liền sau) — chữ "
                                         "không nói đưa / giật", who, hb[thing], "doi_tay"))
                state(pair[1], hb[thing], "cam", thing)["status"] = "lech"
            else:
                findings.append(_finding("cam", ["P31-G51", "P31-G52"], pair, who,
                                         f"{who} cầm {thing} ở shot {pair[0]} nhưng shot {pair[1]} (liền sau) không còn — chữ không nói "
                                         "thả / ném", thing, None, "mat"))
                state(pair[1], who, "cam", None)["status"] = "lech"
        pa, pb = _poses(da), _poses(db)
        for who in both:
            if who not in pa or who not in pb:
                continue
            end, start = pa[who]["cuoi"], pb[who]["dau"]
            if end == start:
                edges.append({"from": pair[0], "to": pair[1], "entity": who, "attribute": "tu_the", "value": end})
            elif not _POSE.search(tb):
                findings.append(_finding("tu_the", ["P31-G52"], pair, who,
                                         f"{who} kết thúc shot {pair[0]} ở tư thế '{end}' nhưng bắt đầu shot {pair[1]} ở '{start}' — chữ "
                                         "không nói đứng dậy / ngã", end, start))
                state(pair[1], who, "tu_the", pb[who])["status"] = "lech"
        pla, plb = _place(da), _place(db)
        if pla is not None and plb is not None:
            if pla == plb:
                edges.append({"from": pair[0], "to": pair[1], "entity": "_NOI", "attribute": "noi", "value": pla})
            else:
                findings.append(_finding("noi", ["P31-G1"], pair, "_NOI",
                                         f"nơi chốn đổi (Kho #{pla} → #{plb}) giữa hai shot liền cùng nhóm {a.get('sequence')} — xác "
                                         "nhận đúng ý đồ", pla, plb))
                state(pair[1], "_NOI", "noi", plb)["status"] = "lech"
        dir_a, dir_b = continuity_shadow.direction(ta), continuity_shadow.direction(tb)
        if dir_a and dir_b and len(both) == 1:
            state(pair[0], both[0], "huong_khung", dir_a)
            st = state(pair[1], both[0], "huong_khung", dir_b)
            if dir_a == dir_b:
                edges.append({"from": pair[0], "to": pair[1], "entity": both[0], "attribute": "huong_khung", "value": dir_a})
            elif not continuity_shadow._TURN.search(tb):
                findings.append(_finding("huong_khung", ["P31-G41"], pair, both[0],
                                         f"{both[0]} đổi hướng trên khung giữa shot {pair[0]} và {pair[1]} — vượt trục 180° nếu không quay "
                                         "lại / máy đổi phía", dir_a, dir_b))
                st["status"] = "lech"
    need: Dict[str, List[int]] = {}
    for f in observed or []:
        for s in (f.get("evidence") or {}).get("shots") or []:
            hit = [st for st in states.values() if st["shot"] == s]
            for st in hit:
                st["observed"].append({"qc_code": f.get("qc_code"), "why": f.get("why")})
                st["status"] = "lech_quan_sat"
            if not hit:
                state(s, "_SHOT", "quan_sat", None).update(status="lech_quan_sat",
                                                           observed=[{"qc_code": f.get("qc_code"), "why": f.get("why")}])
            for j in continuity_shadow.dependents(edges, s):
                need.setdefault(str(j), [])
                if s not in need[str(j)]:
                    need[str(j)].append(s)
    return {"states": sorted(states.values(), key=lambda x: (x["shot"], x["entity"], x["attribute"])), "edges": edges,
            "findings": findings, "unknown": unknown, "can_xem": {k: sorted(v) for k, v in need.items()}}


def observed_of(conn, data_dir: str, project_id: int) -> List[Dict]:
    """Phát hiện QC shadow đã ghi, gắn số shot: M4.2 (job → shot idx) + M4.3 'observed' (Claude). Chỉ đọc."""
    from . import video_qc_shadow
    out: List[Dict] = []
    idx_of: Dict[int, int] = {}
    for rec in video_qc_shadow.read(data_dir, project_id):
        for jid in rec.get("job_ids") or []:
            if jid not in idx_of:
                row = conn.execute("SELECT s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (jid,)).fetchone()
                idx_of[jid] = row["idx"] if row is not None else None
            if idx_of[jid] is None:
                continue
            for f in rec.get("findings") or []:
                out.append(dict(f, evidence=dict(f.get("evidence") or {}, shots=[idx_of[jid]]), source="M4.2"))
    try:
        with open(continuity_shadow.result_path(data_dir, project_id), encoding="utf-8") as fh:
            m43 = json.load(fh)
        out += [dict(f, source="M4.3") for f in m43.get("observed") or [] if (f.get("evidence") or {}).get("shots")]
    except (OSError, ValueError):
        pass
    return out


def result_path(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "world", "continuity_state.json")


def run(p, project_id: int, data_dir: str) -> Optional[Dict]:
    """Cờ bật: dựng expected + đồ thị, gắn observed, ghi tệp; trả bản ghi. Cờ tắt → None, không ghi. Không bao giờ ném lỗi."""
    if not enabled():
        return None
    try:
        res = build(continuity_shadow.rows_of(p, project_id), observed_of(p.conn, data_dir, project_id))
        rec = {"qc_version": QC_VERSION, "mode": "shadow", "scope": "sequence", "project_id": project_id,
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **res}
        path = result_path(data_dir, project_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        return rec
    except Exception as e:  # noqa: BLE001 - shadow never touches the real run: said in diag
        try:
            from . import diag
            diag.record(p.conn, "video", "warn", f"continuity_state (shadow) lỗi ({type(e).__name__}: {e})", "continuity_state", project_id)
        except Exception:  # noqa: BLE001
            pass
        return None
