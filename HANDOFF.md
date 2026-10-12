# HANDOFF — Bộ viết motion BẰNG CODE (ca #27 12/10, 21 shot)

## Nguyên nhân gốc (đọc chỉ-đọc manifest #27)
- #27 KHÔNG có lượt `translate` trong llm_calls; diag motion 12/10 12:58: Anthropic HẾT TIỀN → `translate_motion_fields` lỗi →
  `write_by_code` chỉ ghi warn rồi `code_motion` vẫn viết prompt tiếng Việt và DUYỆT ngay (21/21 approved).
- `shot_motion` lấy mọi `dialogue[].speaker` → "LỜI DẪN speaks"; không có câu điểm bắt đầu / lớp nền (luật ambient chỉ ở đường Claude).

## Xong
- `core/speaker_lint.py`: `is_narrator` (so CẢ DẤU, cả tên: 'VÕ' ≠ 'VO', 'LỜI' ≠ 'LỜI DẪN', hậu tố "(V.O.)"), `in_frame`,
  `voice_only_names`/`voice_only_of` (hồ sơ "voice-over / ngoài hình / không xuất hiện trên hình"); `speakers()` chỉ người có mặt
  (`data.characters`; không có danh sách → như cũ trừ người dẫn). Áp cho Kling speaker check (runner) + kiểm 'thoai' của công thức.
- `core/seedance_refs.py`: `shot_motion` — chỉ người trong khung "speaks"; cờ `prompt_formula` → `START_SENTENCE` đầu; cờ
  `ambient_motion` → `prompt_formula.ambient_sentence`. Cả 2 cờ tắt → y từng byte (test). `prompt()` bỏ START_SENTENCE khỏi từng shot
  (khối mở đầu nhóm đã nói). `code_motion`: còn tiếng Việt / ĐỎ / VÀNG phần công thức code tự viết (HOLD_PARTS: điểm bắt đầu, hành
  động, máy quay, trạng thái cuối, thoại, nguồn động tác, chuyển động nền) / formula_check không khớp sha prompt → 'pending' + diag
  `code_motion_held`; VÀNG khác (vd "hồ sơ trang phục không so được") → tự duyệt + diag info nêu lý do. `vietnamese_held` viết lại
  shot bị giữ khi đã có bản dịch. `translate_estimate` (= project_budget._translate_worst, 0 khi không cần dịch). `write_by_code`
  trả `held`; không có Claude mà cần dịch → warn.
- `core/prompt_formula.py`: `ambient_sentence` (weather giông/mưa/sương → câu theo thời tiết; ngoài trời có cỏ/cây/nước/lửa/khói →
  câu vật đó, gió nhẹ chỉ khi không ghi trời lặng; trong nhà chỉ lửa/nến có sẵn; trong+ngoài lẫn / thiếu weather / không thấy vật →
  "" và VÀNG giữ nguyên). Tránh khớp nhầm: không 'cây' trần (cây súng), không 'hồ' trần (đồng hồ), không 'phòng' trần (phòng thủ).
- `core/autopilot.py` `_motion_phase`: đọc lại lý do giữ mỗi lượt; tiếng Việt / ĐỎ → không duyệt, `_Stop` có ghi chú (không "đang
  chạy" trả tiền dịch mãi); VÀNG → tự duyệt như luật cũ của chạy tự động + log nêu lý do.
- `dashboard/steps/step3.py`: nút cộng tiền 1 lượt dịch (worst case) vào ước tính + ghi "gồm 1 lượt dịch ≈ X USD"; đếm shot tiếng
  Việt bị giữ (chỉ khi có Claude); cảnh báo danh sách shot chờ duyệt.
- Test: `tests/test_code_motion_p27.py` (13; 10 đỏ trước sửa, test autopilot thêm sau phản hồi agent rà). Sửa 2 test cũ
  `test_seedance_refs.py` vốn ghim hành vi bị yêu cầu đổi (mock Director viết tiếng Việt → trước được duyệt): test 1 cấp motion_en
  tiếng Anh; test nút: dịch lỗi → 'pending' + held. 424 test liên quan xanh. Agent rà khu liên quan: 2 lỗi + 4 điểm, đã sửa hết.

## Viết lại motion #27 sau khi gộp
- Nạp tiền Anthropic. Bước 3 → xóa/làm cũ prompt hiện có (đã approved nên code không tự viết lại) rồi bấm "🤖 Viết motion prompt"
  — hoặc gọi `seedance_refs.write_by_code(p, 27, client)` sau `DELETE FROM motion_prompts WHERE scene_id IN (shot #27)`.
  Tiền: 1 lượt dịch ≈ 0,10 USD worst case (`project_budget._translate_worst` đo trên manifest #27 = 0.101).

## Rủi ro
- Câu nền là luật chữ, chưa thử video thật. Shot trong nhà #27 (thế giới song song) sẽ VÀNG → chờ duyệt ở nút Bước 3.
- Mặc định đổi: START_SENTENCE vào mọi prompt code khi prompt_formula BẬT (mặc định BẬT).

# HANDOFF — Khóa đạo cụ dự án (cờ `project_prop_lock`, lỗi #27 12/10)

## Xong
- `core/prop_lock.py` (mới): xếp món Kho weapon/prop đã gắn dự án theo loại (súng / tường keo); shot chỉ nói từ chung (ranh giới từ,
  giữ dấu: "kéo" ≠ "keo") → câu "Prop lock" nêu tên + mô tả từ `assets.description` (bỏ nhãn nguồn `[..]`); nhiều món cùng loại → VÀNG
  phần `dao_cu`, không đoán. Dạng: đoạn "(a) MẶC ĐỊNH …; (b) skin …" trong mô tả; ảnh có `asset_images.variant` chỉ gửi khi chữ shot
  nhắc variant (vd "Gloowall"/"OB55"), không nhắc → dạng mặc định, không gửi ảnh skin.
- `core/runner.py` `build_image_prompt`: phần `_prop_part` sau phần hành động (cờ tắt → "" → prompt giữ nguyên từng byte).
- `core/assets.py` `scene_references`: món bị khóa vào ảnh tham chiếu (role object); món weapon/prop có tên → chọn ảnh theo variant.
- `core/prompt_formula.py`: `_prop_issues` vào `formula_check["image"]` (after_director + on_prompt_saved); nhãn "Đạo cụ dự án".
- `core/features.py`: cờ `project_prop_lock` (verified False). `devsys/areas.json`: thêm file + test (không tăng version).
- Test `tests/test_prop_lock.py` 8 test đỏ → xanh; chạy kèm 8 file test liên quan: 188 passed.

## Dở / rủi ro
- Chưa chạy thật (cờ tắt). Bật cờ rồi gen lại 1 shot rẻ của #27 (shot 1 "assault rifle", 1 shot tường keo) để có bằng chứng.
- Chỉ prompt ẢNH; motion prompt video chưa khóa đạo cụ.
- Từ chung "weapon" xếp vào loại súng; dự án có vũ khí cận chiến/lựu đạn khác loại súng chưa có loại riêng.

## Bước kế
- Phiên chính: rà theo quy ước 7 (`py tools/related_areas.py`), gộp vào main, cập nhật TODO.
