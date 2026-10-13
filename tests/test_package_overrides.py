import json
from unittest import mock

import pytest

from core import db, package_overrides as pkg


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_PACKAGE_OVERRIDES', '1')
    conn = db.connect()
    conn.execute("INSERT INTO projects(id,name,created_at) VALUES(24,'thử','now')")
    conn.execute("INSERT INTO scenes(id,project_id,idx,data) VALUES(9,24,1,?)",
                 (json.dumps({'story_scene': 1, 'shot_no': 1, 'characters': ['KELLY']}),))
    path = tmp_path / '419.png'
    path.write_bytes(b'anh-gia-419')
    from core.sent_package import sha256_of
    sha = sha256_of(str(path))
    conn.execute("INSERT INTO assets(id,game,kind,name) VALUES(419,'FF','character','KELLY')")
    conn.execute("INSERT INTO project_assets(project_id,asset_id) VALUES(24,419)")
    conn.execute("INSERT INTO asset_images(id,asset_id,path,sha256) VALUES(419,419,?,?)", (str(path), sha))
    conn.commit()
    yield conn, path, sha
    conn.close()


def edit(sha, op='add'):
    return {'op': op, 'source_kind': 'kho', 'asset_image_id': 419,
            'content_sha': sha, 'role': 'character', 'look': 'default'}


def shot():
    return {'action': 'hành động mới', 'image_prompt': 'ảnh mới', 'size': 'MS',
            'role': 'action', 'duration_s': 5}


def test_save_cas_undo_and_no_sent_package_change(setup):
    conn, path, sha = setup
    conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,sent_package,created_at,updated_at) VALUES(649,24,9,'image_gen','queued','immutable','now','now')")
    conn.commit()
    assert pkg.save(conn, 9, [edit(sha)], 'owner@example', 'thiếu Kho 419', 0, base_refs=[]) == 1
    first = pkg.load(conn, 9)
    assert first['updated_by'] == 'owner@example' and first['updated_at']
    assert 'package_overrides' in json.loads(conn.execute('SELECT data FROM scenes').fetchone()[0])['_user_locked']
    with pytest.raises(pkg.OverrideError, match='revision'):
        pkg.save(conn, 9, [], 'owner@example', 'ghi đè', 0, base_refs=[])
    assert pkg.save(conn, 9, [], 'owner@example', 'bỏ chỉnh', 1, base_refs=[]) == 2
    assert pkg.undo(conn, 9, 1, 'owner@example', base_refs=[]) == 3
    assert pkg.load(conn, 9)['edits'] == first['edits']
    assert conn.execute('SELECT sent_package FROM jobs WHERE id=649').fetchone()[0] == 'immutable'
    assert conn.execute("SELECT count(*) FROM audit_log WHERE action='package_override'").fetchone()[0] == 3


def test_645_651_add_pin_exclude_and_changed_file_warns(setup):
    conn, path, sha = setup
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thêm Kho 419', 0, base_refs=[])
    overrides = pkg.load(conn, 9)
    refs, warnings = pkg.apply([], overrides)
    assert len(refs) == 1 and refs[0]['path'] == str(path) and not warnings
    original = [{'path': str(path), 'role': 'character', 'label': 'KELLY'}]
    pkg.save(conn, 9, [edit(sha)], 'owner', 'duyệt gói có ảnh', 1, base_refs=original)
    overrides = pkg.load(conn, 9)
    overrides['edits'][0]['op'] = 'exclude'
    assert pkg.apply(original, overrides) == ([], [])
    assert len(original) == 1
    overrides['edits'][0]['op'] = 'pin'
    assert pkg.apply(original, overrides)[0] == original
    path.write_bytes(b'doi-noi-dung')
    assert pkg.apply(original, overrides)[0] == original
    assert pkg.apply(original, overrides)[1][0]['severity'] == 'yellow'


