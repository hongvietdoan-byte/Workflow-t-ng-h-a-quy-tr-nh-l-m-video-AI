# HANDOFF — F1-A công thức prompt (09/10/2026, nhánh `worktree-agent-a22dfa0dcc0951c59`, chưa push)

**Đã xong** (0 USD, không gọi model):
- `core/prompt_formula.py`: `shot_kind`, `check_image` / `check_motion` (a thiếu phần · b khung↔tư thế · c ghê không tiết chế ·
  d vật lao sát người không đường đi · e luật người cho quái · f câu tự mâu thuẫn · g câu dính), `cross_shot`, `growth_check`,
  `review_shot`, `warnings` (báo cáo Đạo diễn), `after_director`, `on_prompt_saved`, `red_issues(conn, scene_id, kind=None)`.
- Móc (chỉ đọc + ghi `scenes.data["formula_check"]` + diag mã `prompt_formula`, KHÔNG chặn gửi): `llm_io.store_scene_analysis`
  (snapshot trước `_store` → so 'trồng thêm'), `llm_io.store_motion_prompts`, `llm_io.update_scene` (sửa tay image_prompt),
  `prompt_rewrite.save_rewrite` / `revert`; `director_report` khóa "continuity". Cờ `prompt_formula` (verified, mặc định bật).
- Sổ công thức `knowledge/formula/` (README, anh_khung_dau.md, motion.md). `devsys/areas.json` khai file + cờ (không tăng version).
- `tests/test_prompt_formula.py` 26 test, câu thật #22/#24.

**Đang dở / bước kế (phiên chính)**:
- Nối `prompt_formula.red_issues(conn, sid, kind="image")` vào `ImageRunner._blocked`, `kind="motion"` vào `VideoRunner._blocked`.
- Kiểm trên prompt ĐÃ DỰNG (runner.build_image_prompt / câu seedance_refs tự gắn như "Natural human eyes") — hiện chỉ kiểm câu
  Đạo diễn/người viết + trường data; câu code gắn lúc gửi chưa qua lớp dò.
- Bước (3) của mục 4b (một lượt Claude "biên tập prompt" khi có lỗi) chưa làm — tốn tiền, cần hỏi giá.
- Phần chưa kiểm bằng code: khóa nền, nối tiếp, vật lý, thứ đứng yên (ghi trong sổ).

# HANDOFF — Codex 06/10/2026

Bước 1–2 bàn giao đã hoàn tất phần code và push main. Bản code được kiểm: `12d2779`; commit tài liệu này cập nhật trạng thái sau kiểm thử.

- G-a: mặc định UI v2, gỡ bố cục cũ Kịch bản / Video / Theo dõi; giữ CSS/header theo cờ tới G-b. Báo cáo `docs/RA_GA_CODEX_2026-10-06.md`.
- Cloud: S14.24, S14.25 Đợt 6a, S14.45, S14.50, phần code S14.51, P1; 4 lỗi có test hồi quy đỏ→xanh. Báo cáo `docs/RA_CLOUD_CODEX_2026-10-06.md`.
- Cả bộ cuối: **2748 qua, 8 bỏ qua, 66 subtest qua, 0 lỗi**; 748,27 s trên Linux / Python 3.12 / Streamlit 1.65.
- Không gộp code S14.29; chỉ bản lưu. `devsys/areas.json` version 24 tăng một lần.
- `lesson_judge`, `feedback_to_mistakes`, `palette_check` vẫn TẮT. Không gọi API trả phí; chưa truy cập dữ liệu hoặc khởi động lại máy Windows chính.

**Bước tiếp: S14.47(2)** theo 1c/2b/3a trong TODO/plan, nguồn chi riêng “chat Kịch bản”; chưa bắt đầu code. Sau đó G-b / G-c + S13.3 / S13.10. S14.12 người dùng tự chạy trên Dashboard; hỏi trước mọi việc tốn tiền.

**Triển khai Windows còn mở:** sao lưu CSDL trước migration; tại `D:\AI-Video-Pipeline` pull `--ff-only`, restart Dashboard 8501 và Dev System 8502 theo AGENTS.md, kiểm health và UI thật. Môi trường Codex hiện tại không có máy/data Windows.

Điểm nghỉ theo mục 3 `.claude/skills/vong-lam-viec-theo-plan/SKILL.md`: không có số hạn mức tương ứng, đã xử lý ba nhánh bàn giao. Không ghi số token giả vào workflow.

## Cloud 07/10 — nhánh `claude/read-s14-45-cloud-tasks-ngb0q2-v2` (fast-forward từ main b93b1ac; rà rồi gộp)
- `886f4cd` TODO: xóa hẳn mục cũ 🚧/👤 (09/2026–03/10); gỡ mọi chỗ nhắc S14.29 (kế hoạch + TODO; chỉ còn docs/cat_giu + 1 dòng TODO_LICH_SU).
- `ff5dce0` Khủng Long Đỏ 2/3/7: nút Gen video chỉ gửi cảnh mới + cảnh đã cũ được tích (`batch.video_plan`, `queue_videos(only=)` —
  autopilot không đổi); danh sách 'Sẽ gửi' ghi model THẬT + độ phân giải (`clipai.display_name`); '⏳ chờ duyệt clip cảnh trước'
  (`batch.chain_waits`). Chưa thử trên Dashboard thật.
- `07edd58` Khủng Long Đỏ 6: `cost.SEEDANCE_MEASURED` hệ số 0,72 cho Seedance 2.0 @ 1080p (ước tính 2,94 ≥ giá thật 2,93 / 12 s);
  tổ hợp khác giữ công thức (chưa có giá thật). RÀ KỸ (tiền).
- `2f530dc` P4: `effectiveness.waste` tiền lãng phí theo lý do / loại, dòng 💸 ở 🎯 Hiệu quả workflow.
- `6790416` P6: bọc ví dụ lỗi (gồm thông báo lỗi ClipAI) trong prompt viết bài học (`lessons._write_rule`) + test chèn lệnh.
  Đổi chữ prompt khâu 'lessons' (chỉ thêm khối bọc).
