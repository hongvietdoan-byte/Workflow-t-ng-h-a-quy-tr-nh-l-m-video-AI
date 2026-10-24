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
    lock_holder(data_dir, pid, scene, conn, clean=True)     khóa S đang giữ đoạn (clean=False: chỉ đọc, khóa cũ trả {"stale": lý do})
    busy(conn, pid, data_dir) -> [(seg_id, holder)]         mọi đoạn đang bị khóa S của dự án
    cam_mark(stage_camera) -> str|None                      dấu máy một shot (scene_status["marks"]) — UI giữ lúc MỞ màn duyệt
  Giữ khóa S (autopilot `_stage_phase`, CLI tools/stage_auto.py — hai chiều với nút):
    hold_segments(conn, pid, data_dir, segs, action, who)   context manager; đoạn đang bị giữ → DeskError (câu lock_line)

  Nút (mục 4 kế hoạch; `who` = write_guard.actor(...) của người / phiên bấm; mọi nút trả dict có "ok"; lỗi = "errors" [câu]):
    N1 check_inputs(conn, pid, data_dir, scene, who)        nền: K1 (Blender nếu chưa có) + đầu vào + cổng 0 USD
    N2 estimate(conn, pid, data_dir, scene)                 đồng bộ: ước tính Claude của cảnh (chỉ để XEM — Đợt 1 không có nút API)
    N3 write_prompt(conn, pid, data_dir, scene, who)        đồng bộ, khóa S: đề bài vai đang tới lượt → doan_<S>/crew/de_bai_<phase>.md
    N4 load_answer(conn, pid, data_dir, scene, obj, who, user=None)  nền: câu trả lời vai (source cố định "claude_code" — KHÔNG nhận người dùng)
    N5 build_sheet(conn, pid, data_dir, scene, who)         nền: tấm ghép → doan_<S>/beats/san_khau_canh<S>.png (không ghi CSDL)
    N6 approve(conn, pid, data_dir, scene, who, user, confirm_drawn=False, expected_revs=None, expected_marks=None)
                                                            S-B: chỉ EP; `user` = common.access_user() BẮT BUỘC (None chỉ khi đăng
                                                            nhập TẮT); expected_marks = scene_status()["marks"] lúc MỞ màn duyệt
                                                            (máy đổi xen giữa → từ chối); máy ghi qua write guard
    N7 return_(conn, pid, data_dir, scene, tra_lai, who, user)                                   S-B: chỉ EP; không ghi CSDL
    N4 / N8 / N9 / N11 nhận thêm user=common.access_user() (rà kỹ mục 4): có user mà không có quyền SỬA dự án → từ chối; None = như cũ
    N8 reset(conn, pid, data_dir, scene, who, confirm=False)  S-D: confirm=False → chỉ XEM TRƯỚC (preview) thay đổi + phụ thuộc
    N9 rerender(conn, pid, data_dir, scene, who, confirm_drawn=False)   nền: K3 + K4 từ câu trả lời đã lưu; ghi máy qua guard
    N10 score(conn, pid, data_dir, scene)                   đồng bộ, khóa S: chấm lại các lượt đã lưu (không ghi CSDL)
    N11 render_plates(conn, pid, data_dir, scene, who)      quên render nền hỏng của các shot cảnh + place_refs.ensure_async
  S-C (cổng trước gen trả phí — C-FIX6: MỘT hàm paid_hold ở core.runner._submit_pending cho mọi đường gửi trả phí ảnh + video: nút
  Gen ảnh, autopilot, gen video, gửi lại; cùng hàm ở hai đường trả phí theo shot KHÔNG qua runner: core/end_frames (ảnh khung cuối) và
  core/quality_samples (phép thử Seedance + bản cuối từ mẫu). batch.image_gates / tools/pregen_check báo trước bằng paid_gate. Không áp
  dụng: lipsync (ghép môi clip ĐÃ có), scene_establish (ảnh cấp cảnh, không theo shot). Chỉ chạy khi EP đã đánh dấu bắt buộc — chưa
  đánh dấu thì không VÀNG / không giữ, y hệt trước):
    paid_hold(conn, pid, data_dir, scene_ids) -> str|None             lý do GIỮ job trả phí (runner), None = gửi được
    require_plate(conn, pid, data_dir, scene_id, on, who, user)       EP đánh dấu shot BẮT BUỘC có plate 3D đã duyệt làm reference
    allow_exception(conn, pid, data_dir, scene_id, why, who, user)    EP xác nhận ngoại lệ (gen trả phí khi sân khấu chưa duyệt)

