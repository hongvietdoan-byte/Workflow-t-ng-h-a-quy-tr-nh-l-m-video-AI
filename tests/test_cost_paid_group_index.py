import json
import os
import sqlite3
import tempfile
from unittest import mock

import pytest


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(os, 'environ', {'PYTHONUTF8': '1'})
    from core import cost, quality_tier, lineage, shots
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'test.sqlite')
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.executescript('''CREATE TABLE projects(id INTEGER PRIMARY KEY);
            CREATE TABLE scenes(id INTEGER PRIMARY KEY, project_id INTEGER);
            CREATE TABLE jobs(scene_id INTEGER, project_id INTEGER, type TEXT, state TEXT, external_id TEXT, sent_group TEXT);
            CREATE TABLE motion_prompts(scene_id INTEGER);
            INSERT INTO projects VALUES(1); INSERT INTO projects VALUES(2);''')
        conn.executemany('INSERT INTO scenes VALUES(?,1)', [(i,) for i in range(1, 101)])
        conn.commit()
        with mock.patch.object(quality_tier, 'enabled', return_value=False), mock.patch.object(lineage, 'approved_image_id', return_value=None), mock.patch.object(shots, 'image_scene', side_effect=lambda c,s:s):
            yield cost, conn, path
        conn.close()


def paid(conn, members, project=1):
    conn.execute("INSERT INTO jobs VALUES(100,?,'video_gen','running','fake',?)", (project, json.dumps(members)))


def test_groups_read_and_members_parsed_once_per_project(db):
    cost, conn, _ = db
    from core import memo
    for start in range(1, 100, 5):
        paid(conn, [{'id': i} for i in range(start, min(start+5, 100))])
    conn.commit()  # Chỉ đo cache trên dữ liệu đã commit; transaction cần đọc mới sau rollback.
    scans = []
    conn.set_trace_callback(lambda sql: scans.append(sql) if 'SELECT sent_group' in sql else None)
    original = json.loads
    visits = []
    class Counted(list):
        def __iter__(self):
            for member in super().__iter__():
                visits.append(1)
                yield member
    def counted(value):
        return Counted(original(value))
    with mock.patch.object(cost.json, 'loads', side_effect=counted) as parsed, memo.per_rerun():
        for sid in range(1, 100):
            assert not cost.video_need(conn, sid)['needed']
        assert parsed.call_count == 20
        assert len(visits) == 99
        index = cost._paid_running_groups(conn, 1)
        assert cost._paid_running_groups(conn, 1) is index
    assert len(scans) == 1


def test_project_isolation(db):
    cost, conn, _ = db
    paid(conn, [{'id': 1}], project=2)
    assert cost.video_need(conn, 1)['needed']


def test_rollback_and_other_connection_commit_invalidate(db):
    cost, conn, path = db
    from core import memo
    with memo.per_rerun():
        assert cost.video_need(conn, 1)['needed']
        paid(conn, [{'id': 1}])
        assert not cost.video_need(conn, 1)['needed']
        conn.rollback()
        assert cost.video_need(conn, 1)['needed']
        other = sqlite3.connect(path)
        paid(other, [{'id': 1}])
        other.commit()
        other.close()
        assert not cost.video_need(conn, 1)['needed']
        conn.execute("UPDATE jobs SET external_id='' ")
        assert cost.video_need(conn, 1)['needed']
        conn.commit()
        assert cost.video_need(conn, 1)['needed']


@pytest.mark.parametrize('change', ['insert', 'delete', 'update'])
def test_savepoint_rollback_refreshes_index_and_video_need(db, change):
    cost, conn, _ = db
    from core import memo
    if change != 'insert':
        paid(conn, [{'id': 1}])
        conn.commit()
    with memo.per_rerun():
        conn.execute('BEGIN')
        conn.execute('SAVEPOINT paid_group_change')
        if change == 'insert':
            paid(conn, [{'id': 1}])
        elif change == 'delete':
            conn.execute('DELETE FROM jobs')
        else:
            conn.execute("UPDATE jobs SET external_id=''")
        during = change == 'insert'
        assert (1 in cost._paid_running_groups(conn, 1)) is during
        assert cost.video_need(conn, 1)['needed'] is (not during)
        stamp = (conn.total_changes, conn.execute('PRAGMA data_version').fetchone()[0], conn.in_transaction)
        conn.execute('ROLLBACK TO paid_group_change')
        assert stamp == (conn.total_changes, conn.execute('PRAGMA data_version').fetchone()[0], conn.in_transaction)
        after = not during
        actual = (1 in cost._paid_running_groups(conn, 1), cost.video_need(conn, 1)['needed'])
        assert actual == (after, not after)
        assert cost.video_need(conn, 1)['needed'] is (not after)
        conn.rollback()


def test_malformed_prefix_and_transitions(db):
    cost, conn, _ = db
    paid(conn, [{'id': 1}, {'id': 'bad'}, {'id': 2}])
    assert not cost.video_need(conn, 1)['needed']
    assert cost.video_need(conn, 2)['needed']
    for value in ['broken', '{}', '[null]', 'null']:
        conn.execute('UPDATE jobs SET sent_group=?', (value,))
        assert cost.video_need(conn, 1)['needed']
    paid(conn, [{'id': 1}])
    for state in ['queued', 'succeeded', 'cancelled', 'rejected']:
        conn.execute('UPDATE jobs SET state=?', (state,))
        assert cost.video_need(conn, 1)['needed']
    conn.execute("UPDATE jobs SET state='running', sent_group='[{\"id\":1}]'")
    assert not cost.video_need(conn, 1)['needed']


