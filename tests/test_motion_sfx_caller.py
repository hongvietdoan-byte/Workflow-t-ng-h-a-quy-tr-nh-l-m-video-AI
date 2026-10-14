import os
from unittest.mock import patch
import pytest

@pytest.fixture
def mod():
    with patch.object(os, 'environ', {'PYTHONUTF8': '1', 'USERPROFILE': 'C:/qa-step5-fake-home'}):
        from core import sfx_plan
        with patch.object(sfx_plan, 'catalog', return_value=[dict(id=4,heard_label='Impact')]):
            yield sfx_plan


def test_motion_is_explicit_only(mod):
    from core import features
    assert 'motion_sfx' in features.OPT_IN_ONLY


def test_motion_stale_before_apply(mod):
    from types import SimpleNamespace
    p = SimpleNamespace(user=None)
    plan = {'_motion': {'signature': 'old', 'scenes': []}, 'cues': []}
    with patch('core.features.on', return_value=True), patch.object(mod, 'motion_signature', return_value='new'), patch.object(mod, 'apply') as apply:
        with pytest.raises(mod.SfxPlanError, match='đổi'):
            mod.apply_motion(p, 'fixture', 1, plan, [], 'cut', 1)
        apply.assert_not_called()


def test_motion_preserves_anchor_when_time_edited(mod):
    from types import SimpleNamespace
    p = SimpleNamespace(user=None)
    plan = {'_motion': {'signature': 'same', 'scenes': [{'idx': 3, 'start': 8, 'length': 4}]},
            'cues': [{'id': 4, 'at': 9, 'scene': 3, 'anchor_idx': 3, 'offset': 1, 'volume': .5}]}
    with patch('core.features.on', return_value=True), patch.object(mod, 'motion_signature', return_value='same'), patch('core.motion_sfx_safe.atomic_apply', return_value=1) as apply:
        assert mod.apply_motion(p, 'fixture', 1, plan, [{'index': 0, 'at': 10, 'volume': .6}], 'cut', 1) == 1
        cue = apply.call_args.args[4][0]
        assert cue['anchor_idx'] == 3 and cue['scene'] == 3 and cue['offset'] == 2


def test_motion_readonly_rejected_before_work(mod):
    from types import SimpleNamespace
    from core import access
    p = SimpleNamespace(user={'email': 'viewer'})
    with patch.object(mod.access, 'need_edit', side_effect=access.AccessDenied('chỉ xem')), patch('core.features.on', return_value=True), patch.object(mod, 'timeline') as timeline:
        with pytest.raises(access.AccessDenied):
            mod.propose_motion_review(p, 'fixture', 1)
        timeline.assert_not_called()


@pytest.mark.parametrize('change', ['scene', 'motion', 'clip', 'transition', 'fade'])
def test_signature_tracks_inputs(mod, tmp_path, change):
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
    conn.executescript("CREATE TABLE scenes(id, idx, data, project_id); CREATE TABLE motion_prompts(scene_id, motion_prompt); INSERT INTO scenes VALUES(1, 1, '{}', 7); INSERT INTO motion_prompts VALUES(1, 'falls');")
    p = SimpleNamespace(conn=conn, user=None)
    path = tmp_path / '7' / 'videos' / 'clip.mp4'; path.parent.mkdir(parents=True); path.write_bytes(b'fixture')
    clips = [{'idx': 1, 'path': str(path), 'requested_sec': 4}]
    with patch.object(mod.final_cut, 'collect_clips', return_value=clips):
        sig = mod.motion_signature(p, str(tmp_path), 7)
        transition, fade = 'cut', 1
        if change == 'scene': conn.execute("UPDATE scenes SET data='{\"byd\":{}}'")
        if change == 'motion': conn.execute("UPDATE motion_prompts SET motion_prompt='walks'")
        if change == 'clip': path.write_bytes(b'new fixture longer')
        if change == 'transition': transition = 'fade'
        if change == 'fade': fade = 2
        assert sig != mod.motion_signature(p, str(tmp_path), 7, transition, fade)
    conn.close()


