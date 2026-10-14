# Kiểm thật trước tập 2 #27 — 14/10/2026 (phiên máy chính, Claude thao tác Dashboard)

Người dùng duyệt trần **2 USD**; từ 14/10 người dùng không tự bấm Dashboard — Claude thao tác (mở `?op=claude`, nhật ký `ui_actions`).
Main lúc kiểm: `d3779800` (gộp 4 nhánh `claude/tap2-a/b/c/d` + sửa nhật ký thao tác). Sao lưu trước khi kiểm:
`data/backup/manifest.backup_20261014_kiem_that_tap2.sqlite`, `data/feature_settings.backup_20261014_kiem_that_tap2.json`.

## Các bước
1. Bật ở 🧪 qua Dashboard: `side_truth`, `script_pose_fix` (`chat_prompts`, `two_tier_quality` đã bật sẵn).
2. #28 "🤖 Chạy Director … (chạy lại)" → Dashboard từ chối "Dự án đã có ảnh/video… bấm ↺ Làm lại" (0 USD, nhật ký ghi
   `chay_dao_dien error 267 ms`). Không xóa bản thử D6 → **🧬 Nhân bản #28 → #30** "Kiểm thật tập 2 — Tháp Đồng Hồ (từ #28)" (5 shot, 4 mục Kho).
3. #30 chạy Director hai lượt (báo giá 0,90) → **7 shot**. ▶ Gen ảnh 7 shot (báo giá 0,36; job 936–942, Blender render nền 0 USD rồi tự gửi).
4. Ảnh: `D:\AI-Video-Output\2026-10-14_kiem_that_tap2\anh\` (+ `tong_hop_7_shot.jpg`). Chưa duyệt — người dùng duyệt qua chat.

**Tiền thật:** Claude ≈ 1,32 USD (director 3 lượt + D6 7 lượt + trainee QC 7) + ảnh 7 × GPT Image 2.5 ≈ 0,36 → **≈ 1,68 USD**.

## Kết quả theo danh sách kiểm (bàn giao [14/10 15:46])
| Điểm kiểm | Kết quả |
|---|---|
| Shot 1 nền away khi máy trước mặt (`plate_view_fix`) | Đạo diễn tự ghi `scenery` (máy đối mặt Kelly) → lớp sửa không cần chạy. **NHƯNG ảnh shot 1 Kelly chạy XUỐNG cầu thang, tháp sau lưng** — hướng chạy vẫn sai kịch bản (A chân cầu thang → B bậc cao nhất) ❌ |
| Tư thế shot "đứng sát, núp" (`script_pose`) | ✅ shot 4 BYĐ + prompt "standing pressed against the left side", ảnh Kelly ĐỨNG |
| Trái/phải (`side_truth`) | ✅ shot 5 code chèn FRAME-LEFT (máy sau lưng), ảnh Kelly chạy sang trái khung; shot 4 VÀNG (shot không ghi máy sau/trước) — đúng thiết kế, không đoán |
| Tường keo CONG + skin thang máy + cỡ ~1,2 người / rộng ~4 m | ❌ **tường trắng như tuyết/đá**, KHÔNG phải skin thang máy; dáng hơi cong ở shot 3, 5, 6; cỡ tạm được |
| D6 không bị chặn mã/độ dài | ❌ **6/7 shot D6 bị code chặn "mất mã ảnh: Image 3"** → gửi bản code ghép; chỉ 1/7 gửi bản D6 |
| Không 'clock tower' / mặt đồng hồ | ✅ code đổi chữ (diag `chat_prompt_feature_word` 6 lần), ảnh không có mặt đồng hồ |
| Nhật ký thao tác (nhánh D) | ✅ sau bản sửa `d3779800` (kết nối riêng) — lần đầu 0 dòng vì ghi qua `p.conn` của trang |

## Gốc lỗi đã tìm (chưa sửa — việc phiên kế)
1. **Tường keo trắng — dạng skin bị rơi giữa kịch bản và shot:** `script_text` cảnh ghi "tường keo (skin thang máy)" nhưng KHÔNG shot nào
   (scenes.data 302–308) còn chữ "skin"/"thang máy" (Đạo diễn chia shot bỏ mất) → chọn dạng theo chữ shot → dạng MẶC ĐỊNH trắng → gói gửi
   (`jobs.sent_refs` 938, 941) không có ảnh Kho #367. Sửa đúng gốc (một nguồn sự thật): dạng/biến thể mục Kho ghi trong câu kịch bản của
   cảnh phải được code mang xuống mọi shot dùng mục đó (không trông Đạo diễn chép chữ) + test; diag khi cảnh nói dạng mà shot mất.
2. **D6 chặn "mất mã ảnh: Image 3":** 6/7 lượt `chat_prompt` (≈ 0,04 USD/lượt, vẫn tốn tiền) bị loại. Gói ảnh có 7 mục (render nền, KELLY ×2,
   SKORP, toàn cảnh, ảnh neo khung 1, storyboard) — cần xem Image 3 là mục nào và vì sao Claude bỏ (trùng nhãn KELLY ×2? ảnh neo?), sửa đề
   bài D6 hoặc luật so mã (không nới để che lỗi).
3. **Shot 1 chạy xuống cầu thang:** máy đối mặt Kelly + tháp sau lưng → model vẽ Kelly đi xuống. Cần câu hướng chuyển động do code viết
   (lên/xuống theo độ cao chỗ đứng A→B đã biết trong 3D: z 3,9 → 8,5) thay vì để chữ.

## Chưa làm
- **Bước 5 dựng thật** (người dùng duyệt thử): để sau khi hạn mức 5 giờ đặt lại; dự án đề xuất #29 (đã có 5 clip duyệt) — hỏi giá nút trước.
- Video nháp #30: chưa gen (chờ người dùng duyệt ảnh qua chat).