def test_transaction_reads_groups_again_without_replacing_trace(db):
    cost, conn, _ = db
    from core import memo
    paid(conn, [{'id': 1}])
    scans = []
    conn.set_trace_callback(lambda sql: scans.append(sql) if 'SELECT sent_group' in sql else None)
    with memo.per_rerun():
        assert not cost.video_need(conn, 1)['needed']
        assert not cost.video_need(conn, 1)['needed']
    assert len(scans) == 2
    conn.set_trace_callback(None)


def test_outside_rerun_does_not_retain_groups(db):
    cost, conn, _ = db
    assert cost.video_need(conn, 1)['needed']
    paid(conn, [{'id': 1}])
    assert not cost.video_need(conn, 1)['needed']
    conn.execute('DELETE FROM jobs')
    assert cost.video_need(conn, 1)['needed']


@pytest.mark.parametrize('scenario', ['draft', 'final_only', 'follower'])
def test_quote_bytes_match_legacy_group_scan(monkeypatch, scenario):
    # Môi trường giả được thay nguyên object trước imports/calls; không đọc khóa máy.
    monkeypatch.setattr(os, 'environ', {'PYTHONUTF8': '1'})
    from core import cost, features, image_models, model_router, quality_tier, memo
    from tests.test_cost_route_e1 import Base
    from contextlib import nullcontext
    pricing = {'currency': 'USD', 'per_image': {'mock-image': 1}, 'per_video_clip': {},
               'per_video_second': {'seedance:720p': 1}, 'per_audio': {}}
    choice = {'model': 'seedance-2.5', 'resolution': '480p', 'e1': 'draft_first', 'reason': 'fixture'}
    with mock.patch.object(features, 'on', return_value=False), mock.patch.object(features, 'active', return_value=False), mock.patch.object(quality_tier, 'enabled', return_value=True), mock.patch.object(model_router, 'scene_choice', return_value=choice), mock.patch.object(image_models, 'of_project', return_value='mock-image'), mock.patch('core.final_cut.measured_size', return_value=(480, 854)), mock.patch.object(quality_tier, 'upgrade_block', return_value=None), mock.patch.object(quality_tier, 'draft_stale_reason', return_value=None):
        fixture = Base()
        fixture.N = 3
        fixture.setUp()
        try:
            rows = [{'scene_id': sid, 'model': 'seedance-2.5', 'resolution': '480p', 'billed_seconds': 4,
                     'seconds': 4, 'cost': 1, 'e1': 'draft_first'} for sid in fixture.sids]
            jobs = []
            if scenario == 'final_only':
                for sid in fixture.sids:
                    jid = fixture.approved_draft(sid)
                    fixture.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE id=?", (jid,))
                    jobs.append(jid)
            elif scenario == 'follower':
                jid = fixture.p.create_job(fixture.s1, 'video_gen')
                fixture.p.conn.execute("UPDATE jobs SET quality_tier='draft', state='running', external_id='fake', sent_group=? WHERE id=?",
                    (json.dumps([{'id': sid, 'seconds': 4} for sid in fixture.sids]), jid))
            fixture.p.conn.commit()
            class LegacyMembership:
                def __contains__(self, sid):
                    for paid_row in fixture.p.conn.execute("SELECT sent_group FROM jobs WHERE type='video_gen' AND state='running' AND external_id IS NOT NULL AND external_id!='' AND sent_group IS NOT NULL"):
                        try:
                            if any(int(r['id']) == sid for r in json.loads(paid_row['sent_group'] or '[]')):
                                return True
                        except (ValueError, TypeError, KeyError):
                            pass
                    return False
            with mock.patch.object(model_router, 'plan', return_value=rows):
                with mock.patch.object(cost, '_paid_running_groups', return_value=LegacyMembership()), mock.patch.object(memo, 'per_rerun', side_effect=nullcontext):
                    before = json.dumps(cost.estimate_run(fixture.p, fixture.pid, pricing))
                scans = []
                fixture.p.conn.set_trace_callback(lambda sql: scans.append(sql) if 'SELECT sent_group FROM jobs WHERE project_id=' in sql else None)
                after = json.dumps(cost.estimate_run(fixture.p, fixture.pid, pricing))
                fixture.p.conn.set_trace_callback(None)
                assert before == after
                assert len(scans) == 1
            if scenario == 'final_only':
                assert cost.video_need(fixture.p.conn, fixture.s1)['final_only']
        finally:
            fixture.p.conn.close()
            fixture.doCleanups()


def test_overflow_after_match_preserves_lazy_legacy_result(db):
    cost, conn, _ = db
    paid(conn, [{'id': 1}, {'id': float('inf')}])
    assert not cost.video_need(conn, 1)['needed']
    with pytest.raises(OverflowError):
        cost.video_need(conn, 2)
