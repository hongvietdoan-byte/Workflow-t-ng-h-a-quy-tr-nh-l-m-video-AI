"""M4.8 Đợt 1 (C-M48-DESK-CORE) — tầng lõi "Bàn đạo diễn 3D" trên Dashboard: các nút thao tác sân khấu (0 USD) gọi đúng hàm có sẵn của
core/stage_auto, chạy nền một luồng mỗi dự án, khóa S theo đoạn, tiến độ ra tệp. Kế hoạch: docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md
(mục 2, 4, 5, 7). Quyết định: sổ v31-ep-stage-desk-actions-2026-10-21 (S-A … S-G). Không gọi Claude API, không tốn tiền (N13 = Đợt 3).

API CÔNG KHAI (dashboard/stage_desk_ui.py — C-M48-DESK-UI — chỉ gọi các hàm này; mọi hàm nhận `scene` = cảnh truyện `story_scene` dạng chữ):

  Đọc (thuần — KHÔNG Blender, KHÔNG ghi; gọi được mỗi lần Streamlit vẽ lại):
    status(conn, pid, data_dir) -> [dict]                  một dòng mỗi cảnh (xem scene_status)
    scene_status(conn, pid, data_dir, scene) -> dict        {scene, seg_id, stage, shots, phase, label, k1, inputs_changed, approved_by,
                                                             cams, bad, round, sheet, drawn, revs, lock, progress, running, buttons, ...}
    progress(data_dir, pid, scene, conn=None) -> dict|None tiến độ tác vụ nền gần nhất (state running / done / error / interrupted)
    is_executive_producer(conn, pid, user) -> bool          S-B: người được Duyệt / Trả lại sân khấu
    paid_gate(conn, pid, data_dir, scene_ids) -> [dict]     S-C: VÀNG / HOLD trước generation trả phí
    lock_holder(data_dir, pid, scene, conn) -> dict|None    khóa S đang giữ đoạn (autopilot / CLI hỏi)
    busy(conn, pid, data_dir) -> [(seg_id, holder)]         mọi đoạn đang bị khóa S của dự án

  Nút (mục 4 kế hoạch; `who` = write_guard.actor(...) của người / phiên bấm; mọi nút trả dict có "ok"; lỗi = "errors" [câu]):
    N1 check_inputs(conn, pid, data_dir, scene, who)        nền: K1 (Blender nếu chưa có) + đầu vào + cổng 0 USD
    N2 estimate(conn, pid, data_dir, scene)                 đồng bộ: ước tính Claude của cảnh (chỉ để XEM — Đợt 1 không có nút API)
    N3 write_prompt(conn, pid, data_dir, scene, who)        đồng bộ, khóa S: đề bài vai đang tới lượt → doan_<S>/crew/de_bai_<phase>.md
    N4 load_answer(conn, pid, data_dir, scene, obj, who)    nền: câu trả lời vai (source cố định "claude_code" — KHÔNG nhận người dùng)
    N5 build_sheet(conn, pid, data_dir, scene, who)         nền: tấm ghép → doan_<S>/beats/san_khau_canh<S>.png (không ghi CSDL)
    N6 approve(conn, pid, data_dir, scene, who, user, confirm_drawn=False, expected_revs=None)   S-B: chỉ EP; ghi máy qua write guard
    N7 return_(conn, pid, data_dir, scene, tra_lai, who, user)                                   S-B: chỉ EP; không ghi CSDL
    N8 reset(conn, pid, data_dir, scene, who, confirm=False)  S-D: confirm=False → chỉ XEM TRƯỚC (preview) thay đổi + phụ thuộc
    N9 rerender(conn, pid, data_dir, scene, who, confirm_drawn=False)   nền: K3 + K4 từ câu trả lời đã lưu; ghi máy qua guard
    N10 score(conn, pid, data_dir, scene)                   đồng bộ, khóa S: chấm lại các lượt đã lưu (không ghi CSDL)
    N11 render_plates(conn, pid, data_dir, scene, who)      quên render nền hỏng của các shot cảnh + place_refs.ensure_async
  S-C (cổng trước gen trả phí — Dashboard / phiên chính nối vào nút Gen; ở đây chỉ là luật + dữ liệu):
    require_plate(conn, pid, data_dir, scene_id, on, who, user)       EP đánh dấu shot BẮT BUỘC có plate 3D đã duyệt làm reference
    allow_exception(conn, pid, data_dir, scene_id, why, who, user)    EP xác nhận ngoại lệ (gen trả phí khi sân khấu chưa duyệt)

Luồng nền: một `threading.Thread` daemon mỗi DỰ ÁN (`_RUNNING[pid]`) mở kết nối sqlite riêng (CSDL :memory: → từ chối, như
place_refs.ensure_async); bấm lại khi còn chạy → "đang chạy …", không luồng thứ hai. Khóa S: tệp doan_<S>/.desk.lock {pid tiến trình, owner,
nút, giờ} — autopilot `_stage_phase` và CLI tools/stage_auto.py gặp khóa thì chờ / từ chối CÓ CÂU; khóa của tiến trình đã chết / quá
LOCK_STALE_SEC → gỡ + báo. Blender xếp hàng sẵn trong stage_grid.run_blender_safe / plates3d.render (plates3d.blender_turn) — ở đây
không khóa Blender lần nữa (khóa tệp không vào lại được). Không bao giờ gán biến môi trường cờ (FEATURE_…) — stage_auto.run(manual=True)."""
import datetime
import json
import os
import sqlite3
import threading
import time
from typing import Callable, Dict, List, Optional, Sequence