Luồng nền: một `threading.Thread` daemon mỗi DỰ ÁN (`_RUNNING[pid]`) mở kết nối sqlite riêng (CSDL :memory: → từ chối, như
place_refs.ensure_async); bấm lại khi còn chạy → "đang chạy …", không luồng thứ hai. Khóa S: tệp doan_<S>/.desk.lock {pid tiến trình, owner,
nút, giờ} — autopilot `_stage_phase` và CLI tools/stage_auto.py gặp khóa thì chờ / từ chối CÓ CÂU; khóa của tiến trình đã chết / quá
LOCK_STALE_SEC → gỡ + báo. Blender xếp hàng sẵn trong stage_grid.run_blender_safe / plates3d.render (plates3d.blender_turn) — ở đây
không khóa Blender lần nữa (khóa tệp không vào lại được). Không bao giờ gán biến môi trường cờ (FEATURE_…): đường chạy tay có
stage_auto.run(manual=True) cho nút API N13 (Đợt 3 — chưa có ở đây). Nút đồng bộ N3 / N6 / N7 / N10 có thể đo K1 (Blender ≈ 20 s) khi K1
chưa có / model đổi — UI nên chạy N1 trước (trạng thái `k1`)."""
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
RESET_STALE_FILE = "desk_reset_stale.json"      # S-D (C-FIX6 mục 5): shot đổi máy / ảnh / world map đã cũ sau lượt duyệt kế một lần làm lại
HOLD_PREFIX = "sân khấu 3D — "                  # đầu câu lý do giữ của paid_hold (autopilot._desk_wait nhận ra lý do runner giữ)
GATE_FILE = "desk_gate.json"                   # <data>/<pid>/stage/desk_gate.json — S-C: shot bắt buộc plate đã duyệt + ngoại lệ
LOCK_STALE_SEC = 3 * 3600                       # một thao tác sân khấu (đo K3 + K4 nhiều shot) không quá chừng này
LOG_KEEP = 50
SOURCE_DESK = "claude_code"                     # N4: câu trả lời vai từ phiên Claude Code / người viết — KHÔNG phải người dùng duyệt

ACTIONS = {
    "N1": "🔍 Kiểm đầu vào", "N2": "💲 Ước tính", "N3": "📝 Đề bài cho phiên Claude Code", "N4": "📥 Nạp câu trả lời vai",
    "N5": "🖼 Dựng tấm ghép", "N6": "✅ Duyệt sân khấu cảnh", "N7": "↩ Trả lại", "N8": "🗑 Làm lại từ Đạo diễn",
    "N9": "🔁 Render lại từ câu trả lời đã lưu", "N10": "🧮 Chấm lại các lượt đã lưu", "N11": "↻ Render lại nền 3D cảnh này",
    "N12": "🎞 Previs one-shot", "N14": "🎯 Chọn lần đo cho shot", "N15": "🗺 Dựng lại world map cảnh",
    "N16": "🏷 Khai họ sân khấu",
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
_HELD: set = set()                              # mã thẻ khóa S đang được giữ TRONG tiến trình này (khóa cùng pid mà thẻ không còn = cũ)
BROKEN_LOCK_SEC = 60                            # tệp khóa rỗng / hỏng (chết giữa tạo và ghi) quá chừng này → coi là cũ


def _pid_alive(pid: int) -> bool:
    from .plates3d import pid_alive
    return pid_alive(pid)


def _lock_path(data_dir: str, pid: int, seg: Dict) -> str:
    return os.path.join(seg_dir(data_dir, pid, seg), LOCK_FILE)


def _stale_why(path: str, h: Optional[Dict]) -> Optional[str]:
    """Lý do khóa S là CŨ (gỡ được), None = còn hiệu lực."""
    if h is None:
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            return None                               # đã biến mất
        return f"tệp khóa hỏng / rỗng quá {BROKEN_LOCK_SEC} giây" if age > BROKEN_LOCK_SEC else None
    age = time.time() - float(h.get("since_ts") or 0)
    lp = int(h.get("pid") or 0)
    if lp == os.getpid() and h.get("token") not in _HELD:
        return "luồng giữ khóa trong Dashboard này đã dừng mà chưa nhả"
    if lp > 0 and lp != os.getpid() and not _pid_alive(lp):
        return f"tiến trình {lp} không còn chạy"
    if age > LOCK_STALE_SEC:
        return f"quá {LOCK_STALE_SEC // 60} phút"
    return None


def _remove_if_same(path: str, judged: Optional[Dict]) -> Optional[bool]:
    """C-FIX6 mục 6: gỡ khóa CŨ nguyên tử — đổi tên sang tệp riêng (os.replace) rồi mới so nội dung với bản đã xét là cũ; khác (tiến
    trình khác vừa gỡ + giữ khóa mới trong khe đọc-xóa) → trả lại chỗ cũ bằng os.link (không đè khóa mới hơn nữa). True = đã gỡ,
    False = tệp đã biến mất trước (người khác gỡ), None = không gỡ (khóa đã đổi / không đổi tên được)."""
    import uuid
    grave = f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.cu"
    try:
        os.replace(path, grave)
    except FileNotFoundError:
        return False
    except OSError:
        return None
    if _read(grave) == judged:
        try:
            os.remove(grave)
        except OSError:
            pass
        return True
    try:
        os.link(grave, path)                        # O_EXCL-like: không đè khóa mới hơn nếu đã có
    except FileExistsError:
        pass
    except OSError:                                 # hệ tệp không có liên kết cứng: Windows rename cũng từ chối khi đã có tệp
        try:
            if not os.path.exists(path):
                os.rename(grave, path)
        except OSError:
            pass
    try:
        os.remove(grave)
    except OSError:
        pass
    return None


def lock_holder(data_dir: str, pid: int, scene, conn=None, seg: Optional[Dict] = None, clean: bool = True) -> Optional[Dict]:
    """Khóa S đang giữ đoạn (dict {pid, owner, action, since, since_ts, token}) hoặc None. Khóa CŨ (tiến trình chết, luồng của chính
    Dashboard đã dừng, tệp hỏng, quá hạn): `clean` → gỡ + báo ⚙ Chẩn đoán; clean=False (vẽ trạng thái — rà 7: không ghi khi vẽ) → trả
    {"stale": lý do, ...} để màn nói, không gỡ."""
    seg = seg or segment(conn, pid, scene)
    path = _lock_path(data_dir, pid, seg)
    if not os.path.exists(path):
        return None
    h = _read(path)
    why = _stale_why(path, h)
    if why is None:
        return h or {"owner": "?", "action": "?", "since": "?"}
    if not clean:
        return dict(h or {}, stale=why)
    gone = _remove_if_same(path, h)
    if gone is None:                                # tệp khóa đã đổi giữa lúc đọc và gỡ (người khác vừa giữ) → không gỡ, coi là đang giữ
        now = _read(path)
        return now or dict(h or {"owner": "?", "action": "?", "since": "?"}, stale=why)
    if not gone:                                    # người khác đã gỡ trước: không báo lần hai
        return None
    if conn is not None:
        _say(conn, pid, "warn", f"Bàn đạo diễn: gỡ khóa thao tác sân khấu {seg['id']} ({(h or {}).get('action')}, "
                                f"{(h or {}).get('owner')}) — {why}; state chia vai giữ nguyên (crew_answer không lưu nửa vời)")
    return None


def busy(conn, pid: int, data_dir: str) -> List[tuple]:
    """[(seg_id, holder)] — đoạn của dự án đang bị khóa S (autopilot `_stage_phase` chờ, CLI từ chối)."""
    out = []
    for g in _sa().segments(conn, pid):
        h = lock_holder(data_dir, pid, g["scene"], conn, seg=g)
        if h:
            out.append((g["id"], h))
    return out


def lock_line(seg_id: str, h: Dict) -> str:
    return (f"đang thao tác sân khấu {seg_id} ({h.get('action')}, {h.get('owner') or 'không rõ người'}, từ {h.get('since')}) — chờ xong "
            "rồi chạy lại")


class _Hold:
    """Khóa S của đoạn: tạo O_EXCL (hai tiến trình không cùng giữ), ghi mã thẻ; nhả chỉ khi tệp vẫn là của MÌNH (rà 6: không xóa khóa
    người khác sau khi khóa mình bị gỡ quá hạn), thử lại vài lần (Windows: tệp đang bị đọc). Đang bị giữ → DeskError có câu.
    Dùng `with` hoặc acquire() / release() (luồng nền: giữ ở luồng gọi, nhả ở luồng nền — không lọt khe giữa kiểm và giữ)."""

    def __init__(self, data_dir: str, pid: int, seg: Dict, action: str, who: Optional[Dict], conn=None):
        self.path = _lock_path(data_dir, pid, seg)
        self.args = (data_dir, pid, seg, action, who, conn)
        self.token = None

    def acquire(self) -> "_Hold":
        data_dir, pid, seg, action, who, conn = self.args
        h = lock_holder(data_dir, pid, seg["scene"], conn, seg=seg)
        if h:
            raise DeskError(lock_line(seg["id"], h))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise DeskError(lock_line(seg["id"], _read(self.path) or {})) from None
        import uuid
        token = uuid.uuid4().hex
        _HELD.add(token)
        try:
            try:
                os.write(fd, json.dumps({"pid": os.getpid(), "token": token, "owner": _who_text(who), "action": action,
                                         "since_ts": time.time(), "since": time.strftime("%Y-%m-%d %H:%M:%S")},
                                        ensure_ascii=False).encode("utf-8"))
            finally:
                os.close(fd)
        except BaseException:                           # C-FIX6 mục 6: ghi khóa lỗi → không để tệp khóa rỗng / thẻ treo
            _HELD.discard(token)
            try:
                os.remove(self.path)
            except OSError:
                pass
            raise
        self.token = token
        return self

    def release(self) -> None:
        if self.token is None:
            return
        _HELD.discard(self.token)
        for _ in range(5):
            h = _read(self.path)
            if h is not None and h.get("token") != self.token:
                break                                   # khóa đã bị gỡ và người khác giữ: không đụng
            try:
                os.remove(self.path)
                break
            except FileNotFoundError:
                break
            except OSError:
                time.sleep(0.2)
        self.token = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()
        return False


class hold_segments:
    """Autopilot / CLI giữ khóa S của các đoạn TRƯỚC khi ghi (rà CAO 2: khóa phải chặn hai chiều — nút gặp autopilot / CLI đang chạy cũng
    từ chối có câu). Đoạn nào đang bị giữ → DeskError (câu như lock_line); các khóa đã lấy được nhả lại."""

    def __init__(self, conn, pid: int, data_dir: str, segs: Sequence[Dict], action: str, who: Optional[Dict]):
        self.holds = [_Hold(data_dir, pid, g, action, who, conn) for g in segs]

    def __enter__(self):
        got = []
        try:
            for h in self.holds:
                got.append(h.acquire())
        except BaseException:                           # C-FIX6 mục 6: mọi lỗi (cả OSError khi ghi khóa) nhả các đoạn đã khóa
            for h in got:
                h.release()
            raise
        return self

    def __exit__(self, *exc):
        for h in self.holds:
            h.release()
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
           work: Callable[[sqlite3.Connection, Callable[[str], None]], Dict], read_only: bool = False) -> Dict:
    """Chạy `work(conn_riêng, log)` trong luồng nền của dự án; khóa S của đoạn GIỮ NGAY ở luồng gọi (rà CAO 2: không có khe giữa kiểm và
    giữ) và nhả ở luồng nền khi xong; ghi tiến độ. Trả {"ok", "started"|"errors"}."""
    db = _db_path(conn)
    if not db:
        return {"ok": False, "errors": ["CSDL trong bộ nhớ — không mở được từ luồng nền (chạy Dashboard với tệp CSDL)"]}
    with _LOCK:
        t = _RUNNING.get(pid)
        if t is not None and t.is_alive():
            pr = _read(_progress_path(data_dir, pid, seg)) or {}
            return {"ok": False, "errors": [f"đang chạy {t.name.split('|', 1)[-1]} của dự án này"
                                            + (f" ({pr.get('step')})" if pr.get("step") else "") + " — chờ xong rồi bấm lại"]}
        hold = _Hold(data_dir, pid, seg, action, who, conn)
        try:
            hold.acquire()
        except DeskError as e:
            return {"ok": False, "errors": [str(e)]}
        name = f"stage_desk_{pid}|{action} {seg['id']}"
        path = _progress_path(data_dir, pid, seg)
        pr = {"action": action, "label": ACTIONS.get(action, action), "seg": seg["id"], "who": _who_text(who), "started": _now(),
              "updated": _now(), "step": "chờ bắt đầu", "log": [], "state": "running", "process": os.getpid(), "thread": name}
        try:
            _write(path, pr)
        except OSError as e:                         # C-FIX6 mục 6: khóa đã giữ → nhả, nói lỗi (không để khóa treo tới khi quá hạn)
            hold.release()
            return {"ok": False, "errors": [f"không ghi được tiến độ ({type(e).__name__}: {e}) — chưa chạy"]}

        def log(msg: str) -> None:
            pr["log"] = (pr["log"] + [str(msg)[:400]])[-LOG_KEEP:]
            pr["step"], pr["updated"] = str(msg)[:200], _now()
            try:
                _write(path, pr)
            except OSError:
                pass

        def run():
            if read_only:
                uri = __import__("pathlib").Path(db).resolve().as_uri() + "?mode=ro"
                c = sqlite3.connect(uri, uri=True, timeout=60)
            else:
                c = sqlite3.connect(db, timeout=60)
            c.row_factory = sqlite3.Row
            try:
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
                hold.release()
                c.close()

        t = threading.Thread(target=run, name=name, daemon=True)
        _RUNNING[pid] = t
        try:
            t.start()
        except Exception:
            hold.release()
            raise
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
    (access level 'admin' / 'own') hoặc người được chủ dự án/Owner cấp EP riêng; đăng nhập TẮT (máy một người, access_user None) = chủ máy.
    Người chỉ sửa / xem → không.
    C-FIX6 mục 6: user None khi đăng nhập BẬT (nơi gọi quên truyền danh tính) KHÔNG phải chủ máy → không phải EP."""
    from . import access
    if user is None and login_on():
        return False
    return access.RANK.get(access.level(conn, pid, user), 0) >= access.RANK["ep"]


