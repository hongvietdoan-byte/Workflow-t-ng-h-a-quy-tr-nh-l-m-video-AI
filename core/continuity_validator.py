"""V3.1 M6.9 (C-M61-M69, cloud-E 21/10) — Continuity Validator chế độ SHADOW. Sổ v31-ep-m6-pack-a-approved-2026-10-21.
Thiết kế: docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md mục 5 (QC độc lập, định tuyến lỗi về vai chủ, leo thang, continuity dùng chung).

Một NĂNG LỰC kiểm (không phải phiên Claude): gom phát hiện đã có —
  continuity_state (M3.4) `build` (expected từ BYĐ + đồ thị; tính lại tại chỗ, KHÔNG ghi tệp của M3.4),
  observed của QC shadow M4.2 (`qc_shadow/video_qc.jsonl`) + M4.3 (`continuity_shadow.json`) qua `continuity_state.observed_of`,
  bằng chứng QC M4.1 (`qc_runs`/`qc_findings` nếu đã có bảng, không thì `qc_shadow/qc_evidence.jsonl`) —
rồi định tuyến từng phát hiện về VAI CHỦ theo Role Registry (core/crew.owner_of_error: mã QC → category sổ lỗi → khâu sổ lỗi → Director)
+ devsys/errors.json. Lỗi hệ thống / API / code → Kỹ sư (kênh tools/hop_thu.py — shadow: chỉ ghi, KHÔNG đăng).

CHỈ ghi bằng chứng: bản đầy đủ lần mới nhất `<data_dir>/<pid>/crew/continuity_validator_latest.json` (ghi đè) + một dòng tóm tắt nối vào
`continuity_validator.jsonl`. qc_evidence chỉ lấy phát hiện còn mở của lần chạy mới nhất mỗi (scope, qc_path).
Vai chủ = vai SỬA được (actionability.layer → trường → vai chủ trường đó), vai của loại lỗi giữ ở `registry_owner`; fallback nói ở `canh_bao`. Không chặn, không giữ job,
không tạo / gửi job, không sửa dữ liệu, không gọi model (0 USD). Cờ `continuity_validator` TẮT → không làm gì (không đọc registry, không
dựng). Cờ bật mà `crew_registry` TẮT → không chạy, nói ở diag (không im lặng). Không bao giờ ném lỗi ra đường QC thật."""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import crew

FLAG = "continuity_validator"
QC_VERSION = "continuity_validator@1"
ENGINEER_CHANNEL = "tools/hop_thu.py (Kỹ sư — shadow: chưa đăng)"
ROLE_CHANNEL = "phiếu cho vai chủ (handoff M6.2 — shadow: chưa gửi)"


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def result_path(data_dir: str, project_id: int) -> str:
    """Nhật ký: MỘT dòng tóm tắt mỗi lần chạy (đếm, đầu vào) — không phình theo số phát hiện."""
    return os.path.join(data_dir, str(project_id), "crew", "continuity_validator.jsonl")


def latest_path(data_dir: str, project_id: int) -> str:
    """Bản đầy đủ của lần chạy MỚI NHẤT (ghi đè)."""
    return os.path.join(data_dir, str(project_id), "crew", "continuity_validator_latest.json")


def _compact(f: Dict, source: str) -> Dict:
    ev = f.get("evidence") if isinstance(f.get("evidence"), dict) else {}
    shots = ev.get("shots") if isinstance(ev.get("shots"), list) else []
    act = f.get("actionability") if isinstance(f.get("actionability"), dict) else {}
    return {"qc_code": f.get("qc_code"), "attribute": ev.get("attribute"),
            "shots": [x for x in shots if isinstance(x, int) and not isinstance(x, bool)], "layer": act.get("layer"),
            "qc_run_id": f.get("qc_run_id"),
            "entity": ev.get("entity"), "severity": f.get("severity") or "REVIEW", "why": f.get("why") or ev.get("problem") or "",
            "source": source}


def _open(status) -> bool:
    return (status or "open") == "open"


