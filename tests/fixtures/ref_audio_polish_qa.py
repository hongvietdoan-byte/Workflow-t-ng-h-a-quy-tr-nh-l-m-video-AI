"""QA actual extras_section, DB/env/manifest giả, không gọi provider/ffmpeg."""
import os
from unittest.mock import patch
with patch.object(os,'environ',{'PYTHONUTF8':'1','USERPROFILE':'C:/qa-ref-polish-fake-home','SYSTEMROOT':'C:/Windows','PATH':'C:/Windows/System32'}):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    from contextlib import ExitStack
    from types import ModuleType
    with ExitStack() as isolation:
        def forbidden(*args,**kwargs): raise AssertionError('QA không được đọc credentials/registry hoặc gọi provider/model/ffmpeg.')
        for name in ('winreg','keyring'):
            present=name in sys.modules
            previous=sys.modules.get(name)
            def restore(module=name,old=previous,had=present):
                if had: sys.modules[module]=old
                else: sys.modules.pop(module,None)
            isolation.callback(restore)
            fake=ModuleType(name)
            if name=='winreg':
                fake.HKEY_CURRENT_USER=1; fake.OpenKey=forbidden; fake.QueryValueEx=forbidden
            else:
                fake.get_password=forbidden; fake.get_credential=forbidden; fake.set_password=forbidden
            sys.modules[name]=fake
        # Imports modules pure dưới env/registry giả, patch loaders trước dashboard.common.
        from core.adapters import factory
        from core import model_router,voice,auth
        for module,method in ((factory,'video_provider'),(factory,'image_provider'),(factory,'subject_library'),(model_router,'load_profiles'),(voice,'library'),(auth,'identity'),(auth,'owner_remote_check')):
            isolation.enter_context(patch.object(module,method,forbidden))
        import sqlite3,tempfile
        from types import SimpleNamespace
        import streamlit as st
        from dashboard.steps import step5 as S
        from core import ref_audio,access,features
        st.set_page_config(layout='wide',page_title='QA tiếng ref · Bước 5')
        st.title('Bước 5 · Lấy tiếng video tham chiếu')
        st.caption('QA component extras_section thật · chỉ dữ liệu giả · 0 USD')
        controls=st.columns(3)
        pid=controls[0].selectbox('Dự án giả',[1,2],key='qa_ref_pid')
        sync=controls[1].checkbox('QA · nguồn gốc + đoạn + tốc độ',True,key='qa_ref_sync')
        readonly=controls[2].checkbox('QA · chỉ xem',key='qa_ref_readonly')
        fail=st.checkbox('QA · lỗi probe giả',key='qa_ref_fail')
        if 'qa_ref_directory' not in st.session_state:
            st.session_state.qa_ref_directory=tempfile.mkdtemp(prefix='qa-ref-polish-')
        directory=st.session_state.qa_ref_directory
        conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
        conn.executescript("CREATE TABLE projects(id,name,created_by); INSERT INTO projects VALUES(1,'QA A','creator'),(2,'QA B','creator'); CREATE TABLE project_watchers(project_id,email,level); INSERT INTO project_watchers VALUES(1,'viewer','view'),(2,'viewer','view'); CREATE TABLE scenes(id,idx,project_id); INSERT INTO scenes VALUES(2,2,1),(5,5,1),(9,9,2); CREATE TABLE motion_prompts(scene_id,ref_video_path); INSERT INTO motion_prompts VALUES(2,'fake-ref-a'),(5,'fake-ref-b'),(9,'fake-ref-c');")
        p=SimpleNamespace(conn=conn,user={'email':'viewer' if readonly else 'creator','role':'member'})
        def forbidden(*args,**kwargs): raise AssertionError('QA không được gọi provider/model/ffmpeg hoặc ghi dữ liệu.')
        def propose(*args,**kwargs):
            access.need_edit(p,pid,'đề xuất tiếng video tham chiếu')
            if fail: raise ValueError('VÀNG: lỗi probe giả; chưa tách tiếng.')
            return dict(added=[],no_audio=[2,5] if pid==1 else [9],missing=[],already=[],failed=[],removed=[],stale_used=[])
        entries=[dict(kind='sound_effect',label='QA ref · legacy',state='succeeded',source='ref_video',file=None,use=False,start=0,volume=.5,fit_file='legacy_fit.wav',fit_tempo=1.2),
                 dict(kind='sound_effect',label='QA ref · nguồn gốc',state='succeeded',source='ref_video',file=None,use=False,start=0,volume=.5,fit_file='sync.wav',ref_audio_metadata=dict(source_path='QA fake only',start=0,end=1,speed=.5))]
        try:
            with patch.object(S.C,'access_user',return_value=p.user),patch.object(S.C,'DATA',directory),patch.object(S.audio_lib,'assets_dir',return_value=directory),patch.object(S.audio_lib,'overlapping_tts',return_value=[]),patch.object(S.audio_lib,'load',return_value=entries),patch.object(S.audio_lib,'set_mix',forbidden),patch.object(S.audio_lib,'remove',forbidden),patch.object(S.trash,'move_to_trash',forbidden),patch.object(ref_audio,'propose',propose),patch.object(ref_audio.ffmpeg_studio,'find_ffmpeg',forbidden),patch.object(features,'on',side_effect=lambda name:name=='ref_audio_sync' and sync),patch.object(S.music,'audio_provider',forbidden),patch.object(S.factory,'video_provider',forbidden),patch.object(S.factory,'image_provider',forbidden),patch.object(S.factory,'subject_library',forbidden),patch.object(S.voice,'library',forbidden),patch.object(S.model_router,'load_profiles',forbidden),patch.object(S.C,'llm_client',forbidden):
                S.extras_section(p,pid,None)
        finally: conn.close()
