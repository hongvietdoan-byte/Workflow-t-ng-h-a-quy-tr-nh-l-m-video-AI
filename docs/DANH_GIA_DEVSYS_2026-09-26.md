# Chấm điểm lần đầu — AI Development System (2026-09-26)

> **Người chấm:** 2 agent độc lập (phiên Claude Code, miễn phí; không agent nào viết code được chấm), mỗi agent 8 khu vực, theo thang cố định
> `devsys/rubric.md`. Người chấm chỉ ghi khoản trừ, mỗi khoản có bằng chứng; điểm do code cộng và code kiểm bằng chứng — không bằng chứng nào
> bị ⚠, không khu vực nào bị code hạ điểm. Dữ liệu đầu vào: `py tools/devsys_score.py --export <khu_vực>` tại commit `b2659b4`, lần chạy
> test lưu ngày 2026-09-26 19:13 (1144 test, 0 lỗi, 1 bỏ qua). File điểm đầy đủ (từng khoản trừ + bằng chứng) nằm ở
> `devsys/data/scores/` trên máy chạy dashboard (không đưa vào git) — xem trang **Chấm điểm AI** của web (`Start-DevSystem.bat`, cổng 8502).

## Điểm (/100) — hoàn thiện tổng có trọng số: **79,8**

| Khu vực | Điểm | Việc quan trọng nhất cần kiểm (theo người chấm) |
|---|---|---|
| Chẩn đoán & theo dõi lỗi (`diag`) | 91 | So ước tính "video X s ≈ Y phút" với thời gian thật sau đợt thử; `diag.record` nuốt lỗi SQLite không báo (`core/diag.py:63-64`) |
| Bước 3 · Motion & giọng | 86 | Nghe thử câu có `delivery` với giọng Việt trước khi giữ bật `voice_direction`; nên cài faster-whisper để kiểm giọng so chữ |
| Lõi pipeline & nhà cung cấp | 86 | Theo dõi khóa trần + giới hạn 2 video ClipAI trong đợt thử (mới chứng minh bằng test); 6 ảnh Kho mất file (diag); `V0_SETUP`, `WORKFLOW_REVIEW` sai trạng thái |
| Dashboard chung / giao diện | 84 | Chạy trọn một dự án qua giao diện (đợt 2A chạy bằng script `pilot_run`); thông báo lỗi còn lộ tên lỗi tiếng Anh (`dashboard/common.py:185`) |
| Bước 5 · Âm thanh & xuất bản | 83 | Chưa ai nghe/xem bản dựng bật 9 cờ dựng; nhiều nút nhạc/SFX/giọng/Claude ở `dashboard/steps/step5.py` chưa hiện ước tính |
| Bước 1 · Kịch bản & Đạo diễn | 81 | Chạy Director hai lượt với Claude thật một lần (mới thử bằng Claude giả lập) |
| Bước 4 · Video + QC | 81 | **Thử nghiệm Kling multi-shot gửi job trả tiền không qua `budget.check_video`** (`core/experiments.py:62`), hộp xác nhận không có giá, module không có test |
| Autopilot | 79 | Xác nhận autopilot dừng kèm lý do khi trần chặn (chưa thử thật); `docs/RUNBOOK.md` mục chạy tự động còn tả luồng cũ |
| Ngân sách & sổ chi | 79 | Đường gửi video ngoài trần (`experiments.py`); âm thanh chưa có giá; giá ảnh Deepix $0,052 là tạm; trần Claude chỉ chặn sau khi đã vượt |
| Kho tài nguyên | 79 | "🤖 Đọc mô tả ngoại hình" (`dashboard/admin.py:425`) gọi Claude hàng loạt không báo giá; TODO ghi "tối đa 4 ảnh/cảnh" còn code 8 (`core/assets.py:418`) |
| Bước 2 · Ảnh + QC | 77 | Đo đồng thuận QC–người trên ≥ 20 ảnh cùng look; theo dõi `layout_to_model`, `chain_previous_auto` (từng lỗi GĐ6, nay bật để thử) |
| Web AI Development System | 77 | Bộ đo làm sai dữ liệu gửi người chấm (xem dưới) |
| Kiến thức & bộ kỹ năng 3 vai | 75 | Chạy Director thật với `film_crew`; nút "Nghiên cứu tài liệu mới ngay" không hiện giá, phí tìm kiếm web không vào sổ chi (`core/llm_runner.py:278-282`) |
| Gói bối cảnh 3D | 71 | Thử 1 shot phông xanh Deepix thật + ghép nền tháp; `ensure_plates` bỏ qua im lặng góc máy Blender không trả về (`core/location_pack.py:220`, `:241`) → có thể render lại mỗi lượt |
| Khớp môi | 69 | Thử 1 shot cận Seedance kèm giọng Việt (~$0,60); không sync.so thì shot trung/toàn không khớp môi; nhãn cờ `lip_sync` còn nhắc sync.so (`core/features.py:103`) |
| Tài liệu | 69 | `TODO.md` còn ô cũ (W1–W16, "tự động v2") mở dù đã xong/đã thay; số test đầu TODO (1142) lệch lần chạy lưu (1144); nhiều mục cùng "PHIÊN MỚI ĐỌC TRƯỚC TIÊN" |

