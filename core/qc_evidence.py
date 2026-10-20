"""V3.1 M4.1 (DP4, cloud-C 20/10) — schema BẰNG CHỨNG QC + ghi SHADOW. Thiết kế: docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md.

Cờ `qc_evidence` (mặc định TẮT: không ghi gì mới — byte giống). Bật: các đường QC đã nối (nay: Q9 `final_qc.run`) ghi MỘT lần chạy
(`qc_runs`) + các phát hiện (`qc_findings`) song song, KHÔNG đổi quyết định QC hiện có (shadow).

- Bảng `qc_runs` / `qc_findings`: migration bổ sung `migrate_up` / `migrate_down` — KHÔNG tự chạy khi mở CSDL (áp CSDL thật = Cấp 3, phiên chính
  sau sao lưu). Chưa có bảng → ghi tạm `<data_dir>/<pid>/qc_shadow/qc_evidence.jsonl` (cùng trường; nhập bảng sau, không đổi nghĩa).
- `CODES` = bảng mã QC thống nhất (thiết kế mục 3) ↔ loại lỗi `devsys/error_types.json` ↔ mã sổ `devsys/errors.json`.
- `validate(finding)` = luật mức D07: BLOCK chỉ khi mã tất định đã được duyệt chặn (đang chặn từ trước, `PREEXISTING_BLOCK`) hoặc tất định +
  bằng chứng metadata/segment + `confidence_calibration`; mã từ model (VLM) không bao giờ BLOCK.
- Adapter: `from_final_qc` (Q9), `from_clip_measure` (Q3), `normalize_shadow` (bản ghi tạm của M4.2 `video_qc_shadow` / M4.3 `continuity_shadow`)."""
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

FLAG = "qc_evidence"
SEVERITIES = ("BLOCK", "REVIEW", "INFO")
EVIDENCE_TYPES = ("metadata", "frame", "segment", "vlm")
STATUSES = ("open", "overridden", "resolved", "false_positive")
SCOPES = ("image", "clip", "scene", "sequence", "final", "pregen")
MODES = ("shadow", "guarded")
RUN_STATUSES = ("ok", "failed", "partial")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# qc_code: (error_type, tất định?, mức tối đa, mã sổ lỗi) — thiết kế M4.1 mục 3 + mã mới của M4.2 (video_qc_shadow).
CODES: Dict[str, Tuple[str, bool, str, Tuple[str, ...]]] = {
    "QC-L1-IDENTITY_DRIFT": ("L1", False, "REVIEW", ()),
    "QC-L2-FORM_OUTFIT": ("L2", False, "REVIEW", ("P31-G37", "P31-G27")),
    "QC-L3-EXTRA_PEOPLE": ("L3", False, "REVIEW", ()),
    "QC-L4-POSE_ACTION": ("L4", False, "REVIEW", ("P31-G19",)),
    "QC-L6-SIZE_MISMATCH": ("L8", False, "REVIEW", ("P33-A5", "P31-G28")),
    "QC-L7-PROP_MISSING": ("L7", False, "REVIEW", ("V21-R3", "P31-G38", "P31-G7")),
    "QC-L9-HORIZON_MISMATCH": ("L9", False, "REVIEW", ("P31-G20",)),
    "QC-L11-PLACE_MISMATCH": ("L11", False, "REVIEW", ("P31-G40", "P31-G26")),
    "QC-L13-CONTINUITY": ("L13", False, "REVIEW", ("P31-G52", "P31-G42", "P31-G51", "P31-G41", "P31-G37")),
    "QC-L14-ARTIFACT": ("L14", False, "REVIEW", ()),
    "QC-V1-DRIFT": ("V1", False, "REVIEW", ()),
    "QC-V1-FIRST_FRAME_MISMATCH": ("V1", False, "REVIEW", ("P31-G28",)),
    "QC-V2-JERK_FREEZE": ("V2", False, "REVIEW", ("P31-G51",)),
    "QC-V2-STILL_OVER_1_5S": ("V2", False, "REVIEW", ("P31-G51",)),
    "QC-V2-REF_TRANSITION": ("V2", False, "REVIEW", ("P33-B8",)),
    "QC-V3-LIP_SYNC": ("V3", False, "REVIEW", ("P31-G16", "P31-G10")),
    "QC-V4-MOTION_VS_BYD": ("V4", False, "REVIEW", ("P31-G11",)),
    "QC-PKG-VI_TEXT": ("L12", True, "BLOCK", ("P33-B7", "P31-G12")),
    "QC-PKG-FORM_PICTURE_MISSING": ("L2", True, "BLOCK", ("P31-G27",)),
    "QC-PKG-PROMPT_TOO_LONG": ("L12", True, "BLOCK", ("P31-G13", "P31-G54")),
    "QC-A4-LENGTH_MISMATCH": ("A4", True, "BLOCK", ()),
    "QC-A2-PEAK_OVER": ("A2", True, "BLOCK", ()),
    "QC-A2-SILENT_GAP": ("A2", True, "REVIEW", ()),
    "QC-A4-BLACK_FRAME": ("A4", True, "REVIEW", ()),      # C-FIX-DP345: G2-5 — QC bản dựng cuối không chặn xuất
    "QC-A4-FREEZE_FRAME": ("A4", True, "REVIEW", ()),
    "QC-A4-DELIVERY_RES": ("A4", True, "BLOCK", ()),
}
# Mã ĐANG chặn từ trước (người dùng đã chấp nhận — thiết kế mục 4 "Ngoại lệ đã có"): chỉ chuẩn hóa cách ghi, không cần hiệu chuẩn mới.
PREEXISTING_BLOCK = frozenset({"QC-PKG-VI_TEXT", "QC-PKG-FORM_PICTURE_MISSING", "QC-PKG-PROMPT_TOO_LONG", "QC-A4-LENGTH_MISMATCH",
                               "QC-A2-PEAK_OVER", "QC-A4-DELIVERY_RES"})