from . import diag

CODE = "stage_desk"
LOCK_FILE = ".desk.lock"
PROGRESS_FILE = "desk_progress.json"
RESET_FILE = "desk_reset.json"
GATE_FILE = "desk_gate.json"                    # <data>/<pid>/stage/desk_gate.json — S-C: shot bắt buộc plate đã duyệt + ngoại lệ
LOCK_STALE_SEC = 3 * 3600                       # một thao tác sân khấu (đo K3 + K4 nhiều shot) không quá chừng này
LOG_KEEP = 50
SOURCE_DESK = "claude_code"                     # N4: câu trả lời vai từ phiên Claude Code / người viết — KHÔNG phải người dùng duyệt

ACTIONS = {
    "N1": "🔍 Kiểm đầu vào", "N2": "💲 Ước tính", "N3": "📝 Đề bài cho phiên Claude Code", "N4": "📥 Nạp câu trả lời vai",
    "N5": "🖼 Dựng tấm ghép", "N6": "✅ Duyệt sân khấu cảnh", "N7": "↩ Trả lại", "N8": "🗑 Làm lại từ Đạo diễn",
    "N9": "🔁 Render lại từ câu trả lời đã lưu", "N10": "🧮 Chấm lại các lượt đã lưu", "N11": "↻ Render lại nền 3D cảnh này",
}
PHASE_LABEL = {None: "chưa dàn", "dao_dien": "đang ở vai Đạo diễn", "quay_phim": "đang ở vai Quay phim",
               "quay_phim_duyet": "Quay phim đang duyệt số đo", "dao_dien_tra_loi": "Đạo diễn đang trả lời",
               "duyet": "chờ Executive Producer duyệt", "xong": "đã chốt"}

_RUNNING: Dict[int, threading.Thread] = {}
_LOCK = threading.Lock()


class DeskError(ValueError):
    """Thao tác bị từ chối có lý do (câu nói cho người bấm)."""


# ---- tiện ích ---------------------------------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _sa():
    from . import stage_auto
    return stage_auto


def segment(conn, pid: int, scene) -> Dict:
    """Đoạn (cảnh truyện, sân khấu) của cảnh `scene`. Một cảnh trên nhiều sân khấu → đoạn đầu (bàn đạo diễn làm theo cảnh)."""
    for g in _sa().segments(conn, pid):
        if str(g["scene"]) == str(scene):
            return g
    raise DeskError(f"cảnh {scene} không có shot nào trên bối cảnh 3D")


def seg_dir(data_dir: str, pid: int, seg: Dict) -> str:
    sa = _sa()
    return os.path.join(sa.base_dir(data_dir, pid, seg["stage"]), f"doan_{sa.key_of(seg['scene'])}")


def _read(path: str) -> Optional[Dict]:
    try:
        with open(path, encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, dict) else None
    except (OSError, ValueError):
        return None


