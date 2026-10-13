import json
from unittest import mock

import pytest

from core import change_review, features, prompts
from core.db import connect
from core.pipeline import Pipeline


def stage_fixture(tmp_path):
    p = Pipeline(connect())
    pid = p.create_project('KL')
    p.add_scene_next(pid, 'approved')
    sid = p.conn.execute('SELECT id FROM scenes WHERE project_id=?', (pid,)).fetchone()[0]
    p.conn.execute("INSERT INTO jobs(project_id,scene_id,type,state,created_at,updated_at) VALUES (?,?,'image_gen','approved',datetime('now'),datetime('now'))", (pid, sid))
    old = {'objects': [{'key': 'kelly', 'kind': 'nguoi', 'at': [1, 0]}, {'key': 'maxim', 'kind': 'nguoi', 'at': [0, 0]}]}
    new = json.loads(json.dumps(old))
    new['objects'][0]['at'] = [2, 0]
    for name, bl in [('old', old), ('new', new)]:
        d = tmp_path / name
        d.mkdir()
        (d / 'blocking.json').write_text(json.dumps(bl), encoding='utf-8')
        (d / 'shot_specs.json').write_text(json.dumps({'shots': [{'shot': 1}]}), encoding='utf-8')
        (d / 'v2.json').write_text(json.dumps({'shots': [{'shot': 1, 'best': {'m': {'at': [0, -4], 'aim': [0, 0]}}}]}), encoding='utf-8')
    return p, pid, sid


def test_stage_file_change_records_real_finding_and_restoration(tmp_path, monkeypatch):
    p, pid, sid = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    assert change_review.record_stage_blocking_change(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'new')) > 0
    rows = change_review.open_findings(p.conn, pid)
    assert any(r['scene_id'] == sid and r['source'] == 'layout_drift' and r['level'] == 'vang' for r in rows)
    assert change_review.blocking(p.conn, sid) is None
    change_review.record_stage_blocking_change(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'old'))
    assert not [r for r in change_review.open_findings(p.conn, pid) if r['source'] == 'layout_drift']


def test_stage_producer_round_commits_and_flag_off_has_no_effect(tmp_path, monkeypatch):
    from tools.stage_grid import review_stage_round
    p, pid, sid = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    assert review_stage_round(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'new')) > 0
    assert not p.conn.in_transaction
    monkeypatch.setattr(features, 'on', lambda n: n == 'change_review')
    with mock.patch.object(change_review, 'record_stage_blocking_change', side_effect=AssertionError('OFF')):
        assert review_stage_round(None, None, None, None) == 0


def test_missing_baseline_and_unmapped_approved_shot_are_visible(tmp_path, monkeypatch):
    p, pid, sid = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    assert change_review.record_stage_blocking_change(p.conn, pid, None, str(tmp_path / 'new')) == 1
    assert 'chưa kiểm được' in change_review.open_findings(p.conn, pid)[0]['msg']
    (tmp_path / 'old' / 'shot_specs.json').write_text('{"shots":[]}', encoding='utf-8')
    assert change_review.record_stage_blocking_change(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'new')) == 1
    assert 'thiếu ánh xạ' in change_review.open_findings(p.conn, pid)[0]['msg']


def test_stage_flag_off_does_not_read_files_or_write(monkeypatch):
    p = Pipeline(connect())
    monkeypatch.setattr(features, 'on', lambda n: False)
    assert change_review.record_stage_blocking_change(p.conn, 999, 'missing', 'missing') == 0
    assert p.conn.execute('SELECT COUNT(*) FROM change_findings').fetchone()[0] == 0


def test_short_lock_own_outfit_does_not_remove_other_guard(monkeypatch, tmp_path):
    own = tmp_path / "own.png"
    from PIL import Image
    Image.new("RGB", (32, 32), "white").save(own)
    p = Pipeline(connect())
    pid = p.create_project('KL')
    for name in ('MAXIM KL', 'KELLY KL', 'KENTA'):
        p.conn.execute('INSERT INTO characters(project_id,name,description,outfit_image_ids) VALUES (?,?,?,?)', (pid, name, '', '1' if name != 'KENTA' else ''))
    monkeypatch.setattr(features, 'on', lambda n: n in ('profile_digest', 'short_lock_outfit'))
    with mock.patch('core.assets.outfit_images', side_effect=lambda c, i, n: [{'id': 1, 'path': str(own)}] if n != 'KENTA' else []), mock.patch('core.profile_digest.for_character', side_effect=lambda c, i, n, k: n + ' default clothes'):
        text = prompts.short_lock_block(p.conn, pid)
    assert 'MAXIM KL' not in text and 'KELLY KL' not in text
    assert 'KENTA default clothes' in text