def login_on() -> bool:
    """Đăng nhập Dashboard BẬT — cùng luật dashboard/common.auth_on (DASHBOARD_AUTH, mặc định bật)."""
    return os.environ.get("DASHBOARD_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")


def _need_ep(conn, pid: int, who: Optional[Dict], user, what: str) -> None:
    """S-B. `user` = common.access_user() của phiên (BẮT BUỘC truyền — None CHỈ khi đăng nhập TẮT = chủ máy); `who` phải là người và
    trùng email của `user` (rà 3: không để nơi gọi khai actor người mà không có danh tính đăng nhập)."""
    if (who or {}).get("kind") != "human":
        raise DeskError(f"{what} chỉ do NGƯỜI (Executive Producer) bấm — Director / phiên Claude / công cụ đề xuất, không tự duyệt "
                        "(S-B, sổ v31-ep-stage-desk-actions-2026-10-21)")
    from . import access
    if user is None and login_on():
        raise DeskError(f"{what}: không có danh tính đăng nhập (đăng nhập đang BẬT) — Dashboard phải truyền common.access_user() (S-B)")
    u = access.user_of(user)
    if u is not None and str((who or {}).get("who") or "").strip().lower() != (u.get("email") or ""):
        raise DeskError(f"{what}: người bấm ({(who or {}).get('who')}) khác người đăng nhập ({u.get('email')}) (S-B)")
    if not is_executive_producer(conn, pid, user):
        raise DeskError(f"{what} chỉ Executive Producer của dự án (Owner, chủ dự án hoặc người được cấp vai EP) được bấm (S-B)")