**Vì sao chưa cao hơn:** tiêu chí **"Bằng chứng chạy thật"** bị trừ nhiều nhất ở mọi khu vực — cả 23 cờ `verified: False`, chưa có lần chạy
trả tiền nào với code mới. Chỉ tăng khi chạy dự án thử. Tiêu chí **Test** gần trọn điểm nhờ lần chạy 1144 test, 0 lỗi.

## Lỗi người chấm tìm ra — ✅ đã sửa cả 6 (2026-09-26 tối, test hồi quy `tests/test_grader_fixes_0926.py`, 1159 test qua)
> 1 → `experiments.kling_multishot` kiểm `budget.check_video` trong `SPEND_LOCK`, nút hiện giây + giá. 2 → nút "Đọc mô tả ngoại hình",
> "Rút bài học", "Nghiên cứu", brief nhạc, phụ đề dịch, AI đề xuất SFX hiện giá Claude; nút nhạc/SFX/giọng hiện số lượt âm thanh + trần
> đợt thử; lượt tìm web ghi sổ (`tier web_search`, 0,01 USD/lượt, `pricing.json per_web_search`). 3 → góc máy Blender không trả về: ghi
> `failed.json` + diag `plate_missing`, không render lại mỗi lượt, shot vẽ ảnh thường thay vì chờ mãi, `forget_failures` để thử lại.
> 4 → `diag.record` thử lại khi CSDL bận, không ghi được thì in stderr + `<db>.diag_lost.log` + đếm (hiện ở 🩺). 5 → bộ đo devsys đọc cờ
> trong `dashboard.env`, nhận test của `devsys/`, `tools/` và các màn dashboard chạy qua AppTest, đọc TODO theo mục (dòng ngắt + ô con dưới
> mục "đã thay"), cảnh báo khi kết quả test cũ hơn code. 6 → ô cũ trong TODO đóng, nhãn cờ `lip_sync`, RUNBOOK mục chạy tự động viết lại
> theo V4, V0_SETUP/WORKFLOW_REVIEW ghi "tài liệu lịch sử".
1. **`core/experiments.py:62` gửi job video trả tiền không qua trần ngân sách**, hộp xác nhận không có giá, không có test — nặng nhất.
2. Nút gọi Claude chưa báo giá: "🤖 Đọc mô tả ngoại hình" (Kho), một số nút Bước 5, "Nghiên cứu tài liệu mới ngay" (phí tìm kiếm web ngoài sổ chi).
3. `core/location_pack.py:220/241` bỏ qua im lặng góc máy Blender không trả về → render lại mỗi lượt autopilot.
4. `core/diag.py:63-64` nuốt lỗi SQLite khi ghi chẩn đoán.
5. Bộ đo của web devsys: ghi 23 cờ "đang tắt" (không đọc `dashboard.env`); chỉ nhận test của module `core`/`dashboard` nên báo nhầm
   `devsys/`, `tools/` và các màn dashboard (có AppTest trong `tests/test_dashboard.py`) là "không có test"; TODO đọc theo từng dòng nên dòng
   ngắt xuống mất khu vực, ô con dưới mục "đã thay" vẫn tính là mở; không cảnh báo khi kết quả test cũ hơn code.
6. Tài liệu: ô cũ trong `TODO.md`, số test đầu file, nhãn cờ `lip_sync`, `docs/RUNBOOK.md` / `V0_SETUP.md` / `WORKFLOW_REVIEW.md` tả luồng cũ.