def _write(path: str, obj: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _who_text(who: Optional[Dict]) -> str:
    return f"{(who or {}).get('kind', '?')}:{(who or {}).get('who', '?')}"


def _say(conn, pid: int, sev: str, msg: str, scene_id: Optional[int] = None) -> None:
    try:
        diag.record(conn, "director", sev, msg, CODE, pid, scene_id)
    except Exception:  # noqa: BLE001 - a diag write never stops a desk action
        pass


# ---- khóa S -----------------------------------------------------------------------------------------------------------------
def _pid_alive(pid: int) -> bool:
    from .plates3d import pid_alive
    return pid_alive(pid)


def lock_holder(data_dir: str, pid: int, scene, conn=None, seg: Optional[Dict] = None) -> Optional[Dict]:
    """Khóa S đang giữ đoạn (dict {pid, owner, action, since, since_ts}) hoặc None. Khóa của tiến trình đã chết / quá hạn → gỡ + báo."""
    seg = seg or segment(conn, pid, scene)
    path = os.path.join(seg_dir(data_dir, pid, seg), LOCK_FILE)
    h = _read(path)
    if h is None:
        return None
    age = time.time() - float(h.get("since_ts") or 0)
    dead = int(h.get("pid") or 0) > 0 and not _pid_alive(int(h["pid"]))
    if dead or age > LOCK_STALE_SEC:
        try:
            os.remove(path)
        except OSError:
            pass
        why = f"tiến trình {h.get('pid')} không còn chạy" if dead else f"quá {LOCK_STALE_SEC // 60} phút"
        if conn is not None:
            _say(conn, pid, "warn", f"Bàn đạo diễn: gỡ khóa thao tác sân khấu {seg['id']} ({h.get('action')}, {h.get('owner')}) — {why}; "
                                    "state chia vai giữ nguyên (crew_answer không lưu nửa vời)")
        return None
    return h


def busy(conn, pid: int, data_dir: str) -> List[tuple]:
    """[(seg_id, holder)] — đoạn của dự án đang bị khóa S (autopilot `_stage_phase` chờ, CLI từ chối)."""
    out = []
    for g in _sa().segments(conn, pid):
        h = lock_holder(data_dir, pid, g["scene"], conn, seg=g)
        if h:
            out.append((g["id"], h))
    return out


def lock_line(seg_id: str, h: Dict) -> str:
    return (f"đang thao tác sân khấu {seg_id} trên Dashboard ({h.get('action')}, {h.get('owner') or 'không rõ người'}, từ "
            f"{h.get('since')}) — chờ xong rồi chạy lại")


class _Hold:
    """Giữ khóa S của đoạn trong `with` (tạo O_EXCL — hai tiến trình không cùng giữ). Đang bị giữ → DeskError có câu."""

    def __init__(self, data_dir: str, pid: int, seg: Dict, action: str, who: Optional[Dict], conn=None):
        self.path = os.path.join(seg_dir(data_dir, pid, seg), LOCK_FILE)
        self.args = (data_dir, pid, seg, action, who, conn)

    def __enter__(self):
        data_dir, pid, seg, action, who, conn = self.args
        h = lock_holder(data_dir, pid, seg["scene"], conn, seg=seg)
        if h:
            raise DeskError(lock_line(seg["id"], h))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise DeskError(lock_line(seg["id"], _read(self.path) or {})) from None
        os.write(fd, json.dumps({"pid": os.getpid(), "owner": _who_text(who), "action": action, "since_ts": time.time(),
                                 "since": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False).encode("utf-8"))
        os.close(fd)
        return self

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except OSError:
            pass
        return False


# ---- tiến độ + luồng nền ---------------------------------------------------------------------------------------------------
def _progress_path(data_dir: str, pid: int, seg: Dict) -> str:
    return os.path.join(seg_dir(data_dir, pid, seg), PROGRESS_FILE)


def progress(data_dir: str, pid: int, scene, conn=None, seg: Optional[Dict] = None) -> Optional[Dict]:
    """Tiến độ tác vụ nền gần nhất của đoạn. 'running' mà luồng không còn sống (tiến trình Streamlit tắt / luồng chết) → 'interrupted'
    kèm câu "tác vụ bị ngắt lúc …, state giữ nguyên"."""
    seg = seg or segment(conn, pid, scene)
    pr = _read(_progress_path(data_dir, pid, seg))
    if not pr or pr.get("state") != "running":
        return pr
    mine = int(pr.get("process") or 0) == os.getpid()
    alive = (_RUNNING.get(pid) is not None and _RUNNING[pid].is_alive() and _RUNNING[pid].name == pr.get("thread")) if mine \
        else _pid_alive(int(pr.get("process") or 0))
    if not alive:
        pr = dict(pr, state="interrupted", error=f"tác vụ bị ngắt lúc {pr.get('updated') or pr.get('started')} — state chia vai giữ "
                                                 "nguyên (crew_answer không lưu nửa vời khi đo lỗi); bấm lại nút để chạy tiếp")
    return pr


def running(pid: int) -> bool:
    t = _RUNNING.get(pid)
    return t is not None and t.is_alive()


def _db_path(conn) -> Optional[str]:
    row = conn.execute("PRAGMA database_list").fetchone()
    return (row[2] if row else "") or None


def _start(conn, pid: int, data_dir: str, seg: Dict, action: str, who: Optional[Dict],
           work: Callable[[sqlite3.Connection, Callable[[str], None]], Dict]) -> Dict:
    """Chạy `work(conn_riêng, log)` trong luồng nền của dự án, giữ khóa S của đoạn, ghi tiến độ. Trả {"ok", "started"|"errors"}."""
    db = _db_path(conn)
    if not db:
        return {"ok": False, "errors": ["CSDL trong bộ nhớ — không mở được từ luồng nền (chạy Dashboard với tệp CSDL)"]}
    with _LOCK:
        t = _RUNNING.get(pid)
        if t is not None and t.is_alive():
            pr = _read(_progress_path(data_dir, pid, seg)) or {}
            return {"ok": False, "errors": [f"đang chạy {t.name.split('|', 1)[-1]} của dự án này"
                                            + (f" ({pr.get('step')})" if pr.get("step") else "") + " — chờ xong rồi bấm lại"]}
        h = lock_holder(data_dir, pid, seg["scene"], conn, seg=seg)
        if h:
            return {"ok": False, "errors": [lock_line(seg["id"], h)]}
        name = f"stage_desk_{pid}|{action} {seg['id']}"
        path = _progress_path(data_dir, pid, seg)
        pr = {"action": action, "label": ACTIONS.get(action, action), "seg": seg["id"], "who": _who_text(who), "started": _now(),
              "updated": _now(), "step": "chờ bắt đầu", "log": [], "state": "running", "process": os.getpid(), "thread": name}
        _write(path, pr)

        def log(msg: str) -> None:
            pr["log"] = (pr["log"] + [str(msg)[:400]])[-LOG_KEEP:]
            pr["step"], pr["updated"] = str(msg)[:200], _now()
            try:
                _write(path, pr)
            except OSError:
                pass

        def run():
            c = sqlite3.connect(db, timeout=60)
            c.row_factory = sqlite3.Row
            try:
                with _Hold(data_dir, pid, seg, action, who, c):
                    res = work(c, log) or {}
                pr.update(state="done" if res.get("ok", True) else "error", result=res, updated=_now(),
                          error="; ".join(res.get("errors") or []) or None)
            except Exception as e:  # noqa: BLE001 - said in the progress file + diag, never swallowed
                pr.update(state="error", error=f"{type(e).__name__}: {e}"[:600], updated=_now())
                _say(c, pid, "error", f"Bàn đạo diễn {ACTIONS.get(action, action)} {seg['id']} lỗi: {pr['error']}")
            finally:
                try:
                    _write(path, pr)
                except OSError:
                    pass
                c.close()

        t = threading.Thread(target=run, name=name, daemon=True)
        _RUNNING[pid] = t
        t.start()
    return {"ok": True, "started": True, "action": action, "seg": seg["id"]}


def wait(pid: int, timeout: float = 60.0) -> bool:
    """Chờ luồng nền của dự án xong (test / công cụ). True khi đã xong."""
    t = _RUNNING.get(pid)
    if t is not None:
        t.join(timeout)
    return not running(pid)


def _sync(data_dir: str, pid: int, seg: Dict, action: str, who: Optional[Dict], conn, fn: Callable[[], Dict]) -> Dict:
    """Nút nhanh: chạy ngay, giữ khóa S. Đang có tác vụ nền của dự án / khóa → từ chối có câu."""
    if running(pid):
        return {"ok": False, "errors": [f"đang chạy {_RUNNING[pid].name.split('|', 1)[-1]} của dự án này — chờ xong rồi bấm lại"]}
    try:
        with _Hold(data_dir, pid, seg, action, who, conn):
            return fn()
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}


# ---- quyền (S-B) ------------------------------------------------------------------------------------------------------------
def is_executive_producer(conn, pid: int, user) -> bool:
    """S-B: chỉ Executive Producer duyệt / trả lại sân khấu. EP = người dùng làm chủ: Owner (users.role 'owner') hoặc chủ dự án
    (access level 'admin' / 'own'); đăng nhập TẮT (máy một người, access_user None) = chủ máy. Người chỉ sửa / xem → không."""
    from . import access
    return access.RANK.get(access.level(conn, pid, user), 0) >= access.RANK["own"]


def _need_ep(conn, pid: int, who: Optional[Dict], user, what: str) -> None:
    if (who or {}).get("kind") != "human":
        raise DeskError(f"{what} chỉ do NGƯỜI (Executive Producer) bấm — Director / phiên Claude / công cụ đề xuất, không tự duyệt "
                        "(S-B, sổ v31-ep-stage-desk-actions-2026-10-21)")
    if not is_executive_producer(conn, pid, user):
        raise DeskError(f"{what} chỉ Executive Producer (Owner / chủ dự án) được bấm (S-B)")


# ---- trạng thái -------------------------------------------------------------------------------------------------------------
def _revs(conn, seg: Dict) -> Dict[int, int]:
    from . import write_guard
    out = {}
    for s in seg["shots"]:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (s["id"],)).fetchone()
        try:
            out[s["idx"]] = write_guard.rev(json.loads(row["data"] or "{}") if row else {})
        except ValueError:
            out[s["idx"]] = 0
    return out


