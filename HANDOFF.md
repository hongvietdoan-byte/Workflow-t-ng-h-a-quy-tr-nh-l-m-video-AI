# HANDOFF — F3 đường chi phí video E1 (09/10/2026, nhánh worktree `agent-ab063a250f23dd922`, chưa push)

**Đã xong** (0 USD, không gọi dịch vụ tốn tiền; chỉ khi cờ `two_tier_quality` BẬT — tắt thì y như cũ):
- Chọn model E1: `quality_tier.e1_choice` (gọi từ `model_router.scene_choice`): shot dễ (`group_path == direct`) → Seedance 2.0 720p
  ("E1: shot dễ — 2.0 720p, dựng phóng 1080p"); khó / chưa rõ → `seedance-2.5` 480p (nháp `draft=True` qua `low_tier`). Nhóm gen chung
  có shot nháp-trước → cả nhóm nháp-trước. Chọn tay thắng; chọn tay không phải 2.5 ở shot nháp-trước → `warning` (NEW_GEN),
  `model_router.e1_warning(conn, sid)` cho F4 hiện. Kling / model khác giữ đường cũ.
- Không tự gen mới bản cao: `quality_tier.upgrade_block` / `final_offer` / `needs_confirm`; `request_final(..., confirm_new=True)` bắt
  buộc khi không nâng được từ nháp (kèm giá `scene_final_price`), lưu `jobs.confirm_new` (cột mới). `VideoRunner._blocked` +
  `_submit_kwargs` (`_hold`) → job `final` chưa xác nhận bị đánh hỏng `stale_input: … cần xác nhận gen MỚI bản cao`, không gửi.
  Gen mới đã xác nhận: độ phân giải `final_resolution(model)` (cao nhất luật model cho phép), diag `final_resend` mức warn.
- Không ghi đè clip nháp: `VideoRunner._finish_group` gọi `takes.make_room` cho từng shot đi theo trước khi tách clip nhóm (file cũ
  vào thùng rác dưới số job của nó, `result_path` trỏ theo). `Pipeline.use_older_take` nhận cả take video ĐÃ DUYỆT (nháp).
- Phóng 1080p lúc dựng: `ffmpeg_studio.needs_upscale` + `_fit(upscale=True)` (lanczos + unsharp 5×5:0,5, hằng `UPSCALE_FLAGS`,
  `UNSHARP_*`) trong cùng lượt `render_final(upscale=…)`; `delivery.render` ghi manifest `upscaled: [idx…]` + `upscale`.
- Giá: `cost.clip_estimate` dùng công thức token ClipAI cho lựa chọn E1; `cost.video_button_tag` gom shot cùng nhóm Seedance thành
  1 clip (sửa "Còn tồn" 08/10 trong TODO — phiên chính gạch); `final_estimate` / `scene_final_price` theo clip nhóm + nâng/gen mới;
  `quality_tier.e1_estimate(conn, pid)` → {"usd", "film_seconds", "target_usd", "within", "line"} (mục tiêu < 30 / < 60 USD).
- UI `dashboard/quality_ui.py`: nâng được → "⬆ Gen bản cao"; không → "⬆ Gen MỚI bản cao (nội dung sẽ khác nháp) — ≈ X USD" + hộp
  xác nhận (`confirm_all`, khóa `qfinal_new_<sid>` / gom `qfinal_allnew_<pid>`).
- Test `tests/test_cost_route_e1.py` (13, khai trong `devsys/areas.json`). Sửa test cũ theo hợp đồng mới: `test_quality_tier` (nháp
  hết hạn → không tự gửi, xác nhận rồi mới gửi; nháp model khác → cần confirm), `test_ui_quality_tier` (nháp mẫu có model 2.5 + mã task).

**Cần đo thật / rủi ro**:
- Giá nâng 2.5 → 1080p từ nháp (`submit_final_from_sample`) là ƯỚC TÍNH theo công thức token, chưa đo (đo 1 lần; lệch thì thêm
  `cost.SEEDANCE_MEASURED`).
- `data/provider_rules.json` hiện không cho gửi thẳng 2.5 ở 1080p → bản cao gen MỚI (đã xác nhận) ra 720p; chỉ đường nâng từ nháp có 1080p.
- `e1_choice` đổi model khi bật cờ trên dự án đang làm → nháp cũ làm bằng alias `seedance` (2.0) không nâng được (đúng ý: phải xác nhận).
- Chưa nối `e1_estimate` vào Bước 1 / AI Dev System, chưa hiện `e1_warning` ở màn Video (việc F4).

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

