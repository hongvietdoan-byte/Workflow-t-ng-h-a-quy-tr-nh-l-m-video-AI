"""Hồi quy CX21, chỉ CSDL và provider tổng hợp."""
import os
import json
import sqlite3
import threading
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def isolated():
    with patch.object(os, 'environ', {}):
        yield


@pytest.mark.parametrize('present,related,code', [(True, True, 'READY'), (False, False, 'READY'),
                                                (False, True, 'QUEUE_UNKNOWN_CAPACITY')])
def test_processing_null_reconcile(tmp_path, present, related, code):
    from core import subjects
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    pic = tmp_path / 'pic.png'
    pic.write_bytes(b'fixture')
    sha = subjects.picture_sha(pic)
    subjects._save_picture(conn, sha if related else 'unrelated', 'fixture', 'processing', path=str(pic))
    asset = {'name': 'fixture', 'asset_id': 'a', 'asset_uri': 'asset://a', 'provider_status': 'active'}
    lib = Mock()
    lib.list_assets.return_value = [asset] if present else []
    result = subjects.capacity(conn, lib, [('pic', str(pic))], limit=2)
    assert result['code'] == code
    if present:
        assert result['needed'] == 0
        for _ in range(2):
            assert subjects.ensure_picture(conn, lib, str(pic), 'fixture')['asset_id'] == 'a'
            lib.get.return_value = asset
        assert subjects.picture_row(conn, sha)['status'] == 'active'
        lib.upload.assert_not_called()
    if not related:
        assert result['free'] == 1


def test_inbox_cold_database_readonly():
    from core import subjects
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA query_only=ON')
    assert subjects.rejected_frame_assets(conn, 1) == []
    assert conn.execute('SELECT name FROM sqlite_master').fetchall() == []


def test_processing_named_asset_already_occupies_one_slot(tmp_path):
    from core import subjects
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
    pic = tmp_path / 'pic.png'; pic.write_bytes(b'fixture')
    subjects._save_picture(conn, subjects.picture_sha(pic), 'fixture', 'processing', path=str(pic))
    lib = Mock()
    lib.list_assets.return_value = [{'asset_id': 'a', 'name': 'fixture', 'provider_status': 'processing'}]
    result = subjects.capacity(conn, lib, [('pic', str(pic))], limit=1)
    assert result['code'] == 'READY' and result['count'] == 1 and result['needed'] == 0


def test_two_submit_passes_reconcile_null_without_duplicate(tmp_path):
    from contextlib import ExitStack
    from core import subjects, features, video_pregen
    from core.db import connect
    from core.pipeline import Pipeline
    from core.runner import VideoRunner
    from core.providers import MockVideoProvider
    pipeline = Pipeline(connect())
    pid = pipeline.create_project('synthetic')
    jid = pipeline.create_job(pipeline.create_scene(pid, 1, 'synthetic'), 'video_gen')
    pic = tmp_path / 'pic.png'; pic.write_bytes(b'fixture')
    sha = subjects.picture_sha(pic)
    subjects._save_picture(pipeline.conn, sha, 'fixture', 'processing', path=str(pic))
    provider = MockVideoProvider()
    provider.supports_subjects = provider.supports_aspect = True
    runner = VideoRunner(pipeline, provider, str(tmp_path))
    runner.subject_library = lib = Mock()
    asset = {'name': 'fixture', 'asset_id': 'a', 'asset_uri': 'asset://a', 'provider_status': 'active'}
    lib.list_assets.return_value = [asset]
    with ExitStack() as stack:
        stack.enter_context(patch.object(features, 'on', side_effect=lambda n: n in ('seedance_subjects', 'subject_capacity_guard')))
        stack.enter_context(patch.object(video_pregen, 'enabled', return_value=True))
        for name, value in (('_wait', False), ('_blocked', None), ('_gate_hold', None), ('_pregen', False),
                            ('_over_budget', None), ('_stamp', {}), ('_record_usage', None), ('_write_sent_package', [])):
            stack.enter_context(patch.object(runner, name, return_value=value))
        stack.enter_context(patch.object(runner, '_submit_args', return_value=(str(pic), 'synthetic', None, 5)))
        stack.enter_context(patch.object(runner, '_submit_kwargs', side_effect=lambda job: {'image_references': runner._hosted_pictures(job, [('pic', str(pic))])}))
        submit = stack.enter_context(patch.object(provider, 'submit', return_value='synthetic-task'))
        assert runner.submit_pending(pid) == 1
        assert runner.submit_pending(pid) == 0
    assert pipeline.job(jid)['state'] == 'running'
    assert subjects.picture_row(pipeline.conn, sha)['status'] == 'active'
    submit.assert_called_once()
    lib.upload.assert_not_called()
    pipeline.conn.close()


def test_capacity_get_before_finish_lock(tmp_path):
    from core import features, subjects, budget, video_pregen
    from core.runner import VideoRunner
    runner = object.__new__(VideoRunner)
    runner.p = Mock(conn=sqlite3.connect(':memory:'))
    runner.provider = Mock(supports_subjects=True)
    runner.subject_library = lib = Mock()
    runner._diag = Mock()
    pic = tmp_path / 'pic.png'; pic.write_bytes(b'fixture')
    checked = []
    def slow_snapshot(**kwargs):
        obtained = []
        def probe():
            got = budget.SPEND_LOCK.acquire(timeout=.1)
            obtained.append(got)
            if got:
                budget.SPEND_LOCK.release()
        thread = threading.Thread(target=probe); thread.start(); thread.join()
        checked.append(obtained == [True])
        return []
    lib.list_assets.side_effect = slow_snapshot
    with patch.object(features, 'on', return_value=True), patch.object(video_pregen, 'enabled', return_value=True), \
         patch.object(runner, '_submit_kwargs', side_effect=lambda job: {'refs': runner._hosted_pictures(job, [('pic', str(pic))])}), \
         patch.object(subjects, 'picture_refs', return_value={'refs': [{'uri': 'asset://a', 'uploaded': False}]}):
        kwargs = runner._prepare_kwargs({'id': 1, 'project_id': 1})
        with budget.SPEND_LOCK:
            runner._finish_kwargs({'id': 1, 'project_id': 1}, kwargs)
    assert checked == [True]


