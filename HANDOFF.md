# HANDOFF — G0 Đạo diễn đặt máy 3D (09/10, nhánh `g0-director-camera-plan`, dựng trên `70f7259`, chưa push)

## Đã xong (0 USD — Claude/Blender giả trong test; chưa chạy thật)
- Cờ `director_camera_plan` (`core/features.py`, TẮT, chưa verified; khai khu `plates3d` trong `devsys/areas.json`, không tăng version).
- `core/camera_plan.py` (mới):
  - mục 1–2 `before_plates`: mỗi cảnh (story_scene × bối cảnh 3D) chưa có sơ đồ → MỘT lượt Claude khâu `director_camera_plan`
    (ước tính ghi diag trước, qua sổ chi; STAGE_SETTINGS max_tokens 8000; cost.LLM_STAGE_TOKENS). Đầu vào: luật cách nghĩ
    `prompts/28_director_camera_plan.md` + hướng mốc/chỗ đứng (`place_facts` từ `model3d.anchor` + spots) + kịch bản cảnh + shot + ảnh
    `plates/top_view.png` nếu có (thiếu anchor/topview → diag warn). Ra JSON: props, beats, axis, 1–6 setup, shot→setup+size+angle.
    `check` (code): angle theo setup, shot nhìn xuống mà setup không cúi → tách setup `X-DOWN` (high/down), vượt trục không lý do,
    nền chưa giới thiệu (lệch > 40° cả shot mở lẫn hướng ngược), muốn thấy mốc mà nhìn lệch. `apply` ghi `plate_setup`,
    `plate_view` = {background: phương vị độ, why}, size, angle (+ `shot`); trường `_user_locked` giữ + báo; đổi cỡ → warn.
    Sơ đồ lưu `<data_dir>/<pid>/plates/camera_plan.json`. Claude lỗi → ghi `failed` + `tries`, tự thử tối đa 2 lượt (không trả tiền mỗi tick).
  - mục 4 `after_plates`: mỗi setup một render (+ render shot mở) → Claude khâu `director_plate_review` chỉ khai quan sát enum
    (`OBSERVATIONS`); `judge` (code) kết luận + cách sửa; sửa (`_apply_fix`: phương vị/angle) → `apply` → `ensure_plates` render lại,
    ≤ 2 vòng, rồi diag error `director_plate_review` "CẦN BẠN QUYẾT". Quan sát mâu thuẫn / không rõ → không đoán, báo người.
- mục 3 `core/plate_camera.plan_cameras(..., setup_field)` + `location_pack.plan`: cờ BẬT → shot cùng `plate_setup` + cỡ + chỗ đứng
  dùng CÙNG camera (chiều cao người của shot đầu) → cùng cache key, render một lần. Cờ TẮT → gộp cũ y nguyên (test so trước–sau).
- mục 5 `core/plate_layout_qc.py`: sau khi ảnh về (`runner.ImageRunner._after_download`, chỉ khi cờ bật) so ảnh với render: chân trời
  (bước sáng/tối), dải quanh chân trời phẳng (tường che), F1 cạnh (place_refs.background_match) → diag `plate_layout` warn
  "nền lệch render" + `<data_dir>/<pid>/plate_layout.json`. Chỉ đánh dấu, không vẽ lại. Ngưỡng tạm, CHƯA hiệu chỉnh.
- Autopilot `_plates_phase` → `_camera_plan` trước plan() và sau ensure_plates (cờ tắt: không làm gì; lỗi → diag, chạy tiếp luồng cũ).
- CLI: `py tools/location_pack.py camera-plan --project 24 [--yes] [--review] [--force]` (không --yes: chỉ in ước tính).
- MockLlm (LLM_PROVIDER=mock) có câu trả lời cho 2 khâu mới.
- Test `tests/test_camera_plan_g0.py` (29 test).

