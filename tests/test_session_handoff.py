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


def test_line_merely_mentioning_mark_is_not_a_pack():
    # lỗi 16/10: dòng báo XONG nhắc cụm "ĐỌC ĐẦU TIÊN" trong ngoặc bị nhận nhầm là gói chưa ai nhận
    todo = TODO.replace(
        "ĐỌC ĐẦU TIÊN.** (1)", "ĐÃ NHẬN 16:14 (phiên C).** (1)").replace(
        "  - [16/10 16:00]", '  - [16/10 16:08] phiên D → **XONG hook** in gói "ĐỌC ĐẦU TIÊN" mới nhất\n  - [16/10 16:00]')
    out = sh.render(todo, "origin/main")
    assert "CHƯA AI NHẬN" not in out and "ĐÃ NHẬN 16:14" in out


def test_behind_main_warns_and_no_section():
    assert "chậm 3 commit" in sh.render(TODO, "origin/main", behind=3)
    assert "Không thấy mục" in sh.render("# TODO\n", "x")


def test_compact_event_tells_the_same_session_to_continue_even_on_a_claimed_pack():
    # 21/10: clear_session lưu trữ phiên + đứt Remote Control → nay tự nén trong cùng phiên, hook `compact` nạp lại gói
    todo = TODO.replace("ĐỌC ĐẦU TIÊN.** (1)", "ĐÃ NHẬN 16/10 16:20 (phiên C).** (1)")
    out = sh.render(todo, "origin/main", event="compact")
    assert "VỪA TỰ NÉN" in out and "(1) sửa previs" in out and "gói cũ" not in out
    assert "KHÔNG gọi clear_session" in out


def test_hook_event_reads_source_from_stdin_json():
    assert sh.hook_event('{"source": "compact", "session_id": "x"}') == "compact"
    assert sh.hook_event("") == "startup" and sh.hook_event("không phải json") == "startup"


def test_settings_compact_window_350k_and_hook_runs_after_compaction():
    import json, os
    cfg = json.load(open(os.path.join(os.path.dirname(__file__), "..", ".claude", "settings.json"), encoding="utf-8"))
    # 22/10: % override chỉ là % của cửa sổ 1M (≈ 677k) → dùng cửa sổ tuyệt đối 350k
    assert cfg["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "350000"
    assert "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" not in cfg["env"]
    assert "compact" in cfg["hooks"]["SessionStart"][0]["matcher"].split("|")
