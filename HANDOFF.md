# HANDOFF — nhánh `claude/fix-shot-payload` (14/10/2026)

Gốc: main `92b40562`. Việc: 3 lỗi gốc kiểm thật #30 (docs/handoff/KIEM_THAT_TAP2_2026-10-14.md mục "Gốc lỗi" 1 và 3) + việc 4 (công cụ
kiểm 0 USD). Không push, không sửa TODO.md (phiên chính gộp).

## 1. Công cụ `tools/replay_payload.py` (việc 4)
`PYTHONUTF8=1 py tools/replay_payload.py --project 30 [--shot 1] [--flag travel_truth=on] [--json out.json] [--width 300]`
- Gọi đúng `ImageRunner._submit_args` (prompt cuối + `sent_refs`, gắn mã mục Kho cho từng ảnh), so nhãn với `jobs.sent_refs` thật.
- An toàn: thư mục thử tạm (bản sao CSDL qua sqlite backup chỉ đọc + bản sao feature_settings, D6 `chat_prompts` luôn TẮT + bản sao
  `data/projects/<pid>`), junction `data/assets`, `data/_plates3d` → bản chính, cwd = thư mục thử, provider giả không có hàm gửi,
  `WriteGuard` chặn mọi ghi dưới `<main>/data`; cuối gỡ junction bằng `os.rmdir` rồi mới xóa thư mục thử.
- Bằng chứng: `docs/handoff/replay_p30_2026-10-14/` (trước/sau sửa, bản đầy đủ + tóm tắt). Trước sửa: nhãn gói GIỐNG hệt job 936–942
  thật (tái hiện đúng), shot 3–7 câu khóa "tường keo màu TRẮNG", không shot nào có ảnh Kho #367; shot 1 không có câu hướng chạy.

## 2. Tường keo trắng (gốc lỗi 1)
Gốc: `core/prop_lock.py` `locks()` (trước: dòng ~338) chọn dạng bằng `chosen_variant(a, shot_text(data))` — chỉ chữ SHOT; kịch bản cảnh
(`story_scenes.text` #30: "tường keo (skin thang máy)") không được đọc → dạng mặc định trắng → `usable_images` chỉ lấy ảnh không variant
(Kho #367 chỉ có ảnh variant skin) → không ảnh. Cùng lỗi ở `core/assets.py` `_named_extras` (~1757).
Sửa (một nguồn sự thật): `prop_lock.variant_source()` = dạng chữ shot nói, không có thì dạng câu kịch bản CẢNH nói (chỉ câu có nhắc món,
đúng một dạng; nhiều dạng → không đoán + VÀNG). Dùng ở `locks()`, `_named_extras`, `prompt_rewrite` (nguồn cho phép biến thể).
VÀNG `prop_variant_scene` (runner + `issues()`/formula_check) khi dạng lấy từ cảnh. Sau sửa: shot 3–7 #30 có ảnh Kho #367 + "skin Gloowall".

## 3. Shot 1 chạy xuống cầu thang (gốc lỗi 3)
Gốc: không chỗ nào trong prompt nói hướng chạy theo dữ liệu 3D; nền shot 1 (`plate_view` 'scenery' hỏng → hướng mặc định chỗ đứng 298°)
đặt máy PHÍA DƯỚI nhìn lên theo hướng chạy (camera_plan 302: nhìn 118° = hướng A→B), chữ Đạo diễn lại "chạy về phía máy".
Sửa: `core/travel_truth.py` (cờ mới `travel_truth`, mặc định TẮT — chưa gen thật) — câu "Direction of travel (measured on the 3D map): …
UP the stairs … 3.9 m → 8.5 m … AWAY from the camera … never going down" vào prompt ảnh (place_extra) + video (sau side_truth, có trần ký
tự) + giữ sau D6. Chữ shot trái nền → VÀNG nêu cách sửa (plate_view ≈ 298° rồi render lại nền, 0 USD).

## Việc mở / rủi ro
- **Shot 1 #30 vẫn cần quyết**: theo nền hiện tại Kelly chạy lên = quay lưng về máy; kịch bản muốn chạy VỀ PHÍA máy → phải đổi nền
  (plate_view background ≈ 298°) rồi render lại. Code không tự đổi nền (không đoán).
- Storyboard (`scene_storyboard.shared_references`) chia ảnh món cho cả cảnh → shot 1–2 (không có tường keo) giờ cũng nhận ảnh #367
  (trước đó SKORP đã vậy). Thiết kế cũ, chưa sửa.
- Cờ `travel_truth` cần bật ở 🧪 để có tác dụng. Chữ "thang máy" trong câu khóa bị skill_objects đổi thành "tấm kim loại" (luật cũ 13/10).
- Nhánh song song `claude/fix-d6-image3` sửa core/chat_prompt.py; nhánh này chỉ sửa `runner.chat_rewrite` (giữ câu hướng chạy) — có
  thể đụng khi gộp.

## Rà soát + vòng sửa (14/10 tối, commit thứ 2)
Rà khâu liên quan (agent) + rà diff; đã sửa:
- `prompt_rewrite`: chữ kịch bản cảnh KHÔNG còn nối vào chữ shot (lời thoại/câu khác từng cho phép mọi skin); nguồn riêng = đúng dạng
  `variant_source` trả 'scene'. `prop_lock.chosen_variant`: cụm dạng đầy đủ thắng dạng đứng trước trong Kho ("skin Gloowall OB56" từng
  ra OB55 theo luật 'skin + từ chung').
- `lineage.image_key/forms_key`: vân tay ảnh thêm [(món, dạng)] lấy từ CẢNH chỉ khi có (cờ prop lock bật) — ảnh khác giữ hash cũ; ảnh
  #30 shot 3–7 cũ (tường trắng) nay hiện "⚠ cũ" (đúng). travel_truth KHÔNG vào vân tay (như side_truth/stage_facts: bật cờ không được
  làm ảnh đã duyệt thành cũ → autopilot gen lại tốn tiền).
