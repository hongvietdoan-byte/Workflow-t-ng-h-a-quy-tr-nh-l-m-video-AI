import os
from unittest.mock import patch
# Môi trường GIẢ trước import pipeline/provider/loader; không đọc data thật.
with patch.object(os, 'environ', {'PYTHONUTF8': '1', 'FEATURE_MOTION_SFX': '1', 'USERPROFILE': 'C:/qa-step5-fake-home'}):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import sqlite3
    import tempfile
    from pathlib import Path
    from contextlib import contextmanager
    from types import SimpleNamespace
    import streamlit as st
    from dashboard.steps import step5 as S
    from core import features, sfx_plan, motion_sfx_safe

    st.set_page_config(layout='wide', page_title='QA SFX Bước 5 · dữ liệu giả')
    st.title('Bước 5 · Hiệu ứng âm thanh')
    readonly = st.checkbox('QA · chỉ xem', key='qa_readonly')
    if 'qa_dir' not in st.session_state:
        st.session_state.qa_dir = tempfile.mkdtemp(prefix='qa-step5-sfx-')
    directory = st.session_state.qa_dir
    path = Path(directory) / '7' / 'videos' / 'clip.mp4'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists(): path.write_bytes(b'QA clip fixture only')
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
    conn.executescript("CREATE TABLE scenes(id, idx, data, project_id); CREATE TABLE motion_prompts(scene_id, motion_prompt); INSERT INTO scenes VALUES(1, 1, '{}', 7); INSERT INTO motion_prompts VALUES(1, 'She falls.');")
    p = SimpleNamespace(conn=conn, user=None)
    @contextmanager
    def fold(*args, **kwargs):
        with st.expander(args[0], expanded=True): yield True
    def need_edit(*args, **kwargs):
        if readonly:
            from core.access import AccessDenied
            raise AccessDenied('Bạn chỉ được XEM dự án giả.')
    def fake_apply(*args, **kwargs):
        st.session_state.qa_applied = len(args[4])
        return len(args[4])
    def forbidden(*args, **kwargs): raise AssertionError('QA không được gọi provider/Claude')
    sounds = [dict(id=4, heard_label='Thump, thud', name='Va chạm · Kho giả', category='Điểm nhấn')]
    with patch.object(features, 'on', side_effect=lambda name: name == 'motion_sfx' and st.session_state.get('qa_motion_enabled', True)), patch.object(S.C, 'DATA', directory), patch.object(S.ui, 'fold', fold), patch.object(S.sound_lib, 'counts', return_value={'sfx': 1}), patch.object(S.audio_lib, 'load', return_value=[]), patch.object(sfx_plan, 'catalog', return_value=sounds), patch.object(sfx_plan, 'timeline', return_value=[dict(idx=1, title='Cảnh giả', start=0, length=4, text='', mood='', shot='')]), patch.object(sfx_plan.final_cut, 'collect_clips', return_value=[dict(idx=1, path=str(path), requested_sec=4)]), patch('core.clip_measure.motion_series', return_value=([.1, 2, .1], 1, [1, 1, 1])), patch.object(sfx_plan.access, 'need_edit', need_edit), patch.object(sfx_plan.access, 'can_edit', return_value=not readonly), patch.object(motion_sfx_safe, 'atomic_apply', fake_apply), patch.object(S.cost, 'llm_estimate', return_value=0.01), patch.object(S, 'llm_client', forbidden), patch.object(sfx_plan.llm_runner, 'ask_json', forbidden):
        try:
            S.sfx_assistant(p, 7)
        finally:
            conn.close()
    if st.session_state.get('qa_applied'):
        st.success('QA: đã duyệt ' + str(st.session_state.qa_applied) + ' cue qua apply giả; 0 lời gọi trả phí.')
    conn.close()
