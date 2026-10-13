# Kế hoạch việc còn lại TRƯỚC tập 2 #27 (14/10/2026 01:46, phiên cloud `claude/wonderful-fermi-am712r`)

> Người dùng chốt trong chat 14/10. File này gom mọi việc còn lại trước khi chạy thật tập 2 #27, chia theo **nơi làm**
> (cloud = code/test thuần · máy chính = cần `data/`, Blender, Dashboard 8501, khóa API, tiền). Phiên nào nhận việc thì ghi
> `ĐANG LÀM` → `XONG <commit>` ở dòng tương ứng trong mục 📨 đầu `TODO.md` (dòng [14/10 01:46]), không sửa file này trừ khi đổi kế hoạch.
>
> **Thời điểm chạy:** người dùng 14/10: đợi **gói 5 giờ đặt lại** rồi làm **lần lượt** theo thứ tự dưới. Việc tốn tiền: hỏi trước.

## 0. Quyết định người dùng 14/10 (đã chốt)

| # | Câu hỏi | Chốt |
|---|---|---|
| Q1 | Ảnh mẫu tường keo (gen từ thông tin thiếu) | **Gen lại** theo bảng thiết kế đầy đủ (mục 3) — ảnh cũ `gloowall_ob55_trien_khai_1.png` KHÔNG đưa vào Kho |
| Q2 | Bật `change_review_motion` + R14 (rà bản motion máy tự viết lại) | **Bật CẢ HAI**, nhưng phải sửa tối ưu vấn đề của R14 (mục 1, việc C1). Thêm lời gọi Claude: tạm chấp nhận |
| Q3 | Tập 2 có hiện đủ hiệu ứng bom keo (cửa mở + nữ quỷ)? | **ĐỔI 14/10 (sau khi chốt thứ tự 3 bước): KHÔNG làm hiệu ứng động** — hiệu ứng chiếm quá nhiều thời gian trong clip. Tập 2 dùng tường keo **TĨNH ở trạng thái CỬA THANG MÁY MỞ** (ảnh tĩnh, không đóng/mở, không chớp đèn). Trạng thái cửa mở nào (bước 1 đèn xanh / bước 3 đèn đỏ có hoặc không nữ quỷ): **chờ người dùng chọn** sau khi so ảnh mẫu đã gen. Việc M2 (thử clip hiệu ứng) **BỎ**; mục 3.2 giữ làm tư liệu |
| Q4 | Đưa bảng thiết kế vào Kho #367 + viết lại mô tả + gen lại ảnh mẫu | **Đồng ý** (việc M1) |
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

### C4 · Tường keo TĨNH "cửa thang máy mở" cho `skill_object_guard` (≈ $8–12) — **sửa theo Q3 đổi 14/10:** không làm chế độ hiệu ứng động; chỉ cho phép tả trạng thái tĩnh cửa MỞ (cabin nông, đèn theo trạng thái người dùng chọn), giữ mọi câu khóa chống thang máy thật. Phần dưới về `effect` là thiết kế cũ, chỉ làm nếu người dùng mở lại
- Hiện `core/skill_objects.py` (cờ `skill_object_guard`) BỎ mọi từ elevator/door/thang máy/cửa và ép "already standing at full
  height" → đúng cho **TĨNH**, nhưng chặn luôn hiệu ứng cửa thang máy thật của skin (bảng thiết kế mục 3).
- Thêm lựa chọn theo vật kỹ năng (dữ liệu Kho `profile`, không cứng tên): `effect_mode: static | effect` (mặc định `static` = hành vi
  hiện tại). `effect`: cho phép từ "cửa thang máy" CHỈ trong khối mô tả hiệu ứng theo bước (mục 3.2), kèm câu khóa: tường đứng
  sẵn khi ném · cabin nông ~1 m sau cửa, không hành lang/tòa nhà · nữ quỷ đứng yên trong cabin, không bước ra · không người thật
  khác. Shot không nhắc hiệu ứng → vẫn TĨNH.