def test_job_649_check_reuses_camera_and_cast_guards(setup, tmp_path):
    conn, path, sha = setup
    from core import location_pack, scene_storyboard
    rec = {'key': 'own', 'camera_plan': {'locked': True}, 'wide': {'key': 'wide'}}
    refs = [{'path': str(path), 'role': 'plate', 'plate_key': 'foreign'}]
    with mock.patch.object(location_pack, 'index', return_value={'9': rec}), \
            mock.patch.object(scene_storyboard, 'cast_missing', return_value=['KELLY']) as cast:
        errors = pkg.check(conn, str(tmp_path), 24, 9, refs)
    assert {e['code'] for e in errors} >= {'plate_package_mixed', 'cast_missing'}
    assert all(e['severity'] == 'red' for e in errors)
    cast.assert_called_once()
    with pytest.raises(pkg.OverrideError, match='dự án'):
        pkg.check(conn, str(tmp_path), 25, 9, refs)


def test_off_is_exact_noop(setup, monkeypatch):
    conn, path, sha = setup
    monkeypatch.setenv('FEATURE_PACKAGE_OVERRIDES', '0')
    before = conn.execute('SELECT data FROM scenes').fetchone()[0]
    refs = [{'path': 'missing', 'role': 'character'}]
    assert pkg.load(conn, 9) is None
    assert pkg.apply(refs, {'edits': [edit(sha)]}) == (refs, [])
    assert pkg.apply(refs, {})[0] is refs
    assert pkg.check(conn, 'missing', 24, 9, refs) == []
    with pytest.raises(pkg.OverrideError, match='tắt'):
        pkg.save(conn, 9, [edit(sha)], 'owner', 'thử', 0, base_refs=[])
    assert conn.execute('SELECT data FROM scenes').fetchone()[0] == before


def test_reject_path_injection_sha_and_empty_actor(setup):
    conn, path, sha = setup
    for e in [dict(edit(sha), path='secret'), edit('0' * 64)]:
        with pytest.raises(pkg.OverrideError):
            pkg.save(conn, 9, [e], 'owner', 'thử', 0, base_refs=[])
    with pytest.raises(pkg.OverrideError):
        pkg.save(conn, 9, [], '', 'thử', 0, base_refs=[])


def test_override_not_watched_or_image_lineage(setup):
    from core import change_review, lineage
    assert 'package_overrides' not in change_review.WATCH
    assert 'package_overrides' not in lineage.IMAGE_KEYS


@pytest.mark.parametrize('enabled', [True, False])
def test_replace_from_keeps_only_package_and_warns_after_replan(setup, monkeypatch, enabled):
    from core import shots
    from types import SimpleNamespace
    conn, path, sha = setup
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thêm ảnh', 0, base_refs=[])
    before = pkg.load(conn, 9)
    monkeypatch.setenv('FEATURE_PACKAGE_OVERRIDES', '1' if enabled else '0')
    pipeline = SimpleNamespace(conn=conn)
    plan = [{'idx': 1, 'shots': [shot()]}]
    shots.replace_from(pipeline, 24, plan, 1)
    row = conn.execute('SELECT id,data FROM scenes').fetchone()
    data = json.loads(row['data'])
    if enabled:
        assert data['package_overrides'] == {k: v for k, v in before.items() if k != 'stale'}
        assert data['_user_locked'] == ['package_overrides']
        assert pkg.load(conn, row['id'])['stale']
        assert pkg.apply([], pkg.load(conn, row['id']))[1][0]['code'] == 'override_stale'
    else:
        assert 'package_overrides' not in data and '_user_locked' not in data


def test_store_plan_keeps_package_and_warns(setup):
    from core import shots
    from types import SimpleNamespace
    conn, path, sha = setup
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thêm ảnh', 0, base_refs=[])
    shots.store_plan(SimpleNamespace(conn=conn), 24, [{'idx': 1, 'shots': [shot()]}])
    row = conn.execute('SELECT id,data FROM scenes').fetchone()
    assert json.loads(row['data'])['package_overrides']['revision'] == 1
    assert pkg.load(conn, row['id'])['stale']