def _need_edit(conn, pid: int, user, what: str) -> Optional[Dict]:
    """Rà kỹ C-M48-DESK-UI mục 4: nút GHI (N4 / N8 / N9 / N11) cần quyền SỬA dự án (core/access.py — lõi là chỗ chặn thật, giao diện
    "Chỉ xem" chỉ khóa widget). `user` = common.access_user(); None = hệ thống / CLI / autopilot / đăng nhập TẮT → như cũ (không kiểm).
    Trả dict lỗi {"ok": False, "errors"} hoặc None (được làm)."""
    if user is None:
        return None
    from . import access
    try:
        access.require(conn, pid, user, "edit", what)
    except access.AccessDenied as e:
        return {"ok": False, "errors": [str(e)]}
    return None


# ---- trạng thái -------------------------------------------------------------------------------------------------------------
def cam_mark(cam) -> Optional[str]:
    """Dấu ngắn của `stage_camera` một shot (None = không có máy) — UI giữ dấu lúc MỞ màn duyệt rồi đưa lại cho approve (rà 4: _rev chưa
    tăng ở chế độ SHADOW nên không bắt được ghi xen giữa)."""
    if not cam:
        return None
    import hashlib
    return hashlib.sha1(json.dumps(cam, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def _marks(conn, seg: Dict) -> Dict[int, Optional[str]]:
    """{idx: cam_mark(stage_camera)} hiện tại của các shot đoạn (đọc CSDL, không ghi)."""
    out = {}
    for s in seg["shots"]:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (s["id"],)).fetchone()
        try:
            out[s["idx"]] = cam_mark(json.loads((row["data"] if row else None) or "{}").get(_sa().FIELD))
        except ValueError:
            out[s["idx"]] = None
    return out


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
    fp = _fingerprint_now(conn, pid, data_dir, seg) if state else None          # rà 7: chỉ tính vân tay khi có lượt chia vai để so
    changed = bool(state and fp and state.get("fp") != fp)
    cams, mine, marks = [], [], {}
    for s in seg["shots"]:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (s["id"],)).fetchone()
        data = json.loads((row["data"] if row else None) or "{}")
        marks[s["idx"]] = cam_mark(data.get(sa.FIELD))
        if data.get(sa.FIELD):
            cams.append(s["idx"])
            if data.get(sa.SEG_FIELD) == seg["id"]:
                mine.append(s["idx"])
    sheet = os.path.join(d, "beats", f"san_khau_canh{seg['scene']}.png")
    h = lock_holder(data_dir, pid, seg["scene"], conn, seg=seg, clean=False)   # rà 7: vẽ trạng thái không gỡ khóa / không ghi diag
    pr = progress(data_dir, pid, seg["scene"], conn, seg=seg)
    busy_now = bool(h) or (pr or {}).get("state") == "running"
    user_ok = stage_crew.user_approves()
    has_round = bool(result and result.get("round"))
    shot_hist = {str(k): list(v or []) for k, v in ((state or {}).get("shot_hist") or {}).items()}
    family_suggestions = _sa().family_suggestions(_sa().segments(conn, pid))
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
        if not changed:
            if has_round:
                btn.append("N12")
            if any(shot_hist.values()):
                btn.append("N14")
            from . import world_map
            if world_map.enabled():
                btn.append("N15")
            if family_suggestions:
                btn.append("N16")
    return {"scene": seg["scene"], "seg_id": seg["id"], "stage": seg["stage"], "shots": [s["idx"] for s in seg["shots"]],
            "phase": phase, "label": PHASE_LABEL.get(phase, phase) if not changed else "đầu vào đổi — lượt dở không dùng được",
            "k1": _sa().k1_cached(seg, _sa().base_dir(data_dir, pid, seg["stage"])) is not None, "inputs_changed": changed,
            "inputs_known": bool(state is None or fp is not None), "marks": marks, "approved_by": (state or {}).get("approved_by"),
            "n_returns": (state or {}).get("n_returns"), "cams": cams, "cams_this_stage": mine,
            "bad": {str(k): v for k, v in ((result or {}).get("bad") or {}).items()}, "round": (result or {}).get("round"),
            "sheet": sheet if os.path.exists(sheet) else None, "drawn": drawn_shots(conn, seg), "revs": _revs(conn, seg),
            "lock": h, "progress": pr, "running": running(pid), "user_approves": user_ok, "buttons": btn,
            "shot_hist": shot_hist, "accepted": dict((state or {}).get("accepted") or {}),
            "family_suggestions": family_suggestions,
            "reset": _read(os.path.join(d, RESET_FILE)), "reset_stale": _read(os.path.join(d, RESET_STALE_FILE))}


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


def load_answer(conn, pid: int, data_dir: str, scene, obj: Dict, who: Optional[Dict], user=None) -> Dict:
    """N4 (nền, 0 USD; đo K3 + K4 khi phase cần): câu trả lời vai → crew_answer(source="claude_code"). Nguồn CỐ ĐỊNH — nút này không
    nhận câu trả lời "người dùng" (duyệt chốt chỉ qua N6 / N7, S-B); phase `duyet` → crew_answer tự từ chối."""
    denied = _need_edit(conn, pid, user, "nạp câu trả lời vai sân khấu")
    if denied:
        return denied
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
    """N5 (nền, 0 USD): tấm ghép — lượt chia vai dở / chờ duyệt: ghép từng shot theo lần đo N6 sẽ chốt (crew/xem_ghep, lần đo từng
    shot ghi lên tiêu đề + notes); không có thì lượt đang dùng (result.json) → doan_<S>/beats/
    san_khau_canh<S>.png (màn XEM đọc). Không ghi CSDL. Như `tools/stage_auto.py --beats`."""
    sa = _sa()
    seg = segment(conn, pid, scene)
    d = seg_dir(data_dir, pid, seg)
    output = os.path.join(d, "beats", f"san_khau_canh{seg['scene']}.png")

    def work(c, log):
        # N5 và tools/stage_auto.py dùng cùng renderer + cùng crew_preview, tránh lệch ảnh/nhãn từng shot.
        return sa.render_beats_sheet(data_dir, pid, seg, output, log=log)
    return _start(conn, pid, data_dir, seg, "N5", who, work)


