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