- Khung đầu/cuối theo bước: khung đầu = trạng thái bước 1 (cửa mở, đèn xanh); khung cuối = bước 3 cửa mở đèn đỏ (có / không nữ quỷ) khi clip dừng ở ≈ 9 s, hoặc lại bước 1 khi clip đủ vòng ≈ 12 s (khi đó bước 3 dùng ảnh tham chiếu, không làm khung cuối).
- Test: prompt ảnh + motion ở hai chế độ (so chữ trước–sau), luật cấm vẫn giữ ở chế độ TĨNH (không đổi hành vi hiện có).

### C5 · Lỗi 10 — đưa khâu dựng `tools/experiments/p27_final_mix.py` thành Bước 5 (việc lớn ≈ $15–25, làm SAU C1–C4)
- Theo `docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md` mục 10: đệm shot, mỗi lớp tiếng 1 WAV, … → khâu Bước 5 thật (nút, ước tính,
  test). Gộp ý người dùng 07/10 (TODO khối "việc để sau KLĐ" mục 12–13): Editor cắt đầu / cuối / đoạn lỗi bất kỳ + nhạc nền theo
  đoạn cảnh là MẶC ĐỊNH. Đọc lại hai chỗ đó trước khi chia nhỏ.

## 2. Việc MÁY CHÍNH (cần `data/`, Blender, Dashboard 8501, khóa API) — ghi hộp thư, phiên máy chính nhận

| Mã | Việc | Tiền | Ghi chú |
|---|---|---|---|
| **M0** | Sau mỗi việc cloud gộp main: `git pull` ở `D:\AI-Video-Pipeline` + khởi động lại 8501 (và 8502 nếu đổi `devsys/`) + cả bộ test Windows `py -m pytest -q -n 8 -p no:cacheprovider`. Sau C1: **bật** `change_review` + `change_review_motion` ở 🧪 (sao lưu `data/feature_settings.json` trước) | 0 | Q2 |
| **M1** | Đưa bảng thiết kế `docs/images/kho/kho367_bom_keo_obt55_halloween_thang_may_day_du.jpg` vào **Kho #367** làm ảnh thiết kế chính (`design_sheet`, sort đầu); viết lại mô tả Kho theo mục 3.1 (tiếng Việt + câu prompt tiếng Anh); ảnh cũ `gloowall_ob55_trien_khai_1.png` KHÔNG thêm. Gen lại ảnh mẫu "dạng triển khai" theo bảng: **báo giá + hỏi trước** (≈ 0,05 USD/ảnh; đề xuất 2 ảnh: bước 1 + bước 3 có nữ quỷ) | ≈ 0,1 | Q1, Q4 |
| **M2** | **Thử 1 clip hiệu ứng bom keo** (sau C4 + M1): dự án tập 2 hoặc dự án thử, shot cận tường keo đứng trong nền FF, Seedance 2.5 720p ≈ 9–12 s theo khung mục 3.2, khung đầu = bước 1, khung cuối = bước 3 có nữ quỷ (clip ≈ 9 s — đề xuất thử bản này trước). **Báo giá + hỏi** (≈ 2,1–2,8 USD; thêm biến thể không nữ quỷ ≈ +2,1–2,8). Gửi người dùng xem → quyết Q3: đạt → kịch bản tập 2 dùng hiệu ứng; không → TĨNH | ≈ 2,5–5 | Q3 — có video quay hiệu ứng trong game thì gửi kèm làm video tham chiếu (cách T1 tốt nhất) |
| **M3** | **Sân khấu 3D thật + biên đạo hành động** (TODO mục "SÂN KHẤU 3D CHƯA DÙNG ĐÚNG CÁCH"): (1) đọc tài liệu chính thức GPT Image 2.5 / Seedance 2.5 / Kling qua API: sửa-từ-ảnh, ảnh độ sâu, video hình nộm; (2) render 3D đứng ĐẦU danh sách ref + câu vai trò; (3) đặt hình nộm mỗi nhân vật (màu = định danh, `core/whitebox.py`) + khối thô vật kịch bản (cổng, tường keo) vào cảnh 3D theo sơ đồ cảnh; (4) gửi `depth.png` nơi API nhận; (5) Kling gửi kèm render; shot 8/9 điền `plate_spot`. Thử thật 1–2 shot: báo giá + hỏi | thử ≈ 1–3 | Q5 — cần Blender |
| **M4** | **Đo ngưỡng** `framing_guard` / V2 / V12 / hộp thân trên clip THẬT #27 (job 912/903/915/907 + clip đã duyệt), ghi số đo, chỉnh ngưỡng nếu lệch (test kèm số đo thật) | 0 | Q7a |
| **M5** | Kiểm cả chuỗi Bước 2 → 4 bằng **bấm thật** trên Dashboard 8501 với nhà cung cấp GIẢ trên bản sao dự án (memory `reference_safe_copy_testing`); ghi nhật ký vướng + ảnh chụp ở `docs/handoff/` | 0 | TODO "kiểm CẢ CHUỖI" bước (2) |
| **M6** | Kiểm dự án tập 2 đã tạo: Kho gắn đúng danh sách (TODO "TẬP 2 = DỰ ÁN MỚI SẠCH"), không mang `director_intent_raw` / mốc nhạc / chủ thể Seedance cũ; thiết lập FF_INGAME + GPT Image 2.5 + Seedance 2.5 | 0 | Q8 |
| **M7** | **Chạy thật tập 2** — CHỈ khi người dùng gọi (người dùng: "đợi chạy tập 2 sau"), trần đề xuất 80 USD, hỏi trước mỗi bước tốn tiền | ≤ 80 | để sau |