def approve(conn, pid: int, data_dir: str, scene, who: Optional[Dict], user, confirm_drawn: bool = False,
            expected_revs: Optional[Dict] = None, expected_marks: Optional[Dict] = None) -> Dict:
    """N6 (0 USD): Executive Producer duyệt sân khấu (S-B) → crew_user_verdict(approve=True) (source "nguoi_dung") → máy ghi qua write
    guard với actor người bấm + `expected_revs` (đọc lúc mở lượt duyệt — scene_status["revs"]). Có shot đã vẽ ảnh → cần
    `confirm_drawn` (ảnh shot đó sẽ lệch nền — tương đương --force). `expected_marks` = scene_status["marks"] lấy lúc MỞ màn duyệt:
    máy của shot nào đã bị ghi khác từ lúc đó (autopilot / CLI xen giữa) → từ chối, hỏi lại — không ghi lặng."""
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
    def need_confirm():
        drawn = drawn_shots(conn, seg)
        if drawn and not confirm_drawn:
            return {"ok": False, "needs_confirm": drawn,
                    "errors": [f"shot {', '.join(map(str, drawn))} đã vẽ ảnh — ảnh sẽ lệch nền 3D mới; xác nhận để vẫn đổi máy"]}
        return None
    early = need_confirm()                          # hỏi sớm, không chờ khóa
    if early:
        return early

    def fn():
        late = need_confirm()                       # rà kỹ C-FIX6 A3: kiểm lại TRONG khóa S — ảnh vẽ xong lúc chờ khóa không lọt
        if late:
            return late
        if expected_marks is not None:              # C-FIX6 mục 4: kiểm-và-ghi trong CÙNG khóa S (không khe giữa kiểm và ghi)
            now = _marks(conn, seg)
            moved = sorted(i for i in now if (expected_marks.get(i, expected_marks.get(str(i))) != now[i]))
            if moved:
                return {"ok": False, "stale": moved, "errors": [f"máy shot {', '.join(map(str, moved))} đã đổi từ lúc mở màn duyệt (tác vụ "
                                                                "khác vừa ghi) — xem lại rồi duyệt"]}
        r = sa.crew_user_verdict(conn, pid, seg, data_dir, approve=True, who=who, expected_revs=expected_revs)
        out = {k: v for k, v in r.items() if k != "result"}
        if r.get("ok"):
            done = _close_reset(conn, pid, data_dir, seg, who)   # S-D: ghi lại ảnh / nền / world map đã cũ TRƯỚC khi xóa dấu làm lại
            if done is not None:
                out["reset_stale"] = done
            bad = (r.get("result") or {}).get("bad") or {}
            out["bad"] = {str(k): v for k, v in bad.items()}
            _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} DUYỆT sân khấu {seg['id']} — máy shot "
                                    f"{', '.join(map(str, r.get('applied') or [])) or '—'}"
                                    + (f"; dùng máy thường: {', '.join(map(str, sorted(bad)))}" if bad else ""))
        return out
    return _sync(data_dir, pid, seg, "N6", who, conn, fn)


def return_(conn, pid: int, data_dir: str, scene, tra_lai: Sequence[Dict], who: Optional[Dict], user) -> Dict:
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


def _world_path(data_dir: str, pid: int, seg: Dict) -> str:
    """Đường world map của cảnh — cùng đường tệp với hàm path của module bản đồ thế giới, KHÔNG import nó (luật G2-4: map không nằm
    trên đường gen; autopilot import module này)."""
    import re
    return os.path.join(data_dir, str(pid), "world", "scene_" + (re.sub(r"[^0-9A-Za-z]+", "_", str(seg["scene"])).strip("_") or "x")
                        + ".json")


def reset_preview(conn, pid: int, data_dir: str, scene, seg: Optional[Dict] = None) -> Dict:
    """S-D: xem trước "Làm lại từ Đạo diễn" — thư mục lượt sẽ cất, máy đã ghi (GIỮ tới khi duyệt lượt mới). Không ghi gì.
    C-FIX6 mục 5: chưa biết máy lượt mới → KHÔNG đánh dấu shot nào cũ ở đây (`plates_stale_after` / `images_stale_after` rỗng,
    `world_map_stale_after` False); `may_go_stale` = cái CÓ THỂ cũ nếu máy đổi; danh sách thật (chỉ shot ĐỔI máy) tính ở lượt duyệt sau
    so với `marks_before` và ghi vào doan_<S>/desk_reset_stale.json (scene_status["reset_stale"])."""
    from .camera_plan import drawn_shots
    sa = _sa()
    seg = seg or segment(conn, pid, scene)
    d = seg_dir(data_dir, pid, seg)
    st = _read(os.path.join(d, sa.CREW_DIR, "state.json"))
    mine = scene_status(conn, pid, data_dir, scene, seg=seg)["cams_this_stage"]
    world = os.path.exists(_world_path(data_dir, pid, seg))
    return {"seg": seg["id"], "archive": os.path.join(d, sa.CREW_DIR) if os.path.isdir(os.path.join(d, sa.CREW_DIR)) else None,
            "phase": (st or {}).get("phase"), "n_answers": len((st or {}).get("history") or []),
            "cams_kept": mine, "plates_stale_after": [], "images_stale_after": [], "world_map_stale_after": False,
            "may_go_stale": {"plates": mine, "images": [i for i in drawn_shots(conn, seg) if i in mine], "world_map": world},
            "marks_before": {str(k): v for k, v in _marks(conn, seg).items()},
            "say": ("máy cũ của shot " + ", ".join(map(str, mine)) + " giữ tới khi duyệt lượt mới; khi đó CHỈ shot đổi máy có nền 3D (và ảnh "
                    "đã vẽ, world map) thành cũ — danh sách ghi lúc duyệt") if mine else "chưa có máy nào ghi từ sân khấu này"}


def _close_reset(conn, pid: int, data_dir: str, seg: Dict, who: Optional[Dict]) -> Optional[Dict]:
    """S-D, lượt duyệt sau một lần Làm lại (C-FIX6 mục 5): shot ĐỔI máy so với lúc làm lại (marks_before) → nền 3D cũ; ảnh đã vẽ của
    các shot đó cũ; world map cũ khi có shot đổi. GHI danh sách vào desk_reset_stale.json RỒI mới xóa desk_reset.json (không ghi được
    → giữ dấu, báo ⚙). Không có dấu làm lại → None. Chỉ gọi ở N6 (EP duyệt): đường Đạo diễn tự chốt / CLI --crew-approve chưa gọi —
    dấu còn, lần EP duyệt sau so với marks_before lúc làm lại (đúng nghĩa "đổi so với trước khi làm lại")."""
    from .camera_plan import drawn_shots
    d = seg_dir(data_dir, pid, seg)
    path = os.path.join(d, RESET_FILE)
    if not os.path.exists(path):
        return None
    mark = _read(path) or {}
    now = _marks(conn, seg)
    before = mark.get("marks_before")
    if isinstance(before, dict):
        changed = sorted(i for i in now if before.get(str(i)) != now[i])
    else:                                           # dấu cũ (trước C-FIX6) không có dấu máy: như cũ — mọi shot có máy lúc làm lại
        changed = sorted(int(i) for i in (mark.get("cams_kept") or []))
    world = bool(changed) and os.path.exists(_world_path(data_dir, pid, seg))
    rec = {"at": _now(), "by": _who_text(who), "reset_at": mark.get("at"), "reset_by": mark.get("by"), "plates_stale": changed,
           "images_stale": [i for i in drawn_shots(conn, seg) if i in changed], "world_map_stale": world}
    try:
        _write(os.path.join(d, RESET_STALE_FILE), rec)
    except OSError as e:
        _say(conn, pid, "warn", f"Bàn đạo diễn: không ghi được danh sách tài nguyên cũ sau làm lại {seg['id']} ({type(e).__name__}: {e}) — "
                                "giữ dấu làm lại")
        return rec
    try:
        os.remove(path)
    except OSError:
        pass
    if changed:
        _say(conn, pid, "warn", f"Bàn đạo diễn: sau làm lại {seg['id']}, máy đổi ở shot {', '.join(map(str, changed))} — nền 3D cũ"
                                + (f"; ảnh đã vẽ cũ: shot {', '.join(map(str, rec['images_stale']))}" if rec["images_stale"] else "")
                                + ("; world map cảnh cũ" if world else ""))
    return rec


