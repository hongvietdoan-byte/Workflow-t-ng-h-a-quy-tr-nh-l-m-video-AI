import copy
import pytest
from core import qc_observe

CRITERIA = ['character', 'set_match']

def specs(job=678):
    data = {'characters': ['GIRL'], 'byd': {'thanh_phan': [{'vat': 'well', 'vai': 'phu'}]}}
    return qc_observe.compile_checks(None, 24, job, data, CRITERIA,
        profiles={'GIRL': {'must_keep': 'black dress; correct face; red legs'}})

def reply(checks):
    return {'observations': [{'id': c['id'], 'source': c['source'], 'seen': 'thay',
            'region': [0.1, 0.1, 0.9, 0.9], 'evidence': c['detail']} for c in checks]}

@pytest.mark.parametrize('job', [678, 680])
def test_real_cases_seen_correct_ignores_model_verdict(job):
    checks = specs(job)
    obj = reply(checks)
    obj['verdict'] = 'fail'
    obj['criteria'] = {'character': 0.1, 'set_match': 0.1}
    result = qc_observe.judge(checks, obj, CRITERIA)
    assert result['criteria'] == dict.fromkeys(CRITERIA, 1.0)
    assert not result['yellow']
    assert any(c['detail'] == 'black dress' for c in checks)
    assert any(c['detail'] == 'well' for c in checks)

@pytest.mark.parametrize('bad', ['duplicate', 'missing', 'unknown', 'enum', 'evidence', 'source', 'region'])
def test_strict_guard(bad):
    checks = specs()
    obj = reply(checks)
    first = obj['observations'][0]
    if bad == 'duplicate': obj['observations'].append(copy.deepcopy(first))
    if bad == 'missing': obj['observations'].pop()
    if bad == 'unknown': first['id'] = 'unasked'
    if bad == 'enum': first['seen'] = 'THAY'
    if bad == 'evidence': first['evidence'] = ''
    if bad == 'source': first['source'] = 'invented'
    if bad == 'region': first['region'] = [0, 0, 3, 1]
    with pytest.raises(ValueError): qc_observe.judge(checks, obj, CRITERIA)

def test_unclear_is_yellow_without_penalty():
    checks = specs()
    obj = reply(checks)
    obj['observations'][0]['seen'] = 'khong_chac'
    obj['observations'][0]['region'] = None
    result = qc_observe.judge(checks, obj, CRITERIA)
    assert result['yellow']
    assert result['criteria'] == dict.fromkeys(CRITERIA, 1.0)

def test_missing_profile_never_autoapprove():
    with pytest.raises(ValueError, match='hồ sơ'):
        qc_observe.compile_checks(None, 24, 678, {'characters': ['GIRL']}, CRITERIA, profiles={})

from types import SimpleNamespace
from unittest.mock import MagicMock
from core import assets, features, llm_runner, prompts

class FakeLLM:
    def __init__(self, unclear=False):
        self.unclear = unclear
        self.calls = []
    def complete(self, text, images):
        import json
        self.calls.append((text, images))
        checks = json.loads(text.split('\nĐặc điểm: ')[1])
        obj = reply(checks)
        obj.update(verdict='fail', criteria={'character': 0.1})
        if self.unclear:
            obj['observations'][0].update(seen='khong_chac', region=None)
        return SimpleNamespace(text=json.dumps(obj), input_tokens=7, output_tokens=8)