def _fingerprint_now(conn, pid: int, data_dir: str, seg: Dict) -> Optional[str]:
    """Vân tay đầu vào HIỆN TẠI khi K1 đã có (không đo Blender); None = chưa biết (chưa có K1 / lỗi đọc)."""
    sa = _sa()
    k1 = sa.k1_cached(seg, sa.base_dir(data_dir, pid, seg["stage"]))
    if not k1:
        return None
    try:
        inputs, _ = sa.inputs_for(conn, pid, seg, k1, sa.stored_state_before(data_dir, pid, seg, conn))
        return sa.fingerprint(inputs)
    except Exception:  # noqa: BLE001 - trạng thái chỉ để xem: không biết thì nói không biết
        return None


def scene_status(conn, pid: int, data_dir: str, scene, seg: Optional[Dict] = None) -> Dict:
    """Một cảnh: đọc thuần crew/state.json + result.json + scenes.data (không Blender, không ghi). `buttons` = nút hợp phase (lõi vẫn
    kiểm lại khi bấm)."""
    from . import stage_crew
    from .camera_plan import drawn_shots
    sa = _sa()
    seg = seg or segment(conn, pid, scene)
    d = seg_dir(data_dir, pid, seg)
    state = _read(os.path.join(d, sa.CREW_DIR, "state.json"))
    result = _read(os.path.join(d, "result.json"))
    phase = (state or {}).get("phase")
    fp = _fingerprint_now(conn, pid, data_dir, seg)
    changed = bool(state and fp and state.get("fp") != fp)
    cams, mine = [], []
    for s in seg["shots"]:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (s["id"],)).fetchone()
        data = json.loads((row["data"] if row else None) or "{}")
        if data.get(sa.FIELD):
            cams.append(s["idx"])
            if data.get(sa.SEG_FIELD) == seg["id"]:
                mine.append(s["idx"])
    sheet = os.path.join(d, "beats", f"san_khau_canh{seg['scene']}.png")
    h = lock_holder(data_dir, pid, seg["scene"], conn, seg=seg)
    pr = progress(data_dir, pid, seg["scene"], conn, seg=seg)
    busy_now = bool(h) or (pr or {}).get("state") == "running"
    user_ok = stage_crew.user_approves()
    has_round = bool(result and result.get("round"))
    btn = ["N2"]
    if not busy_now:
        btn.append("N1")
        if changed:
            btn += ["N8"]                                  # đầu vào đổi: lượt dở không dùng được — chỉ còn Làm lại
        elif phase == "duyet" and user_ok:
            btn += ["N5", "N6", "N7", "N8"]
        elif phase == "xong":
            btn += ["N5", "N8", "N9", "N10", "N11"]
        elif phase is not None:
            btn += ["N3", "N4", "N8"] + (["N5"] if (state or {}).get("measure") else [])
        else:
            btn += ["N3", "N10"] + (["N5", "N9"] if has_round else [])
        if mine and "N11" not in btn:
            btn.append("N11")
    return {"scene": seg["scene"], "seg_id": seg["id"], "stage": seg["stage"], "shots": [s["idx"] for s in seg["shots"]],
            "phase": phase, "label": PHASE_LABEL.get(phase, phase) if not changed else "đầu vào đổi — lượt dở không dùng được",
            "k1": fp is not None, "inputs_changed": changed, "approved_by": (state or {}).get("approved_by"),
            "n_returns": (state or {}).get("n_returns"), "cams": cams, "cams_this_stage": mine,
            "bad": {str(k): v for k, v in ((result or {}).get("bad") or {}).items()}, "round": (result or {}).get("round"),
            "sheet": sheet if os.path.exists(sheet) else None, "drawn": drawn_shots(conn, seg), "revs": _revs(conn, seg),
            "lock": h, "progress": pr, "running": running(pid), "user_approves": user_ok, "buttons": btn,
            "reset": _read(os.path.join(d, RESET_FILE))}


