# Kế hoạch việc còn lại TRƯỚC tập 2 #27 (14/10/2026 01:46, phiên cloud `claude/wonderful-fermi-am712r`)

> Người dùng chốt trong chat 14/10. File này gom mọi việc còn lại trước khi chạy thật tập 2 #27, chia theo **nơi làm**
> (cloud = code/test thuần · máy chính = cần `data/`, Blender, Dashboard 8501, khóa API, tiền). Phiên nào nhận việc thì ghi
> `ĐANG LÀM` → `XONG <commit>` ở dòng tương ứng trong mục 📨 đầu `TODO.md` (dòng [14/10 01:46]), không sửa file này trừ khi đổi kế hoạch.
>
> **Thời điểm chạy:** người dùng 14/10: đợi **gói 5 giờ đặt lại** rồi làm **lần lượt** theo thứ tự dưới. Việc tốn tiền: hỏi trước.

## 0. Quyết định người dùng 14/10 (đã chốt)

| # | Câu hỏi | Chốt |
|---|---|---|
| Q1 | Ảnh mẫu tường keo | **DUYỆT ảnh phiên Remote control đã gen** `D:\AI-Video-Output\2026-09-30_tai_san_toi_uu\gloowall_ob55_trien_khai_1.png` (người dùng tự xem, 14/10) → vào Kho #367 nhãn "triển khai", sort=0, ảnh gốc làm phụ (việc M1) |
| Q2 | Bật `change_review_motion` + R14 (rà bản motion máy tự viết lại) | **Bật CẢ HAI**, nhưng phải sửa tối ưu vấn đề của R14 (mục 1, việc C1). Thêm lời gọi Claude: tạm chấp nhận |
| Q3 | Bom keo có hiệu ứng? | **KHÔNG.** Tập 2 dùng tường keo TĨNH như ảnh mẫu đã duyệt (Q1). Đã BỎ hẳn hướng bom keo có hiệu ứng và bảng thiết kế người dùng gửi (xóa khỏi repo để tránh nhầm) |
| Q4 | Kho #367 | Chỉ thêm ảnh mẫu đã duyệt (Q1); KHÔNG thêm bảng thiết kế, không viết lại mô tả theo hiệu ứng |
| Q5–7 | Sân khấu 3D · dọn "Chờ bạn" thừa · 3 việc nhỏ (ngưỡng khung cuối, nút gửi không khung cuối, lỗi 10) | **Giải quyết hết** |
| Q8 | Tạo dự án tập 2 | **Đã có** dự án tập 2 trên máy chính — không tạo lại; phiên máy chính kiểm lại Kho gắn theo TODO dòng "TẬP 2 = DỰ ÁN MỚI SẠCH" |

## 1. Việc CLOUD (code + test, 0 USD) — làm lần lượt, mỗi việc 1 nhánh `cloud/<mã>` tách từ main, push sau mỗi commit

Luật: `docs/CLOUD_TASKS.md` (hỏi credit trước mỗi việc, dừng cứng $90, không Agent con, test đỏ→xanh, không sửa TODO trong nhánh
việc — phiên điều phối cập nhật). Mỗi việc thêm cờ mới thì TẮT mặc định trừ khi ghi rõ dưới.

### C1 · R14 tối ưu + bật `change_review_motion` (≈ $8–15)
- **Hiện trạng:** `core/prompt_rewrite.py::save_rewrite` (≈ dòng 366–390) đánh `skipped` mọi sự kiện `change_events` kind `motion`
  vừa sinh khi Đạo diễn tự viết lại motion trước lần gen lại (R14 mặc định "không rà"). Nếu cho rà theo đường thường, sự kiện đi
  vào hàng chờ `core/change_review.py::process_pending` (vòng nền) → `blocking()` giữ CHÍNH lần gen lại tới vòng nền sau (chậm,
  có thể ĐỎ nhầm rồi đứng chờ người bấm).