def test_short_lock_flag_off_exact_original(monkeypatch):
    p = Pipeline(connect())
    pid = p.create_project('KL')
    p.conn.execute("INSERT INTO characters(project_id,name,description) VALUES (?,'KELLY KL','')", (pid,))
    monkeypatch.setattr(features, 'on', lambda n: n == 'profile_digest')
    with mock.patch('core.profile_digest.for_character', return_value='old digest'), mock.patch('core.assets.outfit_images', side_effect=AssertionError('flag off must not read outfits')):
        assert prompts.short_lock_block(p.conn, pid) == '# Nhận diện ngắn (hồ sơ chuẩn rút gọn ≤ 200 ký tự — motion prompt chỉ nhắc nhân vật bằng các chữ này, không chép Lock dài)\n- **KELLY KL**: old digest'


@pytest.mark.xfail(strict=True, reason='Đ8 việc 2: đợi #24 xong mới sửa end_frames; khung cuối WS phải dùng mốc Kho thay nền góc khác')
def test_end_frame_wide_reference_must_choose_landmark(tmp_path, request):
    from core import assets, end_frames
    from core.providers import MockImageProvider
    from tests.test_end_frames import EndFrameFlowTests
    case = EndFrameFlowTests()
    case.setUp()
    request.addfinalizer(lambda: __import__("shutil").rmtree(case.data))
    end_frames.queue(case.p, case.pid)
    scene = json.loads(case.p.conn.execute('SELECT data FROM scenes WHERE id=?', (case.sid,)).fetchone()[0])
    scene['size'] = 'WS'
    case.p.conn.execute('UPDATE scenes SET data=? WHERE id=?', (json.dumps(scene), case.sid))
    wide = tmp_path / 'wide.png'
    mark = tmp_path / 'mark.png'
    from PIL import Image
    for path in (wide, mark):
        Image.new('RGB', (32, 32), 'white').save(path)
    place = {'id': -1, 'name': 'Kho', 'images': [{'path': str(wide), 'role': 'eye_level'}, {'path': str(mark), 'role': 'detail'}]}
    provider = MockImageProvider()
    with mock.patch.object(assets, 'scene_location', return_value=place):
        end_frames.tick(case.p, case.pid, provider, case.data)
    sent = [refs for ext, refs in provider.references.items() if 'lies on the ground' in provider.prompts[ext]]
    assert sent
    assert str(mark) in sent[0] and str(wide) not in sent[0]


@pytest.mark.parametrize("problem", ["empty", "oversize", "unreadable"])
def test_short_lock_unassigned_outfit_keeps_digest(problem, tmp_path, monkeypatch):
    own = tmp_path / "own.png"
    if problem != "unreadable":
        with own.open("wb") as f:
            f.truncate(11 * 1024 * 1024 if problem == "oversize" else 0)
    p = Pipeline(connect())
    pid = p.create_project("KL")
    for name in ("KELLY KL", "KENTA"):
        p.conn.execute("INSERT INTO characters(project_id,name,description) VALUES (?,?,?)", (pid, name, ""))
    monkeypatch.setattr(features, "on", lambda n: n in ("profile_digest", "short_lock_outfit"))
    with mock.patch("core.assets.outfit_images", side_effect=lambda c, i, n: [{"id": 1, "path": str(own)}] if n == "KELLY KL" else []), mock.patch("core.profile_digest.for_character", side_effect=lambda c, i, n, k: n + " default clothes"):
        text = prompts.short_lock_block(p.conn, pid)
    assert "KELLY KL default clothes" in text
    assert "KENTA default clothes" in text


def test_stage_missing_approved_baseline_is_explicit(tmp_path, monkeypatch):
    from tools.stage_grid import review_stage_round
    p, pid, _ = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    with pytest.raises(ValueError, match='bản đã duyệt'):
        review_stage_round(p.conn, pid, None, str(tmp_path / 'new'))
    assert not change_review.open_findings(p.conn, pid)


def test_v3_trial_records_proposal_without_resolving_applied(tmp_path, monkeypatch):
    from tools.stage_grid import review_stage_round
    p, pid, _ = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    review_stage_round(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'new'))
    review_stage_round(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'new'), proposal=True)
    findings = change_review.open_findings(p.conn, pid)
    assert any(r['source'] == 'layout_drift' for r in findings)
    proposal = [r for r in findings if r['source'] == 'layout_drift_proposal']
    assert proposal and all('chưa áp dụng' in r['msg'] and '(new)' in r['msg'] and str(tmp_path) not in r['msg'] for r in proposal)


