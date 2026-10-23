"""M8.0c: lô gửi tay xem trước đúng tập, tổng giá, xác nhận và hoàn tác 30 giây.
Không lưu provider/connection/callback trong session; dispatcher chỉ nhận action allowlist.
"""
import hashlib
import json
import streamlit as st
from dashboard import paid_confirm as P


def fingerprint(p, pid, action, data_dir):
    """Chỉ lưu hash đầu vào; mọi thay đổi dự án/job/thoại trong lúc chờ đều dừng lô."""
    out = {}
    for table in ("projects", "scenes", "characters", "jobs"):
        where = "id" if table == "projects" else "project_id"
        out[table] = [dict(r) for r in p.conn.execute(f"SELECT * FROM {table} WHERE {where}=? ORDER BY id", (pid,))]
    out["motion"] = [dict(r) for r in p.conn.execute(
        "SELECT m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=? ORDER BY s.id", (pid,))]
    if action == "voice":
        from core import voice, audio_lib
        out["audio"] = audio_lib.load(audio_lib.assets_dir(data_dir, pid))
        out["lines"] = voice.planned_lines(p.conn, pid)
    if action == "music":
        from core import music
        drafts, _ = music.project_dirs(data_dir, pid)
        out["drafts"] = music.load_drafts(drafts)
    raw = json.dumps(out, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def voice_items(conn, pid, data_dir):
    """Đúng các câu 🎙 sẽ gửi TTS — từ chính vòng lọc của voice.generate (plan_only), không tính song song (rà M8.0c)."""
    from core import voice
    plan = voice.generate(conn, pid, None, data_dir, by_person=True, plan_only=True)["plan"]
    return [f"S{ln['idx']:02d} · {ln.get('speaker') or 'chưa rõ vai'} · {'câu mới' if ln['new'] else 'đọc lại (đổi/lỗi/tốc độ)'}: "
            f"{ln['text']}" for ln in plan]


def paid_batch_button(label, key, tag, container=None, *, p, pid, action, items, preview=None, params=None, **kwargs):
    """True chỉ nhánh OFF để caller chạy nguyên code cũ. ON luôn hẹn, không chạy caller."""
    if not P.enabled():
        return P.paid_button(label, key=key, tag=tag, container=container, **kwargs)
    from dashboard import common as C
    ss, box = st.session_state, container if container is not None else st
    items, params = list(items), dict(params or {})
    fp = fingerprint(p, pid, action, C.DATA)
    payload = {"fp": fp, "items": items, "params": params, "tag": tag}
    saved_key = f"paid_batch_snapshot_{key}"
    if ss.get(saved_key) != payload:
        ss.pop(f"paid_ask_{key}", None)
        ss[saved_key] = payload
    if ss.get(f"paid_ask_{key}"):
        box.markdown("**Xem trước lô sẽ gửi:**")
        for item in list(preview or items):
            box.caption(str(item))
        box.caption(f"Tổng {len(items)} mục{tag or ' · chưa có giá'}")
    if P.paid_button(label, key=key, tag=tag, container=box, **kwargs):
        same = [it for it in P.pending(ss, pid) if it["action"] == "paid_batch" and it.get("batch_action") == action]
        if same and (same[0].get("items"), same[0].get("params")) != (items, params):
            # rà M8.0c: lô cùng loại đang chờ hoàn tác → KHÔNG thay im lặng; nói rõ, người dùng hoàn tác lô cũ rồi bấm lại
            ss["_paid_undo_note"] = f"Chưa hẹn lô mới “{label.strip()}”: lô cùng loại đang chờ hoàn tác — bấm ↩ Hoàn tác rồi xác nhận lại."
            ss.pop(saved_key, None)
            st.rerun()
        P.schedule(ss, "paid_batch", pid, label, tag, actor=p.actor, user=C.access_user(),
                   batch_action=action, items=items, params=params, fp=fp, data_dir=C.DATA,
                   event="hen_gui_lo", page="storyboard", done="Đã xử lý lô")
        ss.pop(saved_key, None)
        st.rerun()
    return False


def run(p, it):
    from core import access, batch, music, voice
    from dashboard import common as C
    pid, action, data_dir = it["pid"], it["batch_action"], it["data_dir"]
    if action not in {"retry_images", "retry_videos", "stale_videos", "voice", "music"}:
        return "Không gửi: loại lô không được phép."
    access.need_edit(p, pid, "gửi lô đã xác nhận")
    if fingerprint(p, pid, action, data_dir) != it["fp"]:
        return "Không gửi: đầu vào hoặc trạng thái lô đã đổi trong lúc chờ hoàn tác — xem lại và xác nhận lại."
    if action.startswith("retry_"):
        kind = "image_gen" if action == "retry_images" else "video_gen"
        ids = batch.provider_failures(p, pid, kind)
        if ids != it["items"]:
            return "Không gửi: danh sách job lỗi đã đổi."
        for jid in ids:
            p.retry(jid, "gửi lại lỗi nhà cung cấp (lô đã xác nhận)", by_user=True)
        if kind == "video_gen":
            runner = C.video_runner(p)
            if runner is None:
                return "Đã xếp hàng nhưng chưa gửi: chưa cấu hình nhà cung cấp video."
            runner.submit_pending(pid)
    elif action == "stale_videos":
        ids = [r["id"] for r in batch.input_failures(p, pid)]
        if ids != it["items"]:
            return "Không gửi: danh sách job cũ đã đổi."
        result = batch.requeue_input_failures(p, pid)
        if result.get("created"):
            runner = C.video_runner(p)
            if runner is None:
                return "Đã xếp hàng nhưng chưa gửi: chưa cấu hình nhà cung cấp video."
            runner.submit_pending(pid)
    else:
        a = it["params"]
        if action == "music":
            keys = a.get("session_keys") or {}
            settings = a.get("settings") or {}
            # ô đã rời màn (đổi bước) thì Streamlit xóa khóa → không coi là "đã đổi"; ô còn trên màn mà khác → dừng
            if any(key in st.session_state and st.session_state[key] != settings.get(name) for name, key in keys.items()):
                return "Không tạo nhạc: brief hoặc số bản đã đổi trong lúc chờ hoàn tác — xem lại và xác nhận lại."
        provider = music.audio_provider()
        if provider is None:
            return "Không gửi: chưa cấu hình nhà cung cấp âm thanh."
        if action == "voice":
            from core import audio_lib, voice_check
            voice_check.settle_redos(audio_lib.assets_dir(data_dir, pid))     # như generate(settle=True), làm TRƯỚC khi so danh sách
            if voice_items(p.conn, pid, data_dir) != it["items"]:
                return "Không gửi: danh sách câu sẽ tạo giọng đã đổi — xem lại và xác nhận lại."
            voice.generate(p.conn, pid, provider, data_dir, by_person=True, p=p, settle=False)
            return ""
        drafts, _ = music.project_dirs(data_dir, pid)
        music.submit_drafts(provider, drafts, a["prompt"], a["length_ms"], a["instrumental"], a["count"],
                            ledger=(p.conn, pid), p=p, project_id=pid)
    return ""