Thứ tự gợi ý máy chính: M6 → M1 → M4 → M5 → (sau C4) M2 → M3 → M0 sau mỗi lần gộp → M7 khi người dùng gọi.

## 3. Bom keo OBT55 Halloween "泡沫手雷" (skin thang máy) — từ bảng thiết kế đầy đủ

### 3.1 Bảng thiết kế nói gì (dịch)
- Tiêu đề: 【OBT55 泡沫手雷】【橙】万圣节 泡沫手雷（换模型+特效）= Bom keo OBT55, bậc Cam, Halloween (đổi mô hình + hiệu ứng).
- Tường keo = **khối cửa thang máy kim loại cũ** (khung thép gỉ, dải đèn vàng phía trên, tủ khóa hai bên, bảng điều khiển, biển
  hình người đỏ, biển cảnh báo vàng dưới chân). Mặt sau / mặt cửa đóng có **dấu tay máu**. Nhìn từ trên: tường **cong nhẹ**; nhìn
  ngang: khối mỏng đứng.
- **Mô tả thiết kế (nguyên văn, người dùng xác nhận cách hiểu 14/10):** 开始为正常电梯，然后电梯门开始关闭关到一半卡住打开，此时电梯内白灯狂闪，
  突然变为红灯，电梯门打开出现女鬼step3，接着电梯门关闭，再打开回到step1形成循环 = (1) thang máy bình thường, cửa mở, cabin đèn xanh lạnh →
  (2) cửa bắt đầu đóng, đóng **một nửa thì kẹt rồi BẬT MỞ RA LẠI** → (3) **ngay lúc đó** đèn trắng trong cabin **chớp loạn** → (4) **đột
  ngột chuyển đèn đỏ**, cửa mở, **nữ quỷ xuất hiện** (bước 3; ngẫu nhiên có / không) → (5) cửa **đóng**, rồi **MỞ RA LẠI về bước 1**, lặp vòng.
