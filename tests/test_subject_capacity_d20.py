"""Đ20: dữ liệu giả, provider đóng kín, không mạng hay CSDL sản xuất."""
import os
import sqlite3
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def isolated():
    with patch.object(os, 'environ', {}):
        yield


def test_full_100_capacity_no_upload(tmp_path):
    from core import subjects
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE seedance_subject_pictures (sha TEXT, status TEXT, asset_id TEXT)')
    pic = tmp_path / 'new.png'
    pic.write_bytes(b'fake picture')
    lib = Mock()
    lib.list_assets.return_value = [{'asset_id': str(i), 'provider_status': 'active'} for i in range(100)]
    result = subjects.capacity(conn, lib, [('new', str(pic))])
    assert result['code'] == 'QUEUE_CAPACITY'
    assert (result['count'], result['needed'], result['free']) == (100, 1, 0)
    lib.upload.assert_not_called()
    lib.delete_many.assert_not_called()


def test_network_list_fail_yellow_zero_delete():
    from core import subjects
    lib = Mock()
    lib.list_assets.side_effect = OSError('offline')
    result = subjects.capacity(sqlite3.connect(':memory:'), lib, [('new', 'unused')])
    assert result['code'] == 'QUEUE_UNKNOWN_CAPACITY'
    assert result['severity'] == 'warn'
    lib.delete_many.assert_not_called()


@pytest.mark.parametrize('payload', [None, {}, {'assets': None}, {'assets': {}}])
def test_native_malformed_snapshot_holds_unknown(payload, tmp_path):
    from core import subjects
    from core.adapters.clipai_subjects import ClipAISubjectLibrary
    lib = object.__new__(ClipAISubjectLibrary)
    lib.client, lib._sleep = Mock(), Mock()
    lib.client.get.return_value = payload
    pic = tmp_path / 'fixture.png'
    pic.write_bytes(b'fixture')
    with patch.object(lib, 'upload') as upload, patch.object(lib, 'delete_many') as delete:
        result = subjects.capacity(sqlite3.connect(':memory:'), lib, [('new', str(pic))])
    assert result['code'] == 'QUEUE_UNKNOWN_CAPACITY'
    upload.assert_not_called()
    delete.assert_not_called()


@pytest.mark.parametrize('payload', [{'assets': [], 'count': 100}, {'assets': [], 'count': -1},
                                    {'assets': [], 'count': '100'}])
def test_native_inconsistent_count_holds_unknown(payload, tmp_path):
    from core import subjects
    from core.adapters.clipai_subjects import ClipAISubjectLibrary
    lib = object.__new__(ClipAISubjectLibrary)
    lib.client, lib._sleep = Mock(), Mock()
    lib.client.get.return_value = payload
    pic = tmp_path / 'fixture.png'
    pic.write_bytes(b'fixture')
    with patch.object(lib, 'upload') as upload, patch.object(lib, 'delete_many') as delete:
        result = subjects.capacity(sqlite3.connect(':memory:'), lib, [('new', str(pic))])
    assert result['code'] == 'QUEUE_UNKNOWN_CAPACITY'
    upload.assert_not_called()
    delete.assert_not_called()


def test_job_without_subject_refs_skips_capacity_queue():
    from core import subjects
    lib = Mock()
    assert subjects.capacity(None, lib, [])['code'] == 'READY'
    lib.list_assets.assert_not_called()


def test_candidates_eight_eligible_three_protected():
    from core import subjects
    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    evidence = []
    for i in range(11):
        evidence.append({'asset_id': str(i), 'verified': True, 'owners_complete': True,
                         'project_refs': [{'project_id': 1, 'state': 'archived',
                                           'terminal_at': '2026-10-16T00:00:00+00:00'}],
                         'job_refs': [{'job_id': i, 'state': 'rejected', 'type': 'image_gen'}] if i < 5 else [],
                         'character_refs': []})
    for i in (8, 9):
        evidence[i]['project_refs'][0]['terminal_at'] = '2026-10-19T00:00:00+00:00'
    evidence[10]['project_refs'].append({'project_id': 2, 'state': 'active'})
    assets = [{'asset_id': str(i), 'provider_status': 'active'} for i in range(11)]
    result = subjects.auto_clean_candidates(assets, evidence, now=now)
    assert len(result['eligible']) == 8
    assert len(result['protected']) == 3
    assert result['dry_run'] is True
    assert result['plan_hash']


def test_unknown_character_processing_restore_veto():
    from core import subjects
    base = {'asset_id': 'a', 'verified': True, 'owners_complete': True,
            'project_refs': [{'project_id': 1, 'state': 'archived', 'terminal_at': '2026-10-01T00:00:00+00:00'}],
            'job_refs': [], 'character_refs': []}
    for changes in ({'verified': False}, {'character_refs': [1]}, {'processing': True},
                    {'project_refs': [{'project_id': 1, 'state': 'restored'}]},
                    {'job_refs': [{'job_id': 4, 'state': 'running'}]}):
        evidence = dict(base, **changes)
        assert not subjects.auto_clean_candidates([{'asset_id': 'a', 'provider_status': 'active'}], [evidence])['eligible']