- `travel_truth`: LIMIT 1 (shot kế/trước ngay); "steps" lẻ trong chữ shot không còn biến dốc thành cầu thang. Video Seedance: câu hướng
  chạy cộng vào `reserve`. Khung cuối (`end_frames._side_guard`) nhận câu hướng chạy (cờ bật).
- `skill_objects`: ảnh triển khai xếp theo dạng của shot/cảnh (`_by_form`, chỉ khi prop lock bật; `deployed_pictures` hiện chưa nơi
  nào gọi). Ảnh Kho có hình nộm so cỡ (#367 3.png) → câu "The grey mannequin in Image N is only a size guide … never draw the mannequin"
  (prompt ảnh: `mannequin_note`; video: `deployed_line(mannequin=)`). SHAPE tường keo: ~1,3 lần chiều cao ≈ 2,3 m, rộng ~4 m ≈ 2,3 lần
  chiều cao.
- `tools/replay_payload.py`: chép cờ FEATURE_ từ `<main>/dashboard.env` (chỉ dòng FEATURE_), so từng shot với `jobs.sent_package`
  thật (ảnh, câu khóa, SHAPE, câu hướng chạy). Kiểm: code gốc 92b40562 dựng lại job 936/938–942 Y HỆT gói thật (937 = bản D6).
  Kết quả: `docs/handoff/replay_p30_2026-10-14/sau_ra_soat_tom_tat.txt`.

## Rủi ro gộp với `claude/fix-d6-image3`
- HANDOFF.md: cả hai nhánh tạo mới → xung đột add/add (gộp tay hai nội dung).
- devsys/areas.json: hai nhánh sửa khu vực khác nhau (Bước 2 vs hệ thống) → không xung đột chữ.
- core/chat_prompt.py chỉ nhánh D6 sửa; nhánh này sửa `runner.chat_rewrite` (giữ câu hướng chạy sau D6). Ngữ nghĩa: câu hình nộm và
  câu khóa dạng skin chưa được giữ sau D6 (không có kept_after_rewrite) — D6 `check` có thể chặn/bỏ; xem khi chạy D6 thật.
- Prompt ảnh #30 đổi (ảnh #367, câu dạng, hình nộm) → khóa cache D6 đổi → lần gen kế gọi D6 lại (đúng chi phí 1 lượt/shot, không thừa).
