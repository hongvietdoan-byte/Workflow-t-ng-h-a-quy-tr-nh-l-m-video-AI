import os
from unittest.mock import patch

import pytest


@pytest.fixture
def module():
    with patch.object(os, 'environ', {'PYTHONUTF8': '1'}):
        from core import motion_sfx
        yield motion_sfx


def scene(**kw):
    return dict(idx=2, start=10, length=4, motion_en='She falls.',
                byd={'hanh_dong': [{'ai': 'KELLY', 'bat_dau': {'tu_the': 'dung'},
                      'dinh': {'tu_the': 'nga'}, 'ket_thuc': {'tu_the': 'nam'}}]}, **kw)


def test_off_has_no_work(module):
    with patch('core.features.on', return_value=False), patch('core.clip_measure.motion_series', side_effect=AssertionError):
        assert module.plan([scene()], [], opted_in=True) is None


def test_optin_required(module):
    with patch('core.features.on', return_value=True):
        assert module.plan([scene()], [], opted_in=False) is None


def test_catalog_and_estimated_activity_not_semantics(module):
    sounds = [{'id': 4, 'heard_label': 'Thump, thud', 'name': 'A', 'category': 'B'}]
    with patch('core.features.on', return_value=True), patch('core.clip_measure.motion_series', return_value=([0.1, 3, 0.1], 1, [1, 1, 1])):
        result = module.plan([scene(clip_path='fixture')], sounds, opted_in=True)
    assert result['cues'][0]['id'] == 4
    assert result['cues'][0]['at'] == 12
    assert result['cues'][0]['estimated'] is True
    assert result['measurements'][0]['frame_activity_peak_s'] == 2
    assert result['warnings']


@pytest.mark.parametrize('length', [-1, float('nan'), None, '4', True])
def test_invalid_duration_no_cues(module, length):
    row = scene(); row['length'] = length
    with patch('core.features.on', return_value=True):
        result = module.plan([row], [], opted_in=True)
    assert result['cues'] == [] and result['warnings']


def test_missing_sound_and_unknown_are_visible(module):
    row = scene(); row['motion_en'] = 'She teleports.'; row['byd'] = {}
    with patch('core.features.on', return_value=True):
        result = module.plan([row], [], opted_in=True)
    assert result['unmet'] and result['warnings'] and result['cues'] == []


@pytest.mark.parametrize('series', [([], 24, []), ([float('nan')], 24, [1]), ([-1], 24, [1]), ([1], 0, [1]), ([1], 24, [])])
def test_bad_measurement_does_not_claim_measured(module, series):
    with patch('core.features.on', return_value=True), patch('core.clip_measure.motion_series', return_value=series):
        result = module.plan([scene(clip_path='fixture')], [], opted_in=True)
    assert result['measurements'][0]['frame_activity_peak_s'] is None
    assert result['warnings']


def test_stale_glitch_not_dialogue_or_negation(module):
    with patch('core.features.on', return_value=True):
        result = module.plan([scene(sound={'sfx': ['glitch']})], [], opted_in=True)
        neg = scene(sound={'sfx': ['no glitch']}); neg['motion_en'] = 'KELLY: glitch\nShe falls.'
        other = module.plan([neg], [], opted_in=True)
    assert any('lỗi thời' in w for w in result['warnings'])
    assert not any('lỗi thời' in w for w in other['warnings'])


def test_postfx_schema_and_missing_catalog(module):
    fx = {'loai': 'glitch', 'vi_tri': 'cuoi', 'thoi_luong_s': 1, 'cuong_do': .4}
    with patch('core.features.on', return_value=True):
        result = module.plan([scene(post_fx=fx)], [], opted_in=True)
        bad = module.plan([scene(post_fx={'loai': 'glitch'})], [], opted_in=True)
    assert any(c['kind'] == 'noise' and c['at'] == 13 for c in result['requests'])
    assert not any(c['source'] == 'post_fx' for c in bad['requests'])
    assert bad['warnings']