@pytest.mark.parametrize('ids', ['1', '99', ' 1 ', 'broken'])
def test_short_lock_matches_full_lock_outfit_policy(ids, monkeypatch):
    p = Pipeline(connect())
    pid = p.create_project('KL')
    p.conn.execute("INSERT INTO characters(project_id,name,description,outfit_image_ids,lock_rules) VALUES (?,'KELLY KL','',?,?)", (pid, ids, json.dumps({'must_keep': 'default clothes'})))
    monkeypatch.setattr(features, 'on', lambda n: n in ('profile_digest', 'short_lock_outfit'))
    with mock.patch('core.assets.standard_for', return_value=None), mock.patch('core.profile_digest.for_character', return_value='default clothes'), mock.patch('core.assets.outfit_images', return_value=[]):
        assert 'OUTFIT' in prompts.lock_text(p.conn, pid)
        assert 'default clothes' in prompts.short_lock_block(p.conn, pid)


def test_stage_explicit_baseline_without_hand(tmp_path, monkeypatch):
    from tools.stage_grid import review_stage_round
    p, pid, _ = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    assert review_stage_round(p.conn, pid, None, str(tmp_path / 'new'), proposal=True,
        approved_blocking=str(tmp_path / 'old' / 'blocking.json'),
        approved_specs=str(tmp_path / 'old' / 'shot_specs.json')) > 0
    assert all(r['source'] == 'layout_drift_proposal' for r in change_review.open_findings(p.conn, pid))


@pytest.mark.parametrize('field', ['approved_blocking', 'approved_specs'])
def test_stage_partial_explicit_baseline_does_not_fall_back(tmp_path, monkeypatch, field):
    from tools.stage_grid import review_stage_round
    p, pid, _ = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    with pytest.raises(ValueError, match='cả --approved-blocking'):
        review_stage_round(p.conn, pid, str(tmp_path / 'old'), str(tmp_path / 'new'),
                           **{field: str(tmp_path / 'missing.json')})
    assert not change_review.open_findings(p.conn, pid)


def test_proposal_dedupe_and_revert_leave_official_open(tmp_path, monkeypatch):
    from tools.stage_grid import review_stage_round
    p, pid, _ = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    old, new = str(tmp_path / 'old'), str(tmp_path / 'new')
    review_stage_round(p.conn, pid, old, new)
    assert review_stage_round(p.conn, pid, old, new, proposal=True) > 0
    assert review_stage_round(p.conn, pid, old, new, proposal=True) == 0
    assert review_stage_round(p.conn, pid, old, old, proposal=True) == 0
    assert {r['source'] for r in change_review.open_findings(p.conn, pid)} == {'layout_drift'}
    assert p.conn.execute("SELECT count(*) FROM change_findings WHERE source='layout_drift_proposal' AND status='resolved'").fetchone()[0] > 0


def test_proposal_latest_round_resolves_previous(tmp_path, monkeypatch):
    import shutil
    p, pid, sid = stage_fixture(tmp_path)
    monkeypatch.setattr(features, 'on', lambda n: n in ('change_review', 'layout_drift_review'))
    change_review.record_stage_blocking_change(p.conn, pid, str(tmp_path/'old'), str(tmp_path/'new'), proposal=True)
    shutil.copytree(tmp_path/'new', tmp_path/'round2')
    change_review.record_stage_blocking_change(p.conn, pid, str(tmp_path/'old'), str(tmp_path/'round2'), proposal=True)
    rows = change_review.open_findings(p.conn, pid)
    assert rows and all('(round2)' in r['msg'] and str(tmp_path) not in r['msg'] for r in rows)
    assert p.conn.execute("SELECT count(*) FROM change_findings WHERE status='resolved'").fetchone()[0] > 0


@pytest.mark.parametrize('problem', ['missing', 'empty', 'oversize'])
def test_assigned_unusable_outfit_keeps_short_lock(problem, tmp_path, monkeypatch):
    own = tmp_path/'own.png'
    if problem != 'missing':
        with own.open('wb') as f:
            f.truncate(11*1024*1024 if problem == 'oversize' else 0)
    p = Pipeline(connect())
    pid = p.create_project('KL')
    p.conn.execute("INSERT INTO characters(project_id,name,description,outfit_image_ids) VALUES (?,'KELLY','', '99')", (pid,))
    monkeypatch.setattr(features, 'on', lambda n: n in ('profile_digest', 'short_lock_outfit'))
    with mock.patch('core.assets.outfit_images', return_value=[{'id':99,'path':str(own)}]), mock.patch('core.profile_digest.for_character', return_value='face hair build'):
        assert 'face hair build' in prompts.short_lock_block(p.conn, pid)