def status(conn, pid: int, data_dir: str) -> List[Dict]:
    return [scene_status(conn, pid, data_dir, g["scene"], seg=g) for g in _sa().segments(conn, pid)]


# ---- N1 … N11 ---------------------------------------------------------------------------------------------------------------
def check_inputs(conn, pid: int, data_dir: str, scene, who: Optional[Dict]) -> Dict:
    """N1 (nền, 0 USD): K1 (Blender ≈ 20 s nếu chưa có) + đầu vào + cổng 0 USD — như `--dry` một cảnh. Không ghi CSDL."""
    sa = _sa()
    seg = segment(conn, pid, scene)

    def work(c, log):
        base = sa.base_dir(data_dir, pid, seg["stage"])
        log("đo / đọc K1")
        k1 = sa.ensure_k1_seg(seg, base, log)
        inputs, missing = sa.inputs_for(c, pid, seg, k1, sa.stored_state_before(data_dir, pid, seg, c))
        with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
            gate = sa.preflight(inputs, json.load(f).get("marks"))
        log("xong: " + ("đủ đầu vào" if not (missing or gate) else f"{len(missing) + len(gate)} vấn đề"))
        return {"ok": True, "missing": missing, "gate": gate, "fingerprint": sa.fingerprint(inputs)}
    return _start(conn, pid, data_dir, seg, "N1", who, work)


def estimate(conn, pid: int, data_dir: str, scene) -> Dict:
    """N2 (0 USD, < 1 s): ước tính Claude của ĐÚNG cảnh này (một đoạn) — số của stage_auto (crew_usd / llm_estimate × LLM_MARGIN), không
    tính tay. Đợt 1 không có nút gọi API: chỉ để xem."""
    from . import cost, stage_crew
    from .stage_director import MAX_ROUNDS, STAGE
    sa = _sa()
    segment(conn, pid, scene)
    if stage_crew.enabled():
        one, worst = sa.crew_usd(conn), sa.crew_usd(conn, worst=True)
        out = {"crew": True, "usd": None if one is None else round(one, 3), "usd_max": None if worst is None else round(worst, 3)}
    else:
        try:
            one = cost.llm_estimate(conn, STAGE, 1)
        except Exception:  # noqa: BLE001 - bảng giá lỗi: nói, không ném
            one = None
        out = {"crew": False, "usd": None if one is None else round(one * cost.LLM_MARGIN, 3),
               "usd_max": None if one is None else round(one * cost.LLM_MARGIN * 2 * MAX_ROUNDS, 3)}
    out["ok"] = True
    if out["usd"] is None:
        out["note"] = "chưa có giá Claude cho model đang dùng (bảng giá)"
    return out


