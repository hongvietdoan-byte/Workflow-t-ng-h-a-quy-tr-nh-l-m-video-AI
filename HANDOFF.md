# HANDOFF — S14.43 nhánh A (Biên kịch theo phiếu 05d) — xóa khi xong

Test: `tests/test_s1443_screenwriter.py` (+ test_idea_to_script, test_s1435_scene_extras, test_asset_checklist).

| Mục | Trạng thái |
|---|---|
| 4 Màn hình điện thoại (từ xa / lộ → tài nguyên) | ✅ commit 1 — `idea_buildable.screen_view/screen_needs`, bảng kê `asset_checklist.to_create_rows` |
| 5 idea_to_script bật mặc định + hỏi khi sơ sài + ý định trong chat | ✅ commit 2 — `I.sparse/expand_request/expand_usd`, `step1_box.sparse_offer/_expand_from_chat`, features verified=True; test_ui_script/test_script_reader ghim FEATURE_IDEA_TO_SCRIPT=0 cho màn cũ |
| 1 Tên thật FF (Kho tên + alias trong prompt) | ⬜ |
| 2/3 Thoại GenZ + khớp hành động (screenwriter.md) | ⬜ |
| 6 Kho khuôn hài `knowledge/craft/khuon_hai.md` | ⬜ |

Ghi chú: đổi RULES (prompt Biên kịch) → bản ghi replay S11.2 cũ không khớp (chấp nhận; KHÔNG chạy đo thật).
Test cũ đổi: `test_idea_to_script.py::test_scenes_with_the_game_interface_or_gameplay_are_blocked` — mẫu 'bad' bỏ điện thoại (điện thoại không còn bị chặn).
