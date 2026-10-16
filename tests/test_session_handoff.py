from tools import session_handoff as sh

TODO = """# TODO

- **📨 BÀN GIAO GIỮA CÁC PHIÊN** (người dùng 11/10) — luật mục
  - [16/10 16:00] phiên A → **PHIÊN KẾ — ĐỌC ĐẦU TIÊN.** (1) sửa previs
  - [16/10 15:37] phiên A → người dùng: XONG tối ưu
  - [15/10 10:00] phiên B → **PHIÊN KẾ — ĐỌC ĐẦU TIÊN.** gói cũ

## Việc phải làm lại MỖI LẦN
  - [99/99] không thuộc mục bàn giao — ĐỌC ĐẦU TIÊN
"""


def test_handoff_lines_only_section():
    lines = sh.handoff_lines(TODO)
    assert len(lines) == 3
    assert lines[0].startswith("[16/10 16:00]")


def test_unclaimed_pack_tells_session_to_continue():
    out = sh.render(TODO, "origin/main")
    assert "CHƯA AI NHẬN" in out and "vong-lam-viec-theo-plan" in out
    assert "(1) sửa previs" in out and "gói cũ" not in out


def test_claimed_pack_is_reference_only():
    todo = TODO.replace("ĐỌC ĐẦU TIÊN.** (1)", "ĐÃ NHẬN 16/10 16:20 (phiên C).** (1)")
    out = sh.render(todo, "origin/main")
    assert "CHƯA AI NHẬN" not in out and "ĐÃ có phiên nhận" in out
    assert "gói cũ" not in out  # gói cũ hơn không được thúc làm lại


def test_behind_main_warns_and_no_section():
    assert "chậm 3 commit" in sh.render(TODO, "origin/main", behind=3)
    assert "Không thấy mục" in sh.render("# TODO\n", "x")