def write_prompt(conn, pid: int, data_dir: str, scene, who: Optional[Dict]) -> Dict:
    """N3 (0 USD): đề bài của vai đang tới lượt → doan_<S>/crew/de_bai_<phase>.md (đường cố định để phiên Claude Code đọc)."""
    sa = _sa()
    seg = segment(conn, pid, scene)

    def fn():
        text, problems, state = sa.crew_prompt(conn, pid, seg, data_dir)
        out = {"ok": bool(text), "phase": state.get("phase"), "problems": problems, "errors": [] if text else problems}
        if text:
            path = os.path.join(seg_dir(data_dir, pid, seg), sa.CREW_DIR, f"de_bai_{state['phase']}.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            out.update(path=path, chars=len(text))
        return out
    return _sync(data_dir, pid, seg, "N3", who, conn, fn)


def load_answer(conn, pid: int, data_dir: str, scene, obj: Dict, who: Optional[Dict]) -> Dict:
    """N4 (nền, 0 USD; đo K3 + K4 khi phase cần): câu trả lời vai → crew_answer(source="claude_code"). Nguồn CỐ ĐỊNH — nút này không
    nhận câu trả lời "người dùng" (duyệt chốt chỉ qua N6 / N7, S-B); phase `duyet` → crew_answer tự từ chối."""
    sa = _sa()
    seg = segment(conn, pid, scene)
    if not isinstance(obj, dict):
        return {"ok": False, "errors": ["câu trả lời phải là một đối tượng JSON"]}
    if "duyet" in obj:
        return {"ok": False, "errors": ["câu trả lời duyệt / trả lại chỉ nhận qua nút ✅ Duyệt / ↩ Trả lại của Executive Producer (S-B)"]}

    def work(c, log):
        log("kiểm câu trả lời + đo (K3 + K4 nếu cần)")
        r = sa.crew_answer(c, pid, seg, data_dir, obj, source=SOURCE_DESK, log=log,
                           who=_tool_who(who, "stage_desk.load_answer"))
        return {k: v for k, v in r.items() if k != "result"}
    return _start(conn, pid, data_dir, seg, "N4", who, work)


def _tool_who(who: Optional[Dict], name: str) -> Dict:
    """Actor ghi máy của nút không phải duyệt: công cụ bàn đạo diễn (người bấm ghi kèm `via`)."""
    from . import write_guard
    return write_guard.actor("tool", name, via=_who_text(who))


def build_sheet(conn, pid: int, data_dir: str, scene, who: Optional[Dict]) -> Dict:
    """N5 (nền, 0 USD): tấm ghép của lượt đang dùng (result.json; chưa có thì lần đo chia vai hiện tại) → doan_<S>/beats/
    san_khau_canh<S>.png (màn XEM đọc). Không ghi CSDL. Như `tools/stage_auto.py --beats`."""
    sa = _sa()
    seg = segment(conn, pid, scene)
    d = seg_dir(data_dir, pid, seg)

    def work(c, log):
        got = sa.result_round(data_dir, pid, seg)
        if got is None:
            st = _read(os.path.join(d, sa.CREW_DIR, "state.json")) or {}
            meas = st.get("full_measure") or st.get("measure")
            got = os.path.join(d, meas) if meas else None
        if got is None or not os.path.isdir(got):
            return {"ok": False, "errors": ["chưa có lượt đã lưu / lần đo nào để dựng tấm ghép"]}
        t = sa.tool()
        notes = []
        if not os.path.exists(os.path.join(got, "top_cut.png")):
            log("cắt mái (Blender)")
            try:
                t.top_cut(got, log=log)
            except Exception as e:  # noqa: BLE001 - vẫn vẽ trên ảnh chưa cắt (như CLI)
                notes.append(f"không cắt được mái ({type(e).__name__}: {e}) — vẽ trên ảnh từ trên thường")
        log("vẽ nhịp + ghép")
        t.draw_beats(got)
        out = os.path.join(d, "beats", f"san_khau_canh{seg['scene']}.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        title = f"#{pid} cảnh {seg['scene']} — {seg['id']} (shot {seg['shots'][0]['idx']}–{seg['shots'][-1]['idx']})"
        path = t.stage_sheet(got, title, out)
        return {"ok": True, "path": path if isinstance(path, str) else out, "notes": notes}
    return _start(conn, pid, data_dir, seg, "N5", who, work)


def approve(conn, pid: int, data_dir: str, scene, who: Optional[Dict], user=None, confirm_drawn: bool = False,
            expected_revs: Optional[Dict] = None) -> Dict:
    """N6 (0 USD): Executive Producer duyệt sân khấu (S-B) → crew_user_verdict(approve=True) (source "nguoi_dung") → máy ghi qua write
    guard với actor người bấm + `expected_revs` (đọc lúc mở lượt duyệt — scene_status["revs"]). Có shot đã vẽ ảnh → cần
    `confirm_drawn` (ảnh shot đó sẽ lệch nền — tương đương --force)."""
    from .camera_plan import drawn_shots
    from . import stage_crew
    sa = _sa()
    seg = segment(conn, pid, scene)
    try:
        _need_ep(conn, pid, who, user, "Duyệt sân khấu")
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}
    if not stage_crew.user_approves():
        return {"ok": False, "errors": ["duyệt chốt do Đạo diễn (cờ stage_crew_user_approve TẮT) — không có bước người duyệt"]}
    drawn = drawn_shots(conn, seg)
    if drawn and not confirm_drawn:
        return {"ok": False, "needs_confirm": drawn,
                "errors": [f"shot {', '.join(map(str, drawn))} đã vẽ ảnh — ảnh sẽ lệch nền 3D mới; xác nhận để vẫn đổi máy"]}

    def fn():
        r = sa.crew_user_verdict(conn, pid, seg, data_dir, approve=True, who=who, expected_revs=expected_revs)
        out = {k: v for k, v in r.items() if k != "result"}
        if r.get("ok"):
            bad = (r.get("result") or {}).get("bad") or {}
            out["bad"] = {str(k): v for k, v in bad.items()}
            _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} DUYỆT sân khấu {seg['id']} — máy shot "
                                    f"{', '.join(map(str, r.get('applied') or [])) or '—'}"
                                    + (f"; dùng máy thường: {', '.join(map(str, sorted(bad)))}" if bad else ""))
        return out
    return _sync(data_dir, pid, seg, "N6", who, conn, fn)


def return_(conn, pid: int, data_dir: str, scene, tra_lai: Sequence[Dict], who: Optional[Dict], user=None) -> Dict:
    """N7 (0 USD): Executive Producer trả lại kèm câu ý đồ từng shot (S-G: người nhập ý đồ, Quay phim chọn số đo). Không ghi CSDL."""
    sa = _sa()
    seg = segment(conn, pid, scene)
    try:
        _need_ep(conn, pid, who, user, "Trả lại sân khấu")
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}

    def fn():
        r = sa.crew_user_verdict(conn, pid, seg, data_dir, approve=False, tra_lai=list(tra_lai or []))
        if r.get("ok"):
            _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} TRẢ LẠI sân khấu {seg['id']} — "
                                    + "; ".join(f"shot {x.get('shot')}: {x.get('y_do')}" for x in tra_lai or [])[:300])
        return {k: v for k, v in r.items() if k != "result"}
    return _sync(data_dir, pid, seg, "N7", who, conn, fn)