# HANDOFF — nhánh F1-B (09/10): sửa 3 câu ghép prompt sai (lỗi thật #24), áp cho MỌI dự án

Nhánh: `worktree-agent-a65469680fb94d746` (chưa push). Không sửa TODO.md, `core/llm_io.py`, `core/director_report.py`, `knowledge/formula/`.

## Đã làm
1. **Luật mắt người không áp cho quái** — `core/seedance_refs.py`: `eyes_guard(data, humans)` + `glowing_eyes_written(data)`;
   `shot_motion(..., humans=)`. Câu "natural human eyes, no glowing eyes" chỉ gắn khi mọi nhân vật trong khung là người và không ai được
   tả mắt phát sáng/đỏ (performance/action/end_state/image_prompt, cả `motion_en`), và ghi tên: "KELLY: natural human eyes…".
   Shot không ghi nhân vật: giữ câu chung cũ. `code_motion` đọc hồ sơ qua `assets.cast_humans`.
   `core/assets.py`: `looks_non_human(text)`, `is_human(conn, pid, name)` (tên + description + lock_rules + tài nguyên Kho: kind pet /
   mô tả), `cast_humans(...)`. Không có cột loại → dựa từ khóa (creature/demon/ghost/monster/… /yêu nữ/quỷ/bóng ma/tà linh…, giữ dấu, \b).
   Đã grep "human/natural/glow/skin/teeth/blink" ở seedance_refs, runner, performance, prompts, motion_physics, shots: chỉ có luật này.
2. **Tiết chế máu/xác cho dự án FF** — `core/looks.py`: `gore_words`, `is_ff`, `gore_restraint(proj, text, video=False, scan=None)`,
   `GORE_VIDEO_MAX=200`. Ảnh: `build_image_prompt` (dò trên chữ Đạo diễn: image_prompt/blocking/action_peak/performance/fix — không dò
   Lock/địa điểm), đổi "everything in focus" → "everything in focus except those hinted details" + câu "Gore restraint: … only hinted —
   in deep shadow, out of focus or partly hidden, never shown clearly; …". Video: `VideoRunner._gore_restraint` (mọi đường: Seedance nhóm,
   khung đầu/Kling), dò motion + image_prompt/action/end_state của các shot; quá giới hạn prompt của model → bỏ câu + diag warn (không chặn
   gửi). Câu chỉ chữ tiếng Anh (lint Seedance chặn chữ Việt). `seedance_refs._estimated_len` cộng 200 ký tự khi nhóm có máu/xác.
   Diag `gore_restraint` (info) khi thêm.
3. **Khóa nền theo render 3D** — `core/assets.py`: `render_place_text(conn, place)` + `RENDER_TAG`; tách `_landmark_heights`,
   `_sizes_sentence` (location_text giữ nguyên kết quả). `build_image_prompt(..., place_render=False)`; ImageRunner `_submit_args` tính
   `place_refs.shot_ref` trước rồi truyền `place_render=True`; `_finish_args` → `runner.name_render` thay `RENDER_TAG` bằng " (Image N)" theo ảnh
   THẬT gửi (render rơi → bỏ số + diag warn). Phòng trong nhà giữ câu INSIDE cũ; khung cuối (end_frames) không gửi render → câu cũ.

## Test
`tests/test_prompt_assembly_f1b.py` (14 test, đỏ 11/12 trước khi sửa → xanh; cả bộ: 3269 qua, 1 lỗi test_storyboard_away_anchor_p24 do mình → đã sửa, chạy lại xanh). Khai vào `devsys/areas.json` step2.tests.

## Việc mở / rủi ro
- Nhận diện "không phải người" bằng từ khóa: mô tả người có chữ "ghost/monster" (vd "cô gái bị bóng ma ám") → mất câu mắt người (chỉ mất
  guard, không hại). Nên có trường loại nhân vật (human/creature) trong hồ sơ — chưa làm.
- Kling multi-shot (multi_prompt từng shot ≤ 512 ký tự) không gắn câu tiết chế vào từng shot, chỉ prompt chính.
- Motion prompt đã lưu trước khi sửa (motion_prompts) vẫn giữ câu mắt cũ đến khi viết lại (lineage motion_stale / nút Bước 3).

---

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
