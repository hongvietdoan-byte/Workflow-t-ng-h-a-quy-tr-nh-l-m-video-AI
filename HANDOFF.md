# HANDOFF — F1-D công thức prompt vào prompt Đạo diễn (09/10/2026, nhánh `worktree-agent-a1b6b770f14ec0461`, chưa push)

**Đã xong** (0 USD, chỉ sửa prompt / knowledge, không đụng `core/`; commit f872a99):
- `prompts/17_director_shots.md` (dùng chung đường một lượt 01+17 và Quay phim 20+17): mục mới "Công thức prompt ảnh (`image_prompt`) và
  motion" — phần bắt buộc theo loại shot, cỡ cảnh ↔ tư thế, trang phục một nguồn (hồ sơ Kho), luật cứng FF chi tiết ghê chỉ gợi, vật gần
  người có đường đi + "never touches", quái không mang luật người, tả cái đúng, các trường cho motion, chạy lại = viết lại không trồng
  thêm (≤ ~20 %). Mỗi ý có bằng chứng #22/#24 + thứ tự ưu tiên; trỏ `knowledge/formula/`, không chép sổ.
- `19_director_intent.md` (Tầng A không viết image_prompt): 1 mục "điều chốt trước" (loại nhân vật, wardrobe theo hồ sơ, ghê chỉ gợi,
  `dp_notes` ghi đường đi vật gần người). `01_…`: 4 dòng trỏ công thức. `20_…`: 1 câu trỏ mục công thức trong 17.
- `26_director_rewrite.md`: mục 2 "Viết lại, không trồng thêm" (thay/bỏ câu sai, ≤ ~20 %, lý do growth_check + chặn gửi); mục 4 thêm luật
  công thức.
- `03_video_motion.md`: thứ tự motion theo công thức, ngoại lệ ref-only (một câu chốt tóc/phụ kiện — trước chỉ có ở `_kld22` sau cờ),
  đường đi vật gần người, loại nhân vật, tả cái đúng. Bỏ 2 câu trùng ("Dựa vào ảnh đã duyệt…" gộp vào điểm bắt đầu; "Kết cảnh yên lặng…"
  trùng trạng thái cuối). `_murch`, `_kld22` không đổi (test khóa câu kld22).
- `knowledge/roles/director.md` N6 (3 tầng bài học, trỏ prompt); `dp.md` Q6 máy 3D hợp lý + ảnh toàn cùng trục, Q10 trang phục theo hồ sơ.
- Ký tự trước → sau: 17 23536→26661 (+13,3 %) · 19 14650→15656 (+6,9 %) · 01 9869→10488 (+6,3 %) · 03 5018→5847 (+16,5 %) ·
  26 2686→3095 (+15,2 %) · 20 5006→5258 (+5,0 %) · director.md 47679→48584 · dp.md 38581→39455.
- Test: `tests/test_director_prompt_formula.py` (ý bắt buộc theo từ khóa + trần độ dài 1,16×). 19 file test liên quan: 294 passed.

**Còn lại / rủi ro**: chưa chạy Đạo diễn thật để đo lỗi đỏ giảm (cần tiền, người dùng quyết); 03 vượt mục tiêu 15 % chút (+16,5 %).

---

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