_SHA = re.compile(r"^[0-9a-f]{64}$")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _known(path: str, key: str, field: str) -> set:
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return {x.get(field) for x in json.load(f)[key]}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def error_types() -> set:
    return _known(os.path.join("devsys", "error_types.json"), "types", "id")


def registry_ids() -> set:
    return _known(os.path.join("devsys", "errors.json"), "items", "id")


def validate(finding: Dict, types: Optional[set] = None, registry: Optional[set] = None) -> List[str]:
    """Lỗi hợp đồng của MỘT finding ([] = hợp lệ)."""
    types = error_types() if types is None else types
    registry = registry_ids() if registry is None else registry
    out = []
    code = finding.get("qc_code")
    if code not in CODES:
        out.append(f"qc_code lạ: {code!r}")
    if finding.get("severity") not in SEVERITIES:
        out.append(f"severity ∉ {SEVERITIES}")
    if finding.get("evidence_type") not in EVIDENCE_TYPES:
        out.append(f"evidence_type ∉ {EVIDENCE_TYPES}")
    if finding.get("error_type") not in types:
        out.append(f"error_type {finding.get('error_type')!r} không có trong devsys/error_types.json")
    if code in CODES and finding.get("error_type") != CODES[code][0]:
        out.append(f"error_type {finding.get('error_type')!r} khác bảng mã ({CODES[code][0]})")
    bad = [r for r in finding.get("registry_ids") or [] if r not in registry]
    if bad:
        out.append(f"registry_ids không có trong sổ lỗi: {bad}")
    sha = finding.get("artifact_sha")
    if sha is not None and not _SHA.match(str(sha)):
        out.append("artifact_sha phải là sha256 (64 hex) hoặc null")
    if finding.get("status", "open") not in STATUSES:
        out.append(f"status ∉ {STATUSES}")
    sev = finding.get("severity")
    if code in CODES and sev in SEVERITIES and SEVERITIES.index(sev) < SEVERITIES.index(CODES[code][2]):
        out.append(f"severity {sev} vượt trần {CODES[code][2]} của mã {code}")        # C-FIX-DP345: finding() hạ mức, ghi tay cũng không lọt
    if finding.get("severity") == "BLOCK":
        det = CODES.get(code, ("", False, "REVIEW", ()))[1]
        if not det:
            out.append("BLOCK chỉ cho luật tất định (mã từ model / ngữ nghĩa → REVIEW, D07)")
        elif code not in PREEXISTING_BLOCK:
            if finding.get("evidence_type") not in ("metadata", "segment"):
                out.append("BLOCK cần bằng chứng metadata / segment đo lại được")
            if not finding.get("confidence_calibration"):
                out.append("BLOCK cần confidence_calibration (benchmark M4.6) + người duyệt bật chặn mã này")
    return out