- **Cách sửa tối ưu (người dùng duyệt hướng):** rà **ngay tại chỗ** khi máy viết lại — trong `save_rewrite` (hoặc `before_retry`),
  chỉ xử lý đúng sự kiện motion của shot đó bằng cùng hàm rà của Tổ rà soát (tách hàm rà-một-sự-kiện từ `process_pending`, không
  viết lối riêng), qua sổ chi + ước tính trước:
  - XANH → đóng sự kiện (`resolved`) + mục đỏ cũ của khâu motion shot đó tự đóng → gen lại gửi ngay, không chờ vòng nền;
  - ĐỎ → giữ lần gen lại kèm lý do trên thẻ + hộp thư; cho máy viết lại thêm **một** lần dùng lời ĐỎ làm ghi chú (vẫn trong luật
    gen lại ≤ 2 lần/ảnh-clip, đổi đầu vào) rồi mới chờ người;
  - Không gọi được Claude (thiếu khóa / hết trần / lỗi) → KHÔNG chặn im lặng: VÀNG "chưa rà bản viết lại — lý do", để sự kiện
    `pending` cho vòng nền, gen lại vẫn đi (bản viết lại đã qua `prompt_formula.on_prompt_saved` kiểm bằng code).
- Thêm hằng/cờ phụ để chọn "rà bản máy viết lại" (mặc định BẬT theo Q2 khi `change_review_motion` bật); `REQUIRES` giữ
  `change_review_motion → change_review`.
- Bật mặc định: `change_review_motion` vẫn để `verified: False` trong `core/features.py` (bật thật do người dùng ở 🧪 trên máy chính,
  ghi ở việc M0) — không đổi mặc định trong code để không làm vỡ test giả định cờ tắt (bài học 20 cờ → 362 test hỏng).
- Test đỏ→xanh: `tests/test_change_review.py::test_director_rewrite_event_handling` đổi theo hành vi mới (XANH gửi ngay / ĐỎ giữ +
  viết lại 1 lần / không có Claude → VÀNG không chặn); thêm ca lần gen lại không bị giữ qua vòng nền. Claude giả (mock).
- File: `core/prompt_rewrite.py`, `core/change_review.py`, `core/features.py`, `tests/test_change_review.py`, `tests/test_prompt_rewrite*.py`.

### C2 · Dọn "Chờ bạn" thừa ở dự án đã xong (≈ $8–15) — TODO mục "Dự án xong/gần xong vẫn hiện nhiều việc Chờ bạn"
- Số liệu (CSDL thật, chỉ đọc 13/10): #27 = 2 clip lỗi (shot 2, 20), 1 mục rà soát ĐỎ (shot 19) + 7 mục lệch sau thay đổi
  (shot 4,6,10,11,15,19), 9 clip chờ duyệt, chưa khóa ngân sách; #24 = 30 mục lệch, 8 ảnh + 7 clip chờ, chưa khóa ngân sách.
- Việc: phân loại từng loại đúng/sai (không ẩn bừa); không đếm mục lỗi thời khi shot đã có bản dùng (take đã chọn / clip đã duyệt)
  hoặc dự án đã giao (`delivered.mark`) / đã cất; mục `change_review` hết hạn khi shot có kết quả mới duyệt; lỗi gen cũ không đếm
  khi shot đã có clip dùng được; nút "🧹 Dọn việc thừa của dự án" có XEM TRƯỚC danh sách + xác nhận (không xóa dữ liệu — đóng/
  đánh dấu, ghi `job_events`).
- File: `core/inbox.py` (`items` dòng ≈ 70, `_video_waits` ≈ 35), `core/change_review.py`, `core/takes.py`, thẻ dự án
  `dashboard/design/screens/`. Test trên CSDL tạm dựng lại đúng các ca trên.

### C3 · Nút "▶ Gửi clip KHÔNG kèm khung cuối" khi autopilot dừng (≈ $5–8)
- Hiện: S3/S4 không vẽ khung cuối cho shot chắc chắn bỏ + giữ clip thiếu khung cuối kèm lý do; khi autopilot đã dừng thì người dùng
  không có cách gửi clip bỏ khung cuối. Thêm nút trên thẻ Bước 4 (có ước tính giá trên nút, ghi lý do vào `job_events`, chỉ người
  có quyền tiền), đi cùng đường gửi hiện có (`runner._end_frame` cho phép "người chọn bỏ khung cuối").
- File: `dashboard/steps/step4.py`, `core/runner.py` (`_end_frame`), test giao diện + runner.

### C4 · (BỎ 14/10) — tường keo giữ luật `skill_object_guard` hiện có (TĨNH); không làm chế độ hiệu ứng

### C5 · Lỗi 10 — đưa khâu dựng `tools/experiments/p27_final_mix.py` thành Bước 5 (việc lớn ≈ $15–25, làm SAU C1–C4)
- Theo `docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md` mục 10: đệm shot, mỗi lớp tiếng 1 WAV, … → khâu Bước 5 thật (nút, ước tính,
  test). Gộp ý người dùng 07/10 (TODO khối "việc để sau KLĐ" mục 12–13): Editor cắt đầu / cuối / đoạn lỗi bất kỳ + nhạc nền theo
  đoạn cảnh là MẶC ĐỊNH. Đọc lại hai chỗ đó trước khi chia nhỏ.