- **Trọng điểm:** hiệu ứng **ngẫu nhiên** — có tường mở cửa có nữ quỷ, có tường không (bước 3 có hai trạng thái).
- Nữ quỷ: tóc đen rất dài che mặt, váy đỏ rách, da xám tái, **dấu tam giác đỏ** ở eo, đứng thẳng.
- Lựu đạn: thân tròn đỏ, nắp đen có tam giác đỏ.

### 3.2 Mô tả theo 3 bước (người dùng hỏi 14/10: "mô tả lần lượt theo 3 step thì sao?")
**Được — và đây là cách nên dùng.** Seedance 2.5 bám **mốc giây** (khác 2.0/Fast chỉ bám "Shot n" — S4.8), nên viết hiệu ứng thành
các đoạn có mốc giây theo đúng 3 bước của bảng, kèm ảnh khung đầu (bước 1) + khung cuối (bước 3). Khung gợi ý cho clip ≈ 12 s (đủ một vòng; muốn ngắn hơn thì bỏ đoạn lặp cuối, còn ≈ 9 s):

| Giây | Bước | Mô tả (ý cho prompt) |
|---|---|---|
| 0–2 | Bước 1 | Tường keo đứng sẵn (đã ném xong), cửa thang máy **mở**, cabin nông đèn **xanh lạnh** bình thường, trống |
| 2–3,5 | Bước 2 | Hai cánh cửa trượt vào, đóng được **một nửa thì kẹt** (khựng lại, khe giữa còn hở) |
| 3,5–4,5 | Bước 2 | Cửa **bật mở ra lại** |
| 4,5–6 | Bước 2 | **Ngay lúc đó** đèn trắng trong cabin **chớp loạn** (cửa vẫn mở) |
| 6–6,5 | chuyển | Đèn **đột ngột chuyển đỏ** toàn cabin |
| 6,5–9 | Bước 3 | Cửa mở, cabin đỏ — biến thể A: **nữ quỷ xuất hiện, đứng yên** giữa cabin (tóc che mặt, váy đỏ); biến thể B: cabin đỏ trống |
| 9–10,5 | lặp | Cửa **đóng** lại |
| 10,5–12 | lặp | Cửa **mở ra lại**, cabin về **đèn xanh** bình thường như bước 1 (có thể cắt trước đoạn này khi dựng) |

Câu khóa bắt buộc (chống lỗi 3 tập 1): tường đứng sẵn từ giây 0, không mọc lên · sau cửa chỉ là **cabin nông ~1 m**, không hành lang,
không tòa nhà, không nhìn xuyên · nữ quỷ **không bước ra**, không đổi tư thế lớn · không người thật nào khác · khung thép, tủ khóa,
biển báo giữ nguyên suốt clip. Ảnh tham chiếu: bảng thiết kế (chỉ lấy hình dạng/chất liệu/màu), không lấy chữ trên bảng.

Rủi ro còn lại (vì sao phải thử 1 clip trước): 7 nhịp trong 9–12 s có thể bị trộn/bỏ bước; model có thể mở rộng cabin thành
thang máy thật; nữ quỷ có thể vướng bộ lọc nội dung hoặc đổi hình. Không đạt → cách dự phòng: chia 2 clip (bước 1–2 / bước 3) rồi
dựng nối; vẫn không đạt → TĨNH (Q3).

## 4. Nguồn
- Chat người dùng 14/10 (phiên cloud `claude/wonderful-fermi-am712r`); bảng thiết kế `docs/images/kho/kho367_bom_keo_obt55_halloween_thang_may_day_du.jpg`.
- `docs/handoff/RA_S3_S4_2026-10-13.md` (R14), `docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md` (lỗi 10), `docs/handoff/RA_GOC_VIDEO_P27_2026-10-13.md`,
  `TODO.md` các mục 13/10 "SÂN KHẤU 3D", "Chờ bạn", "kiểm CẢ CHUỖI", "TẬP 2 = DỰ ÁN MỚI SẠCH"; `docs/CLOUD_TASKS.md`.