def read_evidence(conn, data_dir: Optional[str], project_id: int) -> List[Dict]:
    """Phát hiện M4.1 CÒN MỞ của LẦN CHẠY MỚI NHẤT mỗi (scope, qc_path): bảng qc_findings (khi đã migration) hoặc
    qc_shadow/qc_evidence.jsonl (dòng sau thay dòng trước cùng scope + qc_path). Lỗi đã sửa ở lần chạy sau / status khác 'open' → bỏ. Chỉ đọc."""
    from . import qc_evidence
    out: List[Dict] = []
    if conn is not None and qc_evidence.has_tables(conn):
        q = ("SELECT r.qc_run_id, f.qc_code, f.registry_ids, f.severity, f.evidence, f.actionability, f.status FROM qc_findings f "
             "JOIN qc_runs r ON r.qc_run_id=f.qc_run_id WHERE r.rowid IN (SELECT MAX(rowid) FROM qc_runs WHERE project_id=? "
             "GROUP BY scope, qc_path) ORDER BY f.id")
        for run_id, code, regs, sev, ev, act, st in conn.execute(q, (project_id,)).fetchall():
            if _open(st):
                out.append({"qc_run_id": run_id, "qc_code": code, "registry_ids": json.loads(regs or "[]"), "severity": sev,
                            "evidence": json.loads(ev or "{}"), "actionability": json.loads(act or "{}")})
        return out
    if not data_dir:
        return out
    path = os.path.join(data_dir, str(project_id), "qc_shadow", "qc_evidence.jsonl")
    latest: Dict[tuple, Dict] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict):
                    latest.pop((rec.get("scope"), rec.get("qc_path")), None)
                    latest[(rec.get("scope"), rec.get("qc_path"))] = rec
    except OSError:
        pass
    for rec in latest.values():
        out += [dict(f, qc_run_id=rec.get("qc_run_id")) for f in rec.get("findings") or [] if isinstance(f, dict) and _open(f.get("status"))]
    return out


def build(rows: List[Dict], observed: List[Dict], evidence: List[Dict], reg: Dict, errors: Optional[List[Dict]] = None) -> Dict:
    """Thuần (không I/O ngoài đọc devsys/errors.json khi errors=None): rows như continuity_shadow.rows_of; observed = finding có
    evidence.shots (M4.2/M4.3); evidence = finding M4.1. → bản ghi {routed, unrouted, inputs, counts, can_xem}."""
    from . import continuity_state
    errors = crew.errors_index(errors)                          # nạp sổ lỗi MỘT lần cho cả lượt
    cs = continuity_state.build(rows, observed) if rows else {"findings": [], "can_xem": {}, "unknown": []}
    items = [(f, "M3.4") for f in cs["findings"]] + [(f, str(f.get("source") or "observed")) for f in observed] + \
            [(f, "M4.1") for f in evidence]
    seen, routed, unrouted = set(), [], []
    for f, src in items:
        if not isinstance(f, dict) or not f.get("qc_code"):
            continue
        c = _compact(f, src)
        key = (c["qc_code"], c["attribute"], tuple(c["shots"]), c["why"], c["qc_run_id"])
        if key in seen:
            continue
        seen.add(key)
        regs = [r for r in f.get("registry_ids") or [] if isinstance(r, str)]
        r = crew.owner_of_error(c["qc_code"], regs, reg, errors, layer=c["layer"])
        owner = r["owner"]
        if owner == "continuity_validator" or crew.role(owner, reg) is None:
            unrouted.append({"finding": c, "registry_ids": regs, "ly_do": f"vai chủ không hợp lệ: {owner!r}"})
            continue
        role = crew.role(owner, reg)
        routed.append({"finding": c, "registry_ids": regs, "owner": owner, "via": r["via"],
                       "candidates": [x["role"] for x in r["candidates"]], "registry_owner": r["registry_owner"],
                       "fix_field": r["fix_field"], "owner_cannot_fix": r["owner_cannot_fix"], "canh_bao": r["note"],
                       "reports_to": role.get("reports_to"),
                       "escalate": role.get("escalate") or {}, "kenh": ENGINEER_CHANNEL if owner == "engineer" else ROLE_CHANNEL,
                       "phieu": {"to_role": owner, "status": "returned", "shadow": True}})
    thieu = []
    if not rows:
        thieu.append("rows: khong_co shot (continuity_state không dựng)")
    if not observed:
        thieu.append("observed: khong_co (QC shadow M4.2/M4.3 chưa ghi)")
    if not evidence:
        thieu.append("qc_evidence: khong_co (M4.1 chưa ghi)")
    by_owner: Dict[str, int] = {}
    for x in routed:
        by_owner[x["owner"]] = by_owner.get(x["owner"], 0) + 1
    return {"qc_version": QC_VERSION, "mode": "shadow", "registry_version": reg.get("version"),
            "inputs": {"rows": len(rows), "continuity_state": len(cs["findings"]), "observed": len(observed), "qc_evidence": len(evidence),
                       "unknown": len(cs.get("unknown") or []), "thieu": thieu},
            "counts": {"routed": len(routed), "unrouted": len(unrouted), "by_owner": by_owner},
            "routed": routed, "unrouted": unrouted, "can_xem": cs.get("can_xem") or {}}


