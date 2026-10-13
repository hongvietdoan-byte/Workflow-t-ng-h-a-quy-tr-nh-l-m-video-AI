import pytest
from core import tts_pronunciation as pron

def test_replacement_is_single_pass_and_preserves_accents():
    assert pron.apply("Trồi Lên! Trồi Lênh.", {"Trồi Lên": "Trờ ôi lên", "Trờ ôi": "sai"}) == "Trờ ôi lên! Trồi Lênh."

def test_plain_text_only():
    with pytest.raises(ValueError):
        pron.validate({"Trồi": "<phoneme>tr</phoneme>"})

def test_scope_and_unrelated_cache():
    p = {"voice_id": 70, "pronunciation": {"voice_id": 70, "model": "eleven_v3", "words": {"Trồi": "Trờ ôi"}}}
    assert pron.prepare("Trồi", p, "eleven_v3")[0] == "Trờ ôi"
    assert pron.prepare("Trồi", p, "eleven_flash_v2_5")[0] == "Trồi"
    first = pron.prepare("Xin chào", p, "eleven_v3")[1]
    p["pronunciation"]["words"]["khác"] = "khác nữa"
    assert pron.prepare("Xin chào", p, "eleven_v3")[1]["key"] == first["key"]


from unittest.mock import patch
import json
from core import audio_lib, voice
from core.db import connect
from core.pipeline import Pipeline


def setup_project():
    p = Pipeline(connect())
    pid = p.create_project("fixture")
    sid = p.create_scene(pid, 1, "Cảnh")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"dialogue": [{"speaker": "Kelly", "text": "Trồi Lên!"}]}), sid))
    p.conn.execute("INSERT INTO characters(project_id,name,description) VALUES (?,?,?)", (pid,"Kelly","fixture"))
    voice.set_profile(p.conn,pid,"Kelly",{"voice_id":70,"model":"eleven_v3"})
    return p, pid


class Tts:
    def __init__(self): self.calls = []
    def generate_tts(self, text, *args, **kwargs):
        self.calls.append(text)
        return str(len(self.calls))


def finish(directory):
    items = audio_lib.load(directory)
    for e in items:
        if e["state"] == "running": e["state"] = "succeeded"
    audio_lib._save(directory, items)


def test_generate_legacy_toggle_and_explicit_changed_input(tmp_path):
    p, pid = setup_project()
    provider = Tts()
    directory = audio_lib.assets_dir(str(tmp_path),pid)
    with patch("core.features.on", return_value=False):
        voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False)
    finish(directory)
    pron.save(p,pid,"Kelly",{"Trồi Lên":"Trờ ôi lên"})
    with patch("core.features.on", side_effect=lambda f:f == "tts_pronunciation"):
        r = voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False)
        assert r["held"] and provider.calls == ["Trồi Lên!"]
        voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False,by_person=True)
        assert provider.calls == ["Trồi Lên!","Trờ ôi lên!"]
        finish(directory)
        from core import voice_check
        voice_check.settle_redos(directory)
        pron.save(p,pid,"Kelly",{"Trồi Lên":"Trờ ôi lên","khác":"khác nữa"})
        assert voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False,by_person=True)["sent"] == 0
    with patch("core.features.on", return_value=False):
        assert voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False,by_person=True)["sent"] == 0
    entry = audio_lib.load(directory)[0]
    assert entry["text"] == "Trồi Lên!"
    assert entry["pronunciation"]["sent_text"] == "Trờ ôi lên!"


def test_asr_original_text_yellow_and_unavailable(tmp_path):
    directory = str(tmp_path)
    import wave
    with wave.open(str(tmp_path/"voice.wav"), "wb") as wav:
        wav.setparams((1,2,16000,16000,"NONE","not compressed"))
        wav.writeframes(b"\x00\x00" * 16000)
    audio_lib._save(directory,[{"kind":"tts","state":"succeeded","file":"voice.wav","text":"Trồi Lên", "pronunciation":{"key":"a"}}])
    pron.check(directory, asr=lambda path:"Gồi lên")
    assert audio_lib.load(directory)[0]["pronunciation_check"]["level"] == "yellow"
    (tmp_path/"voice.wav").write_bytes(b"changed")
    pron.check(directory, asr=lambda path:None)
    assert "ASR/model local" in audio_lib.load(directory)[0]["pronunciation_check"]["message"]


def test_dictionary_writer_denies_before_mutation():
    p,pid = setup_project()
    with patch("core.access.need_edit", side_effect=PermissionError("cấm")):
        with pytest.raises(PermissionError): pron.save(p,pid,"Kelly",{"Trồi":"trờ"})
    assert "pronunciation" not in voice.profiles(p.conn,pid)["KELLY"]



