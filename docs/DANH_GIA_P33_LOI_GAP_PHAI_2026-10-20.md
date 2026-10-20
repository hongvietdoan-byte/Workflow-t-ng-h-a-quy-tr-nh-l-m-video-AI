# Dự án #33 — OB55 Con rối nhảy Tháp đồng hồ (thế giới song song): lỗi gặp phải và cách xử lý

Ngày 19–20/10/2026, phiên `hungry-mayer` + phiên lịch `ob55-con-roi-nhay-thap-dong-ho`. Kế hoạch dự án ở
`docs/DU_AN_OB55_CON_ROI_2026-10-19.md`. Bản giao ở `D:/AI-Video-Output/2026-10-19_du-an-33/`
(`p33_tiktok_1080x1920.mp4`, `p33_ban_cao_1080p_hau_ky.mp4`, `p33_ban_cao_1080p_hau_ky_ghep_ref_chu.mp4`).

## 1. Chi phí thật (sổ chi)

| Hạng mục | USD |
|---|---|
| Ảnh mẫu con rối (3 lượt × 3 ảnh) | 0,47 |
| Ảnh khung đầu (5 lượt × 6 ảnh + sửa S2/S4/S6) | ≈ 1,81 |
| Video nháp 480p (4,51 + 0,52 S3 + 3,48 + 2,96) | ≈ 11,47 |
| Bản cao 1080p (6 clip nâng từ nháp) | 22,91 |
| **Tổng** | **≈ 36,66** |

Claude: 0 USD API (Anthropic hết tiền; mọi bước Claude chạy bằng Claude Code trên máy).

## 2. Lỗi hệ thống / pipeline (cần sửa code — CHƯA làm)