## Việc mở / rủi ro
- Chưa chạy thật (mục 6): ước tính Claude #24 ≈ 0,06 USD sơ đồ (1 cảnh) + ≈ 0,08 USD duyệt 4 góc (tối đa ≈ 0,23 nếu sửa đủ 2 vòng).
- `beats` (chỗ đứng theo nhịp) + `props` mới được LƯU, chưa dời nhân vật/đạo cụ trong 3D (máy vẫn đặt quanh chỗ đứng đăng ký).
- Sơ đồ có thể đổi `size` shot → prompt ảnh còn tả cỡ cũ (đã warn) — mục 6 sửa prompt shot 4–7.
- Ngưỡng `plate_layout_qc` (chân trời 0,15; dải 30 %; F1 0,15) và luật `judge` cần đo trên render/ảnh #24 thật.
- Chưa có nút Dashboard riêng (chạy qua autopilot khi bật cờ, hoặc CLI).

## Bước kế
- Rà nhánh; người dùng duyệt giá → bật cờ, chạy `camera-plan --project 24 --review --yes`, gửi tấm ghép render các setup, rồi mục 6.

# HANDOFF — P24 đặt máy 3D theo ngôn ngữ máy của shot (09/10, nhánh worktree-agent-ab5a90511a3b9ff78)

## Đã xong (0 USD, chưa chạy Blender)
- `core/plate_camera.py` (hàm thuần): `looks_down(data)` (action/blocking/start_frame/camera_setup, nguyên từ, bỏ phủ định);
  `camera_for`: angle high/ots + nhìn xuống → cúi 35° (qua vai: máy trên đầu 0,15 m, nhìn mặt đất phía trước nhân vật; chân trời ra
  khỏi khung → tháp chỉ còn chân / mất); low → máy từ 0,5× chiều cao (không còn 0,45 m), WS ngửa 8°; trả thêm `why` {distance, pitch,
  direction} + `pitch_deg` (KHÔNG nằm trong dict camera → cache key shot không đổi giữ nguyên). `clearance_fix(...)`: quyết theo tia
  Blender — máy trong/sau vật cản → tiến dọc hướng nhìn; tường thấp ≤ cao nhân vật + 0,3 m sát sau nhân vật → nâng máy qua tường;
  tường cao → chỉ cảnh báo (chọn plate_view khác), không im lặng.
- `tools/render_plates.py`: `clearance()` bắn tia (thân nhân vật→máy; ngang theo hướng nhìn + tia xuống đo đỉnh vật cản), nạp
  `core/plate_camera.py` theo đường dẫn; manifest mỗi plate có `clearance`.
- `core/location_pack.py`: meta.json có `why` (+ `clearance`); diag `plate_clearance`; `ensure_plates(..., fresh=[idx])`;
  CLI `tools/location_pack.py render --project N --fresh-shot IDX` (render lại dù đã cache).
- Test: `tests/test_plate_camera_p24_angles.py` (khai `devsys/areas.json`).

## Việc phiên chính
- Render lại #24: `py tools/location_pack.py render --project 24 --fresh-shot 4 --fresh-shot 7` (shot 3, 5 đổi key nên tự render;
  shot 4, 7 key không đổi → cần --fresh-shot để chạy kiểm tia). Xem meta.json `why`/`clearance` + ảnh plate trước khi vẽ lại ảnh.
- ~~Rủi ro: máy bị tiến/nâng trong Blender thì `subject_box` lệch~~ → đã sửa (rà, nhánh p24-camera-fixes): manifest có
  `clearance.location_model`, `location_pack.reframe` tính lại `subject_box`/`distance_m`/`horizon_y` → meta.json `reframed`, index dùng.

