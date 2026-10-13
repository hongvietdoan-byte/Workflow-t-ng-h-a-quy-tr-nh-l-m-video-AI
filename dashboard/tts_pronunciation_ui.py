"""Lưu chữ TTS theo giọng; kiểm local chỉ khi người dùng bấm."""
import os
import streamlit as st
from core import access, tts_pronunciation as pron, voice, audio_lib


def render(p, pid, data_dir):
    access.need_view(p, pid, "xem từ điển phát âm")
    editable = access.can_edit(p.conn, pid, getattr(p, "user", None))
    with st.expander("🗣 Sửa phát âm theo giọng"):
        st.caption("Giữ nguyên câu gốc và phụ đề. Lưu miễn phí; tạo lại giọng cần bấm nút TTS và tốn credit.")
        if not editable:
            st.info("Bạn có quyền chỉ xem; cần quyền sửa để lưu hoặc kiểm lại phát âm.")
        for row in p.conn.execute("SELECT name, voice_profile FROM characters WHERE project_id=? ORDER BY name", (pid,)):
            profile = voice.get_profile(row)
            if not profile.get("voice_id"):
                continue
            name = row["name"]
            st.markdown(f"**{name} · giọng {profile['voice_id']}**")
            cfg = profile.get("pronunciation") or {}
            try:
                if not isinstance(cfg, dict):
                    raise ValueError("Từ điển phát âm bị hỏng")
                words = pron.validate(cfg.get("words") or {}) if cfg.get("voice_id") == profile["voice_id"] and cfg.get("model") == voice.vi_model(profile.get("model")) else {}
            except ValueError:
                st.warning("Từ điển phát âm bị hỏng — nhập và lưu lại trước khi tạo giọng.")
                words = {}
            edited = st.data_editor([{"Cụm gốc": k, "Chữ để TTS đọc": v} for k, v in words.items()] or
                                    [{"Cụm gốc": "", "Chữ để TTS đọc": ""}],
                                    num_rows="dynamic", hide_index=True, disabled=not editable,
                                    key=f"tts_pron_words_{pid}_{name}_{profile['voice_id']}_{voice.vi_model(profile.get('model'))}",
                                    column_config={"Cụm gốc": st.column_config.TextColumn("Cụm gốc"),
                                                   "Chữ để TTS đọc": st.column_config.TextColumn("Chữ để TTS đọc")},
                                    width="stretch")
            st.caption("Ví dụ: Trồi Lên → Trờ ôi lên. Cần nghe lại để xác nhận cách đọc.")
            if st.button("Lưu từ điển (0 USD)", key=f"tts_pron_save_{pid}_{name}", disabled=not editable):
                try:
                    pairs = [(r.get("Cụm gốc") or "", r.get("Chữ để TTS đọc") or "") for r in edited]
                    pairs = [(a, b) for a, b in pairs if a.strip() or b.strip()]
                    if len({a.strip().casefold() for a, _ in pairs}) != len(pairs):
                        raise ValueError("Cụm từ bị trùng")
                    pron.save(p, pid, name, dict(pairs))
                    st.success("Đã lưu. Giữ giọng cũ tới khi bạn bấm tạo lại.")
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
        directory = os.path.join(data_dir, str(pid), "audio_assets")
        if st.button("Kiểm lại phát âm (0 USD)", key=f"tts_pron_check_{pid}", disabled=not editable):
            try:
                with st.spinner("Đang kiểm bằng model có sẵn trên máy…"):
                    pron.check(directory, p=p, project_id=pid, force=True)
            except (PermissionError, OSError) as exc:
                st.error(str(exc))
        for entry in audio_lib.load(directory):
            result = entry.get("pronunciation_check") or {}
            if result.get("level") == "yellow":
                st.warning(f"S{entry.get('scene_idx', '?')} · {entry.get('speaker', '')}: {result['message']}")