def test_failed_dictionary_redo_restores_old_audio(tmp_path):
    from core.providers import ProviderError
    p,pid = setup_project()
    directory = audio_lib.assets_dir(str(tmp_path),pid)
    provider = Tts()
    with patch("core.features.on",side_effect=lambda f:f == "tts_pronunciation"):
        voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False)
        finish(directory)
        pron.save(p,pid,"Kelly",{"Trồi":"trờ ôi"})
        with patch.object(provider,"generate_tts",side_effect=ProviderError("fixture refused")):
            voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False,by_person=True)
    kept = audio_lib.load(directory)
    assert len(kept) == 1 and kept[0]["asset_id"] == "1" and kept[0]["state"] == "succeeded"
    assert kept[0].get("redo_error")


def test_asr_constructor_has_no_download(tmp_path):
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock
    from core import voice_check
    constructor = Mock(side_effect=RuntimeError("model not cached"))
    with patch.object(voice_check,"asr_available",return_value=True), patch.dict(sys.modules,{"faster_whisper":SimpleNamespace(WhisperModel=constructor)}):
        assert voice_check.transcribe_local(str(tmp_path/"v.wav")) is None
    assert constructor.call_args.kwargs["local_files_only"] is True

def test_check_keeps_concurrent_job_and_does_not_revive_deleted(tmp_path):
    path = tmp_path / 'voice.wav'; path.write_bytes(b'fixture')
    original = {'kind':'tts','asset_id':'old','state':'succeeded','file':'voice.wav','text':'gốc','pronunciation':{'key':'k'}}
    audio_lib._save(str(tmp_path), [original])
    def asr(path):
        audio_lib._save(str(tmp_path), [{'asset_id':'new','state':'running'}])
        return 'gốc'
    pron.check(str(tmp_path), asr)
    assert audio_lib.load(str(tmp_path)) == [{'asset_id':'new','state':'running'}]

@pytest.mark.parametrize('filename', ['../outside.wav', r'\\server\share\voice.wav', r'C:\outside.wav'])
def test_check_rejects_external_before_file_io(tmp_path, filename):
    audio_lib._save(str(tmp_path), [{'state':'succeeded','file':filename,'text':'gốc','pronunciation':{'key':'k'}}])
    with patch('os.path.isfile', side_effect=AssertionError('outside IO')):
        pron.check(str(tmp_path), asr=lambda p: pytest.fail('outside ASR'))
    assert audio_lib.load(str(tmp_path))[0]['pronunciation_check']['level'] == 'yellow'

def test_unavailable_asr_can_be_checked_again(tmp_path):
    (tmp_path / 'voice.wav').write_bytes(b'fixture')
    audio_lib._save(str(tmp_path), [{'state':'succeeded','file':'voice.wav','text':'gốc','pronunciation':{'key':'k'}}])
    pron.check(str(tmp_path), asr=lambda p: None)
    pron.check(str(tmp_path), asr=lambda p: 'gốc')
    assert audio_lib.load(str(tmp_path))[0]['pronunciation_check']['level'] == 'ok'

def test_legacy_model_change_has_same_stale_count_as_generate(tmp_path):
    p,pid = setup_project(); provider = Tts()
    with patch('core.features.on', return_value=False):
        voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False)
    directory = audio_lib.assets_dir(str(tmp_path),pid)
    finish(directory)
    items = audio_lib.load(directory)
    items[0]['model'] = 'eleven_v3'  # legacy có model lưu; thiếu model không được suy đoán rồi trả tiền lại
    audio_lib._save(directory, items)
    voice.set_profile(p.conn,pid,'Kelly',{'voice_id':70,'model':'eleven_flash_v2_5'})
    assert len(pron.stale_lines(p.conn,pid,str(tmp_path))) == 1

def test_check_missing_file_is_yellow_and_no_asr(tmp_path):
    audio_lib._save(str(tmp_path), [{'state':'succeeded','file':'missing.wav','text':'gốc','pronunciation':{'key':'k'}}])
    pron.check(str(tmp_path), asr=lambda p: pytest.fail('missing ASR'))
    assert 'Thiếu file' in audio_lib.load(str(tmp_path))[0]['pronunciation_check']['message']

@pytest.mark.parametrize('state', ['superseded','cancelled','failed'])
def test_check_does_not_patch_state_changed_during_asr(tmp_path, state):
    (tmp_path/'voice.wav').write_bytes(b'fixture')
    e = {'state':'succeeded','file':'voice.wav','text':'gốc','pronunciation':{'key':'k'}}
    audio_lib._save(str(tmp_path), [e])
    def asr(path):
        audio_lib._save(str(tmp_path), [{**e,'state':state}]); return 'gốc'
    pron.check(str(tmp_path), asr)
    assert 'pronunciation_check' not in audio_lib.load(str(tmp_path))[0]

