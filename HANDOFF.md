# HANDOFF — S14.14 phần G-a (ui_v2 mặc định + gỡ giao diện cũ nhóm nhẹ)

## Đã xong
- `core/features.py`: `ui_v2` verified=True (mặc định BẬT), why ghi "2026-10-05 người dùng duyệt (S14.14)".
- Gỡ nhánh cũ: `dashboard/steps/step1.py` (step1() chỉ gọi step1_v2; script_input; scene_list), `step1_v2.py` (cap/say/is_next không
  còn nhánh cờ tắt; `is_next(name)` bỏ tham số legacy), `step1_characters/director/idea/refs/run/prep.py`, `step1_refs.inputs_and_refs`
  (cũ) xóa, `step4.py` (step4 → step4_v2; `video_card` cũ xóa), `admin.py` (monitor → _monitor_v2; thân cũ xóa).
- Giữ theo cờ (cặp với header nhóm nặng, G-b gỡ): `ui.inject_css`/`dark_on`/`set_dark` (CSS v2 + nền tối) và `app.shell_header`
  (FEATURE_UI_V2=0 → header cũ đã vẽ level_bar; vẽ lần hai lỗi trùng khóa level_<pid>).
- Test mới `tests/test_ui_v2_default.py` (đỏ ở 7a7154f: 4 failed; xanh sau đổi). Test đổi/xóa: xem message commit 8e21d0b.
- `tools/ui_v2_acceptance.py`: OLD_CLICKS_BASELINE = 14.

- Cả bộ lần 1: 13 failed (đều do mặc định bật) → đã sửa: màn nhẹ đổi theo v2 (test_director_two_pass, test_new_skills,
  test_references, test_screens_dashboard script); màn nặng ghim FEATURE_UI_V2=0 (test_image_history, test_image_progress,
  test_storyboard_gate, test_users NameBar, test_screens_dashboard team) — G-b bỏ các dòng ghim này.

- Cả bộ lần 2 (94edc00): 2662 passed, 4 skipped, 0 failed (15 phút 32 giây).

## Bước kế
- G-b: gỡ nhánh cũ header.py, step2/grid_v2, step3, step5, team_screen*, home.py (home.py chưa nằm trong danh sách nhóm nào —
  vẫn đọc cờ, FlagOffTests của test_ui_home còn đúng); sau đó gỡ cờ ở ui.inject_css/dark_on/set_dark + app.shell_header, bỏ dòng
  FEATURE_UI_V2=0 trong setUp của tests/test_dashboard.py.
- G-c: tách file.