@pytest.mark.parametrize('unclear', [False, True])
def test_fake_llm_routes_real_qc_and_holds_yellow(monkeypatch, tmp_path, unclear):
    import json
    image = tmp_path / 'frame.png'
    image.write_bytes(b'fake')
    data = {'characters': ['GIRL'], 'byd': {'thanh_phan': [{'vat': 'well', 'vai': 'phu'}]}}
    p = MagicMock()
    p.job.return_value = {'id': 680, 'project_id': 24, 'scene_id': 12}
    p.conn.execute.return_value.fetchone.return_value = {'idx': 12, 'data': json.dumps(data)}
    p.apply_qc.return_value = 'approved'
    from core.states import JobState
    p.state.return_value = JobState.SUCCEEDED
    monkeypatch.setattr(llm_runner.access, 'need_edit_job', lambda *a: None)
    monkeypatch.setattr(llm_runner, 'image_path', lambda *a: str(image))
    monkeypatch.setattr(features, 'on', lambda key: key == 'qc_observe_enum')
    monkeypatch.setattr(prompts, 'qc_criteria', lambda: CRITERIA)
    monkeypatch.setattr(prompts, 'qc_references', lambda *a: [])
    monkeypatch.setattr(assets, 'standard_for', lambda *a: {'must_keep': 'black dress; correct face; red legs'})
    monkeypatch.setattr(assets, 'reference_gaps', lambda *a: [])
    monkeypatch.setattr(assets, 'scene_references', lambda *a, **kw: [{'role': 'character', 'label': 'GIRL', 'path': str(image)}])
    monkeypatch.setattr(assets, 'thumbnail', lambda path, *a: path)
    fake = FakeLLM(unclear)
    result = llm_runner.run_qc.__wrapped__(p, 680, fake, str(tmp_path), autofix=True)
    assert len(fake.calls) == 1
    if unclear:
        p.apply_qc.assert_not_called()
        p.transition.assert_called_once()
        assert 'VÀNG' in result['issues']
    else:
        assert p.apply_qc.call_args.args[1] == dict.fromkeys(CRITERIA, 1.0)
        assert result['decision'] == 'approved'

def test_off_prompt_output_byte_equal_baseline(monkeypatch, tmp_path):
    import json
    import subprocess
    old = subprocess.check_output(['git', 'show', '08c11b4:core/llm_runner.py'], text=True, encoding='utf-8')
    start = old.index('def run_qc(')
    stop = old.index('\n\nNO_FEET_SIZES', start)
    namespace = dict(llm_runner.__dict__)
    exec(old[start:stop], namespace)
    baseline = namespace['run_qc']
    image = tmp_path / 'frame.png'; image.write_bytes(b'fake')
    p = MagicMock()
    p.job.return_value = {'id': 678, 'project_id': 24, 'scene_id': 11}
    p.conn.execute.return_value.fetchone.return_value = {'idx': 11, 'data': '{}'}
    p.apply_qc.return_value = 'approved'
    monkeypatch.setattr(llm_runner.access, 'need_edit_job', lambda *a: None)
    monkeypatch.setattr(features, 'on', lambda key: False)
    monkeypatch.setattr(prompts, 'qc_criteria', lambda: CRITERIA)
    monkeypatch.setattr(prompts, 'qc_references', lambda *a: [])
    monkeypatch.setattr(prompts, 'build_qc_bundle', lambda *a: 'chuỗi prompt cũ')
    monkeypatch.setattr(llm_runner, 'image_path', lambda *a: str(image))
    namespace['image_path'] = llm_runner.image_path
    class OldFake:
        def __init__(self): self.calls = []
        def complete(self, text, images):
            self.calls.append((text, images))
            return SimpleNamespace(text=json.dumps({'criteria': dict.fromkeys(CRITERIA, 1.0), 'issues': []}), input_tokens=1, output_tokens=2)
    before, after = OldFake(), OldFake()
    expected = baseline(p, 678, before, str(tmp_path))
    actual = llm_runner.run_qc.__wrapped__(p, 678, after, str(tmp_path))
    assert before.calls == after.calls
    assert json.dumps(actual, ensure_ascii=False) == json.dumps(expected, ensure_ascii=False)


def test_spec_does_not_remove_remainder_of_checklist():
    checks = qc_observe.compile_checks(None, 24, 1,
        {'characters': [], 'size': 'CU', 'byd': {'thanh_phan': [{'vat': 'well'}]}},
        ['composition', 'consistency', 'set_match'], profiles={})
    assert {c['source'] for c in checks} >= {
        'qc_checklist.composition', 'qc_checklist.consistency', 'qc_checklist.set_match'}