def test_structural_three_way_keeps_mappings():
    from tools import merge_union
    base = {'version': 1, 'areas': [{'id': 'a', 'code': ['old'], 'tests': []}]}
    ours = {'version': 1, 'areas': [{'id': 'a', 'code': ['old', 'ours'], 'tests': []}, {'id': 'b', 'code': ['b']}]}
    theirs = {'version': 1, 'areas': [{'id': 'a', 'code': ['old'], 'tests': ['theirs']}, {'id': 'c', 'code': ['c']}]}
    merged = merge_union.merge_json(base, json.loads(json.dumps(ours, indent=2)), theirs)
    assert [a['id'] for a in merged['areas']] == ['a', 'b', 'c']
    assert merged['areas'][0] == {'id': 'a', 'code': ['old', 'ours'], 'tests': ['theirs']}
    assert '"code": ["old", "ours"]' in merge_union.format_json(merged)


def test_invalid_stage_does_not_write(tmp_path):
    from tools import merge_union
    target = tmp_path / 'areas.json'; target.write_text('conflict', encoding='utf-8')
    with patch.object(merge_union, 'read_stage', side_effect=['{}', '{broken', '{}']):
        with pytest.raises(ValueError):
            merge_union.resolve_json(target)
    assert target.read_text(encoding='utf-8') == 'conflict'


def test_three_way_deletion_and_scalar_conflict():
    from tools import merge_union
    base = {'areas': [{'id': 'a', 'code': ['a']}, {'id': 'b', 'code': ['b']}]}
    ours = {'areas': [{'id': 'b', 'code': ['b', 'new']}]}
    theirs = {'areas': [{'id': 'a', 'code': ['a']}, {'id': 'b', 'code': ['b'], 'tests': ['t']}]}
    result = merge_union.merge_json(base, ours, theirs)
    assert result == {'areas': [{'id': 'b', 'code': ['b', 'new'], 'tests': ['t']}]}
    assert json.loads(merge_union.format_json(result)) == result
    with pytest.raises(ValueError):
        merge_union.merge_json({'version': 1}, {'version': 2}, {'version': 3})


def test_stage_git_uses_whitelist_and_repo_relative_path(tmp_path):
    from tools import merge_union
    target = tmp_path / 'areas.json'
    with patch.object(merge_union.Path, 'is_file', return_value=True), \
         patch.object(merge_union.subprocess, 'run', side_effect=[Mock(stdout=str(tmp_path)), Mock(stdout='{}')]) as run:
        assert merge_union.read_stage(target, 2) == '{}'
    assert run.call_args.args[0][-1] == ':2:areas.json'
    assert run.call_args.kwargs['env'] == ({'SYSTEMROOT': 'C:/Windows'} if os.name == 'nt' else {})


def test_resolve_complete_multiline_stages_preserves_twenty_areas(tmp_path):
    from tools import merge_union
    target = tmp_path / 'areas.json'; target.write_text('conflict', encoding='utf-8')
    base = {'version': 88, 'areas': [{'id': 'shared', 'code': ['base'], 'tests': []}]}
    ours = {'version': 88, 'areas': [{'id': 'shared', 'code': ['base', 'left'], 'tests': []}] +
            [{'id': str(i), 'code': ['module' + str(i)]} for i in range(10)]}
    theirs = {'version': 88, 'areas': [{'id': 'shared', 'code': ['base'], 'tests': ['right']}] +
              [{'id': str(i), 'code': ['module' + str(i)]} for i in range(10, 20)]}
    stages = [json.dumps(base), json.dumps(ours, indent=4), json.dumps(theirs)]
    with patch.object(merge_union, 'read_stage', side_effect=stages):
        merge_union.resolve_json(target)
    got = json.loads(target.read_text(encoding='utf-8'))
    assert len(got['areas']) == 21
    assert got['areas'][0] == {'id': 'shared', 'code': ['base', 'left'], 'tests': ['right']}
    assert {a['id']: a['code'] for a in got['areas'][1:]} == {str(i): ['module' + str(i)] for i in range(20)}


def test_merge_union_deleted_on_one_side_stays_deleted():
    """CX21-FIX2 (rà C-RA-FIX21): list không id — A xóa f2, B thêm fB → kết quả ["f1", "f3", "fB"], f2 không sống lại."""
    from tools import merge_union
    base = {"files": ["f1", "f2", "f3"]}
    ours = {"files": ["f1", "f3"]}
    theirs = {"files": ["f1", "f2", "f3", "fB"]}
    assert merge_union.merge_json(base, ours, theirs) == {"files": ["f1", "f3", "fB"]}
    assert merge_union.merge_json(base, theirs, ours) == {"files": ["f1", "f3", "fB"]}         # đổi phía: vẫn không sống lại
    both_add = merge_union.merge_json(["a"], ["a", "x"], ["a", "y"])            # cùng thêm khác mục → giữ cả hai, thứ tự ours trước
    assert both_add == ["a", "x", "y"]
    assert merge_union.merge_json(None, ["a", "x"], ["a", "y"]) == ["a", "x", "y"]   # base không phải list → union như cũ