def reset(conn, pid: int, data_dir: str, scene, who: Optional[Dict], confirm: bool = False, user=None) -> Dict:
    """N8 (0 USD) — S-D: chia vai lại. confirm=False → chỉ trả `preview` (hỏi xác nhận + xem trước); confirm=True → cất crew/ →
    crew_cu_<giờ>/ (không gỡ stage_camera — giữ tới khi duyệt lượt mới) + ghi doan_<S>/desk_reset.json đánh dấu tài nguyên phụ thuộc
    sẽ cũ (shot có máy, ảnh đã vẽ, world map) để màn XEM / lượt duyệt sau nói rõ."""
    denied = _need_edit(conn, pid, user, "làm lại sân khấu")
    if denied:
        return denied
    sa = _sa()
    seg = segment(conn, pid, scene)
    preview = reset_preview(conn, pid, data_dir, scene, seg=seg)
    if not confirm:
        return {"ok": False, "needs_confirm": True, "preview": preview, "errors": ["cần xác nhận (xem trước thay đổi ở `preview`)"]}

    def fn():
        ctx = {"crew": os.path.join(seg_dir(data_dir, pid, seg), sa.CREW_DIR), "out": seg_dir(data_dir, pid, seg)}
        sa._crew_reset(ctx)
        mark = dict(preview, marks_before={str(k): v for k, v in _marks(conn, seg).items()}, at=_now(), by=_who_text(who))   # trong khóa
        _write(os.path.join(seg_dir(data_dir, pid, seg), RESET_FILE), mark)
        _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} làm lại sân khấu {seg['id']} từ Đạo diễn — {preview['say']}")
        return {"ok": True, "preview": preview}
    return _sync(data_dir, pid, seg, "N8", who, conn, fn)


def rerender(conn, pid: int, data_dir: str, scene, who: Optional[Dict], confirm_drawn: bool = False, user=None) -> Dict:
    """N9 (nền, 0 USD; K3 + K4 ≈ 60 s mỗi 4 shot): dựng lại từ câu trả lời đã lưu (stage_auto.rerender — từ chối khi đầu vào đổi);
    máy ghi qua write guard (actor công cụ). Shot đã vẽ ảnh → cần `confirm_drawn` (như CLI --force)."""
    from .camera_plan import drawn_shots
    denied = _need_edit(conn, pid, user, "render lại sân khấu")
    if denied:
        return denied
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


def render_plates(conn, pid: int, data_dir: str, scene, who: Optional[Dict] = None, user=None) -> Dict:
    """N11 (0 USD): quên render nền 3D HỎNG của từng shot cảnh (location_pack.forget_shot) rồi place_refs.ensure_async render các nền
    thiếu / cũ của dự án (luồng riêng của place_refs; Blender xếp hàng trong plates3d.render)."""
    from . import location_pack, place_refs
    denied = _need_edit(conn, pid, user, "render lại nền 3D")
    if denied:
        return denied
    seg = segment(conn, pid, scene)

    # C-FIX6 mục 6: giữ khóa S — không quên render khi autopilot / CLI đang ghi máy đoạn này. Giới hạn: render thật chạy ở luồng
    # place_refs SAU khi nhả khóa; máy ghi xen giữa lúc đó được runner bắt bằng location_pack.stale_plates (render lại, 0 USD).
    def fn():
        forgot = [s["idx"] for s in seg["shots"] if location_pack.forget_shot(data_dir, pid, s["id"])]
        row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        started = place_refs.ensure_async(conn, pid, data_dir, place_refs.resolution_of(row))
        _say(conn, pid, "info", f"Bàn đạo diễn: {_who_text(who)} render lại nền 3D cảnh {seg['scene']}"
                                + (f" (quên render hỏng shot {', '.join(map(str, forgot))})" if forgot else ""))
        out = {"ok": started, "forgot": forgot, "started": started}
        if not started:
            out["errors"] = ["không chạy được luồng render nền (CSDL trong bộ nhớ)"]
        return out
    return _sync(data_dir, pid, seg, "N11", who, conn, fn)


def previs(conn, pid: int, data_dir: str, scene, shots=None, opts: Optional[Dict] = None,
           who: Optional[Dict] = None, user=None) -> Dict:
    """N12 (0 USD): chạy previs Blender một lượt trong nền; CSDL mở chỉ đọc, không xóa sản phẩm cũ."""
    denied = _need_edit(conn, pid, user, "chạy previs sân khấu")
    if denied:
        return denied
    sa = _sa()
    seg = segment(conn, pid, scene)
    allowed = {int(s["idx"]) for s in seg.get("shots") or []}
    selected = None if shots is None else {int(s) for s in shots}
    if selected is not None and not selected.issubset(allowed):
        return {"ok": False, "errors": ["có shot được chọn nằm ngoài cảnh này"]}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = os.path.join(seg_dir(data_dir, pid, seg), "previs", stamp)

    def work(c, log):
        from tools import stage_previs
        options = dict(opts or {})
        options["data_dir"] = data_dir
        return stage_previs.run(c, pid, scene, shots=selected, out=out, opts=options, log=log)
    return _start(conn, pid, data_dir, seg, "N12", who, work, read_only=True)


def crew_user_pick(conn, pid: int, data_dir: str, scene, shot, lan_do,
                   who: Optional[Dict] = None, user=None) -> Dict:
    """N14 (0 USD): người dùng chọn một lần đo đã lưu trong `shot_hist`; ghi accepted của đúng shot, không sửa CSDL."""
    denied = _need_edit(conn, pid, user, "chọn lần đo cho shot")
    if denied:
        return denied
    sa = _sa()
    seg = segment(conn, pid, scene)
    shot_key = str(int(shot))

    def fn():
        path = os.path.join(seg_dir(data_dir, pid, seg), sa.CREW_DIR, "state.json")
        state = _read(path)
        if not state:
            return {"ok": False, "errors": ["chưa có state chia vai của cảnh này"]}
        hist = list(((state.get("shot_hist") or {}).get(shot_key) or []))
        if lan_do not in hist:
            return {"ok": False, "errors": [f"shot {shot_key}: lan_do '{lan_do}' không phải một lần đo của shot này "
                                                f"({', '.join(map(str, hist))})"]}
        state.setdefault("accepted", {})[shot_key] = lan_do
        _write(path, state)
        return {"ok": True, "shot": int(shot_key), "lan_do": lan_do}
    return _sync(data_dir, pid, seg, "N14", who, conn, fn)


