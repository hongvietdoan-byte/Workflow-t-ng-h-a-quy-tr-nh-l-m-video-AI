"""Widgets shared by several steps: live polling fragments, dialogue check, export panel."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C



def image_busy(conn, pid: int) -> bool:
    """Something the page should keep watching: a job at the provider, pictures being / waiting to be checked automatically, or an
    automatic fix (retry) that is queued."""
    one = lambda sql: conn.execute(sql, (pid,)).fetchone()[0]                     # noqa: E731
    if one("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='running'"):
        return True
    if autoqc.active(pid) or autoqc.can_run(conn, pid):
        return True
    return bool(conn.execute("SELECT qc_autofix FROM projects WHERE id=?", (pid,)).fetchone()[0]
                and one("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued' AND retry_count>0"))


def _poll_running(pid: int, kind: str) -> None:
    """Ask the provider about this project's submitted jobs (read-only, no credit), start the automatic picture check, send queued automatic
    fixes, and redraw the page when anything changed."""
    conn = connect(C.DB)
    job_type = "image_gen" if kind == "image" else "video_gen"
    busy = image_busy(conn, pid) if kind == "image" else bool(
        conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type=? AND state='running' LIMIT 1", (pid, job_type)).fetchone())
    if not busy:
        st.rerun()                                     # nothing left to watch (finished elsewhere): show the final state
    try:
        provider = factory.image_provider() if kind == "image" else factory.video_provider()
    except ProviderError:
        provider = None
    p = Pipeline(conn)
    counts = {"succeeded": 0, "failed": 0, "retried": 0, "running": 0}
    if provider is not None:
        runner = ImageRunner(p, provider, C.DATA) if kind == "image" else VideoRunner(p, provider, C.DATA)
        try:
            counts = runner.poll_once(pid)
            queued_fix = kind == "image" and p.project(pid)["qc_autofix"] and conn.execute(
                "SELECT 1 FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued' AND retry_count>0 LIMIT 1", (pid,)).fetchone()
            if counts["succeeded"] or counts["failed"] or counts["retried"] or queued_fix:
                runner.submit_pending(pid)             # a slot is free: send the next queued job (the person's, or an automatic fix)
        except InvalidTransition:
            st.rerun()                                 # another tab finished the same job first
        except ProviderError as e:
            st.caption(f"⚠ Chưa hỏi được trạng thái ({e}); sẽ thử lại.")
    if kind == "image" and p.project(pid)["operating_mode"] != "auto":  # "auto" mode already runs its own QC via autopilot; avoid doing it twice
        autoqc.start(C.DB, C.DATA, pid)                    # freshly generated pictures are checked by Claude in the background
        rows = conn.execute("SELECT id, state FROM jobs WHERE project_id=? AND type='image_gen' ORDER BY id", (pid,)).fetchall()
        signature = tuple((r["id"], r["state"]) for r in rows)
        key = f"imgsig_{pid}"
        previous = st.session_state.get(key)
        st.session_state[key] = signature
        if previous is not None and previous != signature:
            st.rerun()                                 # a job changed state (finished, checked, sent again): redraw with it
    if counts["succeeded"] or counts["failed"] or counts["retried"]:
        st.rerun()                                     # a result arrived: redraw the whole page with it
    checking = " · 🔍 đang tự kiểm tra ảnh" if kind == "image" and autoqc.active(pid) else ""
    st.caption(f"🔄 Tự cập nhật mỗi {POLL_SECONDS[kind]} giây · {counts['running']} còn đang chạy{checking} · kiểm tra lúc {time.strftime('%H:%M:%S')}")


@st.fragment(run_every=POLL_SECONDS["image"])
def auto_poll_images(pid: int) -> None:
    _poll_running(pid, "image")


@st.fragment(run_every=POLL_SECONDS["video"])
def auto_poll_videos(pid: int) -> None:
    _poll_running(pid, "video")


# ---- step 3 --------------------------------------------------------------------------
def dialogue_panel(p: Pipeline, pid: int, key: str) -> None:
    """Warn when a scene's dialogue is longer than its clip (cut-off / rushed lines, wasted credit)."""
    entries = dialogue.check(p, pid)
    if not entries:
        return
    bad = dialogue.problems(entries)
    proj = p.project(pid)
    label = f"🗣 Thoại so với độ dài clip — {len(bad)} cảnh cần chú ý" if bad else f"🗣 Thoại so với độ dài clip — {len(entries)} cảnh có thoại, đều vừa"
    with st.expander(label, expanded=bool(bad)):
        if not proj["video_audio"]:
            st.caption("Đang tắt “Model tự tạo âm thanh/lời thoại”: thoại sẽ được lồng tiếng riêng (Bước 5a), độ dài clip chỉ cần đủ cho hình.")
        for e in entries:
            icon = {"ok": "✔", "tight": "◐", "extend": "⚠", "split": "✖"}[e["status"]]
            color = {"ok": "green", "tight": "orange", "extend": "orange", "split": "red"}[e["status"]]
            st.markdown(f":{color}[{icon} S{e['idx']:02d}] {escape(', '.join(e['speakers']))} · {e['syllables']} âm tiết ≈ {e['needed']:g}s "
                        f"/ clip {e['planned']:g}s" + (f" — {escape(e['advice'])}" if e["advice"] else ""))
        fixable = [e for e in bad if e["status"] == "extend"]
        if fixable and st.button(f"⏱ Tự tăng thời lượng {len(fixable)} clip cho vừa thoại", key=f"dlg_fix_{key}_{pid}"):
            dialogue.extend(p, entries)
            st.rerun()
        st.caption("Ước lượng theo tốc độ nói ~3,5 âm tiết/giây (DIALOGUE_SYLLABLES_PER_SEC) cộng 0,5s chừa hơi; chỉ là ước lượng.")


