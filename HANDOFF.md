# HANDOFF — F4 màn chọn model gọn (09/10/2026, nhánh `worktree-agent-a301f2427d8281c07`, chưa push)

**Đã xong** (0 USD, không gọi dịch vụ):
- `dashboard/model_line.py` (mới, chỉ ĐỌC): `shot_line(conn, pid, scene_id, row=None)` → {model_text ("Seedance 2.5 · nháp 480p → cao
  1080p" / "Seedance 2.0 · 720p → phóng 1080p lúc dựng" / "Kling 3.0 Omni · pro"), keeps_content (True/False/None), usd (≈, clip nhóm =
  "trong clip nhóm"), source (đề xuất / bạn chọn / …), why, warning (E1 từ scene_choice), path, text}; `shot_lines` (plan một lần);
  `film_line` ("Phim 20 s ≈ X USD — mục tiêu < 30 USD (đạt)"; cờ two_tier_quality bật → `quality_tier.e1_estimate`, tắt → tổng plan).
- Bước Video, bảng "🎛 Model cho từng cảnh": hiện ở CẢ chế độ thường (trước chỉ chuyên gia). Mỗi shot một dòng + popover "Đổi" (model
  `vm_{pid}_{sid}`, đường chất lượng `qpath_{sid}` khi cờ bật, độ phân giải + lý do dạng chữ). Cảnh báo E1 màu cảnh báo trên dòng.
  Dòng 🎬 ước tính cả phim trên đầu bảng. Phần giải thích slide + so sánh tổng 3 ưu tiên chỉ còn ở chế độ chuyên gia.
- Thẻ clip (`quality_ui.card_block(..., line=)`): bỏ selectbox "Đường chất lượng" (đã ở "Đổi"), thay bằng một dòng 🎛 + "đổi ở bảng
  Model (Tinh chỉnh)"; giữ nút ⬆ Gen bản cao / Gen MỚI của F3. Lưới tính `shot_lines` một lần (`step4._shot_lines`).
- Bước 1 · 📐 Định dạng: dòng 🎬 ước tính cả phim dưới "Ưu tiên model video" khi dự án đã có cảnh.
- `tests/test_model_line_f4.py` (5 test) + khai `devsys/areas.json`. Không sửa core/.

**Còn mở / rủi ro**:
- Độ phân giải chưa chọn tay riêng được (không có cột lưu; runner ngoài phạm vi) — trong "Đổi" chỉ hiện chữ, đi theo đường chất lượng.
- Giá nháp→cao trên dòng tự tính bằng `cost.seedance_estimate` như `e1_estimate`; nâng 2.5 → 1080p vẫn là ƯỚC TÍNH chưa đo thật.

---

# HANDOFF — F2 nền 3D đúng trước khi gen (09/10/2026, nhánh `worktree-agent-ada0e86a5b27e6561`, chưa push)

**Đã xong** (0 USD, Blender giả trong test):
- `core/plate_camera.py`: `camera_for` kiểm + đặt lại máy — máy ngửa lên giữ chân trời trong khung (≤ 0,8 nửa khung dưới giữa;
  máy < 0,8 m không ngửa quá 30°) bằng cách NÂNG máy (giữ khoảng cách + điểm nhìn = giữ khung), trừ shot ghi "sky"/"bầu trời";
  máy sát hơn `MIN_DIST_M[cỡ]` (MS 1,0 · MLS 1,2 · WS/EWS 1,5 m) lùi dọc trục + ống dài hơn; cần ống > 200 mm → `problem`.
  Trả thêm `fixes`, `problem`, `horizon_y`, `frame_h_m`. Hàm mới `horizon_y`, `wide_for`, `wants_sky`.
  Ngưỡng cự ly đặt dưới cự ly mặc định của từng cỡ → máy mặc định (và cache render) KHÔNG đổi; chỉ góc thấp ngửa gắt (MS/MCU/CU low) đổi khóa.
- `core/location_pack.py`: `plan()` mỗi shot thêm `wide` {camera, key} (cùng hướng, lùi dọc trục, ống ×0,6 ≥ 18 mm, khung ≥ 3 thân
  người / 2,5× khung shot; không chìm dưới 0,3 m), `camera_fixes`, `camera_problem`. `ensure_plates` render shot + wide cùng một lượt
  Blender + cùng cache; index thêm `wide` {plate,key,camera,camera_plan} hoặc `wide_failed`, `camera_fixes`; máy không đặt được →
  không render, index `failed` + diag error `plate_camera`; đặt lại máy → diag info `plate_camera_fix` + `layout_vi`.
- `core/place_refs.py`: `missing` (thiếu wide cũng là thiếu → render trước), `broken` (render hỏng/phẳng/máy không đặt được),
  `wide_ref`, `add_wide` (sau render shot, thay ảnh toàn cảnh chung LABEL; ưu tiên người > render > wide > khác), `scale_sentence`.
- `core/runner.py` (KHÔNG đụng build_image_prompt): `ImageRunner._wait` giữ chờ job khi `broken` (diag error `plate_broken`, diag tự gộp
  10 phút) · `_submit_args` + nhánh storyboard `_finish_args` thêm wide + `scale_sentence`.
- `core/assets.py reference_note`: vai `place_wide` ("WIDE same-axis view…, do not copy its framing").
- `knowledge/craft/goc_may.md` mục "Mỗi shot 3D một ảnh toàn CÙNG TRỤC". `tests/test_plates_f2.py` 11 test.

