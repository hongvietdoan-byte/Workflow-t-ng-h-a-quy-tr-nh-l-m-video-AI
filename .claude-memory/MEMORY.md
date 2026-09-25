# Memory Index

Memory repo dùng chung cho các phiên Claude Code trên mọi máy của hongviet.doan (đồng bộ qua git — nằm trong repo `Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI`, thư mục `.claude-memory/`).

## Files
- [user/profile.md](user/profile.md) — thông tin về user, cách làm việc ưa thích
- [projects/ai-video-pipeline.md](projects/ai-video-pipeline.md) — dự án Auto Pipeline video AI (repo hiện tại)

## Recent Learnings

| Ngày | Tiêu đề | File |
|---|---|---|
| 2026-09-25 | Sau GĐ4: D/V việc code + GĐ6 (giới hạn hệ thống, chế độ chuyên gia, 4 thẻ) + GĐ7 (12 lỗi rà độc lập); bài học decorator | projects/ai-video-pipeline.md |
| 2026-09-25 | GĐ4 xong: bộ kỹ năng 3 vai chấm độc lập 37/39/36; performance/voice_direction/profile_digest; bỏ tuổi <18 KELLY/MAXIM | projects/ai-video-pipeline.md |
| 2026-09-25 | V4 xong GĐ0–3 (gói bối cảnh, storyboard Deepix qua API, khớp môi); bàn giao GĐ4 ở docs/BAN_GIAO_2026-09-25_V4_GD4.md | projects/ai-video-pipeline.md |
| 2026-09-25 | Kế hoạch V4: rà soát trước, gói bối cảnh (nền pixel thật + thời tiết), khớp môi toàn video, kỹ năng 3 vai + agent chấm, hồ sơ 3 nhân vật đã duyệt; người dùng tự chạy trọn #6 | projects/ai-video-pipeline.md |
| 2026-09-25 | Tháp 90–100%: ảnh render làm tham chiếu chỉ ~70% (model vẽ lại nền) → ghép phông xanh lên render 3D; khớp môi = né + Seedance `reference_audio` | projects/ai-video-pipeline.md |
| 2026-09-25 | Sửa theo phản hồi video 2A: eleven_v3 cắt cụt câu ngắn (đo đuôi, tạo lại kèm "…"), nền void, tháp FF bằng Blender Store + ảnh mốc, nhạc theo nhịp | projects/ai-video-pipeline.md |
| 2026-09-25 | Chạy thử 2A: ClipAI trả mã chờ tạm rồi tạo task mã mới (W12b); 1 đơn vị cost ≈ $0,01; GPT Image từ chối tuổi < 18; video 22 s $3,00 | projects/ai-video-pipeline.md |
| 2026-09-25 | Chốt: tổ làm phim (Đạo diễn + Quay phim + Editor), thứ tự ưu tiên, #6 chạy thử 0–20 s tự chạy trong trần (gen lại ≤ 2) | projects/ai-video-pipeline.md |
| 2026-09-25 | Kế hoạch làm tiếp `docs/KE_HOACH_2026-09-25.md`: Director v2 (H1–H4) → dự án #6 tới video hoàn chỉnh; hướng mới H5 quay theo vị trí máy | projects/ai-video-pipeline.md |
| 2026-09-25 | Bài học Director chia shot từ 4 lần chạy thật "ANH CHỌN AI?": đưa con số thời lượng/thoại, thứ tự cắt thoại, luật mềm phải có code kiểm | projects/ai-video-pipeline.md |
| 2026-09-23 | Sửa xong 2 nguyên nhân gốc (Director nhìn ảnh tham chiếu thật; TTS tự xếp lại hết chồng tiếng); 600 test pass | projects/ai-video-pipeline.md |
| 2026-09-23 | Hậu kiểm video thật: 2 nguyên nhân gốc mới (Character Bible chưa đối chiếu ảnh, TTS chồng tiếng); đã pull 10 commit phiên khác trước khi lưu, chỉ lưu chưa sửa | projects/ai-video-pipeline.md |
| 2026-09-23 | Rà soát Dashboard đầu-cuối (Playwright + mock) + sửa 5 điểm; 594 test | projects/ai-video-pipeline.md |
| 2026-09-23 | Xong code P0 hướng 1: báo cáo 5 chỉ số hiệu quả (core/effectiveness.py, tab 📊); 588 test; chờ user thử thật | projects/ai-video-pipeline.md |
| 2026-09-23 | QC 3 tiêu chí (scale/grounding/set_match) + thay trang phục bằng ảnh + bộ ảnh nhân vật; 586 test | projects/ai-video-pipeline.md |
| 2026-09-23 | Previz 2D xong phần Claude (core/previz.py) + khối Storyboard Bước 1 + Bước 2 gen theo layout; 579 test | projects/ai-video-pipeline.md |
| 2026-09-23 | Chốt Previz 2D (không thêm bước duyệt, claude_cli trước); xong core/layout.py; 573 test | projects/ai-video-pipeline.md |
| 2026-09-23 | Xong P0 (C) blocking + sequence, Storyboard nối theo nhóm; 563 test; commit message dùng -F | projects/ai-video-pipeline.md |
| 2026-09-23 | Xong P0 (A) giữ chỗ ảnh bối cảnh + (B) bối cảnh theo ID/ô Background Bước 1; 556 test | projects/ai-video-pipeline.md |
| 2026-09-23 | CHỐT 3 hướng: ảnh+text là chính (làm ngay); Bàn đạo diễn dò lại ở lần dùng API tới; previz 3D nghiên cứu dần | projects/ai-video-pipeline.md |
| 2026-09-23 | Rà soát nhất quán nhân vật/bối cảnh (mất ảnh bối cảnh khi ≥4 nhân vật); hướng previz 3D từ map FF; kế hoạch P0–P5 | projects/ai-video-pipeline.md |
| 2026-09-23 | Chạy thật 1 video hoàn chỉnh qua Dashboard browser; sửa 2 bug thật (rate-limit vĩnh viễn hóa, external_id lệch); quy tắc "kênh thực hiện" khi user chỉ định dùng browser | projects/ai-video-pipeline.md |
| 2026-09-22 | Phân tích video kỹ năng KENTA không cần API key (Claude tự xem khung hình); phát hiện skill OB55 mới; dọn ảnh trùng | projects/ai-video-pipeline.md |
| 2026-09-22 | Dọn tiếp thanh điều khiển dự án: mode/threshold/xóa dự án vào popover "⚙" riêng | projects/ai-video-pipeline.md |
| 2026-09-22 | Setup memory repo trong chính repo dự án (`.claude-memory/`) | projects/ai-video-pipeline.md |
| 2026-09-22 | 530 unit test pass sau khi sửa 1 test lỗi thời (test_distill.py) | projects/ai-video-pipeline.md |
| 2026-09-22 | Quyết định ClipAI/Deepix: gác Bàn đạo diễn, bỏ Kho chủ thể Seedance, hạ ưu tiên video tham chiếu, không ưu tiên lip-sync, thu hẹp blocklist IP | projects/ai-video-pipeline.md |
| 2026-09-22 | Đối chiếu + bổ sung độ khó/vai trò 65 nhân vật FF từ Google Sheet; bài học: Claude xem video qua browser không hiệu quả | projects/ai-video-pipeline.md |
| 2026-09-22 | Chạy thật 1 cảnh qua Dashboard; tìm bug key trùng Bước 5; claude_cli hoạt động rồi hết hạn mức tháng | projects/ai-video-pipeline.md |
| 2026-09-22 | Thiết kế lại đầu trang Dashboard (gear+dialog); bài học st.dialog cần cờ session_state; cảnh báo sed thay thế không giới hạn dòng | projects/ai-video-pipeline.md |
| 2026-09-22 | Bảng giá ước tính + bảng tổng quan tất cả dự án + phân tích video kỹ năng (MVP); bài học Streamlit hot-reload + PowerShell tool | projects/ai-video-pipeline.md |
