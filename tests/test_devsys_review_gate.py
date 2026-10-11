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


# Mẫu văn bản thật từ docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md (lần 1 dạng "## Lỗ hổng (mức)", lần 7 dạng "Còn lại:").
ROUND_1 = '''# Thẩm định độc lập kế hoạch kiểm soát (10/10/2026)
**Tổng = (7,5×15 + 7×20) / 100 ≈ 6,2 / 10**

## Lỗ hổng (mức)
1. CAO — tài liệu tự mâu thuẫn (N2/N4, 2.1, 8, mục 9 cũ, 9b.2) → hợp nhất một bản.
2. CAO — rủi ro chất lượng N2 → K2 thêm so A/B có trả tiền, trần nhỏ, người dùng chấm; chỉ số vào mục 6.
3. TRUNG — chặn thật dựa regex → kiểm mâu thuẫn ở mức trường BYĐ; regex trên mô tả thêm chỉ vàng.
4. THẤP — ghi tái dùng dấu vân tay + ReplayClient.

## Điểm mạnh thật
Chẩn đoán "kiểm không nhìn đúng gói" có code xác nhận.
1. không phải lỗ hổng
'''

ROUND_7 = '''# Lần 7 — sau sửa 6 lỗ hổng lần 6 (main e457c09): kế hoạch **8,5 / 10**, build **8,5 / 10** — ĐẠT cổng A21 (sát ngưỡng)

Lỗ hổng lần 6: (1)(2) MỘT PHẦN (A18 dòng 33 + A25 dòng 40 còn trỏ #22 + #24); (3)–(6) ĐÓNG.
Còn lại: TRUNG — A18/A25 trỏ bộ trong mẫu; TRUNG — A25 đòi ≥ 2 dự án nhưng K1a chỉ 1 dự án thử (cần người dùng chốt); THẤP — tool luôn in
"TRONG MẪU" (cần cờ giữ riêng); THẤP — docstring identity_declare, TODO, A27 gọi 6/39 là nhãn A25; THẤP — nghiệm thu K1a thiếu (i)–(iii).
Agent: không cần thẩm định 8 nếu chỉ sửa đúng các mục này. **Đã sửa cùng ngày:** A18/A25 trỏ bộ giữ riêng; **A28** (người dùng: bộ giữ riêng =
dự án thử K1a + dự án kế; ĐỎ A18 sớm nhất sau dự án 2); docstring; nghiệm thu K1a (i)–(iv). → **Mở K1a.**
'''


def test_round_one_heading_holes_with_hash_prefix():
    row = gate.parse(ROUND_1)['rows'][0]
    assert row['round'] == 1 and row['holes'] == 4
    assert not any('Lỗ hổng' in e for e in row['errors'])


def test_round_seven_con_lai_counts_severity_clusters_and_marks_same_day_fix():
    row = gate.parse(ROUND_7)['rows'][0]
    assert (row['plan'], row['build'], row['status']) == (8.5, 8.5, 'ĐẠT')
    assert row['holes'] == 5 and row['errors'] == []
    assert 'theo bản thẩm định' in row['holes_note'] and 'đã sửa cùng ngày chưa xác nhận' in row['holes_note']
    assert gate.holes_text(row) == 'Lỗ hổng còn lại: 5 (theo bản thẩm định; phần đã sửa cùng ngày chưa xác nhận)'


def test_holes_text_unreadable_gives_reason_from_data():
    row = gate.parse('# Lần 1 — kế hoạch 9 / 10, build 9 / 10\n**Lỗ hổng còn lại:** chưa đếm')['rows'][0]
    assert gate.holes_text(row) == 'Lỗ hổng còn lại: không đọc được: ' + next(e for e in row['errors'] if 'Lỗ hổng' in e)


def test_score_uses_vietnamese_comma_and_build_note_from_data():
    assert gate.score_text(8.5) == '8,5/10' and gate.score_text(8.0) == '8/10' and gate.score_text(None).startswith('không đọc được')
    rows = gate.parse('# Lần 1 — kế hoạch 6 / 10\n# Lần 2 — kế hoạch 7 / 10, K0a 7,5 / 10\n# Lần 3 — kế hoạch 8 / 10, build 8 / 10')['rows']
    assert gate.build_note(rows) == 'Lần 1 chưa ghi điểm build; không điền 0. Build lần 2 là phạm vi K0a theo nguồn, chưa đại diện toàn pipeline.'
    assert gate.build_note(gate.parse('# Lần 1 — kế hoạch 9 / 10, build 9 / 10')['rows']) == ''


def test_real_file_every_round_reads_holes():
    rows = gate.load()['rows']
    assert len(rows) >= 7 and all(r['holes'] is not None for r in rows)
    assert rows[6]['holes'] == 5 and rows[6]['status'] == 'ĐẠT' and rows[0]['holes'] == 10