def reset_preview(conn, pid: int, data_dir: str, scene, seg: Optional[Dict] = None) -> Dict:
    """S-D: xem trước "Làm lại từ Đạo diễn" — thư mục lượt sẽ cất, máy đã ghi (GIỮ tới khi duyệt lượt mới), tài nguyên phụ thuộc sẽ cũ
    khi lượt mới ghi máy khác (nền 3D, ảnh đã vẽ, world map). Không ghi gì."""
    from .camera_plan import drawn_shots
    sa = _sa()
    seg = seg or segment(conn, pid, scene)
    d = seg_dir(data_dir, pid, seg)
    st = _read(os.path.join(d, sa.CREW_DIR, "state.json"))
    mine = scene_status(conn, pid, data_dir, scene, seg=seg)["cams_this_stage"]
    from . import world_map
    world = world_map.path(data_dir, pid, seg["scene"])
    return {"seg": seg["id"], "archive": os.path.join(d, sa.CREW_DIR) if os.path.isdir(os.path.join(d, sa.CREW_DIR)) else None,
            "phase": (st or {}).get("phase"), "n_answers": len((st or {}).get("history") or []),
            "cams_kept": mine, "plates_stale_after": mine, "images_stale_after": [i for i in drawn_shots(conn, seg) if i in mine],
            "world_map_stale_after": os.path.exists(world),
            "say": ("máy cũ của shot " + ", ".join(map(str, mine)) + " giữ tới khi duyệt lượt mới; khi đó nền 3D (và ảnh đã vẽ) của các shot "
                    "đổi máy thành cũ") if mine else "chưa có máy nào ghi từ sân khấu này"}


def reset(conn, pid: int, data_dir: str, scene, who: Optional[Dict], confirm: bool = False) -> Dict:
    """N8 (0 USD) — S-D: chia vai lại. confirm=False → chỉ trả `preview` (hỏi xác nhận + xem trước); confirm=True → cất crew/ →
    crew_cu_<giờ>/ (không gỡ stage_camera — giữ tới khi duyệt lượt mới) + ghi doan_<S>/desk_reset.json đánh dấu tài nguyên phụ thuộc
    sẽ cũ (shot có máy, ảnh đã vẽ, world map) để màn XEM / lượt duyệt sau nói rõ."""
    sa = _sa()
    seg = segment(conn, pid, scene)
    preview = reset_preview(conn, pid, data_dir, scene, seg=seg)
    if not confirm:
        return {"ok": False, "needs_confirm": True, "preview": preview, "errors": ["cần xác nhận (xem trước thay đổi ở `preview`)"]}

    def fn():
        ctx = {"crew": os.path.join(seg_dir(data_dir, pid, seg), sa.CREW_DIR), "out": seg_dir(data_dir, pid, seg)}
        sa._crew_reset(ctx)
        mark = dict(preview, at=_now(), by=_who_text(who))
        _write(os.path.join(seg_dir(data_dir, pid, seg), RESET_FILE), mark)
        _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} làm lại sân khấu {seg['id']} từ Đạo diễn — {preview['say']}")
        return {"ok": True, "preview": preview}
    return _sync(data_dir, pid, seg, "N8", who, conn, fn)


def rerender(conn, pid: int, data_dir: str, scene, who: Optional[Dict], confirm_drawn: bool = False) -> Dict:
    """N9 (nền, 0 USD; K3 + K4 ≈ 60 s mỗi 4 shot): dựng lại từ câu trả lời đã lưu (stage_auto.rerender — từ chối khi đầu vào đổi);
    máy ghi qua write guard (actor công cụ). Shot đã vẽ ảnh → cần `confirm_drawn` (như CLI --force)."""
    from .camera_plan import drawn_shots
    sa = _sa()
    seg = segment(conn, pid, scene)
    drawn = drawn_shots(conn, seg)
    if drawn and not confirm_drawn:
        return {"ok": False, "needs_confirm": drawn,
                "errors": [f"shot {', '.join(map(str, drawn))} đã vẽ ảnh — máy mới làm ảnh lệch nền; xác nhận để vẫn dựng lại"]}

    def work(c, log):
        r = sa.rerender(c, pid, seg, data_dir, log=log, who=_tool_who(who, "stage_desk.rerender"))
        return dict(r, ok=not r.get("missing"), errors=list(r.get("missing") or []))
    return _start(conn, pid, data_dir, seg, "N9", who, work)


def score(conn, pid: int, data_dir: str, scene, who: Optional[Dict] = None) -> Dict:
    """N10 (0 USD): chấm lại mọi lượt Đạo diễn đã lưu bằng bộ kiểm hiện tại (stage_auto.score_saved). Không ghi CSDL."""
    sa = _sa()
    seg = segment(conn, pid, scene)
    return _sync(data_dir, pid, seg, "N10", who, conn, lambda: dict(sa.score_saved(conn, pid, seg, data_dir), ok=True))