def test_runner_capacity_hold_no_marked_no_kling(tmp_path):
    from core import subjects, features
    from core.runner import VideoRunner
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE seedance_subject_pictures (sha TEXT, status TEXT, asset_id TEXT)')
    pic = tmp_path / 'new.png'
    pic.write_bytes(b'new')
    runner = object.__new__(VideoRunner)
    runner.p = Mock(conn=conn)
    runner.provider = Mock(supports_subjects=True)
    runner.subject_library = lib = Mock()
    lib.list_assets.return_value = [{'asset_id': str(i), 'provider_status': 'active'} for i in range(100)]
    with patch.object(features, 'on', return_value=True):
        with pytest.raises(subjects.CapacityWait) as held:
            runner._hosted_pictures({'id': 1, 'project_id': 1}, [('new', str(pic))])
        runner._diag_once = Mock()
        assert runner._pregen_prepare_error({'id': 1}, held.value)
    lib.upload.assert_not_called()
    runner.provider.submit.assert_not_called()


def test_g59_fix_keeps_legacy_cleanup_dry_run():
    from core import subjects
    lib = Mock()
    found = [{'asset_id': 'a', 'name': 'frame', 'job_id': 1}]
    with patch.object(subjects, 'rejected_frame_assets', return_value=found), patch.object(subjects, '_cleanup_note'):
        result = subjects.run_auto_cleanup(None, 1, 'giao', library=lib)
    assert result['deleted'] == []
    assert result['plan']['dry_run']
    lib.delete_many.assert_not_called()
    lib.delete.assert_not_called()


def test_cold_db_checks_capacity_without_creating_schema(tmp_path):
    from core import subjects
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    pic = tmp_path / 'new.png'
    pic.write_bytes(b'new')
    lib = Mock()
    lib.list_assets.return_value = []
    assert subjects.capacity(conn, lib, [('new', str(pic))])['code'] == 'READY'
    assert not conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()


def test_existing_sha_full_library_needs_no_upload(tmp_path):
    from core import subjects
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE seedance_subject_pictures (sha TEXT, status TEXT, asset_id TEXT)')
    pic = tmp_path / 'old.png'
    pic.write_bytes(b'old')
    conn.execute('INSERT INTO seedance_subject_pictures VALUES (?, ?, ?)', (subjects.picture_sha(pic), 'active', '0'))
    lib = Mock()
    lib.list_assets.return_value = [{'asset_id': str(i), 'asset_uri': 'asset://' + str(i), 'provider_status': 'active'} for i in range(100)]
    check = subjects.capacity(conn, lib, [('old', str(pic)), ('duplicate', str(pic))])
    assert check['code'] == 'READY'
    assert check['needed'] == 0


def test_actual_submit_loop_keeps_job_queued_full_no_kling(tmp_path):
    from core import features
    from core.db import connect
    from core.pipeline import Pipeline
    from core.runner import VideoRunner, held_reason
    from core.providers import MockVideoProvider
    p = Pipeline(connect())
    pid = p.create_project('fixture 100/100')
    sid = p.create_scene(pid, 1, 'fixture')
    jid = p.create_job(sid, 'video_gen')
    pic = tmp_path / 'new.png'
    pic.write_bytes(b'new')
    provider = MockVideoProvider()
    provider.supports_subjects = provider.supports_aspect = True
    runner = VideoRunner(p, provider, str(tmp_path))
    runner.subject_library = lib = Mock()
    lib.list_assets.return_value = [{'asset_id': str(i), 'provider_status': 'active'} for i in range(100)]
    with patch.object(features, 'on', side_effect=lambda name: name in ('seedance_subjects', 'subject_capacity_guard')), \
         patch.object(runner, '_wait', return_value=False), patch.object(runner, '_blocked', return_value=None), \
         patch.object(runner, '_gate_hold', return_value=None), patch.object(runner, '_submit_args', return_value=('seedance', 'fixture')), \
         patch.object(runner, '_prepare_kwargs', side_effect=lambda job: runner._hosted_pictures(job, [('new', str(pic))])), \
         patch.object(provider, 'submit', side_effect=AssertionError('no paid submit')) as submit:
        assert runner.submit_pending(pid) == 0
        assert runner.submit_pending(pid) == 0
        assert lib.list_assets.call_count == 1
    assert p.job(jid)['state'] == 'queued'
    assert p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0] == 1
    assert '100/100' in held_reason(p.conn, jid)
    submit.assert_not_called()
    lib.upload.assert_not_called()
    p.conn.close()


def test_factory_reuses_configured_video_client_without_env_fallback():
    from core.adapters import factory
    from core.adapters.clipai import ClipAIVideoProvider
    provider = object.__new__(ClipAIVideoProvider)
    provider.client = Mock()
    lib = factory.subject_library(video_provider=provider)
    assert lib.client is provider.client
    provider.client.get.assert_not_called()


