# HANDOFF — phiên cloud (hộp thư 12/10 18:13 → phiên cloud)

Nhánh: `claude/wonderful-fermi-am712r` (nhánh được cấp cho phiên cloud này; thay cho `cloud/p27-chay-tai-cho` trong hộp thư). Không đụng `core/seedance_refs.py`.

- **Việc 1 — XONG** (cờ `locomotion_end_frame`, verified False): `motion_physics.in_place_risk/moves_through_space/follows/GROUND_SENTENCE`,
  `sentence(action, camera_move=None)` (mặc định chữ cũ); `runner._end_frame` → `_runs_in_place` (bỏ khung cuối VẼ, giữ ảnh shot sau, diag VÀNG
  `locomotion_end_frame` một lần); `video_pregen._check_end` VÀNG cùng luật; `prompts.build_motion_bundle` physics_hint truyền camera_move.
  Máy chính cần nối `seedance_refs.py:869` → `motion_physics.sentence(action, data.get("camera_move"))` (motion viết bằng code).
  Test: `tests/test_locomotion_end_frame.py` (6 đỏ trước → xanh).
- **Việc 2 — XONG**: `prompt_formula._AMBIENT` nới vật (glow/rings/sparks/embers/ash/snow/petals/flags/curtains/hair + tia lửa/vòng sáng/tro/tuyết/cờ/rèm) + động từ (pulse/flutter/wave/glimmer/shimmer/twinkle/blow + nhấp nháy/bay/phấp phới/lung linh); test `tests/test_ambient_motion.py` (18 đỏ → xanh).
- Việc 3 — chưa làm.
- Credit: chưa hỏi được người dùng (phiên chạy theo hộp thư).