## Rà độc lập P24 (nhánh p24-camera-fixes) — đã sửa + lưu ý
- Sửa: lỗi bpy/ray_cast trong `clearance()` → `warnings` + `skipped`, vẫn render; vật cản sát nhân vật (< 0,8 m) → chỉ cảnh báo,
  không dời máy vào mặt; "looks down the alley/street…" và `camera_setup` không còn làm máy cúi 35°; ảnh toàn cùng trục chỉ cảnh
  báo (không dời); cảnh `indoor` bỏ kiểm tường sau lưng; tia đo đỉnh tường bắt đầu `where.z + 3 m` + tia ngang dò tường cao.
- `SCRIPT_VERSION` KHÔNG tăng (cố ý: cache plate cũ còn dùng, 0 USD). Hệ quả: cùng một khóa cache có thể là ảnh render TRƯỚC khi có
  kiểm tia (không có `clearance` trong meta.json). Muốn áp kiểm tia cho plate đã cache → chỉ có `--fresh-shot IDX`.
- `why` trong meta.json nằm theo khóa cache — khóa dùng chung giữa các dự án/shot cùng máy nên `why` là của lần render ĐẦU
  (dự án/shot khác có thể đọc lý do không phải của mình). Lý do của từng shot hiện tại: xem plan()["camera_why"], không dựa meta.json.
- Dự án cũ: mọi shot `low` và shot high/ots có chữ "nhìn xuống" ĐỔI khóa → render lại (0 USD) nhưng stale_plates có thể đòi vẽ lại
  ảnh (tốn tiền) — báo người dùng trước khi chạy dự án cũ.
# HANDOFF — Rà nhánh lệnh ngắn + ảnh/video chat: 6 lỗi đã sửa (09/10)

- (VỪA) `step1_chatrefs.read_page`: trang trước lấy theo `pending` → `ask` → `text` (dự án đã có cảnh, `_take` đẩy chữ sang pending/ask) → đọc nhiều trang không mất trang 1.
- (VỪA) `script_chat.intent`: `expand_request` xét TRƯỚC `command` → "viết kịch bản từ dàn ý này / theo dàn ý trên" lại đi đường S14.43 mục 5 (box_expand = request).
- (VỪA) "thôi" / "bỏ qua": có đề xuất thoại mở → intent 'chat' (Biên kịch xử lý); `_command(..., typed)` chỉ xóa chữ/thẻ chờ khi gõ đúng "hủy" (`script_chat.hard_cancel`).
- (NHẸ) `chat_refs.add` bỏ trùng (vai, nhãn, tệp), nhãn ≤ 80, mã duy nhất; `chat_refs.remove` + expander "📎 Tư liệu tham khảo (n)" có 🗑 (`step1_chatrefs.ref_list`, gọi trong `script_box`, hiện cả khi chưa có cảnh).
- (NHẸ) Nhiều file kịch bản một tin → `step1_box.extra_files` báo "Chỉ đọc “a”, bỏ “b”, “c”".
- (NHẸ) `chat_refs.read_page` chép ảnh gốc vào `<C.DATA>/<pid>/story_refs/` trước khi bỏ khỏi hộp chờ (chép lỗi → ValueError, ảnh vẫn chờ).
- Test: `tests/test_chat_cmds_refs.py` `ReviewFixTests` 1–6 + `ChatAppTests.test_review_4_…` (10 đỏ trên code cũ → 166 xanh).
- Mở: 🗑 chỉ bỏ dòng tư liệu, tệp đã chép giữ trên đĩa; ảnh trang lưu trong story_refs chưa hiện trong danh sách tư liệu.

# HANDOFF — Chat Kịch bản: lệnh ngắn + ảnh/video thả vào chat (09/10)