**Cần phiên chính chạy Blender thật** (máy chính): render lại #24 (shot 4 phải ra nền có giếng, chân trời trong khung; mỗi shot có
`wide.png` trong cache) — mở plates/index.json xem `wide`, `camera_fixes`; kiểm wide không đứng trong tường / dưới địa hình (máy lùi
4–12 m không biết địa hình — nếu phẳng thì `wide_failed`, shot vẫn gửi không kèm wide).
**Còn mở:** tỉ lệ giếng cần số đo thật — khai `model3d.props` [{name, at, height_m}] của nơi (đo bằng `plates3d.ground_heights` tại
đỉnh thành giếng); chưa có thì `scale_sentence` rỗng. Kiểm vật mốc chắn máy (bán kính vật mốc) chưa làm (không có dữ liệu hình khối).

# HANDOFF — F1-C khuôn ghép prompt (09/10/2026, nhánh `worktree-agent-a9d3224a7f9f54451`, chưa push)

**Đã xong** (0 USD, không gọi model, không đọc data/):
- `core/prompt_template.py` (mới, khai ở `devsys/areas.json` khu director): `close`/`join` (mỗi phần tự đóng câu, câu trùng nguyên văn
  bỏ, phần CUỐI giữ đuôi như viết), `split_director` (bỏ mệnh đề phong cách trùng câu look FF; gom mệnh đề chất lượng về cuối),
  `quality_part`, `shared_sentences` (câu lặp ≥ 2 shot motion → viết một lần).
- `runner.build_image_prompt`: phần theo thứ tự công thức — phong cách → khung → người+hành động (chữ Đạo diễn, blocking, gaze,
  acting, action_peak, pha kỹ năng) → `Fix:` → nền (trong nhà / khóa render / chữ địa điểm + `place_extra`) → `light` → khóa (lock_note,
  view_notes, gore) → chốt chất lượng. Tham số mới `light`, `place_extra`; `ImageRunner._submit_args` tính light/script_sentence/geometry
  trước và truyền vào (không nối đuôi nữa). `PRECEDENCE` (place_refs, F2) vẫn đặt đầu như cũ.
- `lock_note`: thêm "The costume follows the profile above (or the OUTFIT image); any other colour word for these garments is wrong."
- Câu trong nhà viết lại tả cái đúng (bỏ "no plaza, tower, sky or sea").
- `looks.py`: câu look FF tách `style_sentence` + `quality_sentence` (`image_sentence` = cả hai, giữ cho establishing); `gore_sentence`,
  `in_focus_except` (gore_restraint dùng lại).
- `seedance_refs`: `shot_motion` hành động → kết → diễn → thoại → máy quay → vật lý; `prompt()` điểm bắt đầu → shot → câu chung một lần →
  đứng yên → khóa nhận dạng (+ câu màu trang phục khi có OUTFIT) → render → luật; `prompt_limit(model)` (provider_rules → PROMPT_LIMITS);
  `lint_group` dùng nó; `_estimated_len(..., dressed)` tính cả ảnh OUTFIT, `groups()` truyền vào.
- `prompt_formula`: `outfit_vs_profile` + `garment_profile` (+ `_chars` thêm `_garments`) → ĐỎ `nhan_vat` khi màu khác hồ sơ (ảnh: xét cả
  blocking/start_frame/action_peak); `_neg_lists` → cảnh báo `ta_cai_dung` (≥ 2 vật cấm, trừ phủ định phong cách/chú thích).
- Sổ `knowledge/formula/anh_khung_dau.md`, `motion.md` thêm mục F1-C.
- Test `tests/test_prompt_template_f1c.py` (15). Sửa có lý do: `test_trial_fixes` end-frame (câu look giờ tách đầu/cuối).

**Chưa làm / rủi ro**: chỉ gộp câu lặp NGUYÊN VĂN (câu gần giống không gộp); `outfit_vs_profile` có thể ĐỎ nhầm khi gán chủ sai
(nhiều nhân vật, tên đứng gần) — chặn gen ảnh shot đó; `PRECEDENCE`/`scene_establish` "No people, no characters" thuộc F2 chưa đụng;
mô tả địa điểm trong Kho ("No stacked terraces, no fortress.") là dữ liệu, chưa viết lại.

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

**Rà độc lập F3 (09/10) — đã sửa** (`tests/test_cost_route_e1.py` +8 test):
- Nhóm trộn dễ/khó: `tier_for_new_job` (và `batch._draft_tier`) theo `group_path` → job shot dễ trong nhóm có shot khó là `draft`
  (2.5 `draft=True` 480p), shot sau của nhóm khó cũng `draft`. `final_estimate` theo `group_path`.
- Giá bản cao theo nhóm: `scene_final_price` của shot sau = giá cả clip nhóm khi shot đầu chưa có bản cao (0 khi đã có);
  `batch_final_price` (nút gom) tính mỗi nhóm một lần; `_clip_groups`.
- Lỗi TẠM khi đọc hạn nháp (`READ_FAIL`): route `transient` → job bản cao giữ hàng đợi (`_wait`, diag `final_wait` một lần), không
  fail; `upgrade_block` bỏ qua các lần fail do lỗi đọc này (cả dữ liệu cũ).
- Nút / hộp "Gen MỚI bản cao" ghi độ phân giải thật (`final_offer` → `res`, `res_note`; `quality_ui.new_final_texts`).
- Gửi lại y nguyên (RESEND_NOTE / PLAIN_RESEND) một bản cao đã xác nhận giữ `confirm_new` (`Pipeline._insert_job`).
- Clip nhóm dời cả `NN_raw.mp4` của bản cũ (`takes.make_room(with_raw=True)`, chỉ khi tệp cũ có chủ); `trash.find_for_job` bỏ qua
  tệp `_raw` (dùng lại bản cũ lấy đúng clip).
- KHÔNG sửa (có chủ ý): phóng lanczos + unsharp áp cho MỌI clip nhỏ hơn khung, kể cả cờ `two_tier_quality` tắt (trước là bicubic) —
  coi là cải thiện chất lượng dựng.

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