def test_cleanup_cli_readonly_and_no_schema(tmp_path, capsys):
    import json
    from tools.subject_cleanup import main
    db = tmp_path / 'fixture.sqlite'
    sqlite3.connect(db).close()
    before = db.read_bytes()
    snapshot = tmp_path / 'assets.json'
    snapshot.write_text(json.dumps([{'asset_id': 'unknown', 'provider_status': 'active'}]), encoding='utf-8')
    assert main(['--db', str(db), '--snapshot', str(snapshot)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['eligible'] == []
    assert report['protected'][0]['asset_id'] == 'unknown'
    assert db.read_bytes() == before


def test_guard_off_native_get_and_upload_keep_legacy_short_snapshot(tmp_path):
    from core import features
    from core.adapters.clipai_subjects import ClipAISubjectLibrary
    lib = object.__new__(ClipAISubjectLibrary)
    lib.client, lib._sleep = Mock(), Mock()
    lib.poll_sec, lib.timeout_sec = 0, 1
    old = {'asset_id': 'old', 'asset_uri': 'asset://old', 'provider_status': 'active', 'name': 'old'}
    new = dict(old, asset_id='new', asset_uri='asset://new', name='fixture')
    pic = tmp_path / 'fixture.png'
    pic.write_bytes(b'fixture')
    with patch.object(features, 'on', return_value=False):
        lib.client.get.side_effect = [{'assets': [old], 'count': 100}, {'assets': [old], 'count': 100},
                                      {'assets': [old, new], 'count': 100}]
        assert lib.get('old') == old
        assert lib.upload(str(pic), 'fixture') == new


@pytest.mark.parametrize('aid, expected', [('other', 'READY'), (None, 'READY'),
                                         ('missing', 'READY')])
def test_processing_snapshot_evidence_only_blocks_unresolved(aid, expected, tmp_path):
    from core import subjects
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE seedance_subject_pictures (sha TEXT, status TEXT, asset_id TEXT)')
    conn.execute('INSERT INTO seedance_subject_pictures VALUES (?, ?, ?)', ('other-sha', 'processing', aid))
    pic = tmp_path / 'new.png'
    pic.write_bytes(b'new')
    lib = Mock()
    lib.list_assets.return_value = [{'asset_id': 'other', 'provider_status': 'processing'}]
    assert subjects.capacity(conn, lib, [('new', str(pic))])['code'] == expected


def test_capacity_cooling_expires_and_flag_off_bypasses():
    from core import subjects, features, video_pregen
    from core.runner import VideoRunner, PREGEN_RECHECK_S
    runner = object.__new__(VideoRunner)
    runner._diag_once = Mock()
    error = subjects.CapacityWait({'code': 'QUEUE_CAPACITY', 'reason': 'fixture full'})
    with patch.object(features, 'on', return_value=True), patch.object(video_pregen, 'enabled', return_value=False), \
         patch('core.runner.time.time', return_value=100):
        assert runner._pregen_prepare_error({'id': 1}, error)
        assert runner._pregen_cooling({'id': 1})
    with patch.object(features, 'on', return_value=True), patch.object(video_pregen, 'enabled', return_value=False), \
         patch('core.runner.time.time', return_value=100 + PREGEN_RECHECK_S):
        assert not runner._pregen_cooling({'id': 1})
    with patch.object(features, 'on', return_value=False), patch.object(video_pregen, 'enabled', return_value=False), \
         patch('core.runner.time.time', return_value=100):
        assert runner._pregen_prepare_error({'id': 1}, error)
        assert not runner._pregen_cooling({'id': 1})


def test_cleanup_inbox_drops_stale_plan_without_candidates():
    from core import subjects, inbox, diag
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project('fixture stale plan')
    p.conn.execute('UPDATE projects SET archived=1 WHERE id=?', (pid,))
    p.conn.commit()
    diag.record(p.conn, 'video', 'warn', 'fixture plan', code='subject_cleanup_plan', project_id=pid)
    with patch.object(subjects, 'rejected_frame_assets', return_value=[{'asset_id': 'a'}]):
        assert any(i['kind'] == 'Kho chủ thể' for i in inbox.items(p.conn, 'fixture@example.test'))
    with patch.object(subjects, 'rejected_frame_assets', return_value=[]):
        assert not any(i['kind'] == 'Kho chủ thể' for i in inbox.items(p.conn, 'fixture@example.test'))
    p.conn.close()


def test_guard_off_uses_legacy_factory_signature(tmp_path):
    from core import features, subjects
    from core.runner import VideoRunner
    from core.adapters import factory
    runner = object.__new__(VideoRunner)
    runner.provider = Mock(supports_subjects=True)
    runner.p = Mock(conn=Mock())
    runner._diag = Mock()
    lib = Mock()
    with patch.object(features, 'on', side_effect=lambda name: name == 'seedance_subjects'), \
         patch.object(factory, 'subject_library', return_value=lib) as make, \
         patch.object(subjects, 'capacity', side_effect=AssertionError('guard OFF')), \
         patch.object(subjects, 'picture_refs', return_value={'refs': [{'uri': 'asset://fixture', 'uploaded': False}]}):
        assert runner._hosted_pictures({'id': 1, 'project_id': 1}, [('fixture', 'unused')])
    make.assert_called_once_with()