## Đã xong
- Lỗi 1 ("phân tích kịch bản này" → hỏi lại "Bạn muốn làm gì?"): gốc là KHÔNG có bộ nhận câu lệnh — câu ngắn bị `classify` coi là ý tưởng
  → `intent` 'ask'; dòng "Hiểu là KỊCH BẢN (thấy 1 tiêu đề cảnh)" là verdict của kịch bản CŨ còn trong khung. `core/script_chat.command`
  (luật, có dấu NFC, khớp TRỌN tin ≤ 80 ký tự, một dòng): analyse / write / idea / script / cancel; `intent` → 'command' trước mọi nhánh.
  `step1_box._command` chạy đúng hành động nút (▶ Phân tích 0 USD; viết → luồng Biên kịch, lượt vẫn sau nút có giá; dùng làm ý tưởng;
  hủy thẻ / tin hỏi lại / chữ chờ) và luôn nói lý do khi không làm được. "viết kịch bản đi" trước đây thành ý tưởng "viết kịch bản đi" — đã hết.
- Lỗi 2 (image/jpeg not allowed): `chat_input` `file_type=None` + `accept_file="multiple"`; `step1_box.media_in` lọc loại tệp, loại lạ báo
  tiếng Việt; cờ chat_first tắt → `chat_intake.receive` lưu MỘT lần vào `<C.DATA>/<pid>/chat_inbox`, thẻ nút `step1_chatrefs.ref_cards`
  (📄 Ảnh trang kịch bản · ≈ giá / 🏙 Bối cảnh / 🪑 Đồ vật / 🧍 Nhân vật / Hủy; video: 🎬 Video tham khảo / Hủy) + ô Nhãn.
  Cờ bật → thẻ radio cũ có thêm vai script_page (nút có giá) và video_ref.
- (a) `core/chat_refs.read_page`: một lời gọi `client.complete(prompt, [ảnh])`, stage `script_ocr` (STAGE_SETTINGS, LLM_STAGE_TOKENS,
  dòng ngân sách claude_director), chỉ khi bấm; chữ → `_take` như dán (nhiều trang đọc liền nhau được nối).
- (b)/(c) `chat_intake.apply`: bối cảnh/đồ vật/nhân vật → Kho dự án (như cũ) + dòng tư liệu; video_ref → `<C.DATA>/<pid>/story_refs/`.
  Danh sách ở app_settings `chat_refs:<pid>`; `chat_refs.block` vào prompt Biên kịch (`idea_to_script.build_prompt`) và Đạo diễn
  (`build_director_bundle`, `build_intent_bundle`) dạng chữ; không có tư liệu → prompt y như cũ.
- Test: `tests/test_chat_cmds_refs.py` (luật lệnh, _command, tư liệu + prompt, OCR mock, AppTest chat). devsys/areas.json khai file mới.

## Việc mở
- Ảnh tham khảo chưa gửi kèm prompt Biên kịch / Đạo diễn (hai lớp đó chỉ gửi chữ) — mới có tên + vai + ghi chú.
- Chưa có chỗ xem / xóa danh sách tư liệu `chat_refs` trên UI (ảnh đã vào Kho thì xóa ở Kho).
- `script_ocr` chưa có trần riêng (một lời gọi ≈ vài cent, tính vào dòng Đạo diễn).

# HANDOFF — KLD-10 nối dialogue_chat vào khung chat Kịch bản (09/10)

## Đã xong
- `core/script_chat.py`: `send` dùng `dialogue_chat.prompt/parse`; tin assistant lưu `proposals` [{id Px, line, speaker, old, new, why, state}];
  `append(..., **extra)`; `_set` / `_set_state` ghi lại trường (cả mảng proposals) bằng một câu `json_set`.
  Áp dụng chỉ khi `apply` có giá trị + `approved(tin cuối của người)` + đề xuất còn mở; có tin "Đã áp dụng …" (kèm `undo`, `after`).
  `undo(p, pid, i)` khôi phục thoại cảnh + đoạn kịch bản cảnh + kịch bản dự án; từ chối khi đã hoàn tác hoặc thoại đã đổi sau đó.
  Đề xuất trỏ câu không có / áp dụng không đồng ý / đề xuất đã đóng → ghi ⚠ trong tin (không im lặng).
