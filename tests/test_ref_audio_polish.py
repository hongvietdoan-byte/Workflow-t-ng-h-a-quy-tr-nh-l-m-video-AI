"""Hồi quy nhỏ Đ12v3; dữ liệu/env giả, không load Dashboard/provider."""
import ast
import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
import pytest

@pytest.fixture(autouse=True)
def isolated():
    with patch.object(os,'environ',{'PYTHONUTF8':'1','USERPROFILE':'C:/qa-ref-polish-fake-home','SYSTEMROOT':'C:/Windows','PATH':'C:/Windows/System32'}): yield

def step5_helpers():
    source=(Path(__file__).resolve().parents[1] / 'dashboard' / 'steps' / 'step5.py').read_text(encoding='utf-8-sig')
    tree=ast.parse(source)
    names={'_ref_audio_help','_ref_audio_no_audio_notice'}
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    namespace={'st':SimpleNamespace(session_state={},warning=Mock())}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<fake-step5>','exec'),namespace)
    return namespace

@pytest.mark.parametrize('identity',[{'email':'viewer','role':'member'},{'email':'other','role':'member'}])
def test_propose_denies_before_io(tmp_path,identity):
    from core import ref_audio
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('CREATE TABLE projects(id INT,name TEXT,created_by TEXT); CREATE TABLE project_watchers(project_id INT,email TEXT,level TEXT); INSERT INTO projects VALUES(1,"fake","creator"); INSERT INTO project_watchers VALUES(1,"viewer","view");')
    try:
        p=SimpleNamespace(conn=c,user=identity)
        with patch.object(ref_audio.audio_lib,'assets_dir') as directory,patch.object(ref_audio.ffmpeg_studio,'find_ffmpeg') as ff:
            with pytest.raises(PermissionError): ref_audio.propose(p,str(tmp_path),1)
            directory.assert_not_called();ff.assert_not_called()
    finally:c.close()

def test_no_audio_notice_survives_rerun_and_clears_on_success():
    n=step5_helpers();notice=n['_ref_audio_no_audio_notice'];ui=n['st']
    notice(1,{'no_audio':[2,5]})
    notice(1)
    assert ui.warning.call_count==2
    assert '2, 5' in ui.warning.call_args.args[0]
    notice(2)
    assert ui.warning.call_count==2
    notice(1,{'no_audio':[]})
    notice(1)
    assert ui.warning.call_count==2

def test_sync_help_matches_segment_and_speed_not_legacy_limit():
    n=step5_helpers();help_text=n['_ref_audio_help']
    assert '40 %' not in help_text(True)
    assert 'nguồn gốc' in help_text(True).lower()
    assert 'tốc độ' in help_text(True).lower()
    assert '40 %' in help_text(False)



def test_actual_extras_error_survives_rerun_and_readonly_button_disabled():
    from streamlit.testing.v1 import AppTest
    fixture=Path(__file__).parent / 'fixtures' / 'ref_audio_polish_qa.py'
    app=AppTest.from_file(str(fixture)).run()
    assert not app.exception
    app.checkbox(key='qa_ref_fail').check().run()
    app.button(key='ax_refaudio_1').click().run()
    assert not app.exception and len(app.error)==1
    app.checkbox(key='qa_ref_readonly').check().run()
    assert not app.exception and app.button(key='ax_refaudio_1').disabled


def test_actual_extras_warning_pid_scope_and_sync_fit_caption():
    from streamlit.testing.v1 import AppTest
    fixture=Path(__file__).parent / 'fixtures' / 'ref_audio_polish_qa.py'
    app=AppTest.from_file(str(fixture)).run()
    assert not app.exception
    app.button(key='ax_refaudio_1').click().run()
    assert len(app.warning)==1
    app.run(); assert not app.exception and len(app.warning)==1
    app.selectbox(key='qa_ref_pid').select(2).run()
    assert not app.exception and len(app.warning)==0
    app.selectbox(key='qa_ref_pid').select(1).run()
    assert len(app.warning)==1
    app.checkbox(key='qa_ref_sync').uncheck().run()
    assert not app.exception