## 2. Việc MÁY CHÍNH (cần `data/`, Blender, Dashboard 8501, khóa API) — ghi hộp thư, phiên máy chính nhận

| Mã | Việc | Tiền | Ghi chú |
|---|---|---|---|
| **M0** | Sau mỗi việc cloud gộp main: `git pull` ở `D:\AI-Video-Pipeline` + khởi động lại 8501 (và 8502 nếu đổi `devsys/`) + cả bộ test Windows `py -m pytest -q -n 8 -p no:cacheprovider`. Sau C1: **bật** `change_review` + `change_review_motion` ở 🧪 (sao lưu `data/feature_settings.json` trước) | 0 | Q2 |
| **M1** | Đưa ảnh mẫu ĐÃ DUYỆT `D:\AI-Video-Output\2026-09-30_tai_san_toi_uu\gloowall_ob55_trien_khai_1.png` vào **Kho #367**: nhãn "triển khai", sort=0, ảnh gốc Kho làm phụ. Không gen thêm | 0 | Q1, Q4 |
| **M3** | **Sân khấu 3D thật + biên đạo hành động** (TODO mục "SÂN KHẤU 3D CHƯA DÙNG ĐÚNG CÁCH"): (1) đọc tài liệu chính thức GPT Image 2.5 / Seedance 2.5 / Kling qua API: sửa-từ-ảnh, ảnh độ sâu, video hình nộm; (2) render 3D đứng ĐẦU danh sách ref + câu vai trò; (3) đặt hình nộm mỗi nhân vật (màu = định danh, `core/whitebox.py`) + khối thô vật kịch bản (cổng, tường keo) vào cảnh 3D theo sơ đồ cảnh; (4) gửi `depth.png` nơi API nhận; (5) Kling gửi kèm render; shot 8/9 điền `plate_spot`. Thử thật 1–2 shot: báo giá + hỏi | thử ≈ 1–3 | Q5 — cần Blender |
| **M4** | **Đo ngưỡng** `framing_guard` / V2 / V12 / hộp thân trên clip THẬT #27 (job 912/903/915/907 + clip đã duyệt), ghi số đo, chỉnh ngưỡng nếu lệch (test kèm số đo thật) | 0 | Q7a |
| **M5** | Kiểm cả chuỗi Bước 2 → 4 bằng **bấm thật** trên Dashboard 8501 với nhà cung cấp GIẢ trên bản sao dự án (memory `reference_safe_copy_testing`); ghi nhật ký vướng + ảnh chụp ở `docs/handoff/` | 0 | TODO "kiểm CẢ CHUỖI" bước (2) |
| **M6** | Kiểm dự án tập 2 đã tạo: Kho gắn đúng danh sách (TODO "TẬP 2 = DỰ ÁN MỚI SẠCH"), không mang `director_intent_raw` / mốc nhạc / chủ thể Seedance cũ; thiết lập FF_INGAME + GPT Image 2.5 + Seedance 2.5 | 0 | Q8 |
| **M7** | **Chạy thật tập 2** — CHỈ khi người dùng gọi (người dùng: "đợi chạy tập 2 sau"), trần đề xuất 80 USD, hỏi trước mỗi bước tốn tiền | ≤ 80 | để sau |

Thứ tự gợi ý máy chính: M6 → M1 → M4 → M5 → M3 → M0 sau mỗi lần gộp → M7 khi người dùng gọi.

## 3. Bom keo
Đã chốt (Q1, Q3, Q4): tường keo TĨNH theo ảnh mẫu đã duyệt; KHÔNG dùng hiệu ứng, KHÔNG dùng bảng thiết kế (đã xóa khỏi repo 14/10).

## 4. Nguồn
- Chat người dùng 14/10 (phiên cloud `claude/wonderful-fermi-am712r`).
- `docs/handoff/RA_S3_S4_2026-10-13.md` (R14), `docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md` (lỗi 10), `docs/handoff/RA_GOC_VIDEO_P27_2026-10-13.md`,
  `TODO.md` các mục 13/10 "SÂN KHẤU 3D", "Chờ bạn", "kiểm CẢ CHUỖI", "TẬP 2 = DỰ ÁN MỚI SẠCH"; `docs/CLOUD_TASKS.md`.
