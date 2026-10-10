import json
from pathlib import Path
import subprocess
import pytest
from devsys import plans, plan_progress, stages

ROOT = Path(__file__).resolve().parents[1]


def test_registry_files_or_remote_branches_exist():
    records = json.loads((ROOT / 'devsys/plans.json').read_text(encoding='utf-8'))
    assert len({p['id'] for p in records}) == len(records)
    assert {p['kieu'] for p in records} == {'viec_s', 'dot_bang', 'codex', 'ghi_chu', 'phuong_phap'}
    for p in records:
        if p.get('nhanh'):
            assert subprocess.run(['git', 'show', f"{p['nhanh']}:{p['file']}"], cwd=ROOT, capture_output=True).returncode == 0
        else:
            assert (ROOT / p['file']).is_file()


def test_control_table_order_half_progress_and_decisions():
    text = '## A. Chốt\n| A1 | đầu |\n| A3 | mới nhất |\n## 8. Lộ trình\n| **K0b** 🟡 | làm `abcdef1` |\n| **K0a** ✅ | xong `123abcd` |\n' + ''.join(f'| **{d}** | chưa |\n' for d in stages.DOT[2:]) + '## 9. Khác\n| **K0a** | nhiễu |'
    result = plans.parse_control(text)
    assert [r['id'] for r in result['waves']] == list(stages.DOT)
    assert result['waves'][1]['commits'] == ['abcdef1']
    assert result['percent'] == round(150 / len(stages.DOT), 1)
    assert result['decision_count'] == 2 and result['latest_decision']['id'] == 'A3'


def test_unreadable_or_incomplete_never_becomes_zero(tmp_path):
    result = plans.read_control(tmp_path / 'missing.md')
    assert result['percent'] is None and 'không đọc được' in result['error']
    assert plans.parse_control('## 8. Lộ trình\n| K0a ✅ | xong |')['percent'] is None


def test_old_s_api_unchanged():
    text = '- [x] S1.1 · Xong · nặng:1 · ✅ · abcdef1\n- [ ] S1.2 · Dở · nặng:1 · 🔄'
    parsed = plan_progress.parse(text)
    assert plan_progress.percent(parsed['waves'][0]['tasks']) == 75
    assert plans.progress_for({'kieu': 'viec_s'}, text)['percent'] == 75


def test_codex_bullet_results_from_round_one_count():
    text = '## Việc 1 — một\n## Việc 2 — hai\n## Kết quả Codex\n- Việc 1 · `codex/one` · `abcdef1` · test xanh\n# ĐỢT 2 — mới\n## Việc 1 — khác'
    assert plans.progress_for({'kieu': 'codex', 'dot': 1}, text)['percent'] == 50


def test_bad_registry_is_reported(tmp_path):
    (tmp_path / 'devsys').mkdir()
    (tmp_path / 'devsys/plans.json').write_text('[null]', encoding='utf-8')
    assert 'không đọc được' in plans.inventory(tmp_path)['error']