| # | Lỗi | Gốc | Đã xử lý tạm | Việc code đề xuất |
|---|---|---|---|---|
| A1 | Job ảnh/clip **succeeded 2 lần** (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → **tự gen lại** (thừa 0,05 USD job 1162→1163) | `core/bg_poll.poll_all` CỐ Ý hỏi cả dự án tạm dừng; khóa `_turn` của runner chỉ trong MỘT tiến trình → tiến trình riêng + Dashboard cùng poll | Tiến trình riêng chỉ `submit_pending`, để Dashboard poll | Khóa poll/succeed theo job liên tiến trình (như `send_claim`) trong `runner.poll_once` |
| A2 | Vòng nền Tổ rà soát của Dashboard (anthropic hết tiền) chộp `change_events` pending → `failed` → giữ job | Dashboard dùng `LLM_PROVIDER=anthropic`; không đổi được vì #31 đang dở | Rà từng shot bằng `review_scene_now` + client claude_cli ngay sau khi đặt pending | Chọn nhà cung cấp Claude theo dự án (hoặc theo phiên), không chỉ theo `dashboard.env` |
| A3 | `claude -p` báo "Credit balance is too low" / "session limit" | Script gọi `load_env` nạp `ANTHROPIC_API_KEY` → CLI dùng key API hết tiền; CLI dùng tài khoản đăng nhập ở terminal (khác tài khoản phiên) | `os.environ.pop('ANTHROPIC_API_KEY')` sau `load_env` | `ClaudeCliClient.clean_env` bỏ luôn `ANTHROPIC_API_KEY` |
| A4 | Đạo diễn (director_rewrite, chạy claude_cli) **tự viết lại image_prompt shot 1–3** khi loại ảnh, ép thấy đỉnh tháp + xoáy → ảnh bản 3 dời tháp vào giữa, thêm mặt đồng hồ | Viết lại không giữ ý đã chỉnh tay | Khôi phục prompt từ sao lưu; tắt `director_rewrite` + `chat_prompts` CHỈ trong tiến trình gen | Không viết lại trường người đã khóa (`_user_locked`) / so trước–sau trước khi ghi |
| A5 | QC lớp 0 **đo nhầm cỡ cảnh** ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" | Đo cỡ cảnh theo mặt người gần nhất có mặt, không hiểu bố cục qua vai | Hủy job tự gen, đổi size shot sang WS | Bỏ qua kiểm cỡ cảnh khi shot ghi over-the-shoulder / sau lưng |
| A6 | Tổ rà soát **báo nhầm** shot 6 "không có video tham chiếu" (#877) | Dữ liệu đưa cho người rà thiếu `motion_prompts.ref_video_path` | Đóng `dismissed` kèm lý do | Đưa ref_video_path vào đề rà |
| A7 | **Giá lệch**: video nháp sổ chi ≈ 1,37 × bảng giá (phụ phí video ref chưa có trong `cost.clip_price`); bản cao 1080p sổ chi cao hơn `final_estimate` ~24 % → chạm trần `--max-usd` giữa chừng | Bảng giá thiếu phụ phí ref / nâng bản cao | Báo giá theo hệ số thực tế | Cập nhật bảng giá Seedance kèm ref + giá nâng 1080p |
| A8 | Nút Gen video báo 9,13 USD (tính mức 720p + D6 Claude API) trong khi gửi nháp 480p | `estimate_videos_by_scene` lấy tier từ profile, không theo nháp | Tính tay theo 480p | Ước tính theo `_draft_tier` như `video_plan` |
| A9 | `pregen_check` cộng ≈ 1 USD Claude (D6 + QC) theo giá API dù chạy claude_cli; không ước tính giá video | — | Ghi chú khi báo giá | Giá Claude = 0 khi provider claude_cli; thêm phần video |
| A10 | Góc `high` của plate cố định chúc 30° (`plate_camera.HIGH_TILT_DEG`) → nền chỉ còn sàn đá | Không có góc "hơi cao" | Dùng `eye` (máy ngang mắt người lớn ≈ chúc 5–10° xuống con rối chibi) | Thêm mức nghiêng nhẹ |

## 3. Lỗi nội dung / model (đã xử lý trong dự án)

| # | Lỗi | Cách xử lý |
|---|---|---|
| B1 | Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu | Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 % |
| B2 | Ảnh trời tham chiếu dính đỉnh tháp → model vẽ **tháp thứ hai** | Cắt ảnh trời chỉ phần mây/mắt xoáy |
| B3 | Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa | Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py` |
| B4 | Nền ghép "như dán đè ảnh 3D" | Chuyển màu Lab theo ảnh in-game người dùng (`goc_chup_ingame_chuan.png`), mây in-game + vệt gió + sương theo `depth.png`, quầng đỏ sẫm |
| B5 | Góc in-game chuẩn = máy thấp ở thềm nhìn lên cầu thang, tháp TRÁI bị cắt đỉnh; đổi sang EWS cho thấy đỉnh tháp là SAI bố cục | Về WS góc thấp |
| B6 | Cổng công thức chặn TRƯỚC khi trả tiền: câu "nếu đỉnh tháp ngoài khung" ↔ "đỉnh tháp thấy ở trên trái" | Bỏ câu mâu thuẫn (cổng làm đúng việc) |
| B7 | Cổng video chặn: motion còn tiếng Việt (tên RỐI … có dấu, "Tháp Đồng Hồ") | Tên không dấu (ROI DO A…) + "the Clock Tower" |
| B8 | Seedance ref-only **chép cả đoạn chuyển cảnh đầu đoạn ref**: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) | Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc |
| B9 | Seedance ref-only **không giữ khung ảnh đầu**, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo | Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt |
| B10 | Chữ "cats" trong motion ngoài câu chặn → nguy cơ vẽ mèo (Tổ rà soát bắt) | Đổi "like the reference video"; giữ câu chặn "the cats in the reference only give the motion…" |
| B11 | Bản ghép ref 1080×2730 quá khung TikTok; cắt khung con rối quá cao → thấp đầu | 1080×1920: ref 760×570 + nền mờ, con rối 1080×1350 cắt theo từng shot |
| B12 | File > 30 MB không gửi được qua Remote Control | Nén bản xem 24 MB |

## 4. Bài học áp cho dự án sau

1. Dự án mới khi Anthropic hết tiền: chạy bước Claude bằng claude_cli trong tiến trình riêng, CHỈ gửi, để Dashboard poll; rà từng shot ngay sau khi đặt pending.
2. Video theo ref nhảy: kiểm đầu đoạn ref có cảnh chuyển không — có thì thay trước khi gửi.
3. Mọi vật mốc cố định (tháp, xoáy, trời) đặt qua nền 3D, không qua chữ.
4. Báo giá video: nhân hệ số sổ chi thực tế (≈ 1,37 nháp có ref; bản cao +24 %) và đặt trần cứng dư.