def refresh_world_map(conn, pid: int, data_dir: str, scene, who: Optional[Dict] = None, user=None) -> Dict:
    """N15 (0 USD): chỉ dựng world map khi cờ `world_map` bật; cờ tắt thì không đọc/ghi gì."""
    from . import world_map
    if not world_map.enabled():
        return {"ok": False, "errors": ["cờ world_map đang tắt"]}
    denied = _need_edit(conn, pid, user, "dựng lại world map cảnh")
    if denied:
        return denied
    sa = _sa()
    seg = segment(conn, pid, scene)

    def fn():
        k1_dir = sa.k1_cached(seg, sa.base_dir(data_dir, pid, seg["stage"]))
        result = world_map.refresh(data_dir, pid, scene, k1_dir=k1_dir, seg_dir=seg_dir(data_dir, pid, seg))
        if result is None:
            return {"ok": False, "errors": ["cờ world_map đang tắt"]}
        return {"ok": True, "kind": result.get("kind"), "why": result.get("why"),
                "path": world_map.path(data_dir, pid, scene), "map_revision": result.get("map_revision")}
    return _sync(data_dir, pid, seg, "N15", who, conn, fn)


def set_family(conn, pid: int, data_dir: str, scene, place_ids: Sequence[int], family: str,
               who: Optional[Dict] = None, user=None) -> Dict:
    """N16 (0 USD): ghi họ sân khấu qua `stage_auto.set_family` sau khi người dùng chọn đủ một gợi ý VÀNG."""
    denied = _need_edit(conn, pid, user, "khai họ sân khấu")
    if denied:
        return denied
    sa = _sa()
    try:
        ids = sorted({int(x) for x in (place_ids or [])})
    except (TypeError, ValueError):
        return {"ok": False, "errors": ["danh sách bối cảnh không hợp lệ"]}
    if len(ids) < 2:
        return {"ok": False, "errors": ["cần chọn ít nhất hai bối cảnh trong cùng một gợi ý VÀNG"]}
    suggestion_ids = {tuple(sorted(g.get("place_ids") or [])) for g in sa.family_suggestions(sa.segments(conn, pid))}
    if tuple(ids) not in suggestion_ids:
        return {"ok": False, "errors": ["các bối cảnh không khớp trọn một gợi ý VÀNG hiện tại — tải lại trạng thái trước khi ghi"]}
    affected = [g for g in sa.segments(conn, pid) if int((g.get("place") or {}).get("id") or -1) in ids]
    if not affected:
        return {"ok": False, "errors": ["không tìm thấy cảnh phụ thuộc các bối cảnh đã chọn"]}
    if running(pid):
        return {"ok": False, "errors": ["dự án đang có thao tác sân khấu — chờ xong rồi khai họ"]}
    try:
        with hold_segments(conn, pid, data_dir, affected, "N16", who):
            sa.set_family(conn, ids, family)
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}
    except (ValueError, sqlite3.Error) as e:
        return {"ok": False, "errors": [str(e)]}
    return {"ok": True, "place_ids": ids, "family": str(family).strip()}


# ---- S-C: cổng trước generation trả phí -------------------------------------------------------------------------------------
def _gate_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "stage", GATE_FILE)


_GATE_LOCK = threading.Lock()                   # đọc-sửa-ghi desk_gate.json trong một tiến trình không mất lần ghi


def _gate(data_dir: str, pid: int) -> Dict:
    g = _read(_gate_path(data_dir, pid)) or {}
    return {"required": {str(k): v for k, v in (g.get("required") or {}).items()},
            "exceptions": {str(k): v for k, v in (g.get("exceptions") or {}).items()}}


def require_plate(conn, pid: int, data_dir: str, scene_id: int, on: bool, who: Optional[Dict], user) -> Dict:
    """S-C: Executive Producer đánh dấu (on) / bỏ đánh dấu shot BẮT BUỘC có plate 3D đã duyệt làm reference trước gen trả phí."""
    try:
        _need_ep(conn, pid, who, user, "Đặt plate 3D bắt buộc")
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}
    with _GATE_LOCK:
        g = _gate(data_dir, pid)
        if on:
            g["required"][str(scene_id)] = {"by": _who_text(who), "at": _now()}
        else:
            g["required"].pop(str(scene_id), None)
            g["exceptions"].pop(str(scene_id), None)
        _write(_gate_path(data_dir, pid), g)
    return {"ok": True}


def allow_exception(conn, pid: int, data_dir: str, scene_id: int, why: str, who: Optional[Dict], user) -> Dict:
    """S-C: Executive Producer xác nhận NGOẠI LỆ — shot bắt buộc plate được gen trả phí khi sân khấu chưa duyệt (ghi ai, lúc nào, vì sao)."""
    try:
        _need_ep(conn, pid, who, user, "Xác nhận ngoại lệ plate 3D")
    except DeskError as e:
        return {"ok": False, "errors": [str(e)]}
    if not str(why or "").strip():
        return {"ok": False, "errors": ["ngoại lệ cần lý do"]}
    with _GATE_LOCK:
        g = _gate(data_dir, pid)
        g["exceptions"][str(scene_id)] = {"by": _who_text(who), "at": _now(), "why": str(why).strip()[:300]}
        _write(_gate_path(data_dir, pid), g)
    _say(conn, pid, "warn", f"Bàn đạo diễn: {_who_text(who)} cho shot (scene_id {scene_id}) gen trả phí khi sân khấu chưa duyệt — {why}",
         scene_id)
    return {"ok": True}


def _plate_ready(conn, pid: int, data_dir: str, scene_id: int) -> Optional[str]:
    """None khi shot đã có nền 3D render XONG và không cũ so với máy hiện tại; ngược lại là lý do (rà 5: vừa duyệt máy mới thì nền cũ
    đã lệch — chưa phải 'plate đã duyệt')."""
    from . import location_pack, place_refs
    if location_pack.plate_of(data_dir, pid, scene_id) is None:
        return "nền 3D theo máy đã duyệt chưa render (↻ Render lại nền 3D cảnh này)"
    try:
        row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        old = location_pack.stale_plate(conn, pid, data_dir, scene_id, place_refs.resolution_of(row))
    except Exception as e:  # noqa: BLE001 - không so được = chưa chắc: giữ (luật S-C), có câu
        return f"không so được nền 3D với máy ({type(e).__name__}: {e})"
    return (old.get("why") or "nền 3D cũ so với máy hiện tại") if old else None