def test_local_model_reused_and_keyed_by_name(tmp_path):
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock
    from core import voice_check
    model = Mock(); model.transcribe.return_value = ([SimpleNamespace(text='gốc')], None)
    constructor = Mock(return_value=model)
    with patch.object(voice_check, '_local_models', {}), patch.object(voice_check,'asr_available',return_value=True), patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=constructor)}), patch.dict('os.environ', {'VOICE_ASR_MODEL':'fixture'}):
        assert voice_check.transcribe_local('one.wav') == 'gốc'
        assert voice_check.transcribe_local('two.wav') == 'gốc'
        assert constructor.call_count == 1
        with patch.dict('os.environ', {'VOICE_ASR_MODEL':'other'}):
            voice_check.transcribe_local('three.wav')
        assert constructor.call_count == 2
        assert constructor.call_args.kwargs['local_files_only'] is True

@pytest.mark.parametrize('role', ['none','view','edit','owner'])
def test_ui_roles_and_no_automatic_asr(tmp_path, role):
    from streamlit.testing.v1 import AppTest
    script = '''
import streamlit as st
from core.db import connect
from core.pipeline import Pipeline
from core import voice
from dashboard.tts_pronunciation_ui import render
p=Pipeline(connect())
pid=p.create_project('fixture')
p.conn.execute("UPDATE projects SET created_by='creator@example.test' WHERE id=?", (pid,))
p.conn.execute("INSERT INTO characters(project_id,name,description) VALUES (?,?,?)", (pid,'Kelly','fixture'))
voice.set_profile(p.conn,pid,'Kelly',{'voice_id':70,'model':'eleven_v3'})
role=ROLE
p.user={'email':'reader@example.test','role':'owner' if role=='owner' else 'member'}
if role in ('view','edit'):
    p.conn.execute("INSERT INTO project_watchers(project_id,email,level,added_at,added_by) VALUES (?,?,?,'fixture','creator@example.test')", (pid,'reader@example.test',role))
    p.conn.commit()
render(p,pid,DATA)
'''.replace('ROLE',repr(role)).replace('DATA',repr(str(tmp_path)))
    with patch.object(pron,'check') as check:
        app = AppTest.from_string(script).run()
        if role == 'none':
            assert app.exception and 'không có quyền' in app.exception[0].message
            assert not app.button
        else:
            assert not app.exception
            assert len(app.button) == 2
            assert all(b.disabled == (role=='view') for b in app.button)
            assert not (tmp_path/'1'/'audio_assets').exists()
            if role in ('edit','owner'):
                app.button[1].click().run()
                assert not app.exception
                assert check.call_count == 1
                assert check.call_args.kwargs['p'].user['email'] == 'reader@example.test'
        assert check.call_count == (1 if role in ('edit','owner') else 0)

def test_check_preserves_appended_entry_and_changed_source(tmp_path):
    (tmp_path/'voice.wav').write_bytes(b'fixture')
    e = {'asset_id':'old','state':'succeeded','file':'voice.wav','text':'gốc','pronunciation':{'key':'k'}}
    audio_lib._save(str(tmp_path), [e])
    def asr(path):
        audio_lib._save(str(tmp_path), [e, {'asset_id':'new','state':'running'}]); return 'gốc'
    pron.check(str(tmp_path), asr)
    assert len(audio_lib.load(str(tmp_path))) == 2
    assert audio_lib.load(str(tmp_path))[0]['pronunciation_check']['level'] == 'ok'
    def changed(path):
        audio_lib._save(str(tmp_path), [{**e,'text':'chữ mới'}]); return 'gốc'
    pron.check(str(tmp_path), changed, force=True)
    assert 'pronunciation_check' not in audio_lib.load(str(tmp_path))[0]

def test_atomic_manifest_failed_replace_keeps_old(tmp_path):
    audio_lib._save(str(tmp_path), [{'asset_id':'old'}])
    with patch('core.audio_lib.os.replace',side_effect=OSError('fixture')):
        with pytest.raises(OSError): audio_lib._save(str(tmp_path), [{'asset_id':'new'}])
    assert audio_lib.load(str(tmp_path)) == [{'asset_id':'old'}]
    assert not list(tmp_path.glob('.assets-*.tmp'))

def test_check_permission_before_loading(tmp_path):
    p,pid=setup_project()
    with patch('core.access.need_edit',side_effect=PermissionError('fixture')),patch('core.audio_lib.load',side_effect=AssertionError('read forbidden')):
        with pytest.raises(PermissionError): pron.check(str(tmp_path),p=p,project_id=pid)

def test_malformed_dictionary_blocks_send_and_stale_is_visible(tmp_path):
    p,pid=setup_project();provider=Tts()
    with patch('core.features.on',side_effect=lambda f:f=='tts_pronunciation'):
        voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False)
        finish(audio_lib.assets_dir(str(tmp_path),pid))
        p.conn.execute("UPDATE characters SET voice_profile=? WHERE project_id=?",(json.dumps({'voice_id':70,'model':'eleven_v3','pronunciation':'broken'}),pid));p.conn.commit()
        assert len(pron.stale_lines(p.conn,pid,str(tmp_path))) == 1
        with pytest.raises(ValueError,match='bị hỏng'):
            voice.generate(p.conn,pid,provider,str(tmp_path),ledger=False,by_person=True)
    assert len(provider.calls)==1