def test_adapter_off_does_not_touch_data_or_llm(module):
    from core import sfx_plan
    with patch('core.features.on', return_value=False), patch.object(sfx_plan, 'timeline', side_effect=AssertionError), patch.object(sfx_plan.llm_runner, 'ask_json', side_effect=AssertionError):
        assert sfx_plan.propose_motion(None, 'unused', 1, opted_in=True) is None


def test_adapter_permission_before_read(module):
    from core import sfx_plan, access
    with patch('core.features.on', return_value=True), patch.object(access, 'need_view', side_effect=access.AccessDenied('Không có quyền')), patch.object(sfx_plan, 'timeline', side_effect=AssertionError):
        with pytest.raises(access.AccessDenied):
            sfx_plan.propose_motion(None, 'unused', 1, opted_in=True)


def test_actor_names_and_negated_by_motion_are_not_actions(module):
    row = scene(); row['motion_en'] = 'Bo remains still; no glitch.'; row['byd'] = {}
    with patch('core.features.on', return_value=True):
        result = module.plan([row], [], opted_in=True)
    assert result['requests'] == []


def test_malformed_by_motion_and_start_are_yellow(module):
    row = scene(); row['byd'] = {'hanh_dong': ['bad', {'ai': 'KELLY', 'bat_dau': 'crawl'}]}
    with patch('core.features.on', return_value=True):
        result = module.plan([row], [], opted_in=True)
    assert result['warnings'] and all(r['source'] != 'byd.bat_dau' for r in result['requests'])


def test_all_action_table_and_normalized_postures(module):
    assert module.kinds('bước chân; vút; ngã; bò; trườn; bám; biến hình; nấc; nhích; chạm') == {
        'footstep', 'whoosh', 'impact', 'rustle', 'transform', 'hiccup', 'touch'}
    assert module.kinds(module.action_text({'tu_the': 'bo', 'ai': 'BO'})) == {'rustle'}


def test_measured_timestamp_only_locked_camera_estimated_alignment(module):
    sounds = [{'id': 4, 'heard_label': 'Thump, thud', 'name': 'A', 'category': 'B'}]
    with patch('core.features.on', return_value=True), patch('core.clip_measure.motion_series', return_value=([3, .1, .1], 1, [1, 1, 1])):
        locked = module.plan([scene(clip_path='fixture', camera_move='static')], sounds, opted_in=True)
        moving = module.plan([scene(clip_path='fixture', camera_move='pan')], sounds, opted_in=True)
    assert locked['cues'][0]['at'] == 11
    assert locked['cues'][0]['time_source'] == 'frame_activity'
    assert locked['cues'][0]['estimated'] is True
    assert moving['cues'][0]['at'] == 12
    assert moving['cues'][0]['time_source'] == 'uniform_byd'


@pytest.mark.parametrize('start,length', [(10**1000, 4), (0, 10**1000), (1e308, 1e308)], ids=['huge-start', 'huge-length', 'overflow-sum'])
def test_overflow_timeline_is_yellow(module, start, length):
    with patch('core.features.on', return_value=True):
        result = module.plan([dict(idx=1, start=start, length=length)], [], opted_in=True)
    assert result['cues'] == [] and result['measurements'] == [] and result['warnings']


def test_current_motion_overrides_stale_by_motion(module):
    row = scene(); row['motion_en'] = 'She falls; glitch.'
    row['motion_prompt'] = 'She walks.'; row['sound'] = {'sfx': ['glitch']}
    with patch('core.features.on', return_value=True):
        result = module.plan([row], [], opted_in=True)
    assert {r['kind'] for r in result['requests']} == {'footstep'}
    assert any('BYĐ' in w and 'xung đột' in w for w in result['warnings'])
    assert any('lỗi thời (noise)' in w for w in result['warnings'])