def paid_gate(conn, pid: int, data_dir: str, scene_ids: Sequence[int]) -> List[Dict]:
    """S-C: [{scene_id, idx, level 'warn'|'hold', why}] cho các shot sắp gen TRẢ PHÍ. Mặc định cảnh báo VÀNG khi sân khấu của shot chưa
    chốt (đang chia vai / chờ EP duyệt / đầu vào đổi / chưa biết). Shot Executive Producer đã đánh dấu BẮT BUỘC plate 3D đã duyệt làm
    reference chỉ qua khi ĐỦ: sân khấu chốt và do NGƯỜI duyệt (approved_by nguoi_dung — S-B; đường không chia vai / Đạo diễn tự chốt
    không có bước EP duyệt), shot có máy từ sân khấu đó, nền 3D theo máy đó đã render và không cũ; thiếu một điều và CHƯA có ngoại lệ
    → 'hold' (giữ trước khi tốn tiền). Không chạy Blender; lỗi đọc → VÀNG có câu.
    C-FIX6 mục 3 (không thêm cờ — catalog khóa): cổng chỉ chạy khi dữ liệu rõ — EP ĐÃ đánh dấu ít nhất một shot bắt buộc trong dự án
    (desk_gate.json `required`). Chưa đánh dấu (kể cả có thư mục sân khấu, crew/state.json dở) → [] và không đọc sân khấu: y hệt trước."""
    want = {int(x) for x in scene_ids}
    if not want or not os.path.isfile(_gate_path(data_dir, pid)):
        return []
    if _read(_gate_path(data_dir, pid)) is None:    # tệp EP đánh dấu có mà hỏng: không đoán là "không bắt buộc" — giữ, có câu
        return [{"scene_id": sid, "idx": None, "level": "hold",
                 "why": f"không đọc được {GATE_FILE} (danh sách plate 3D bắt buộc của Executive Producer) — sửa / đánh dấu lại trước khi "
                        "gen trả phí"} for sid in sorted(want)]
    g = _gate(data_dir, pid)
    if not g["required"]:
        return []
    out = []
    try:
        segs = _sa().segments(conn, pid)
    except Exception as e:  # noqa: BLE001 - không biết thì nói; shot EP bắt buộc → GIỮ (rà C-FIX6: lỗi đọc không mở cổng)
        return [{"scene_id": sid, "idx": None, "level": "hold" if str(sid) in g["required"] else "warn",
                 "why": f"không đọc được sân khấu 3D ({type(e).__name__}: {e})"
                        + (" — shot có plate 3D bắt buộc: giữ trước khi gen trả phí" if str(sid) in g["required"] else "")}
                for sid in sorted(want)]
    seen = {s["id"] for seg in segs for s in seg["shots"]}
    for sid in sorted(want - seen):                 # rà C-FIX6: shot bắt buộc mà không thuộc sân khấu nào → không im lặng cho qua
        if str(sid) in g["required"] and str(sid) not in g["exceptions"]:
            out.append({"scene_id": sid, "idx": None, "level": "hold",
                        "why": f"shot (scene_id {sid}) có plate 3D bắt buộc nhưng không thuộc sân khấu 3D nào — bỏ đánh dấu hoặc xếp shot "
                               "vào bối cảnh 3D, hoặc Executive Producer xác nhận ngoại lệ"})
    for seg in segs:
        hit = [s for s in seg["shots"] if s["id"] in want]
        if not hit:
            continue
        st = scene_status(conn, pid, data_dir, seg["scene"], seg=seg)
        settled = st["phase"] in (None, "xong") and not st["inputs_changed"] and st["inputs_known"]
        by_person = st["phase"] == "xong" and st["approved_by"] == "nguoi_dung" and not st["inputs_changed"] and st["inputs_known"]
        for s in hit:
            if str(s["id"]) in g["required"]:
                if not by_person:
                    why = (f"sân khấu {seg['id']} chưa được Executive Producer duyệt ({st['label']}"
                           + ("; đường không chia vai / Đạo diễn tự chốt — không có bước EP duyệt" if st["phase"] in (None, "xong") else "")
                           + ")")
                elif s["idx"] not in st["cams_this_stage"]:
                    why = f"shot không có máy từ sân khấu {seg['id']} đã duyệt (dùng máy thường)"
                else:
                    why = _plate_ready(conn, pid, data_dir, s["id"])
                if why is None:
                    continue
                exc = g["exceptions"].get(str(s["id"]))
                if exc:
                    out.append({"scene_id": s["id"], "idx": s["idx"], "level": "warn",
                                "why": f"shot {s['idx']}: plate 3D bắt buộc chưa đạt ({why}) — ĐÃ xác nhận ngoại lệ ({exc.get('by')}: "
                                       f"{exc.get('why')})"})
                else:
                    out.append({"scene_id": s["id"], "idx": s["idx"], "level": "hold",
                                "why": f"shot {s['idx']}: plate 3D bắt buộc làm reference chưa đạt — {why}; duyệt / render xong, hoặc "
                                       "Executive Producer xác nhận ngoại lệ trước khi gen trả phí"})
            elif not settled:
                out.append({"scene_id": s["id"], "idx": s["idx"], "level": "warn",
                            "why": f"shot {s['idx']}: sân khấu {seg['id']} chưa chốt ({st['label'] if st['inputs_known'] else 'chưa biết đầu vào'})"
                                   " — ảnh gen bây giờ có thể lệch máy sau khi duyệt"})
    return out


def paid_hold(conn, pid: int, data_dir: Optional[str], scene_ids: Sequence[int]) -> Optional[str]:
    """S-C — MỘT cổng cho MỌI đường gửi trả phí ảnh + video (C-FIX6 mục 1): core.runner._Runner._submit_pending gọi trước bước tốn tiền,
    nên nút Gen ảnh, autopilot (_images_phase / _videos_phase), gen video, gửi lại / gen lại đều đi qua đây. Câu lý do khi có shot
    'hold' (paid_gate), None = được gửi. Chưa có shot nào EP đánh dấu bắt buộc → None ngay (chỉ một os.path.isfile). Lỗi đọc → giữ có
    câu (cổng EP đã bật thì không im lặng cho qua)."""
    if not data_dir or not scene_ids or not os.path.isfile(_gate_path(data_dir, pid)):
        return None
    try:
        held = [it["why"] for it in paid_gate(conn, pid, data_dir, scene_ids) if it["level"] == "hold"]
    except Exception as e:  # noqa: BLE001 - EP đã đánh dấu bắt buộc: không kiểm được = giữ, có câu
        return f"{HOLD_PREFIX}không kiểm được cổng plate 3D bắt buộc (S-C): {type(e).__name__}: {e}"
    return (HOLD_PREFIX + "; ".join(held)) if held else None