- `intent`: `is_dialogue_talk` (so có dấu, chặn biên chữ; "ok" một mình vẫn 'ask').
- `core/llm_runner.py`: `script_chat` max_tokens 1500 → 3000 (test cũ cập nhật số).
- `core/dialogue_chat.py`: sửa lệch chỉ số khi cảnh có dòng thoại rỗng (`dial[n]` thay `spoken[n]`).
- `dashboard/steps/step1_box.py`: `_messages(p, pid, messages, start)` + thẻ đề xuất (D.card + D.pill, câu cũ gạch ngang, câu mới, lý do, trạng thái),
  nút "↩ Hoàn tác · 0 USD" (in-run, không fragment).
- Test: `tests/test_script_chat_kld10.py` (intent, send/apply/undo, AppTest UI); `devsys/areas.json` khai file mới (không tăng version).

## Sửa 7 lỗi rà độc lập (09/10)
1. `dialogue_chat.approved`: phủ định (`_NEGATE`), hỏi lại ("?"), kèm sửa ý sau từ đồng ý (`_CHANGE`) → False. `script_chat._apply_turn`
   tự áp dụng chỉ Px của tin assistant gần nhất có đề xuất; Px cũ hơn chỉ khi gọi đích danh Px/Lx (`named_codes`), không thì ghi ⚠.
2. `intent(text, p=None, pid=None)`: "ý tưởng/viết kịch bản/dàn ý" xét trước; "điện thoại" không tính; Lx/Px chỉ khi có thật; lời
   đồng ý chỉ là chat khi có đề xuất mở; đang viết ý tưởng → chỉ lời đồng ý là chat. `step1_box` truyền `p, pid`.
3. `apply` chụp chuỗi `data` thô của cảnh; `undo` ghi lại nguyên chuỗi (giữ trường lạ, dòng rỗng, `_user_locked` cũ; lineage tính
   theo vân tay nên tự khớp lại). Kiểm "đã đổi sau khi áp dụng" bằng vân tay sha1 (`fingerprint` / `changed_since`).
4. `_replace_in_text(..., nth)` thay đúng lần xuất hiện thứ n; không thấy → None + `notes` (không thay mù).
5. `HEADING` + `speech()`: "CẢNH 1: …", "INT: …", "LƯU Ý: …", "GHI CHÚ: …" không phải thoại.
6. Đề xuất bị thay → state 'superseded' (thẻ "đã có đề xuất mới hơn").
7. Bỏ mã apply trùng; đề xuất mới cùng lượt đọc `lines()` sau khi áp dụng.

## Đang dở / việc mở
- Chưa thử trên dashboard thật với Claude thật (tốn tiền) — cần người dùng gõ thử.
- Lúc ÁP DỤNG, `update_scene` vẫn chuẩn hóa dòng thoại (bỏ trường lạ như t_start/lang, bỏ dòng rỗng) — hoàn tác thì về nguyên trạng.
- Ảnh chụp hoàn tác kiểu cũ (dict) vẫn đi qua `update_scene` (chỉ tin áp dụng tạo trước bản sửa này).

## Bước kế
- Merge nhánh vào main, cập nhật TODO.md (mục KLD-10), chạy thử thật một lượt.

# HANDOFF — F5-A ô "sẵn sàng gen" + kích thước vật Kho (09/10/2026, nhánh `worktree-agent-aa7c4219627024dac`, chưa push)

**Đã xong** (0 USD, không gọi dịch vụ; Blender giả trong test):
- `core/readiness.py` (mới, chỉ ĐỌC): `shot_ready(conn, data_dir, pid, scene_id, kind)` / `project_ready(...)` (phần chung tính MỘT
  lần: nhân vật, model + giá, ảnh duyệt, motion, vật Kho, dòng model F4) → {ok, items:[{label, state ok|warn|red, why, fix_where}]}.
  Mục: công thức prompt (cùng luật `prompt_formula.red_issues` + cảnh báo vàng), nền 3D (có render + góc rộng / chưa render = warn /
  hỏng = red / chờ hướng máy = red), ảnh tham chiếu thiếu (warn), model · ≈ USD (video dùng `model_line`, cảnh báo E1 = warn), ảnh
  khung đầu đã duyệt (video, thiếu = red), vật mốc Kho chưa có kích thước ở ≥ 2 shot (warn). `summary` / `blocked_reason` / `details_md`.