RESIZE_PRESETS = {"Dọc 1080×1920 (TikTok/Reels/Shorts)": (1080, 1920), "Ngang 1920×1080": (1920, 1080),
                  "Ngang 1558×720": (1558, 720), "Vuông 1080×1080": (1080, 1080), "Tự nhập": None}


def resize_panel(pid: int, src: str) -> None:
    """Export a copy at a given size and file-size limit (2-pass encoding), e.g. for upload limits."""
    with st.expander("📐 Xuất bản theo kích thước / dung lượng"):
        st.caption("Tạo thêm một bản của video cuối theo kích thước và dung lượng tối đa bạn cần (tự tính bitrate, mã hóa 2 lượt, "
                   "tự nén lại nếu vượt). Bản gốc không bị đổi.")
        preset = st.selectbox("Kích thước", list(RESIZE_PRESETS), key=f"rs_preset_{pid}")
        size = RESIZE_PRESETS[preset]
        c1, c2, c3 = st.columns(3)
        width = c1.number_input("Rộng", 64, 7680, size[0] if size else 1080, 2, key=f"rs_w_{pid}", disabled=size is not None)
        height = c2.number_input("Cao", 64, 7680, size[1] if size else 1920, 2, key=f"rs_h_{pid}", disabled=size is not None)
        limit = c3.number_input("Dung lượng tối đa (MB, 0 = không giới hạn)", 0.0, 2000.0, 15.0, 1.0, key=f"rs_mb_{pid}")
        if st.button("Xuất bản", key=f"rs_go_{pid}"):
            w, h = size if size else (int(width), int(height))
            dst = os.path.join(project_dir(pid, "output"), f"FINAL_VIDEO_{w}x{h}.mp4")
            try:
                with st.spinner("Đang mã hóa…"):
                    res = ffmpeg_studio.resize_to_size(src, dst, w, h, limit or None)
            except ERRORS as e:
                st.error(str(e))
            else:
                (st.success if res["fits"] else st.warning)(
                    f"Xong: {res['size_mb']:.1f} MB" + ("" if res["fits"] else f" — vẫn vượt {limit:g} MB sau {res['attempts']} lần, thử kích thước nhỏ hơn"))
                with open(dst, "rb") as f:
                    st.download_button(f"⬇ Tải {os.path.basename(dst)}", f, file_name=os.path.basename(dst), mime="video/mp4",
                                       key=f"rs_dl_{pid}")