def _append(path: str, rec: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _summary(rec: Dict) -> Dict:
    return {k: rec.get(k) for k in ("qc_version", "mode", "project_id", "at", "registry_version", "inputs", "counts")}


def run(p, project_id: int, data_dir: str) -> Optional[Dict]:
    """Cờ bật (+ crew_registry): gom + định tuyến + nối một dòng bằng chứng; trả bản ghi. Cờ tắt → None, không đọc / ghi gì."""
    if not enabled():
        return None
    try:
        from . import diag
        reg = crew.active()
        if reg is None:
            diag.record(p.conn, "qc", "warn", "continuity_validator bật nhưng crew_registry TẮT — không định tuyến được lỗi về vai chủ, "
                        "không ghi bằng chứng (bật crew_registry ở 🧪)", "continuity_validator", project_id)
            return None
        from . import continuity_shadow, continuity_state
        rec = build(continuity_shadow.rows_of(p, project_id), continuity_state.observed_of(p.conn, data_dir, project_id),
                    read_evidence(p.conn, data_dir, project_id), reg)
        rec = {**rec, "project_id": project_id, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        path = latest_path(data_dir, project_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        _append(result_path(data_dir, project_id), _summary(rec))
        return rec
    except Exception as e:  # noqa: BLE001 - shadow never touches the real run: said in diag
        try:
            from . import diag
            diag.record(p.conn, "qc", "warn", f"continuity_validator (shadow) lỗi ({type(e).__name__}: {e}) — QC thật không đổi",
                        "continuity_validator", project_id)
        except Exception:  # noqa: BLE001
            pass
        return None


def main(argv: Optional[List[str]] = None) -> int:
    """py -m core.continuity_validator --fixture <tệp.json> [--out <thư mục>] — chạy NGOẠI TUYẾN trên fixture {rows, observed, qc_evidence}
    (không CSDL, không cờ, 0 USD); in bảng định tuyến, ghi <out>/continuity_validator.jsonl khi có --out."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--fixture" not in argv:
        print(main.__doc__)
        return 2
    with open(argv[argv.index("--fixture") + 1], encoding="utf-8") as f:
        fx = json.load(f)
    rec = build(fx.get("rows") or [], fx.get("observed") or [], fx.get("qc_evidence") or [], crew.load())
    for x in rec["routed"]:
        c = x["finding"]
        print(f"{c['source']:<6} {c['qc_code']:<26} {str(c['attribute'] or '-'):<12} shots={c['shots']} reg={x['registry_ids']} → "
              f"{x['owner']} ({x['via']})")
    for x in rec["unrouted"]:
        print("CHƯA ĐỊNH TUYẾN", x["finding"]["qc_code"], x["ly_do"])
    print(f"tổng: {rec['counts']} | thiếu: {rec['inputs']['thieu']}")
    if "--out" in argv:
        _append(os.path.join(argv[argv.index("--out") + 1], "continuity_validator.jsonl"), _summary(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