def test_3d_649_remove_wrong_wide_then_real_guard_passes(setup, tmp_path):
    from core import place_refs
    conn, path, sha = setup
    plate_dir = tmp_path / '24' / 'plates'
    plate_dir.mkdir(parents=True)
    rec = {'key': 'own', 'plate': str(path), 'wide': {'key': 'wide', 'plate': str(path)},
           'camera_plan': {'locked': True}}
    (plate_dir / 'index.json').write_text(json.dumps({'9': rec}), encoding='utf8')
    e = {'op': 'exclude', 'source_kind': 'shot_3d', 'plate_key': 'wide', 'content_sha': sha,
         'role': place_refs.WIDE_ROLE, 'project_id': 24, 'scene_id': 9}
    pkg.save(conn, 9, [e], 'owner', 'bỏ ảnh rộng job 649', 0, data_dir=str(tmp_path), base_refs=[])
    refs = [{'path': str(path), 'role': place_refs.ROLE, 'plate_key': 'own'},
            {'path': str(path), 'role': place_refs.WIDE_ROLE, 'plate_key': 'wide'}]
    pkg.save(conn, 9, [e], 'owner', 'duyệt gói cuối', 1, data_dir=str(tmp_path), base_refs=refs)
    assert place_refs.package_problem(refs, rec)
    result, warnings = pkg.apply(refs, pkg.load(conn, 9))
    assert not warnings and len(result) == 1
    assert place_refs.package_problem(result, rec) is None
    with pytest.raises(pkg.OverrideError):
        pkg.save(conn, 9, [dict(e, scene_id=10)], 'owner', 'sai shot', 2, data_dir=str(tmp_path), base_refs=[])


def test_base_package_change_is_stale(setup):
    conn, path, sha = setup
    pkg.save(conn, 9, [edit(sha)], 'owner', 'duyệt gói rỗng', 0, base_refs=[])
    refs = [{'path': str(path), 'role': 'character', 'label': 'KELLY'}]
    result, warnings = pkg.apply(refs, pkg.load(conn, 9))
    assert result == refs and warnings[0]['code'] == 'override_stale'


@pytest.mark.parametrize('status', ['pending', 'removed', 'redundant'])
def test_reject_unusable_library_image(setup, status):
    conn, path, sha = setup
    conn.execute('UPDATE asset_images SET status=? WHERE id=419', (status,))
    before = conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0]
    with pytest.raises(pkg.OverrideError):
        pkg.save(conn, 9, [edit(sha)], 'owner', 'thử', 0, base_refs=[])
    assert conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0] == before
    assert conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 0


def test_reject_unselected_asset_and_wrong_look(setup):
    conn, path, sha = setup
    conn.execute('DELETE FROM project_assets')
    with pytest.raises(pkg.OverrideError):
        pkg.save(conn, 9, [edit(sha)], 'owner', 'thử', 0, base_refs=[])
    conn.execute('INSERT INTO project_assets(project_id,asset_id) VALUES(24,419)')
    conn.execute("UPDATE projects SET look='FF_INGAME' WHERE id=24")
    conn.execute("UPDATE asset_images SET look='anime' WHERE id=419")
    with pytest.raises(pkg.OverrideError):
        pkg.save(conn, 9, [dict(edit(sha), look='ingame')], 'owner', 'thử', 0, base_refs=[])