def test_overlap_cue_keeps_own_shot_anchor(module):
    row = dict(idx=1, start=0, length=4, byd={'hanh_dong': [{'ket_thuc': {'action': 'falls'}}]})
    sounds = [dict(id=4, heard_label='Impact', name='A', category='B')]
    with patch('core.features.on', return_value=True):
        result = module.plan([row, dict(idx=2, start=3, length=4)], sounds, opted_in=True)
    cue = result['cues'][0]
    assert cue['anchor_idx'] == 1 and cue['offset'] == 3.95


@pytest.fixture
def adapter_db(module):
    import sqlite3
    from types import SimpleNamespace
    db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE scenes (id INTEGER, idx INTEGER, project_id INTEGER, data TEXT)')
    db.execute('CREATE TABLE motion_prompts (scene_id INTEGER, motion_prompt TEXT)')
    db.execute("INSERT INTO scenes VALUES (10, 1, 7, '{\"motion_en\":\"She falls.\"}')")
    db.execute("INSERT INTO scenes VALUES (20, 2, 7, '{}')")
    db.execute("INSERT INTO scenes VALUES (30, 3, 8, '{}')")
    db.execute("INSERT INTO motion_prompts VALUES (10, 'She walks.')")
    yield SimpleNamespace(conn=db)
    db.close()


def test_adapter_reads_current_prompt(module, adapter_db):
    from core import sfx_plan
    with patch('core.features.on', return_value=True), patch.object(sfx_plan.access, 'need_view'), patch.object(sfx_plan, 'timeline', return_value=[dict(idx=1, start=0, length=4)]), patch.object(sfx_plan.final_cut, 'collect_clips', return_value=[]), patch.object(sfx_plan, 'catalog', return_value=[]):
        result = sfx_plan.propose_motion(adapter_db, 'unused', 7, opted_in=True)
    assert {r['kind'] for r in result['requests']} == {'footstep'}


def test_apply_explicit_anchor_and_legacy(module, adapter_db):
    from core import sfx_plan
    scenes = [dict(idx=1, start=0, length=4), dict(idx=2, start=3, length=4)]
    cue = dict(id=4, at=3.95, volume=.5, scene=1, anchor_idx=1, offset=3.95)
    with patch.object(sfx_plan.access, 'need_edit'), patch.object(sfx_plan.audio_lib, 'assets_dir', return_value='unused'), patch.object(sfx_plan.audio_lib, 'load', return_value=[]), patch.object(sfx_plan.sound_lib, 'get', return_value=dict(id=4, path='fixture', name='A')), patch.object(sfx_plan.os.path, 'exists', return_value=True), patch.object(sfx_plan.os.path, 'isfile', return_value=True), patch.object(sfx_plan.sound_lib, 'ensure_duration', return_value=1), patch.object(sfx_plan.audio_lib, 'add_local') as add:
        sfx_plan.apply(adapter_db, 'unused', 7, [cue], scenes)
        assert add.call_args.args[-1] == dict(anchor_idx=1, offset=3.95)
        legacy = {k:v for k,v in cue.items() if k not in ('anchor_idx', 'offset')}
        sfx_plan.apply(adapter_db, 'unused', 7, [legacy], scenes)
        assert add.call_args.args[-1] == dict(anchor_idx=2, offset=.95)


@pytest.mark.parametrize('change', [dict(anchor_idx=3, scene=3), dict(anchor_idx=2), dict(offset=float('nan')), dict(offset=10**1000), dict(offset=5), dict(at=2), dict(id=True), dict(id=10**1000), dict(anchor_idx=10**1000, scene=10**1000)])
def test_apply_bad_explicit_anchor_rejected_before_write(module, adapter_db, change):
    from core import sfx_plan
    scenes = [dict(idx=1, start=0, length=4), dict(idx=2, start=3, length=4), dict(idx=3, start=6, length=4)]
    cue = dict(id=4, at=3.95, volume=.5, scene=1, anchor_idx=1, offset=3.95); cue.update(change)
    with patch.object(sfx_plan.access, 'need_edit'), patch.object(sfx_plan.audio_lib, 'assets_dir', side_effect=AssertionError('không được ghi trước kiểm neo')):
        with pytest.raises(ValueError):
            sfx_plan.apply(adapter_db, 'unused', 7, [cue], scenes)