def test_experimental_does_not_implicitly_enable(mod):
    from core import features
    with patch.object(os, 'environ', {}), patch.object(features, 'settings', return_value={'preset': 'experimental', 'flags': {}}):
        assert not features.on('motion_sfx')
    with patch.object(os, 'environ', {'FEATURE_MOTION_SFX': '1'}), patch.object(features, 'settings', return_value={'preset': 'experimental', 'flags': {}}):
        assert features.on('motion_sfx')



def test_same_size_same_mtime_clip_overwrite_invalidates(mod, tmp_path):
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE scenes(id, idx, data, project_id); CREATE TABLE motion_prompts(scene_id, motion_prompt);')
    p = SimpleNamespace(conn=conn, user=None)
    path = tmp_path / '7' / 'videos' / 'clip.mp4'; path.parent.mkdir(parents=True); path.write_bytes(b'old')
    stamp = path.stat()
    with patch.object(mod.final_cut, 'collect_clips', return_value=[{'idx': 1, 'path': str(path), 'requested_sec': 4}]):
        before = mod.motion_signature(p, str(tmp_path), 7)
        path.write_bytes(b'new'); os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        assert before != mod.motion_signature(p, str(tmp_path), 7)
    conn.close()



def test_step5_actual_component_propose_review_apply_no_provider(mod):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    script = Path(__file__).parent / 'fixtures' / 'motion_sfx_step5_qa.py'
    with patch.object(os, 'environ', {'PYTHONUTF8': '1', 'USERPROFILE': 'C:/qa-step5-fake-home'}):
        app = AppTest.from_file(str(script)).run()
        assert not app.exception
        app.button(key='motion_sfx_propose_7').click().run()
        assert not app.exception
        assert len(app.session_state['sfxplan_7']['cues']) == 1
        assert 'qa_applied' not in app.session_state
        app.button(key='sfx_apply_7').click().run()
        assert not app.exception
        assert app.session_state['qa_applied'] == 1


def test_step5_readonly_disables_code_and_apply(mod):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    script = Path(__file__).parent / 'fixtures' / 'motion_sfx_step5_qa.py'
    with patch.object(os, 'environ', {'PYTHONUTF8': '1', 'USERPROFILE': 'C:/qa-step5-fake-home'}):
        app = AppTest.from_file(str(script)).run()
        app.button(key='motion_sfx_propose_7').click().run()
        app.checkbox(key='qa_readonly').check().run()
        assert not app.exception
        assert app.button(key='motion_sfx_propose_7').disabled
        assert app.button(key='sfx_apply_7').disabled
        assert 'qa_applied' not in app.session_state



def test_unreadable_clip_is_stale_before_apply(mod):
    from types import SimpleNamespace
    p = SimpleNamespace(user=None)
    plan = {'_motion': {'signature': 'old', 'scenes': []}, 'cues': []}
    with patch('core.features.on', return_value=True), patch.object(mod, 'motion_signature', side_effect=mod.SfxPlanError('Không đọc clip')), patch.object(mod, 'apply') as apply:
        assert not mod.motion_current(p, 'fixture', 1, plan)
        with pytest.raises(mod.SfxPlanError, match='đổi'):
            mod.apply_motion(p, 'fixture', 1, plan, [])
        apply.assert_not_called()


