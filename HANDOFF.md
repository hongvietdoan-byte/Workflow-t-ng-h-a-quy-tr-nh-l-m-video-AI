# HANDOFF S14.35

- core/idea_buildable.py: place_kind/scene_choice (anchors), place_state, scene_needs, custom_place_block; gate không chặn nơi đời thường.
- core/asset_checklist.py: hàng status to_create (ghi lựa chọn + ước giá Meshy, không chạy).
- core/scene_merge.py: gộp cảnh cùng nơi sau write(); state["merge"] (joins, cuts), state["script_unmerged"].
- knowledge/craft/kelly_*.md: cú chốt twist, wow 15 s, nối liền mạch.
- Test: tests/test_s1435_scene_extras.py; sửa kỳ vọng 2->1 cảnh ở test_idea_to_script.py, test_idea_script_eval.py (mock 2 cảnh cùng nơi nay gộp).
- Cần xóa HANDOFF.md khi gộp (như S14.33/34).