@pytest.mark.parametrize('size', ['ECU', 'CU', 'MCU', 'MS'])
def test_no_feet_shots_do_not_ask_or_fail_grounding(size):
    checks = qc_observe.compile_checks(None, 24, 1, {'characters': [], 'size': size},
                                      ['composition', 'grounding'], profiles={})
    assert not any(c['criterion'] == 'grounding' for c in checks)
    assert qc_observe.judge(checks, reply(checks), ['composition', 'grounding'])['criteria']['grounding'] == 1.0


def test_wide_shot_still_checks_grounding():
    checks = qc_observe.compile_checks(None, 24, 1, {'characters': [], 'size': 'LS'}, ['grounding'], profiles={})
    obj = reply(checks)
    obj['observations'][0]['seen'] = 'khong_thay'
    assert qc_observe.judge(checks, obj, ['grounding'])['criteria']['grounding'] == 0.0


def test_geometry_missing_cannot_pass(monkeypatch):
    monkeypatch.setattr(qc_observe.qc_spec, 'compile_frame', lambda *a, **kw: {
        'assertions': [], 'missing_profiles': [], 'plan_conflicts': [], 'geometry_missing': 'thiếu máy 3D'})
    with pytest.raises(ValueError, match='3D'):
        qc_observe.compile_checks(None, 24, 1, {}, ['scale'], profiles={})


def test_unexpected_topkeys_rejected_but_legacy_scores_ignored():
    checks = specs()
    obj = reply(checks)
    obj.update(verdict='fail', criteria={'character': 0})
    assert qc_observe.judge(checks, obj, CRITERIA)['criteria']['character'] == 1.0
    obj['unexpected'] = True
    with pytest.raises(ValueError):
        qc_observe.judge(checks, obj, CRITERIA)


@pytest.mark.parametrize('gap', ['cast_cap', 'missing_file'])
def test_references_guard_before_paid_call(monkeypatch, tmp_path, gap):
    image = tmp_path / 'frame.png'; image.write_bytes(b'fake')
    p = MagicMock()
    data = {'characters': ['GIRL', 'OTHER']}
    checks = specs()
    monkeypatch.setattr(qc_observe, 'compile_checks', lambda *a, **kw: checks)
    monkeypatch.setattr(assets, 'reference_gaps', lambda *a: [])
    monkeypatch.setattr(assets, 'scene_references', lambda *a, **kw: [
        {'role': 'character', 'label': 'GIRL', 'path': str(image)},
        *([{'role': 'character', 'label': 'OTHER', 'path': str(image)}] if kw.get('limit') == 99 else [])])
    if gap == 'missing_file':
        monkeypatch.setattr(assets, 'scene_references', lambda *a, **kw: [
            {'role': 'character', 'label': n, 'path': str(tmp_path / 'gone.png')} for n in data['characters']])
    fake = FakeLLM()
    with pytest.raises(llm_runner.LlmError, match='tham chiếu'):
        qc_observe.observe_frame(p, {'id': 680, 'project_id': 24}, fake, str(image), CRITERIA, data)
    assert not fake.calls


def test_yellow_returning_after_user_approval_keeps_decision(monkeypatch):
    from core.states import JobState
    p = MagicMock(); p.state.return_value = JobState.APPROVED
    monkeypatch.setattr(llm_runner.access, 'need_edit_job', lambda *a: None)
    monkeypatch.setattr(qc_observe, 'observe_frame', lambda *a: {
        'criteria': dict.fromkeys(CRITERIA, 1.0), 'yellow': ['uncertain'], 'issues': [],
        'input_tokens': 1, 'output_tokens': 2})
    result = qc_observe.run(p, {'id': 680}, None, '', '', CRITERIA, {}, [], True)
    assert result['decision'] == 'already_processed'
    p.transition.assert_not_called(); p.apply_qc.assert_not_called()


