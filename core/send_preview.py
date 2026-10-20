"""V3.1 M4.7 phần XEM (C-M47A, cờ send_preview_panel — TẮT = Bước 4 y cũ): thẻ clip hiện "Gói sẽ gửi" và "QC shadow", CHỈ ĐỌC.

Gói: dựng bằng ĐÚNG đường của nút Gen — VideoRunner._submit_args / _submit_kwargs / _build_package (như K3 dựng gói trước khi gửi),
không tính tay. Trên một bản sao nông của runner: nhà cung cấp bọc chặn mọi lời gọi (chỉ đọc chữ ký hàm submit để ghép tham số), ảnh
Kho chủ thể không tải lên (đường K3 `_pregen_local`), D6 (Claude viết lại prompt) không gọi, ghi chú của runner trả về màn hình thay
vì ghi ⚙ Chẩn đoán, các ghi khi dựng (lipsync 'generate_sent', kiểu đánh dấu ảnh, đổi bậc) bỏ qua (`_preview`). 0 USD.
QC shadow: đọc bản ghi M4.2 (qc_shadow/video_qc.jsonl), M4.3 (qc_set/sequence/continuity_shadow.json), M4.1 (bảng qc_runs/qc_findings
hoặc qc_shadow/qc_evidence.jsonl) của đúng job / shot. Không có nút sửa / override (C3-4 chờ)."""
import copy
import functools
import json
import os
from typing import Any, Dict, List, Optional

from . import features

FLAG = "send_preview_panel"


def enabled() -> bool:
    return features.on(FLAG)


class PreviewBlocked(RuntimeError):
    """Xem trước định gọi nhà cung cấp — chặn (không gửi, không hỏi)."""