def test_overlap_anchor_stays_with_shot_on_rerender(module):
    from core import sfx_plan
    item = dict(kind='sound_effect', anchor_idx=1, offset=3.95, start=3.95, use=True)
    with patch.object(sfx_plan.audio_lib, 'assets_dir', return_value='unused'), patch.object(sfx_plan.audio_lib, 'load', return_value=[item]), patch.object(sfx_plan.audio_lib, '_save'):
        sfx_plan.place_on_timeline('unused', 7, [dict(idx=1), dict(idx=2)], [6, 4], transition='cut')
    assert item['anchor_idx'] == 1 and item['start'] == 3.95


@pytest.mark.parametrize('initial', [{}, {'PYTHONUTF8': '1', 'MOTION_SFX_TEST_SETTING': 'fixture'}])
def test_fake_environment_restored(module, initial):
    with patch.object(os, 'environ', initial):
        original = os.environ
        with patch.object(os, 'environ', {'PYTHONUTF8': '1'}):
            with patch('core.features.on', return_value=False):
                assert module.plan([], [], opted_in=True) is None
        assert os.environ is original


@pytest.mark.parametrize('case', ['missing-id', 'missing-file', 'bad-volume'])
def test_new_cue_invalid_sound_preserves_old_audio(module, adapter_db, case):
    from core import sfx_plan
    sentinel = dict(label='AI: âm cũ')
    cue = dict(id=4, at=1, volume=.5, scene=1, anchor_idx=1, offset=1)
    row = None if case == 'missing-id' else dict(id=4, path='fixture', name='A')
    if case == 'bad-volume': cue['volume'] = float('nan')
    with patch.object(sfx_plan.access, 'need_edit'), patch.object(sfx_plan.sound_lib, 'get', return_value=row), patch.object(sfx_plan.os.path, 'isfile', return_value=case != 'missing-file'), patch.object(sfx_plan.os.path, 'exists', return_value=case != 'missing-file'), patch.object(sfx_plan.audio_lib, 'assets_dir', return_value='unused'), patch.object(sfx_plan.audio_lib, 'load', return_value=[sentinel]), patch.object(sfx_plan.audio_lib, 'remove') as remove, patch.object(sfx_plan.audio_lib, 'add_local') as add:
        with pytest.raises(ValueError):
            sfx_plan.apply(adapter_db, 'unused', 7, [cue], [dict(idx=1, start=0, length=4)])
    remove.assert_not_called(); add.assert_not_called()
    assert sentinel == dict(label='AI: âm cũ')


def test_new_cue_allows_project_shot_zero(module, adapter_db):
    from core import sfx_plan
    adapter_db.conn.execute("INSERT INTO scenes VALUES (40, 0, 7, '{}')")
    cue = dict(id=4, at=1, volume=.5, scene=0, anchor_idx=0, offset=1)
    with patch.object(sfx_plan.access, 'need_edit'), patch.object(sfx_plan.sound_lib, 'get', return_value=dict(id=4, path='fixture', name='A')), patch.object(sfx_plan.os.path, 'isfile', return_value=True), patch.object(sfx_plan.os.path, 'exists', return_value=True), patch.object(sfx_plan.audio_lib, 'assets_dir', return_value='unused'), patch.object(sfx_plan.audio_lib, 'load', return_value=[]), patch.object(sfx_plan.sound_lib, 'ensure_duration', return_value=1), patch.object(sfx_plan.audio_lib, 'add_local') as add:
        assert sfx_plan.apply(adapter_db, 'unused', 7, [cue], [dict(idx=0, start=0, length=4)]) == 1
    assert add.call_args.args[-1] == dict(anchor_idx=0, offset=1)