@pytest.mark.parametrize("selection", [dict(index=-1, at=1, volume=.5), dict(index=True, at=1, volume=.5), dict(index=0, at=True, volume=.5), dict(index=0, at=1, volume=True)])
def test_selection_rejected_before_apply(mod, selection):
    from types import SimpleNamespace
    plan = {'_motion': {'signature': 'same', 'scenes': [{'idx': 1, 'start': 0, 'length': 4}]}, 'cues': [{'id': 4, 'scene': 1, 'anchor_idx': 1}]}
    with patch.object(mod.access, 'need_edit'), patch('core.features.on', return_value=True), patch.object(mod, 'motion_signature', return_value='same'), patch.object(mod, 'apply') as apply:
        with pytest.raises((ValueError, mod.SfxPlanError)):
            mod.apply_motion(SimpleNamespace(), 'fixture', 7, plan, [selection])
        apply.assert_not_called()


def test_ui_freshness_does_not_hash(mod):
    from types import SimpleNamespace
    plan = {'_motion': {'quick_signature': 'same'}}
    with patch.object(mod, 'motion_signature') as strong, patch.object(mod, 'motion_quick_signature', return_value='same', create=True):
        assert mod.motion_current(SimpleNamespace(), 'fixture', 7, plan, strong=False)
        strong.assert_not_called()


def test_proposal_rejects_changed_snapshot(mod):
    from types import SimpleNamespace
    from core import motion_sfx
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: []))
    with patch.object(mod.access, 'need_view'), patch('core.features.on', return_value=True), patch.object(mod, 'motion_signature', side_effect=['before', 'after']), patch.object(mod, 'timeline', return_value=[]), patch.object(mod.final_cut, 'collect_clips', return_value=[]), patch.object(mod, 'catalog', return_value=[]):
        with pytest.raises(mod.SfxPlanError):
            mod.propose_motion(p, 'fixture', 7, opted_in=True)


def test_clip_scope_rejected_before_read(mod, tmp_path):
    from types import SimpleNamespace
    path = tmp_path / 'outside.mp4'; path.write_bytes(b'fake')
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: []))
    with patch.object(mod.final_cut, 'collect_clips', return_value=[dict(path=str(path), idx=1)]):
        with pytest.raises(mod.SfxPlanError):
            mod.motion_signature(p, str(tmp_path), 7)



def test_atomic_copy_failure_keeps_manifest_and_old_file(mod, tmp_path):
    from pathlib import Path
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    import json
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    old = root / 'old.wav'; old.write_bytes(b'old fixture')
    manifest = root / 'assets.json'; original = json.dumps([dict(label='AI: old', file='old.wav')]).encode()
    manifest.write_bytes(original)
    source = tmp_path / 'new.wav'; source.write_bytes(b'new fixture')
    def staged_apply(*args, **kwargs):
        stage = Path(kwargs['_directory'])
        (stage / 'new.wav').write_bytes(b'new fixture')
        (stage / 'assets.json').write_text(json.dumps([dict(label='AI: new', file='new.wav')]))
        return 1
    with patch.object(mod, 'apply', side_effect=staged_apply), patch.object(mod.sound_lib, 'get', return_value=dict(path=str(source),source_id=1)), patch.object(safe.shutil, 'copyfile', side_effect=OSError('fake copy failure')):
        with pytest.raises(mod.SfxPlanError):
            safe.atomic_apply(mod, SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: dict(path=str(tmp_path))))), str(tmp_path), 7, [dict(id=4)], [])
    assert manifest.read_bytes() == original and old.read_bytes() == b'old fixture'


@pytest.mark.parametrize('case', ['relative', 'file_budget', 'batch_budget', 'count_budget'])
def test_clip_guard_preflight(mod, tmp_path, case):
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    path = tmp_path / '7' / 'videos' / 'clip.mp4'; path.parent.mkdir(parents=True); path.write_bytes(b'fixture')
    clips = [dict(path=str(path), idx=1)]
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: []))
    limits = {}
    if case == 'relative': clips[0]['path'] = '7/videos/clip.mp4'
    if case == 'file_budget': limits['MAX_FILE_BYTES'] = 3
    if case == 'batch_budget': limits['MAX_TOTAL_BYTES'] = 3
    if case == 'count_budget': clips *= 129
    from contextlib import ExitStack
    with ExitStack() as stack:
        for key, value in limits.items(): stack.enter_context(patch.object(safe, key, value))
        stack.enter_context(patch.object(mod.final_cut, 'collect_clips', return_value=clips))
        opened = stack.enter_context(patch('builtins.open'))
        with pytest.raises(mod.SfxPlanError): mod.motion_signature(p, str(tmp_path), 7)
        opened.assert_not_called()


