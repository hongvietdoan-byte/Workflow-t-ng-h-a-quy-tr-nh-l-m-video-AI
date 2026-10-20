"""V3.1 M4.2 (C-M42, cloud-C 20/10) — QC video CHẾ ĐỘ SHADOW: chỉ ghi bằng chứng, KHÔNG đổi quyết định QC, không giữ job, không gen lại.
Cờ `video_qc_shadow` (mặc định TẮT: không đo, không ghi gì — byte giống). Mã theo thiết kế M4.1 (docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md
mục 3); bảng `qc_runs` / `qc_findings` chưa có (DP4 / migration Cấp 3) → bản ghi cùng trường, mỗi lần chạy một dòng JSON ở
`<data_dir>/<pid>/qc_shadow/video_qc.jsonl` (nhập vào bảng sau, không đổi nghĩa).

  QC-V2-STILL_OVER_1_5S      clip đứng yên ≥ STILL_S giây liền (G51 "13 đơ 6 s", "36 chạy tại chỗ") — đo luồng quang cả khung (clip_measure)
  QC-V1-FIRST_FRAME_MISMATCH khung 0 khác ảnh khung đầu đã duyệt (G28: "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm") — framing_guard.similarity
  QC-V2-REF_TRANSITION       video ref có điểm cắt cảnh trong REF_HEAD_S giây đầu, clip cũng có → model chép chuyển cảnh của ref (B8 #33 S4–S6)
  QC-L7-PROP_HELD            vật BYĐ ghi "cầm" (G51 "29 súng biến mất 1–2,5 s"): code KHÔNG đo được vật trong tay → ghi vào `chua_kiem`
                             (cần quan sát VLM — Q4 qc_observe), không bịa kết quả
Mọi finding ở mức REVIEW (D07: chuyển động / bố cục là ngữ nghĩa, chưa benchmark → không BLOCK). Ngưỡng CHƯA hiệu chuẩn (benchmark M4.6) —
`confidence_calibration` để null. Không gọi mạng, 0 USD."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

FLAG = "video_qc_shadow"
QC_VERSION = "video_qc_shadow@1"
STILL_S = 1.5             # V3.1 M4.2: đứng yên lâu hơn → REVIEW
STILL_FLOW = 0.08         # luồng quang trung bình (px ở clip_measure.FLOW_WIDTH) dưới mức này = đứng yên — CHƯA hiệu chuẩn (M4.6)
REF_HEAD_S = 1.5          # B8: chuyển cảnh trong đoạn đầu video ref (#33: khúc chuyển cảnh mở đầu ref bị chép vào S4–S6)


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def still_spans(series: List[float], fps: float, same: Optional[List[float]] = None, min_s: float = STILL_S,
                flow_max: float = STILL_FLOW) -> List[Tuple[float, float]]:
    """[(t0, t1)] giây — các đoạn ≥ min_s mà mọi cặp khung liền có chuyển động < flow_max. Một điểm cắt cảnh (tương quan màu < CUT_CORR)
    ngắt đoạn (hai cảnh khác nhau không phải 'đứng yên')."""
    from .clip_measure import CUT_CORR
    fps = fps or 24.0
    same = same or [1.0] * len(series)
    out, start = [], None
    for i, m in enumerate(list(series) + [None]):
        quiet = m is not None and m < flow_max and same[i] >= CUT_CORR
        if quiet and start is None:
            start = i
        elif not quiet and start is not None:
            t0, t1 = start / fps, i / fps            # cặp i nối khung i và i+1: đoạn từ khung `start` tới khung `i`
            if t1 - t0 >= min_s - 1e-9:
                out.append((round(t0, 2), round(t1, 2)))
            start = None
    return out


def head_cuts(series: List[float], fps: float, same: List[float], head_s: float = REF_HEAD_S) -> List[float]:
    """Điểm cắt cảnh (giây) trong head_s giây đầu — đúng luật cắt của clip_measure.jerks (màu đổi hẳn, hoặc chuyển động nhảy + màu đổi)."""
    from .clip_measure import jerks
    return [t for t in jerks("", series, fps, same).get("cuts") or [] if t <= head_s]


def _finding(code: str, registry: List[str], evidence_type: str, evidence: Dict, why: str, source: str) -> Dict:
    return {"qc_code": code, "error_type": code.split("-")[1], "registry_ids": registry, "severity": "REVIEW",
            "evidence_type": evidence_type, "evidence": evidence, "confidence": None, "confidence_calibration": None,
            "intent_exception": None, "actionability": {"layer": "video", "auto_ok": False}, "source_refs": [source], "why": why}


def _sha(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def _first_frame(clip_frames: List, picture: Optional[str]) -> Tuple[Optional[Dict], Optional[str]]:
    """(finding hoặc None, ghi chú khi không đo được)."""
    from . import framing_guard as fg
    if not picture or not os.path.exists(picture):
        return None, "không có ảnh khung đầu để so khung 0"
    pic = fg._read(picture)
    if pic is None or not clip_frames:
        return None, "không đọc được ảnh khung đầu / khung 0"
    sim = fg.similarity(pic, clip_frames[0])
    if sim.get("keypoints", 0) < fg.MIN_KEYPOINTS:
        return None, "khung 0: " + str(sim.get("note") or "ảnh ít điểm đặc trưng — không đo được")
    if sim.get("scale") is None or sim.get("inlier_share", 0) < fg.F0_INLIERS:
        why = f"khung 0 khác hẳn ảnh đầu (khớp {sim.get('inliers', 0)}/{sim['keypoints']} điểm)"
    elif sim.get("corner", 0) > fg.F0_CORNER:
        why = f"khung 0 lệch ảnh đầu: góc khung dịch {sim['corner'] * 100:.0f} % (cho phép {fg.F0_CORNER * 100:.0f} %), tỉ lệ × {sim['scale']:.2f}"
    else:
        return None, None
    return _finding("QC-V1-FIRST_FRAME_MISMATCH", ["P31-G28"], "frame", {"t": 0.0, **{k: sim.get(k) for k in
                    ("scale", "dx", "dy", "corner", "inliers", "keypoints", "inlier_share")}},
                    why, "core/framing_guard.py:similarity F0_INLIERS/F0_CORNER"), None


def _held(data: Dict) -> List[Dict]:
    from . import shot_intent
    out = []
    for v in shot_intent.vat_items(data.get("byd")):
        if isinstance(v, dict) and str(v.get("cach") or "").lower() in ("cam", "cầm"):
            out.append({"qc_code": "QC-L7-PROP_HELD", "registry_ids": ["P31-G51"], "vat": v.get("vat"), "nguoi": v.get("nguoi"),
                        "ly_do": "code không đo được vật trong tay — cần quan sát VLM (qc_observe), shadow chưa kiểm"})
    return out


def check(clip: str, picture: Optional[str] = None, ref_video: Optional[str] = None, data: Optional[Dict] = None) -> Dict:
    """{findings, chua_kiem, notes, measured} cho một clip — chỉ đọc tệp, không ghi gì."""
    from . import clip_measure
    findings, notes, unchecked = [], [], _held(data or {})
    try:
        series, fps, same = clip_measure.motion_series(clip)
    except Exception as e:  # noqa: BLE001 - OpenCV thiếu / clip hỏng: nói rõ, không coi là đạt
        return {"findings": [], "chua_kiem": unchecked, "notes": [f"không đo được clip ({type(e).__name__}: {e})"], "measured": False}
    if len(series) < 3:
        return {"findings": [], "chua_kiem": unchecked, "notes": ["clip quá ngắn / không đọc được — chưa đo"], "measured": False}
    for t0, t1 in still_spans(series, fps, same):
        findings.append(_finding("QC-V2-STILL_OVER_1_5S", ["P31-G51"], "segment", {"t0": t0, "t1": t1, "flow_max": STILL_FLOW},
                                 f"clip đứng yên {t1 - t0:.1f} s ({t0:.1f}–{t1:.1f} s)", "core/video_qc_shadow.py:STILL_S/STILL_FLOW"))
    try:
        fs, _ = clip_measure.frames(clip, width=640)
        f0, note = _first_frame(fs[:1], picture)
    except Exception as e:  # noqa: BLE001
        f0, note = None, f"không so được khung 0 ({type(e).__name__}: {e})"
    if f0:
        findings.append(f0)
    if note:
        notes.append(note)
    if ref_video and os.path.exists(ref_video):
        try:
            rseries, rfps, rsame = clip_measure.motion_series(ref_video)
            ref_cuts = head_cuts(rseries, rfps, rsame)
        except Exception as e:  # noqa: BLE001
            ref_cuts = []
            notes.append(f"không đo được video ref ({type(e).__name__}: {e})")
        clip_cuts = head_cuts(series, fps, same)
        if ref_cuts and clip_cuts:
            findings.append(_finding("QC-V2-REF_TRANSITION", ["P33-B8"], "segment", {"ref_cuts": ref_cuts, "clip_cuts": clip_cuts},
                                     f"video ref có chuyển cảnh ở {ref_cuts} s và clip cũng cắt ở {clip_cuts} s — model chép khúc chuyển cảnh "
                                     "của ref; cắt đầu clip khi dựng hoặc làm ref mới bỏ khúc đó", "core/video_qc_shadow.py:REF_HEAD_S"))
        elif ref_cuts:
            notes.append(f"video ref có chuyển cảnh ở {ref_cuts} s (clip không thấy cắt — xem lại nếu clip mở đầu lạ)")
    return {"findings": findings, "chua_kiem": unchecked, "notes": notes, "measured": True}


def observe(conn, data_dir: str, job, clip: str, data: Dict, picture: Optional[str] = None) -> Optional[Dict]:
    """Cờ bật: đo + ghi MỘT bản ghi lần chạy (qc_run + findings) vào jsonl của dự án; trả bản ghi. Cờ tắt → None, không làm gì.
    Không bao giờ ném lỗi, không đổi job / QC (shadow)."""
    if not enabled():
        return None
    try:
        ref = None
        row = conn.execute("SELECT ref_video_path FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
        if row is not None and row["ref_video_path"]:
            ref = row["ref_video_path"]
        res = check(clip, picture, ref, data)
        rec = {"qc_run_id": uuid.uuid4().hex, "project_id": job["project_id"], "scope": "clip", "job_ids": [job["id"]],
               "qc_path": "M4.2", "qc_version": QC_VERSION, "mode": "shadow",
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "status": "ok" if res["measured"] and not res["chua_kiem"] else "partial",
               "artifact_id": f"job:{job['id']}", "artifact_sha": _sha(clip), **res}
        folder = os.path.join(data_dir, str(job["project_id"]), "qc_shadow")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "video_qc.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec
    except Exception as e:  # noqa: BLE001 - shadow never touches the real QC: said in diag, the QC goes on
        try:
            from . import diag
            diag.record(conn, "video", "warn", f"QC video shadow lỗi ({type(e).__name__}: {e}) — QC thật không đổi", "video_qc_shadow",
                        job["project_id"], job_id=job["id"])
        except Exception:  # noqa: BLE001
            pass
        return None


def read(data_dir: str, project_id: int) -> List[Dict]:
    """Các bản ghi shadow của dự án (cho báo cáo benchmark M4.6 / Dashboard sau này)."""
    path = os.path.join(data_dir, str(project_id), "qc_shadow", "video_qc.jsonl")
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        pass
    return out