class _NoCall:
    """Bọc nhà cung cấp: thuộc tính (name, supports_*) đọc như thật; mọi hàm → PreviewBlocked. Chữ ký giữ (functools.wraps) để
    sent_package.build ghép tham số đúng như lần gửi thật."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        value = getattr(self._real, name)
        if not callable(value):
            return value

        @functools.wraps(value)
        def blocked(*a, **k):
            raise PreviewBlocked(f"xem trước không gọi nhà cung cấp ({name})")
        return blocked


def _add_note(notes: List[Dict], severity: str, code: Any, text: str) -> None:
    item = {"severity": severity, "code": str(code or ""), "text": str(text)}
    if item not in notes:
        notes.append(item)


def _price(p, job) -> Optional[float]:
    from . import cost
    if not cost.send_estimate_on():
        return None
    try:
        return cost.clip_estimate(p.conn, job["scene_id"], parent_job_id=job["id"])
    except Exception:  # noqa: BLE001 - a price that cannot be read is shown as missing, never a made-up number
        return None


def video_package(p, runner, job) -> Dict[str, Any]:
    """{"ok", "why", "package" (dict như jobs.sent_package, external_id None), "refs" [{n, param, role, label, file, path}], "notes",
    "price" (send_estimate bật, không thì None)}. Không bao giờ ném lỗi."""
    from . import chat_prompt
    notes: List[Dict] = []
    out: Dict[str, Any] = {"ok": False, "why": None, "package": None, "refs": [], "notes": notes, "price": _price(p, job)}
    r = copy.copy(runner)
    r.provider = _NoCall(runner.provider)
    r.__dict__.update(_preview=True, _pregen_local=True, _pregen_deferred=[], _sent={}, _storyboard={}, _final_routes={},
                      _pregen_fingerprints={})
    say = lambda j, severity, code, message: _add_note(notes, severity, code, message)   # noqa: E731
    r._diag = say
    r._diag_once = say
    r._pregen_note = lambda j, code, message: _add_note(notes, "warn", code, message)
    try:
        args = r._submit_args(job)
        if args is None:
            out["why"] = "thiếu đầu vào (ảnh đã duyệt / motion prompt đã duyệt) — nút Gen cũng sẽ không gửi"
            return out
        kwargs = r._submit_kwargs(job) if getattr(runner.provider, "supports_aspect", False) else {}
    except PreviewBlocked as e:
        out["why"] = f"{e} — gói này cần hỏi nhà cung cấp lúc gửi (vd bản cao nâng từ nháp), không dựng trước được"
        return out
    except Exception as e:  # noqa: BLE001 - said on the card, the page goes on
        out["why"] = f"không dựng được gói ({type(e).__name__}: {e})"
        return out
    for key, what in (("_wait", "chờ"), ("_hold", "giữ")):
        if kwargs.get(key):
            _add_note(notes, "warn", key.strip("_"), f"lúc gửi job sẽ {what}: {kwargs[key]}")
    if chat_prompt.enabled():
        _add_note(notes, "info", "d6", "D6 (chat_prompts) bật: lúc gửi Claude viết lại prompt từ bản code ghép dưới đây — xem trước không gọi "
                                   "Claude (0 USD), prompt thật có thể khác chữ")
    if r.__dict__.get("_pregen_deferred"):
        _add_note(notes, "info", "hosted", "ảnh qua Kho chủ thể: lúc gửi sẽ tải lên (asset://) — đây là tệp cục bộ sẽ được tải")
    sent_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_")}
    pkg, warns = r._build_package(job, args, kwargs, sent_kwargs, None)
    for w in warns:
        _add_note(notes, "warn", "sent_package", w)
    if not pkg:
        out["why"] = "không dựng được gói gửi (xem ghi chú)"
        return out
    body = json.loads(pkg)
    out.update(ok=True, package=body,
               refs=[{"n": i, "param": x.get("param"), "role": x.get("role"), "label": x.get("label"), "file": x.get("file"),
                      "path": x.get("path")} for i, x in enumerate(body.get("refs") or [], 1)])
    return out


def _jsonl(path: str) -> List[Dict]:
    rows: List[Dict] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows


def _evidence(conn, data_dir: str, project_id: int, job_id: int) -> List[Dict]:
    from . import qc_evidence
    if conn is not None and qc_evidence.has_tables(conn):
        runs = []
        for run in conn.execute("SELECT * FROM qc_runs WHERE project_id=? ORDER BY started_at", (project_id,)).fetchall():
            try:
                ids = json.loads(run["job_ids"] or "[]")
            except ValueError:
                ids = []
            if job_id in ids:
                found = conn.execute("SELECT * FROM qc_findings WHERE qc_run_id=?", (run["qc_run_id"],)).fetchall()
                runs.append(dict(dict(run), job_ids=ids, findings=[dict(f) for f in found]))
        return runs
    return [r for r in _jsonl(os.path.join(data_dir, str(project_id), "qc_shadow", "qc_evidence.jsonl")) if job_id in (r.get("job_ids") or [])]


SHADOW_CACHE: Dict[tuple, Dict[str, Any]] = {}
SHADOW_CACHE_MAX = 512


def _mtime(path: str) -> Optional[int]:
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def _shadow_key(conn, data_dir: str, project_id: int, job, idx) -> tuple:
    from . import continuity_shadow, qc_evidence
    base = os.path.join(data_dir, str(project_id), "qc_shadow")
    run = None
    try:
        if conn is not None and qc_evidence.has_tables(conn):
            run = conn.execute("SELECT MAX(rowid) FROM qc_runs WHERE project_id=?", (project_id,)).fetchone()[0]
    except Exception:  # noqa: BLE001 - no key part → read again next time
        run = object()
    return (data_dir, project_id, job["id"], idx, _mtime(os.path.join(base, "video_qc.jsonl")),
            _mtime(os.path.join(base, "qc_evidence.jsonl")), _mtime(continuity_shadow.result_path(data_dir, project_id)), run)


def shadow_cached(conn, data_dir: str, project_id: int, job, idx: Optional[int]) -> Dict[str, Any]:
    """C-FIX-THAP-5: shadow_of qua bộ nhớ đệm — thẻ clip vẽ lại mỗi rerun; chỉ đọc lại khi tệp M4.2 / M4.3 / M4.1 đổi (mtime) hoặc có
    qc_run mới trong bảng."""
    key = _shadow_key(conn, data_dir, project_id, job, idx)
    hit = SHADOW_CACHE.get(key)
    if hit is None:
        if len(SHADOW_CACHE) >= SHADOW_CACHE_MAX:
            SHADOW_CACHE.clear()
        hit = SHADOW_CACHE[key] = shadow_of(conn, data_dir, project_id, job, idx)
    return hit


def shadow_of(conn, data_dir: str, project_id: int, job, idx: Optional[int]) -> Dict[str, Any]:
    """Bản ghi QC shadow của job / shot: {"video": [M4.2 của job], "continuity": [M4.3 có shot idx], "can_xem": [shot gốc],
    "evidence": [M4.1 của job], "notes": [chưa có gì → nói]}. Chỉ đọc, không bao giờ ném lỗi."""
    from . import continuity_shadow, video_qc_shadow
    jid = job["id"]
    out: Dict[str, Any] = {"video": [], "continuity": [], "can_xem": [], "evidence": [], "notes": []}
    try:
        out["video"] = [r for r in video_qc_shadow.read(data_dir, project_id) if jid in (r.get("job_ids") or [])]
    except Exception as e:  # noqa: BLE001
        out["notes"].append(f"không đọc được QC video shadow ({type(e).__name__})")
    try:
        with open(continuity_shadow.result_path(data_dir, project_id), encoding="utf-8") as f:
            cont = json.load(f)
        if idx is not None:
            out["continuity"] = [x for x in (cont.get("expected") or []) + (cont.get("observed") or [])
                                 if idx in ((x.get("evidence") or {}).get("shots") or [])]
            out["can_xem"] = list((cont.get("can_xem") or {}).get(str(idx)) or [])
    except (OSError, ValueError):
        pass
    try:
        out["evidence"] = _evidence(conn, data_dir, project_id, jid)
    except Exception as e:  # noqa: BLE001
        out["notes"].append(f"không đọc được bằng chứng QC ({type(e).__name__})")
    if not out["video"]:
        out["notes"].append("chưa có bản ghi QC video shadow (M4.2) cho clip này — cờ video_qc_shadow tắt hoặc clip chưa qua QC; "
                            "chưa kiểm ≠ đạt")
    if not out["continuity"] and not out["can_xem"]:
        out["notes"].append("logic xuyên shot (M4.3): không có ghi nhận cho shot này (hoặc chưa chạy QC logic chuỗi)")
    if not out["evidence"]:
        out["notes"].append("chưa có bằng chứng QC (M4.1) gắn job này")
    return out