def test_duplicate_selection_rejected(mod):
    from types import SimpleNamespace
    plan = {'_motion': {'signature': 'same', 'scenes': [{'idx': 1, 'start': 0, 'length': 4}]}, 'cues': [{'id': 4, 'scene': 1, 'anchor_idx': 1}]}
    with patch.object(mod.access, 'need_edit'), patch('core.features.on', return_value=True), patch.object(mod, 'motion_signature', return_value='same'), patch('core.motion_sfx_safe.atomic_apply') as apply:
        with pytest.raises(mod.SfxPlanError):
            mod.apply_motion(SimpleNamespace(), 'fixture', 7, plan, [dict(index=0,at=1,volume=.5)] * 2)
        apply.assert_not_called()


@pytest.mark.parametrize('concurrent', [False, True])
def test_atomic_success_or_manifest_conflict(mod, tmp_path, concurrent):
    from pathlib import Path
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    import json
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    (root / 'old.wav').write_bytes(b'old'); (root / 'manual.wav').write_bytes(b'manual')
    manual = dict(label='manual', file='manual.wav', use=True)
    manifest = root / 'assets.json'; original = [manual, dict(label='AI: old',file='old.wav')]
    manifest.write_text(json.dumps(original))
    source = tmp_path / 'new.wav'; source.write_bytes(b'new')
    def staged_apply(*args, **kwargs):
        stage = Path(kwargs['_directory']); (stage / 'new.wav').write_bytes(b'new')
        (stage / 'assets.json').write_text(json.dumps([manual,dict(label='AI: new',file='new.wav')]))
        if concurrent: manifest.write_text(json.dumps([manual]))
        return 1
    with patch.object(mod, 'apply', side_effect=staged_apply), patch.object(mod.sound_lib, 'get', return_value=dict(path=str(source),source_id=1)):
        if concurrent:
            with pytest.raises(mod.SfxPlanError): safe.atomic_apply(mod, SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: dict(path=str(tmp_path))))), str(tmp_path), 7, [dict(id=4)], [])
            assert json.loads(manifest.read_text()) == [manual]
            assert not list(root.glob('motion_*'))
        else:
            assert safe.atomic_apply(mod, SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: dict(path=str(tmp_path))))), str(tmp_path), 7, [dict(id=4)], []) == 1
            saved = json.loads(manifest.read_text()); assert saved[0] == manual
            assert saved[1]['file'].startswith('motion_') and (root / saved[1]['file']).read_bytes() == b'new'
        assert (root / 'old.wav').read_bytes() == b'old' and (root / 'manual.wav').read_bytes() == b'manual'


@pytest.mark.parametrize('entry', [dict(label='AI: old',file='../outside.wav'), dict(label='manual',fit_file='C:/outside.wav')])
def test_atomic_rejects_unsafe_manifest_before_stage(mod, tmp_path, entry):
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    import json
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    manifest = root / 'assets.json'; original = json.dumps([entry]).encode(); manifest.write_bytes(original)
    with patch.object(mod, 'apply') as apply:
        with pytest.raises(mod.SfxPlanError): safe.atomic_apply(mod, SimpleNamespace(), str(tmp_path), 7, [], [])
        apply.assert_not_called()
    assert manifest.read_bytes() == original


