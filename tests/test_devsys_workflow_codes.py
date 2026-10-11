import pytest
from devsys import workflow as w


def record(task):
    return dict(task=task, date='2026-10-10', mode='goi', review='nhe', work_k=1)


@pytest.mark.parametrize('task,kind', [('S14.45','S'), ('S1','S'), ('F1.1','S'), ('K0b','K'), ('K1a','K'), ('K1b','K'), ('K8','K'), ('K0b-TD5','K'), ('CX-d2-1','CX'), ('CX-d3-4','CX')])
def test_known_codes_accepted(task, kind):
    assert w.validate(record(task))['task'] == task
    assert w.task_kind(task) == kind


@pytest.mark.parametrize('task', ['anything', 'ABC', 'K99', 'K0bb', 'K0b-', 'K0b-123', 'K0b;rm', 'CX-d0-1', 'CX-d2-0', 'CX-d2-1-extra', 'S14.45\n', 'S14..45'])
def test_junk_rejected_with_reason(task):
    with pytest.raises(w.WorkflowError, match='mã việc'):
        w.validate(record(task))


def test_summarize_groups_old_and_new_codes():
    result = w.summarize([record(t) for t in ('S14.45', 'K0b-TD5', 'CX-d2-1')])
    assert {k: v['n'] for k,v in result['by_kind'].items()} == {'S':1,'K':1,'CX':1}
    assert result['all']['n'] == 3


def test_plan_missing_uses_all_rows_not_filtered_view():
    rows = [record('S14.45'), record('K0b-TD5')]
    plan = [{'task': 'S14.45'}, {'task': 'K0b-TD5'}, {'task': 'S14.46', 'part': 'A'}]
    assert [r['task'] for r in w.plan_missing(rows, plan)] == ['S14.46']


def test_page_load_skips_unknown_code_with_reason_but_write_path_stays_strict(tmp_path):
    import json
    path = tmp_path / 'runs.jsonl'
    path.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in [record('S14.45'), record('KLD-10'), record('CX-d2-1')]) + '\n', encoding='utf-8')
    with pytest.raises(w.WorkflowError, match='KLD-10'):
        w.load(str(path))
    skipped = []
    rows = w.load(str(path), skipped=skipped)
    assert [r['task'] for r in rows] == ['S14.45', 'CX-d2-1']
    assert len(skipped) == 1 and skipped[0]['line'] == 2 and skipped[0]['task'] == 'KLD-10' and 'không đúng dạng' in skipped[0]['reason']


def test_flow_page_warns_skipped_row_and_missing_ignores_kind_filter(tmp_path, monkeypatch):
    import json, os
    from unittest import mock
    AppTest = pytest.importorskip('streamlit.testing.v1').AppTest
    from devsys import plan_progress
    runs = tmp_path / 'runs.jsonl'
    runs.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in [record('S9.1'), record('KLD-10'), record('CX-d2-1')]) + '\n', encoding='utf-8')
    plan = tmp_path / 'plan.md'
    plan.write_text('### S9 — Thử\n- [x] S9.1 · thử · nặng:1 · ✅ · abc1234 · 05/10: x. Số đo: làm ≈ 100k, rà ≈ 0\n'
                    '- [x] S9.2 · thử · nặng:1 · ✅ · abc1235 · 05/10: x. Số đo: làm ≈ 50k, rà ≈ 0\n', encoding='utf-8')
    monkeypatch.setenv('DEVSYS_WORKFLOW_FILE', str(runs))
    at = AppTest.from_file(os.path.join(os.path.dirname(w.__file__), 'app.py'), default_timeout=180)
    with mock.patch.object(plan_progress, 'PLAN_FILE', str(plan)):
        at.run()
        at.sidebar.radio[0].set_value('Hiệu quả quy trình').run()
        assert [e.value for e in at.exception] == []
        warnings = ' '.join(str(x.value) for x in at.warning)
        assert 'dòng 2' in warnings and 'KLD-10' in warnings and 'LOẠI khỏi thống kê' in warnings
        info = lambda: ' '.join(str(x.value) for x in at.info if 'chưa có trong file' in str(x.value))
        assert info().startswith('1 nhánh') and 'S9.2' in info()
        at.multiselect(key='flow_task_kinds').set_value(['CX']).run()       # bỏ chọn loại S
        assert [e.value for e in at.exception] == []
        assert info().startswith('1 nhánh') and 'S9.1' not in info()


def test_import_plan_rejects_code_outside_contract():
    # Rà gộp 11/10: dòng kế hoạch mã "K1"/"AB" không được ghi vào file rồi làm hỏng load() nghiêm
    from devsys import workflow
    text = "- [x] K1 · ✅ abc1234 11/10 · Số đo: 120k làm; 40k rà\n- [x] AB · ✅ 11/10 · Số đo: 50k làm"
    got = workflow.parse_plan(text, year=2026)
    assert got["runs"] == [] and len(got["bad"]) == 2 and all("S/K/CX" in b for b in got["bad"])