@pytest.mark.parametrize('old_route', ['legacy', 'team', 'agent', 'team_agent'])
def test_scene_enum_on_wins_existing_layer1_routes(monkeypatch, tmp_path, old_route):
    import json
    from core import qc_scene, qc_team, qc_agent
    p = MagicMock()
    p.conn.execute.return_value = [(json.dumps({'story_scene': 1}),)]
    frames = [{'job_id': 680, 'state': 'succeeded', 'data': {}, 'path': str(tmp_path / 'f.png')}]
    monkeypatch.setattr(qc_scene, 'scene_frames', lambda *a: frames)
    monkeypatch.setattr(qc_scene, 'claude_on', lambda: True)
    monkeypatch.setattr(features, 'on', lambda flag: flag == 'qc_observe_enum')
    monkeypatch.setattr(qc_team, 'enabled', lambda: 'team' in old_route)
    monkeypatch.setattr(qc_agent, 'enabled', lambda: 'agent' in old_route)
    observe = MagicMock(return_value={'applied': {'K1': 'giữ cho người'}, 'results': {'680': 'pass'}})
    monkeypatch.setattr(qc_observe, 'review_scene', observe, raising=False)
    for module in (qc_scene, qc_team, qc_agent):
        monkeypatch.setattr(module, 'review_scene', MagicMock(side_effect=AssertionError('old route bypass')))
    assert qc_scene.run_ready_scenes(p, 24, None, str(tmp_path))['failed'] == []
    observe.assert_called_once()


def _sqlite_frames(tmp_path, count=2):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project('QC quan sát thử')
    frames = []
    for k in range(1, count + 1):
        sid = p.create_scene(pid, k)
        jid = p.create_job(sid)
        p.start(jid); p.succeed(jid)
        image = tmp_path / f'{jid}.png'; image.write_bytes(b'fake')
        frames.append({'job_id': jid, 'scene_id': sid, 'path': str(image), 'data': {'characters': [], 'size': 'CU'}})
    return p, pid, frames


@pytest.mark.parametrize('shadow', [False, True])
def test_scene_two_frames_one_call_hold_or_shadow_keeps_layer0(monkeypatch, tmp_path, shadow):
    from core import qc_scene, project_budget, money_policy
    from core.states import JobState
    p, pid, frames = _sqlite_frames(tmp_path)
    monkeypatch.setattr(qc_scene, 'shadow', lambda: shadow)
    monkeypatch.setattr(project_budget, 'warning', lambda *a: None)
    monkeypatch.setattr(money_policy, 'note', lambda *a, **kw: None)
    monkeypatch.setattr(qc_scene, 'flags_of', lambda *a: [{'problem': 'cờ lớp 0 tồn tại', 'severity': 'flag'}])
    fake = FakeLLM()
    result = qc_observe.review_scene(p, pid, 1, fake, str(tmp_path), frames)
    assert len(fake.calls) == 1
    assert set(result['results']) == {str(r['job_id']) for r in frames}
    for r in frames:
        assert p.state(r['job_id']) == (JobState.SUCCEEDED if shadow else JobState.PENDING_REVIEW)
    if shadow:
        assert p.conn.execute('SELECT COUNT(*) FROM qc_results').fetchone()[0] == 0
        assert p.conn.execute('SELECT COUNT(*) FROM trainee_log').fetchone()[0] == 2
    else:
        assert p.conn.execute("SELECT COUNT(*) FROM qc_results WHERE criterion='scene_qc_hold'").fetchone()[0] == 2
        notes = [r[0] for r in p.conn.execute("SELECT note FROM job_events WHERE to_state='pending_review'")]
        assert all('cờ lớp 0 tồn tại' in n for n in notes)


def test_real_sqlite_yellow_cannot_overwrite_user_approval(monkeypatch, tmp_path):
    from core.states import JobState
    p, pid, frames = _sqlite_frames(tmp_path, 1)
    r = frames[0]
    class ApproveDuringCall(FakeLLM):
        def complete(self, text, images):
            p.approve(r['job_id'])
            return super().complete(text, images)
    fake = ApproveDuringCall(unclear=True)
    result = qc_observe.run(p, p.job(r['job_id']), fake, str(tmp_path), r['path'], CRITERIA, r['data'], [], True)
    assert result['decision'] == 'already_processed'
    assert p.state(r['job_id']) == JobState.APPROVED
    assert p.conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] == 1