@pytest.mark.parametrize('change', ['rename', 'drop', 'classify', 'clip_state'])
def test_catalog_and_clip_metadata_invalidates(mod, tmp_path, change):
    from types import SimpleNamespace
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: []))
    sounds = [dict(id=4, name='old', heard_label='Impact', heard_score=.9, duration=1, category='sfx', tags='')]
    clips = [dict(idx=1, path=None, state='approved', usable=True, extra=False, scene_id=10)]
    with patch.object(mod, 'catalog', side_effect=lambda *a: sounds), patch.object(mod.final_cut, 'collect_clips', side_effect=lambda *a: clips):
        before = mod.motion_signature(p, str(tmp_path), 7)
        if change == 'rename': sounds[0]['name'] = 'new'
        if change == 'drop': sounds.clear()
        if change == 'classify': sounds[0]['heard_label'] = 'Voice'
        if change == 'clip_state': clips[0]['usable'] = False
        assert before != mod.motion_signature(p, str(tmp_path), 7)


def test_source_audio_changes_during_stage_keeps_mix(mod, tmp_path):
    from pathlib import Path
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    import json
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    manifest = root / 'assets.json'; original = b'[]'; manifest.write_bytes(original)
    source = tmp_path / 'new.wav'; source.write_bytes(b'old')
    def staged_apply(*args, **kwargs):
        stage = Path(kwargs['_directory']); (stage / 'new.wav').write_bytes(b'old')
        (stage / 'assets.json').write_text(json.dumps([dict(label='AI: new',file='new.wav')]))
        source.write_bytes(b'new')
        return 1
    with patch.object(mod, 'apply', side_effect=staged_apply), patch.object(mod.sound_lib, 'get', return_value=dict(path=str(source),source_id=1)):
        with pytest.raises(mod.SfxPlanError): safe.atomic_apply(mod, SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: dict(path=str(tmp_path))))), str(tmp_path), 7, [dict(id=4)], [])
    assert manifest.read_bytes() == original and not list(root.glob('motion_*'))



def test_atomic_real_apply_preserves_manual_and_replaces_ai(mod, tmp_path):
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    import sqlite3, json
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    (root / 'manual.wav').write_bytes(b'manual'); (root / 'old.wav').write_bytes(b'old')
    manual = dict(kind='sound_effect',label='manual',file='manual.wav',use=True)
    manifest = root / 'assets.json'; manifest.write_text(json.dumps([manual,dict(label='AI: old',file='old.wav')]))
    source = tmp_path / 'new.wav'; source.write_bytes(b'new')
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row; conn.execute('CREATE TABLE scenes(project_id,idx)'); conn.execute('INSERT INTO scenes VALUES(7,1)'); conn.execute('CREATE TABLE sound_sources(id,path)'); conn.execute('INSERT INTO sound_sources VALUES(1,?)',(str(tmp_path),))
    cue = dict(id=4,at=1,volume=.5,scene=1,anchor_idx=1,offset=1)
    try:
        with patch.object(mod.access,'need_edit'), patch.object(mod.sound_lib,'get',return_value=dict(id=4,path=str(source),name='new',source_id=1,duration=None)), patch.object(mod.sound_lib,'ensure_duration',return_value=1) as measure:
            assert safe.atomic_apply(mod,SimpleNamespace(conn=conn),str(tmp_path),7,[cue],[dict(idx=1,start=0,length=4)]) == 1
        measure.assert_not_called()
        saved = json.loads(manifest.read_text()); assert saved[0] == manual
        assert saved[1]['duration_ms'] is None
        assert saved[1]['anchor_idx'] == 1 and saved[1]['offset'] == 1 and saved[1]['file'].startswith('motion_')
        assert (root / 'old.wav').read_bytes() == b'old' and (root / 'manual.wav').read_bytes() == b'manual'
    finally: conn.close()