- `dashboard/readiness_ui.py` + thẻ ảnh Bước 2 (v2 `storyboard_cards.image_group_v2` và v1 `image_card_group`) + thẻ clip
  `step4.video_card_v2`: một dòng ("✅ Sẵn sàng" / "✅ Sẵn sàng · 1 lưu ý: Nền 3D" / "⛔ 2 việc cần sửa: …") + expander "Chi tiết
  sẵn sàng gen"; shot red → caption "⛔ Gen sẽ bị giữ/chặn: … → sửa ở Bước X" ngay dưới nút gen. Không nút mới, giữ mọi widget key.
- Vật Kho (kind prop / weapon = `assets.SIZED_KINDS`): `height_m` / `width_m` lưu trong cột `profile` (JSON, như chiều cao nhân vật)
  — `assets.set_size`, `get()`/`list_assets`/`project_assets` trả `size`. Màn Kho (admin, "✏ Sửa"): một ô số "Chiều cao thật (m)"
  (key `lib_e_h_<id>`), lưu bằng nút 💾 Lưu có sẵn.
- `place_refs.shot_objects / object_scale_sentence / unsized_objects`: vật Kho gắn dự án có trong characters/props của shot hoặc được
  nhắc trong image_prompt/blocking/start_frame/action_peak/location → "the stone well is 0.9 m high — about waist height of a 1.7 m
  adult". Vào phần nền `build_image_prompt` (mọi đường: ảnh, khung cuối) và bản gọn vào phần nền Seedance
  (`seedance_refs.prompt(..., scales=)`). Không có số → không câu.
- `tests/test_readiness_f5a.py` (11 test) + khai `devsys/areas.json` (khu step2, không tăng version). Đo truy vấn dự án 10 shot:
  ảnh 40, video ~125 khi màn không truyền dòng model (bước Video truyền sẵn → ít hơn).

**Còn mở / rủi ro**:
- Tên vật trong prompt: tên gọi khác không dấu đầu tiên (nên khai alias tiếng Anh, vd "stone well"); không có → tên bỏ dấu.
- Chiều cao người mặc định 1,7 m (chưa đọc chiều cao hồ sơ nhân vật / render 3D cho câu vật Kho).
- Lỗi đỏ readiness tính lại bằng `prompt_formula` (hàm nội bộ `_chars/_is_ff/_gore_goes/_sha`) — nếu F5-B đổi các hàm đó phải giữ chữ ký.
- Bước 4 video: readiness chỉ xét lint motion của CHÍNH shot (runner còn chặn theo cả nhóm — `group_red_issues`).

# HANDOFF — F5-B dọn việc tồn KLD (09/10/2026, chưa push, 0 USD)

**Đã xong** (test `tests/test_f5b_backlog.py`, chạy cùng bộ liên quan: 199 qua):
- KLD-9 / KLD-25: đã có sẵn ở `knowledge/roles/director_kld22.md` (cờ `kld_lessons_prompts`) — không thêm lại. **KLD-31**: mục "Đ7 bổ
  sung" ở cùng file (một clip 15 s → bịa áo; chia shot → đúng; độ tin 1 mẫu, không là luật). Nhóm Đạo diễn (kelly/murch/film_crew bật):
  **149 960 → 148 934** (trần 150 000, dư 1 066) nhờ gọn `director.md`: bỏ đoạn số 5,25 âm tiết/s không dùng, "Rủi ro chưa thử" N3
  (câu Seedance không hỗ trợ tiếng Việt đã cũ), câu lịch sử Đ9, rút Đ11 "chưa đo thật", Đ12 (MV), câu trùng N3/Đ3/Đ5/Đ8.