def test_pin_plate_and_undo_memory_replan(setup, tmp_path):
    from core import place_refs
    conn, path, sha = setup
    plate_dir = tmp_path / '24' / 'plates'
    plate_dir.mkdir(parents=True)
    rec = {'key': 'own', 'plate': str(path), 'place': 'Quảng trường', 'camera_plan': {'locked': True}}
    index_path = plate_dir / 'index.json'
    index_path.write_text(json.dumps({'9': rec}), encoding='utf8')
    refs = [{'path': str(path), 'role': place_refs.ROLE, 'plate_key': 'own', 'label': 'Quảng trường', '_rec': rec}]
    e = {'op': 'pin', 'source_kind': 'shot_3d', 'plate_key': 'own', 'content_sha': sha,
         'role': place_refs.ROLE, 'project_id': 24, 'scene_id': 9}
    pkg.save(conn, 9, [e], 'owner', 'ghim nền', 0, data_dir=str(tmp_path), base_refs=refs)
    result, warnings = pkg.apply(refs, pkg.load(conn, 9))
    assert not warnings and len(result) == 1 and result[0]['label'] == 'Quảng trường'
    assert place_refs.package_problem(result, rec) is None
    pkg.save(conn, 9, [], 'owner', 'bỏ chỉnh', 1, data_dir=str(tmp_path), base_refs=refs)
    assert pkg.undo(conn, 9, 1, 'owner', data_dir=str(tmp_path), base_refs=refs) == 3
    conn.execute('UPDATE scenes SET id=10 WHERE id=9')
    index_path.write_text(json.dumps({'10': rec}), encoding='utf8')
    assert pkg.undo(conn, 10, 1, 'owner', data_dir=str(tmp_path), base_refs=refs) == 4
    assert pkg.load(conn, 10)['edits'][0]['scene_id'] == 10
    index_path.write_text(json.dumps({'10': dict(rec, key='different')}), encoding='utf8')
    with pytest.raises(pkg.OverrideError):
        pkg.undo(conn, 10, 1, 'owner', data_dir=str(tmp_path), base_refs=refs)


def test_undo_accepts_3d_root(setup, tmp_path):
    from core import place_refs
    conn, path, sha = setup
    plate_dir = tmp_path / '24' / 'plates'
    plate_dir.mkdir(parents=True)
    (plate_dir / 'index.json').write_text(json.dumps({'9': {'key': 'own', 'plate': str(path)}}), encoding='utf8')
    e = {'op': 'add', 'source_kind': 'shot_3d', 'plate_key': 'own', 'content_sha': sha,
         'role': place_refs.ROLE, 'project_id': 24, 'scene_id': 9}
    pkg.save(conn, 9, [e], 'owner', 'thêm nền', 0, data_dir=str(tmp_path), base_refs=[])
    pkg.save(conn, 9, [], 'owner', 'bỏ chỉnh', 1, data_dir=str(tmp_path), base_refs=[])
    assert pkg.undo(conn, 9, 1, 'owner', data_dir=str(tmp_path), base_refs=[]) == 3


def test_real_cast_missing_419_cleared_after_add(setup, tmp_path):
    conn, path, sha = setup
    conn.execute("INSERT INTO characters(project_id,name,description,ref_asset_id,ref_image_ids) VALUES(24,'KELLY','thử',419,'[419]')")
    conn.commit()
    assert any(e['code'] == 'cast_missing' for e in pkg.check(conn, str(tmp_path), 24, 9, []))
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thêm Kho 419', 0, base_refs=[])
    refs, warnings = pkg.apply([], pkg.load(conn, 9))
    assert not warnings
    assert not any(e['code'] == 'cast_missing' for e in pkg.check(conn, str(tmp_path), 24, 9, refs))


def test_trigger_records_change_but_watch_ignores_it(setup):
    from core import change_review
    conn, path, sha = setup
    conn.execute('DELETE FROM change_events')
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thêm ảnh', 0, base_refs=[])
    event = conn.execute("SELECT before,after FROM change_events WHERE kind='scene'").fetchone()
    assert event is not None
    assert change_review.changed_keys(json.loads(event[0]), json.loads(event[1]), list(change_review.WATCH)) == []