def render_plates(conn, pid: int, data_dir: str, scene, who: Optional[Dict] = None) -> Dict:
    """N11 (0 USD): quên render nền 3D HỎNG của từng shot cảnh (location_pack.forget_shot) rồi place_refs.ensure_async render các nền
    thiếu / cũ của dự án (luồng riêng của place_refs; Blender xếp hàng trong plates3d.render)."""
    from . import location_pack, place_refs
    seg = segment(conn, pid, scene)
    forgot = [s["idx"] for s in seg["shots"] if location_pack.forget_shot(data_dir, pid, s["id"])]
    row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    started = place_refs.ensure_async(conn, pid, data_dir, place_refs.resolution_of(row))
    _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} render lại nền 3D cảnh {seg['scene']}"
                            + (f" (quên render hỏng shot {', '.join(map(str, forgot))})" if forgot else ""))
    out = {"ok": started, "forgot": forgot, "started": started}
    if not started:
        out["errors"] = ["không chạy được luồng render nền (CSDL trong bộ nhớ)"]
    return out


# ---- S-C: cổng trước generation trả phí -------------------------------------------------------------------------------------
def _gate_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "stage", GATE_FILE)


def _gate(data_dir: str, pid: int) -> Dict:
    g = _read(_gate_path(data_dir, pid)) or {}
    return {"required": {str(k): v for k, v in (g.get("required") or {}).items()},
            "exceptions": {str(k): v for k, v in (g.get("exceptions") or {}).items()}}


def require_plate(conn, pid: int, data_dir: str, scene_id: int, on: bool, who: Optional[Dict], user=None) -> Dict:
    """S-C: Executive Producer đánh dấu (on) / bỏ đánh dấu shot BẮT BUỘC có plate 3D đã duyệt làm reference trước gen trả phí."""
    try:
        _need_ep(conn, pid, who, user, "Đặt plate 3D bắt buộc")
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}
    g = _gate(data_dir, pid)
    if on:
        g["required"][str(scene_id)] = {"by": _who_text(who), "at": _now()}
    else:
        g["required"].pop(str(scene_id), None)
        g["exceptions"].pop(str(scene_id), None)
    _write(_gate_path(data_dir, pid), g)
    return {"ok": True}


def allow_exception(conn, pid: int, data_dir: str, scene_id: int, why: str, who: Optional[Dict], user=None) -> Dict:
    """S-C: Executive Producer xác nhận NGOẠI LỆ — shot bắt buộc plate được gen trả phí khi sân khấu chưa duyệt (ghi ai, lúc nào, vì sao)."""
    try:
        _need_ep(conn, pid, who, user, "Xác nhận ngoại lệ plate 3D")
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}
    if not str(why or "").strip():
        return {"ok": False, "errors": ["ngoại lệ cần lý do"]}
    g = _gate(data_dir, pid)
    g["exceptions"][str(scene_id)] = {"by": _who_text(who), "at": _now(), "why": str(why).strip()[:300]}
    _write(_gate_path(data_dir, pid), g)
    _say(conn, pid, "warn", f"Bàn đạo diễn: {_who_text(who)} cho shot (scene_id {scene_id}) gen trả phí khi sân khấu chưa duyệt — {why}",
         scene_id)
    return {"ok": True}


def paid_gate(conn, pid: int, data_dir: str, scene_ids: Sequence[int]) -> List[Dict]:
    """S-C: [{scene_id, idx, level 'warn'|'hold', why}] cho các shot sắp gen TRẢ PHÍ. Mặc định cảnh báo VÀNG khi sân khấu của shot chưa
    chốt (đang chia vai / chờ EP duyệt / đầu vào đổi). Shot EP đã đánh dấu BẮT BUỘC plate 3D đã duyệt mà sân khấu chưa duyệt (chưa
    có máy từ sân khấu đã chốt) và CHƯA có ngoại lệ → 'hold' (giữ trước khi tốn tiền). Không đọc Blender; lỗi đọc → VÀNG có câu."""
    want = {int(x) for x in scene_ids}
    if not want:
        return []
    g = _gate(data_dir, pid)
    out = []
    try:
        segs = _sa().segments(conn, pid)
    except Exception as e:  # noqa: BLE001 - không biết thì nói (VÀNG), không im lặng
        return [{"scene_id": sid, "idx": None, "level": "warn", "why": f"không đọc được sân khấu 3D ({type(e).__name__}: {e})"}
                for sid in sorted(want)]
    for seg in segs:
        hit = [s for s in seg["shots"] if s["id"] in want]
        if not hit:
            continue
        st = scene_status(conn, pid, data_dir, seg["scene"], seg=seg)
        settled = st["phase"] in (None, "xong") and not st["inputs_changed"]
        for s in hit:
            approved = st["phase"] == "xong" and not st["inputs_changed"] and s["idx"] in st["cams_this_stage"]
            if str(s["id"]) in g["required"] and not approved:
                exc = g["exceptions"].get(str(s["id"]))
                if exc:
                    out.append({"scene_id": s["id"], "idx": s["idx"], "level": "warn",
                                "why": f"shot {s['idx']}: plate 3D bắt buộc chưa duyệt — ĐÃ xác nhận ngoại lệ ({exc.get('by')}: {exc.get('why')})"})
                else:
                    out.append({"scene_id": s["id"], "idx": s["idx"], "level": "hold",
                                "why": f"shot {s['idx']}: plate 3D bắt buộc làm reference nhưng sân khấu {seg['id']} chưa duyệt "
                                       f"({st['label']}) — duyệt sân khấu, hoặc Executive Producer xác nhận ngoại lệ trước khi gen trả phí"})
            elif not settled:
                out.append({"scene_id": s["id"], "idx": s["idx"], "level": "warn",
                            "why": f"shot {s['idx']}: sân khấu {seg['id']} chưa chốt ({st['label']}) — ảnh gen bây giờ có thể lệch máy sau "
                                   "khi duyệt"})
    return out
