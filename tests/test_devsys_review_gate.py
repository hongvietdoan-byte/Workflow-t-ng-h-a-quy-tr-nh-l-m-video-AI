import pytest
from devsys import review_gate as gate

TEXT = '''# Thẩm định độc lập
**Tổng = (7,5×15 + 7×20) / 100 ≈ 6,2 / 10**
# Lần 2 — thẩm định bản hợp nhất v2: **7,1 / 10** (v1: 6,2)
# Lần 3 — kế hoạch sau A14–A17 + K0a: kế hoạch **7,6 / 10**, K0a **7,5 / 10**
# Lần 4 — kế hoạch + build: kế hoạch **7,9 / 10**, build **8,0 / 10**
**Lỗ hổng còn lại:**
1. cũ
# Lần 5 — kế hoạch + build: kế hoạch **8,1 / 10**, build **8,3 / 10** — CHƯA đạt
**Lỗ hổng còn lại:**
1. lỗi A
   dòng tiếp tục
2. lỗi B
**Kết luận:** chưa đạt, ước sau sửa 9 / 10
'''


def test_five_real_heading_styles_and_missing_build_not_zero():
    result = gate.parse(TEXT)
    assert [(r['round'], r['plan'], r['build']) for r in result['rows']] == [(1, 6.2, None), (2, 7.1, None), (3, 7.6, 7.5), (4, 7.9, 8), (5, 8.1, 8.3)]
    assert 'không đọc được' in result['rows'][0]['errors'][0]
    assert result['rows'][-1]['holes'] == 2 and result['rows'][-1]['status'] == 'CHƯA ĐẠT'


@pytest.mark.parametrize('plan,build,status', [('8,5', '8.5', 'ĐẠT'), ('8,5', '8,4', 'CHƯA ĐẠT'), ('9', '11', 'KHÔNG ĐỦ SỐ ĐO')])
def test_gate_requires_both_valid_scores(plan, build, status):
    row = gate.parse(f'# Lần 1 — kế hoạch **{plan} / 10**, build **{build} / 10**\n**Lỗ hổng còn lại:**\n1. một')['rows'][0]
    assert row['status'] == status


def test_missing_file_and_unparseable_title_report_reason(tmp_path):
    assert 'không đọc được' in gate.load(tmp_path / 'missing.md')['error']
    row = gate.parse('# Lần 1 — chưa có điểm')['rows'][0]
    assert row['plan'] is None and row['build'] is None and row['errors']


def test_inline_holes_of_round_six_exclude_fix_notes():
    text = '# Lần 6 — kế hoạch **8,4 / 10**, build **8,5 / 10**\n**Lỗ hổng lần 5:** (1) ĐÓNG.\n**Lỗ hổng:** (1) CAO — lỗi. (2) TRUNG — lỗi.\n**Đã sửa ngay:** (1) sửa rồi. (2) sửa rồi.'
    row = gate.parse(text)['rows'][0]
    assert row['holes'] == 2 and row['status'] == 'CHƯA ĐẠT'


def test_unreadable_hole_list_does_not_report_zero():
    row = gate.parse('# Lần 1 — kế hoạch 9 / 10, build 9 / 10\n**Lỗ hổng còn lại:** chưa đếm')['rows'][0]
    assert row['holes'] is None and any('Lỗ hổng' in e for e in row['errors'])