def test_new_enum_does_not_open_closed_scene_claude_gate(monkeypatch, tmp_path):
    import json
    from core import qc_scene
    p = MagicMock(); p.job.return_value = {'state': 'pending_review'}
    p.conn.execute.return_value = [(json.dumps({'story_scene': 1}),)]
    monkeypatch.setattr(features, 'on', lambda flag: flag == 'qc_observe_enum')
    monkeypatch.setattr(qc_scene, 'claude_on', lambda: False)
    monkeypatch.setattr(qc_scene, 'scene_frames', lambda *a: [{'job_id': 1, 'state': 'pending_review', 'data': {}}])
    monkeypatch.setattr(qc_observe, 'review_scene', MagicMock(side_effect=AssertionError('closed gate')))
    assert qc_scene.run_ready_scenes(p, 24, None, str(tmp_path))['waiting'] == [1]
    qc_observe.review_scene.assert_not_called()


def test_cost_counts_scene_enum_even_when_team_or_agent_on(monkeypatch):
    from core import cost, qc_scene, qc_team, qc_agent
    monkeypatch.setattr(features, 'on', lambda f: f == 'qc_observe_enum')
    monkeypatch.setattr(qc_scene, 'active', lambda: True)
    monkeypatch.setattr(qc_scene, 'claude_on', lambda: True)
    monkeypatch.setattr(qc_team, 'active', lambda: True)
    monkeypatch.setattr(qc_agent, 'enabled', lambda: True)
    monkeypatch.setattr(cost, '_scenes_to_draw', lambda *a: 3)
    assert cost._picture_qc_calls(None, 24, 10) == 10 * (1 + cost.REDRAW_SHARE)


def test_empty_profile_is_missing_input():
    with pytest.raises(ValueError, match='hồ sơ'):
        qc_observe.compile_checks(None, 24, 1, {'characters': ['GIRL']}, CRITERIA,
                                  profiles={'GIRL': {'must_keep': ''}})


def test_byd_forbidden_prop_is_code_failure_if_seen():
    checks = qc_observe.compile_checks(None, 24, 1,
        {'characters': [], 'byd': {'thanh_phan': [{'vat': 'well', 'vai': 'khong_duoc_co'}]}},
        ['set_match'], profiles={})
    assert qc_observe.judge(checks, reply(checks), ['set_match'])['criteria']['set_match'] == 0.0


def test_specialized_side_observation_stays_yellow():
    checks = qc_observe.compile_checks(None, 24, 1, {'characters': ['GIRL']}, ['character'],
                                      profiles={'GIRL': {'must_keep': 'RIGHT arm: black glove'}})
    result = qc_observe.judge(checks, reply(checks), ['character'])
    assert result['yellow']
    assert result['criteria']['character'] == 1.0


def test_checklist_contains_current_angle_location_mood():
    checks = qc_observe.compile_checks(None, 24, 1,
        {'characters': [], 'size': 'CU', 'angle': 'low', 'location': 'stone room', 'mood': 'fear'},
        ['composition', 'set_match', 'mood_lighting'], profiles={})
    for criterion, term in [('composition', 'low'), ('set_match', 'stone room'), ('mood_lighting', 'fear')]:
        assert term in next(c['detail'] for c in checks if c['source'] == 'qc_checklist.' + criterion)


def test_custom_outfit_never_scored_against_default_library_clothes(tmp_path):
    p, pid, frames = _sqlite_frames(tmp_path, 1)
    p.conn.execute('INSERT INTO characters (project_id,name,description,outfit_image_ids) VALUES (?,?,?,?)',
                   (pid, 'GIRL', 'girl', '999'))
    p.conn.commit()
    fake = FakeLLM()
    with pytest.raises(llm_runner.LlmError, match='OUTFIT'):
        qc_observe.observe_frame(p, p.job(frames[0]['job_id']), fake, frames[0]['path'], CRITERIA,
                                 {'characters': ['GIRL']})
    assert not fake.calls
    assert p.state(frames[0]['job_id']).value == 'succeeded'
    assert p.conn.execute('SELECT COUNT(*) FROM qc_results').fetchone()[0] == 0