def finding(code: str, severity: str, evidence_type: str, evidence: Dict, why: str, artifact_id: str, artifact_sha: Optional[str],
            source: str, layer: Optional[str] = None, confidence: Optional[float] = None) -> Dict:
    """Một finding đủ trường (mức không vượt mức tối đa của mã)."""
    et, _det, top, reg = CODES[code]
    if SEVERITIES.index(severity) < SEVERITIES.index(top):
        severity = top
    return {"qc_code": code, "error_type": et, "registry_ids": list(reg), "severity": severity, "evidence_type": evidence_type,
            "evidence": evidence, "confidence": confidence, "confidence_calibration": None, "intent_exception": None,
            "actionability": {"layer": layer, "auto_ok": False}, "source_refs": [source], "artifact_id": artifact_id,
            "artifact_sha": artifact_sha, "status": "open", "why": why}


def sha256_of(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


# ---- adapter -------------------------------------------------------------------------------------------------------------------
_FINAL = {"length": "QC-A4-LENGTH_MISMATCH", "peak": "QC-A2-PEAK_OVER", "silence": "QC-A2-SILENT_GAP", "black_frame": "QC-A4-BLACK_FRAME",
          "freeze_frame": "QC-A4-FREEZE_FRAME"}


def from_final_qc(res: Dict, artifact_id: str, artifact_sha: Optional[str]) -> List[Dict]:
    """Q9 final_qc.run → finding (chỉ các mã có trong bảng; mã khác — nhạc, phụ đề, gợi ý — chưa có mã M4.1, bỏ qua có chủ đích).
    Mức = mức final_qc đang dùng: block → BLOCK (chỉ mã đã chặn từ trước), warn → REVIEW."""
    out = []
    for it in res.get("issues") or []:
        code = _FINAL.get(it.get("code"))
        if code is None:
            continue
        sev = "BLOCK" if it.get("level") == "block" and code in PREEXISTING_BLOCK else "REVIEW"
        ev = {"at": it.get("at"), "level": it.get("level")}
        out.append(finding(code, sev, "segment" if it.get("at") is not None else "metadata", ev, it.get("msg") or "", artifact_id,
                           artifact_sha, f"core/final_qc.py:{it.get('code')}", layer="edit"))
    return out


def from_clip_measure(measured: Dict, artifact_id: str, artifact_sha: Optional[str]) -> List[Dict]:
    """Q3 clip_measure.measure → finding (mỗi số đo có cờ): `motion` (cắt / giật / đứng-rồi-nhảy) → QC-V2-JERK_FREEZE; `look` (mặt lệch ảnh
    khung đầu) → QC-V1-DRIFT."""
    out = []
    j = measured.get("motion") if isinstance(measured.get("motion"), dict) else {}
    if j.get("flag"):
        out.append(finding("QC-V2-JERK_FREEZE", "REVIEW", "segment", {k: j.get(k) for k in ("cuts", "jerks", "freezes")},
                           str(j.get("why") or j["flag"]), artifact_id, artifact_sha, "core/clip_measure.py:jerks", layer="video"))
    d = measured.get("look") if isinstance(measured.get("look"), dict) else {}
    if d.get("flag"):
        out.append(finding("QC-V1-DRIFT", "REVIEW", "frame", {k: v for k, v in d.items() if k != "why"}, str(d.get("why") or d["flag"]),
                           artifact_id, artifact_sha, "core/clip_measure.py:look_drift", layer="video"))
    return out


def normalize_shadow(rec: Dict) -> List[Dict]:
    """Bản ghi tạm của M4.2 (video_qc_shadow: findings + artifact_*) / M4.3 (continuity_shadow: expected + observed) → finding hợp lệ."""
    rows = list(rec.get("findings") or []) + list(rec.get("expected") or []) + list(rec.get("observed") or [])
    out = []
    for f in rows:
        if not isinstance(f, dict) or f.get("qc_code") not in CODES:
            continue
        g = dict(f)
        g.setdefault("artifact_id", rec.get("artifact_id") or f"project:{rec.get('project_id')}")
        g.setdefault("artifact_sha", rec.get("artifact_sha"))
        g.setdefault("status", "open")
        g["error_type"] = CODES[g["qc_code"]][0]
        out.append(g)
    return out


# ---- bảng (migration bổ sung, không tự chạy) -----------------------------------------------------------------------------------
TABLES = """
CREATE TABLE IF NOT EXISTS qc_runs (
    qc_run_id TEXT PRIMARY KEY, project_id INTEGER, scope TEXT, job_ids TEXT, qc_path TEXT, qc_version TEXT, model TEXT, provider TEXT,
    prompt_sha TEXT, rules_version TEXT, mode TEXT, started_at TEXT, finished_at TEXT, cost_usd REAL, status TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS qc_findings (
    id INTEGER PRIMARY KEY, qc_run_id TEXT REFERENCES qc_runs(qc_run_id), artifact_id TEXT, artifact_sha TEXT, error_type TEXT,
    qc_code TEXT, registry_ids TEXT, severity TEXT, evidence_type TEXT, evidence TEXT, confidence REAL, confidence_calibration TEXT,
    intent_exception TEXT, actionability TEXT, source_refs TEXT, status TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS idx_qc_findings_run ON qc_findings(qc_run_id);
CREATE INDEX IF NOT EXISTS idx_qc_findings_code ON qc_findings(qc_code);
"""


def has_tables(conn) -> bool:
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('qc_runs','qc_findings')")}
    return names == {"qc_runs", "qc_findings"}


def migrate_up(conn) -> bool:
    """Tạo 2 bảng (bổ sung, chạy lại không đổi gì). Cấp 3 trên CSDL thật — phiên chính sau sao lưu. Trả True khi vừa tạo."""
    had = has_tables(conn)
    conn.executescript(TABLES)
    conn.commit()
    return not had


def migrate_down(conn, force: bool = False) -> None:
    """Gỡ 2 bảng; còn dữ liệu → từ chối trừ `force` (thiết kế mục 8: đường lùi an toàn là để bảng, tắt cờ)."""
    if not has_tables(conn):
        return
    n = conn.execute("SELECT COUNT(*) FROM qc_findings").fetchone()[0] + conn.execute("SELECT COUNT(*) FROM qc_runs").fetchone()[0]
    if n and not force:
        raise ValueError(f"còn {n} dòng bằng chứng QC — gỡ sẽ mất; dùng force=True sau khi sao lưu")
    conn.executescript("DROP TABLE IF EXISTS qc_findings; DROP TABLE IF EXISTS qc_runs;")
    conn.commit()


def _js(v) -> Optional[str]:
    return None if v is None else json.dumps(v, ensure_ascii=False)


def record(conn, data_dir: Optional[str], project_id: Optional[int], scope: str, qc_path: str, qc_version: str,
           findings: List[Dict], job_ids: Optional[List[int]] = None, status: str = "ok", error: Optional[str] = None) -> Optional[Dict]:
    """Cờ bật: ghi MỘT lần chạy + các finding (bảng nếu có, không thì jsonl của dự án). Cờ tắt → None, không làm gì. Không bao giờ ném lỗi
    (shadow: QC thật đi tiếp) — lỗi ghi vào diag `qc_evidence`."""
    if not enabled():
        return None
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run = {"qc_run_id": uuid.uuid4().hex, "project_id": project_id, "scope": scope, "job_ids": list(job_ids or []), "qc_path": qc_path,
           "qc_version": qc_version, "mode": "shadow", "started_at": now, "finished_at": now, "status": status, "error": error}
    try:
        if conn is not None and has_tables(conn):
            conn.execute("INSERT INTO qc_runs (qc_run_id, project_id, scope, job_ids, qc_path, qc_version, mode, started_at, finished_at, "
                         "status, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (run["qc_run_id"], project_id, scope, _js(run["job_ids"]), qc_path, qc_version, "shadow", now, now, status, error))
            for f in findings:
                conn.execute("INSERT INTO qc_findings (qc_run_id, artifact_id, artifact_sha, error_type, qc_code, registry_ids, severity, "
                             "evidence_type, evidence, confidence, confidence_calibration, intent_exception, actionability, source_refs, "
                             "status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (run["qc_run_id"], f.get("artifact_id"), f.get("artifact_sha"), f.get("error_type"), f.get("qc_code"),
                              _js(f.get("registry_ids")), f.get("severity"), f.get("evidence_type"), _js(f.get("evidence")),
                              f.get("confidence"), _js(f.get("confidence_calibration")), _js(f.get("intent_exception")),
                              _js(f.get("actionability")), _js(f.get("source_refs")), f.get("status") or "open", now))
            conn.commit()
            run["stored"] = "db"
        elif data_dir and project_id is not None:
            folder = os.path.join(data_dir, str(project_id), "qc_shadow")
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "qc_evidence.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(dict(run, findings=findings), ensure_ascii=False) + "\n")
            run["stored"] = "jsonl"
        else:
            run["stored"] = None
        return dict(run, findings=findings)
    except Exception as e:  # noqa: BLE001 - shadow never touches the real QC: said in diag
        try:
            from . import diag
            diag.record(conn, "qc", "warn", f"ghi bằng chứng QC (shadow) lỗi ({type(e).__name__}: {e}) — QC thật không đổi", "qc_evidence",
                        project_id)
        except Exception:  # noqa: BLE001
            pass
        return None