- KLD-13 `core/motion_prompt_lint.end_frame_problem`: `pull_out`/`crane`/`orbit` không có câu khung cuối → thêm vào cờ ⚑ ở thẻ Bước 3.
- KLD-26 `delivery.shakes_before_music`: rung trước giây nhạc vào → `manifest.shake_before_music` + diag `shake_before_music`; rung vẫn giữ.
  Mốc so = giây nhạc ĐẦU TIÊN vào (chưa phân biệt bài nhảy riêng ở nhạc nhiều chặng).
- KLD-30 `core/timestamps.utc_key` dùng ở `tools/kld_round_stats.py` + `tools/audit_run.py --since`.
- KLD-32 `claude_tasks.translate_motion_fields`: cờ `kld_lessons_prompts` bật → luật "chữ nhiều nghĩa giữ [chữ Việt] + khóa `_ambiguous`";
  ghi `motion_en_ambiguous` + diag `translate_ambiguous`. Cờ tắt → prompt dịch y hệt. Lưu ý: chữ trong [ ] đi vào prompt video trả tiền.
- KLD-33 `prompts/27_asset_checklist.md` mục 7–8.
- KLD-34 (kiểm): tự gen lại VIDEO của QC (`apply_qc` → `reject("ai_agent")`, cả auto và human_qc+autofix; `qc_scene`) ĐI QUA
  `director_rewrite` khi cờ bật; không đi qua khi: giữ cho người (`_no_auto_retry` / KLD-5), hết lượt tự sửa. Đường vẽ lại ẢNH của QC lớp 0
  (`runner.RedrawWithFix` → `Pipeline.retry(fix=)`) KHÔNG qua director_rewrite — chưa đổi (luồng tiền, chờ người quyết).
- Tiếng video ref → SFX: `core/ref_audio.py` (`propose`, `fit`), nút "🎥 Lấy tiếng … video tham chiếu" ở Bước 5 (đề xuất `use: False`, neo shot);
  khi dựng `sfx_plan.place_on_timeline` nén/giãn atempo bản đã tích (≤ 40 %, hơn thì ghi `fit_skipped`), `audio_lib.mix_list` dùng `fit_file`.
- Test chập chờn Blender queue: thay `sleep(0.2)` bằng `threading.Event`.

**Để người dùng quyết:** KLD-10 (nút "Biên kịch đọc thoại" — tốn 1 lượt Claude), KLD-27 (dữ liệu hồ sơ thật).
**Chưa thử Dashboard thật:** nút tiếng ref Bước 5, cờ ⚑ Bước 3.

---

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

## Rà độc lập F5 — sửa 09/10 (mục 1, 2, 4, 5)
- KLD-32: `seedance_refs._en` bỏ `[1–2 từ]` khỏi `motion_en` trước khi ghép prompt video (chữ nhiều nghĩa vẫn báo qua `motion_en_ambiguous` + diag); `claude_tasks._unbracketed` chỉ nhận `[1–2 từ]`.
- Readiness: thêm red "Bố cục nơi chốn" (`assets.missing_layout`, ảnh) + "Nhóm gửi chung" (red_issues các shot khác cùng nhóm, video).
  **Chưa làm:** `seedance_refs.lint_group` (tiếng Việt / dài > prompt_limit / số ảnh) trong readiness — cần dựng prompt nhóm một lần mỗi nhóm (đọc ảnh, segs thoại); runner vẫn chặn trước khi trả tiền.
- `assets.set_profile` giữ `width_m` + chiều cao vật Kho (prop/weapon 0,01–100 m, không gửi số thì giữ số cũ).
- `runner._object_scales` bọc try; `seedance_refs.prompt(reserve=)` bỏ câu kích thước trước khi vượt `prompt_limit`.