@pytest.mark.parametrize('case', ['symlink', 'special', 'deadline'])
def test_clip_no_special_or_unbounded_read(mod, tmp_path, case):
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    from pathlib import Path
    import stat
    path = tmp_path / '7' / 'videos' / 'clip.mp4'; path.parent.mkdir(parents=True); path.write_bytes(b'fixture')
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: []))
    guard = patch.object(Path,'is_symlink',side_effect=lambda: True) if case == 'symlink' else patch.object(Path,'stat',return_value=SimpleNamespace(st_mode=stat.S_IFIFO,st_size=1)) if case == 'special' else patch.object(safe,'MAX_READ_SECONDS',-1)
    with guard, patch.object(mod.final_cut,'collect_clips',return_value=[dict(path=str(path),idx=1)]):
        with pytest.raises(mod.SfxPlanError): mod.motion_signature(p,str(tmp_path),7)



def test_off_readonly_ai_denied_before_provider(mod):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    script = Path(__file__).parent / 'fixtures' / 'motion_sfx_step5_qa.py'
    with patch.object(os, 'environ', {'PYTHONUTF8':'1','USERPROFILE':'C:/qa-step5-fake-home'}):
        app = AppTest.from_file(str(script)).run()
        app.checkbox(key='qa_readonly').check().run()
        app.session_state['qa_motion_enabled'] = False
        app.run()
        assert not any(button.key == 'motion_sfx_propose_7' for button in app.button)
        app.button(key='sfx_ai_go_7').click().run()
        assert not app.exception and len(app.error) == 1


@pytest.mark.parametrize('case', ['outside_source', 'untrusted'])
def test_atomic_source_requires_registered_trusted_library(mod, tmp_path, case):
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    manifest = root / 'assets.json'; manifest.write_bytes(b'[]')
    source = tmp_path / 'new.wav'; source.write_bytes(b'fake')
    conn = SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: dict(path=str(tmp_path / 'registered'))))
    with patch.object(mod.sound_lib,'get',return_value=dict(path=str(source),source_id=1)), patch.object(mod,'catalog',return_value=[] if case == 'untrusted' else [dict(id=4)]), patch.object(mod,'apply') as apply:
        with pytest.raises(mod.SfxPlanError): safe.atomic_apply(mod,SimpleNamespace(conn=conn),str(tmp_path),7,[dict(id=4)],[])
        apply.assert_not_called()
    assert manifest.read_bytes() == b'[]'


@pytest.mark.parametrize('stale', [False, True])
def test_leftover_lock_busy_message_or_cleared_when_stale(mod, tmp_path, stale):
    # Rà gộp 14/10: khóa .motion_sfx.lock của lượt áp đã chết giữa chừng không được chặn mãi với câu sai nguyên nhân.
    from pathlib import Path
    from core import motion_sfx_safe as safe
    from types import SimpleNamespace
    import json, time
    root = tmp_path / '7' / 'audio_assets'; root.mkdir(parents=True)
    manifest = root / 'assets.json'; manifest.write_text('[]')
    lock = root / '.motion_sfx.lock'; lock.write_bytes(b'')
    if stale:
        old = time.time() - safe.LOCK_STALE_SECONDS - 60; os.utime(lock, (old, old))
    source = tmp_path / 'new.wav'; source.write_bytes(b'new')
    def staged_apply(*args, **kwargs):
        stage = Path(kwargs['_directory']); (stage / 'new.wav').write_bytes(b'new')
        (stage / 'assets.json').write_text(json.dumps([dict(label='AI: new',file='new.wav')]))
        return 1
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: dict(path=str(tmp_path)))))
    with patch.object(mod, 'apply', side_effect=staged_apply), patch.object(mod.sound_lib, 'get', return_value=dict(path=str(source),source_id=1)):
        if stale:
            assert safe.atomic_apply(mod, p, str(tmp_path), 7, [dict(id=4)], []) == 1
            assert not lock.exists()
        else:
            with pytest.raises(mod.SfxPlanError, match='lượt khác'):
                safe.atomic_apply(mod, p, str(tmp_path), 7, [dict(id=4)], [])
            assert lock.exists() and json.loads(manifest.read_text()) == []