def test_d10_missing_base_refs_is_clear_and_atomic(setup):
    conn, _, sha = setup
    before = conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0]
    with pytest.raises(pkg.OverrideError, match='base_refs'):
        pkg.save(conn, 9, [edit(sha)], 'owner', 'ghim', 0)
    assert conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0] == before
    assert conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 0


def test_d10_motion_metadata_does_not_stale_package(setup):
    conn, _, sha = setup
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thử', 0, base_refs=[])
    data = json.loads(conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0])
    data.update(motion_en='move', takes=[1], camera_plan={'why': 'move'})
    conn.execute('UPDATE scenes SET data=? WHERE id=9', (json.dumps(data),))
    assert not pkg.load(conn, 9)['stale']
    data['size'] = 'CU'
    conn.execute('UPDATE scenes SET data=? WHERE id=9', (json.dumps(data),))
    assert pkg.load(conn, 9)['stale']


def test_d10_pin_preserves_secondary_character_angle(setup, tmp_path):
    conn, path, sha = setup
    side = tmp_path / 'side.png'
    side.write_bytes(b'side')
    refs = [{'path': str(path), 'role': 'character', 'label': 'KELLY'},
            {'path': str(side), 'role': 'character', 'label': 'KELLY'}]
    pkg.save(conn, 9, [edit(sha, 'pin')], 'owner', 'ghim', 0, base_refs=refs)
    assert pkg.apply(refs, pkg.load(conn, 9)) == (refs, [])


def test_d10_outfit_pin_targets_wearer(setup, tmp_path):
    conn, path, sha = setup
    conn.execute("UPDATE assets SET kind='outfit', name='Kelly đồ bơi' WHERE id=419")
    old = tmp_path / 'old.png'
    old.write_bytes(b'old')
    refs = [{'path': str(old), 'role': 'outfit', 'label': 'KELLY'},
            {'path': str(old), 'role': 'outfit', 'label': 'OTHER'}]
    e = dict(edit(sha, 'pin'), role='outfit', wearer='KELLY')
    pkg.save(conn, 9, [e], 'owner', 'đổi đồ', 0, base_refs=refs)
    result, warnings = pkg.apply(refs, pkg.load(conn, 9))
    assert not warnings
    assert result == [dict(refs[0], path=str(path)), refs[1]]


def test_d10_unreadable_warning_is_not_repeated(setup):
    conn, path, sha = setup
    refs = [{'path': 'missing', 'role': 'character', 'label': 'KELLY'}]
    pkg.save(conn, 9, [edit(sha), edit(sha)], 'owner', 'thử', 0, base_refs=refs)
    _, warnings = pkg.apply(refs, pkg.load(conn, 9))
    assert [w['code'] for w in warnings].count('ref_unreadable') == 1

@pytest.mark.parametrize('method', ['replace_from', 'store_plan'])
def test_d10_orphan_replan_reports_yellow(setup, method):
    from core import shots, diag
    from types import SimpleNamespace
    conn, _, sha = setup
    data = json.loads(conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0])
    data['shot_no'] = 2
    conn.execute('UPDATE scenes SET data=? WHERE id=9', (json.dumps(data),))
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thử', 0, base_refs=[])
    args = [SimpleNamespace(conn=conn), 24, [{'idx': 1, 'shots': [shot()]}]]
    if method == 'replace_from':
        args.append(1)
    with mock.patch.object(diag, 'record') as record:
        getattr(shots, method)(*args)
    calls = [c for c in record.call_args_list if c.kwargs.get('code') == 'override_orphaned']
    assert len(calls) == 1 and calls[0].args[2] == 'warn'


@pytest.mark.parametrize('key', ['characters', 'location_asset', 'image_prompt', 'blocking', 'layout',
                                 'size', 'outfit', 'plate_key', 'stage_camera'])
def test_d10_image_input_changes_hash(key):
    assert pkg._scene_hash({}) != pkg._scene_hash({key: 'changed'})

@pytest.mark.parametrize('target', [{}, {'character': 'KELLY'}, {'wearer': 'KELLY'}])
def test_d10_outfit_single_slot_and_alias(setup, target):
    conn, path, sha = setup
    conn.execute("UPDATE assets SET kind='outfit', name='Kelly đồ bơi' WHERE id=419")
    refs = [{'path': str(path), 'role': 'outfit', 'label': 'KELLY'}]
    e = dict(edit(sha, 'pin'), role='outfit', **target)
    pkg.save(conn, 9, [e], 'owner', 'ghim', 0, base_refs=refs)
    assert pkg.apply(refs, pkg.load(conn, 9)) == (refs, [])
    assert pkg.load(conn, 9)['edits'][0]['wearer'] == 'KELLY'


def test_d10_outfit_ambiguous_rejected_without_write(setup):
    conn, path, sha = setup
    conn.execute("UPDATE assets SET kind='outfit', name='Kelly đồ bơi' WHERE id=419")
    refs = [{'path': str(path), 'role': 'outfit', 'label': name} for name in ('KELLY', 'OTHER')]
    before = conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0]
    with pytest.raises(pkg.OverrideError, match='wearer/character'):
        pkg.save(conn, 9, [dict(edit(sha, 'pin'), role='outfit')], 'owner', 'ghim', 0, base_refs=refs)
    assert conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0] == before
    assert conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 0


def test_d10_pin_existing_side_does_not_duplicate_it(setup, tmp_path):
    conn, path, sha = setup
    front = tmp_path / 'front.png'
    front.write_bytes(b'front')
    refs = [{'path': str(front), 'role': 'character', 'label': 'KELLY'},
            {'path': str(path), 'role': 'character', 'label': 'KELLY'}]
    pkg.save(conn, 9, [edit(sha, 'pin')], 'owner', 'ghim góc phụ', 0, base_refs=refs)
    assert pkg.apply(refs, pkg.load(conn, 9)) == (refs, [])


def test_d10_relative_library_path_uses_explicit_root(setup, tmp_path, monkeypatch):
    conn, path, sha = setup
    conn.execute("UPDATE asset_images SET path='419.png' WHERE id=419")
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (elsewhere / '419.png').write_bytes(b'wrong cwd')
    monkeypatch.chdir(elsewhere)
    pkg.save(conn, 9, [edit(sha)], 'owner', 'thử root', 0, data_dir=str(tmp_path), base_refs=[])
    refs, warnings = pkg.apply([], pkg.load(conn, 9))
    assert refs[0]['path'] == str(path) and not warnings

@pytest.mark.parametrize('target', [{}, {'wearer': 'OTHER'}, {'character': 'OTHER'}])
def test_d10_outfit_wearer_must_belong_to_shot_even_when_inferred(setup, target):
    conn, path, sha = setup
    conn.execute("UPDATE assets SET kind='outfit', name='Kelly đồ bơi' WHERE id=419")
    refs = [{'path': str(path), 'role': 'outfit', 'label': 'OTHER'}]
    before = conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0]
    with pytest.raises(pkg.OverrideError, match='không có trong shot'):
        pkg.save(conn, 9, [dict(edit(sha, 'pin'), role='outfit', **target)],
                 'owner', 'ghim', 0, base_refs=refs)
    assert conn.execute('SELECT data FROM scenes WHERE id=9').fetchone()[0] == before
    assert conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 0


def test_missing_base_refs_has_actionable_error_before_scene_lookup(setup):
    conn, path, sha = setup
    with pytest.raises(pkg.OverrideError, match='base_refs.*tải lại'):
        pkg.save(conn, 999, [], 'owner', 'chỉnh', 0)
    with pytest.raises(pkg.OverrideError, match='base_refs.*tải lại'):
        pkg.undo(conn, 999, 1, 'owner')
