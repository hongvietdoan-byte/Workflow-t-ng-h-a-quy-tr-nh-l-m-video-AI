# Đánh giá cách chấm của AI Development System và thang bản 2 — 2026-10-03

Phạm vi: `devsys/` (thang `rubric.md`, `scorer.py`, `scores.py`, `collect.py`, `feedback_format.md`, `areas.json`), `tools/devsys_score.py`.
Cách làm: Bước 1 chỉ đọc (0 USD) — 32 file điểm ở `devsys/data/scores/` (16 khu vực × 2 lần: 26/09 `b2659b4` và 01/10 `35739fc`),
`docs/DANH_GIA_DEVSYS_2026-09-26.md`, `docs/RA_SOAT_DASHBOARD_2026-10-01.md`, `docs/RA_SOAT_UI_V2_SANG_TOI_2026-10-02.md`, git. Bước 2 viết thang bản 2 + code
+ test (không gọi Claude API, không chấm thật). Các con số dưới đây đều tính bằng script từ dữ liệu thật; chỗ nào là ước lượng / mô phỏng thì ghi rõ.

## 0. Tóm tắt

| Câu hỏi | Kết luận (số) |
|---|---|
| (a) Có chạm trần? | **Có.** 01/10: 16 khu vực nằm trong 79–96, trung bình 88,2 (có trọng số 87,2), 7/16 ≥ 90, 13/16 ≥ 85. Khoản trừ lớn nhất **6 điểm/100**; 92 % số điểm bị trừ đến từ khoản ≤ 3 điểm. Tiêu chí `test` 93 %, `tuan_thu` 94 % (30 điểm gần như luôn đầy). |
| (b) Ổn định? | **Không đo được sạch và có dấu hiệu không ổn định.** Cùng thang (`rubric_hash` giống nhau) nhưng 5 khu vực chỉ đổi 91–290 dòng giữa hai lần vẫn lệch trung bình **+10,8** (lipsync +25 trên 160 dòng). Hai lần do **hai loại người chấm khác nhau** (26/09: 2 subagent, 8–8,8 khoản trừ/khu vực; 01/10: 1 phiên, 5,6 khoản trừ/khu vực) nên không tách được nhiễu khỏi tiến bộ. Tương quan (dòng đổi, điểm đổi) = **0,10**. |
| (c) Bằng chứng kiểm được? | **100 %** bằng chứng có thật (0 ⚠ trên 291 + 153 trích dẫn) — nhưng code chỉ kiểm file có tồn tại và dòng không vượt độ dài. Với trích dẫn `file:dòng` (không phải TODO): chỉ **69 % (26/09) và 56 % (01/10)** có từ trùng với lý do trong ±3 dòng. Trích dẫn `TODO.md:n`: 80 % → 100 % trỏ tới dòng có dấu "còn mở". |
| (d) Lặp / không hành động được | 12 dòng TODO và 6 cờ bị trừ ở ≥ 2 khu vực; **19 %** bằng chứng 01/10 y hệt 26/09. Điểm trừ theo người làm: 💻 119/177 (67 %), 💵 40 (23 %), 👤 18 (10 %) → **33 % điểm trừ không thể gỡ bằng code miễn phí**. 90/90 khoản trừ 01/10 có `feedback`, nhưng **không có cơ chế biến khoản trừ thành việc sửa** (B1–B6 được sửa vì có tài liệu rà soát riêng). |
| (e) Bỏ sót B1–B6? | 26/09: **0/6** (B1–B3 đã có trong code, không ai trừ). 01/10: 6/6 xuất hiện nhưng chỉ vì phiên chấm là phiên rà soát; tổng **19 điểm / 1.600 (1,2 %)**; B1 và B2 (🔴) mỗi chỗ chỉ −3/30 = ngang một nhãn thiếu. Thang không có mức nghiêm trọng, không có "lỗi đã chứng minh", không có checklist. |
| (f) Giao diện | Khu vực `dashboard_ui` 92/100 mà **0/19** khoản trừ `trai_nghiem` (cả 16 khu vực) dẫn một số đo; `tools/ui_v2_acceptance.py`, `ui_contrast_audit.js`, `ui_snapshot.py` **không được devsys đọc ở đâu** (git grep rỗng) — chỉ liệt kê là "assets". Rà soát 02/10 sau đó tìm ra chữ tàng hình 1,03–1,43:1 bằng đúng công cụ đó. |
| (g) Trọng số | 30/20/15/15/10/10 không phản ánh khả năng phân biệt: `chuc_nang` (30 điểm) chỉ giải thích **10 %** phương sai điểm tổng; `trai_nghiem` (10 điểm) giải thích **18 %**, `bang_chung` 29 %. Thiếu: độ tin cậy/an toàn, bảo trì, đo chất lượng đầu ra, bảo mật & quyền. |

Thang bản 2 (mục 2) xử lý từng điểm trên. **Mô phỏng** trên dữ liệu 01/10 (mục 2.6): riêng việc đổi trọng số + thêm khoản trừ tự động *không* làm
điểm trung bình thấp đi (88,2 → ~88,5) mà **dàn lại** (78–97, ví dụ Ngân sách 88 → 82, Tài liệu 81 → 90); phần kéo trần xuống đến từ mức "chặn" + checklist + giới
hạn 89/79, chỉ lộ ra khi chấm thật. Đừng đọc lần chấm bản 2 đầu tiên là "thụt lùi" hay "tiến bộ": nó là mốc mới.

## 1. Phân tích cách chấm hiện tại (bản 1)

### 1.1 (a) Trần điểm
- 26/09: trung bình 79,2 (69–91, độ lệch chuẩn 6,0). 01/10: **88,2** (79–96, độ lệch chuẩn 5,3). Phân tứ vị 01/10: 85 / 88 / 92,75.
- % điểm tối đa trung bình theo tiêu chí (01/10): `test` 93, `tuan_thu` 94, `tai_lieu` 90, `chuc_nang` 87, `bang_chung` 86, `trai_nghiem` 79.
  Số khu vực **đầy điểm** tiêu chí: `test` 12/16, `tuan_thu` 10/16, `tai_lieu` 5/16, `bang_chung` 4/16, `trai_nghiem` 4/16, `chuc_nang` **0/16**.
- Khu vực gần tuyệt đối (≥ 94): Chẩn đoán 96, AI Dev System 95, Khớp môi 94. Chẩn đoán (96) là khu vực chứa
  `effectiveness.look_trust` (B2, 🔴) và `access.py` mới.
- Nguyên nhân cấu trúc: (1) **mọi khoản trừ là 1–3 điểm** (01/10: 1 điểm ×25, 2 ×48, 3 ×14, 4 ×2, 6 ×1) dù là nhãn thiếu hay bug chặn đường chính;
  (2) hai tiêu chí tính cho 30 điểm đã bão hòa nhờ test và luật code; (3) không có cơ chế giới hạn "còn lỗi chặn thì không thể ≥ 90"; (4) người chấm tự ghi số điểm:
  phiên 01/10 trừ trung bình **1,97** điểm/khoản so với 2,42–2,54 của hai subagent 26/09.

### 1.2 (b) Độ ổn định (chấm hai lần)
| Khu vực (đổi ít; Tài liệu 0 dòng code, 81 vs 69 = +12) | Dòng đổi (code+assets) | Điểm 26/09 → 01/10 |
|---|---|---|
| Chẩn đoán | 91 | 91 → 96 (+5) |
| Khớp môi | 160 | 69 → 94 (**+25**) |
| Dashboard chung | 200 | 84 → 92 (+8) |
| Chạy tự động | 250 | 79 → 86 (+7) |
| Kho tài nguyên | 290 | 79 → 88 (+9) |
Trung bình |chênh| cả 16 khu vực = **9,4** (trung vị 7,5); 14/16 khu vực tăng; tương quan(dòng đổi, chênh điểm) = 0,10 (giữa hai commit có 273 commit, 426 file, 51.545 dòng đổi).
**Nhiễu lẫn lộn:** đổi người chấm cùng lúc (subagent A 80,6 / B 77,8 / phiên 88,2) và đổi dữ liệu (01/10 có feedback, bảng test/diff mới). Kết luận: **chưa thể nói chấm hai lần là
ổn định**; thang hiện không ép người chấm giải thích khi lệch, và không lưu khoản trừ cũ để đối chiếu → thang bản 2 thêm quy tắc ổn định (mục 2.5).

### 1.3 (c) Chất lượng bằng chứng
| | 26/09 | 01/10 |
|---|---|---|
| Khoản trừ | 134 | 90 |
| Trích dẫn bằng chứng | 291 | 153 |
| Trích dẫn bị ⚠ (không kiểm được) | 0 (0 %) | 0 (0 %) |
| Trích dẫn code/doc `file:dòng` ngoài TODO | 157 | 52 |
| — có từ khóa của lý do trong ±3 dòng | 109 (69 %) | 29 (56 %) |
| Trích dẫn `TODO.md:n` | 75 | 57 |
| — trỏ tới dòng có dấu "còn mở" | 60 (80 %) | 57 (100 %) |
| Khoản trừ chỉ có `absent:` | — | 3 (3 %) |
Hạn chế của kiểm tự động: code chỉ biết **tồn tại + trong độ dài file**; một số `file:dòng` hợp lệ về hình thức mà không chứng minh điều được nói (44 % ở 01/10 không có từ chung —
chỉ số thô, có thể thấp hơn thực tế vì lý do viết bằng ngôn ngữ khác code). Cấu trúc bằng chứng 01/10 theo khoản trừ: TODO 39 (43 %), cờ 25 (28 %), code/tài liệu 45 (50 %).
Điểm đáng chú ý: **59/177 điểm trừ (33 %) dựa vào `flag:`** — đó là dữ kiện máy có sẵn (cờ BẬT mà `verified=False`) mà code không trừ, người chấm phải tự đếm.

### 1.4 (d) Lặp, không hành động được, không thành việc sửa
- Cùng một dòng TODO bị trừ ở nhiều khu vực: 12 dòng (`TODO.md:805`, `:315` ở 3 khu vực). Cùng một cờ ở 2 khu vực: `film_crew`, `camera_setups`, `setcheck_autofix`, `voice_check_redo`, `audio_first`, `lip_sync`.
- "Cờ BẬT chưa thử thật" = nhóm trừ lớn nhất: `bang_chung` mất **46/177** điểm; cụm "verified" 8 khoản/19 điểm/7 khu vực; "chưa thử thật" 8/13/8; "chưa chạy thật" 5/7/5.
  Đây là việc **máy đếm được** → bản 2 chuyển thành khoản trừ tự động (`co_bat_chua_thu`).
- 19 % (28/146) chuỗi bằng chứng 01/10 trùng hệt 26/09: khoản trừ tồn tại 5 ngày không đổi — vì chúng cần chạy thật tốn tiền (💵 23 %) hoặc người dùng quyết (👤 10 %).
  Điều đó làm điểm **không thể tăng nếu không chi tiền** → bản 2 vẫn giữ nhưng tách "ai làm" rõ trong báo cáo hành động.
- Chuyển thành việc sửa: 01/10 có `feedback` ở 90/90 khoản (21 khoản ưu tiên 1), nhưng không có bước nào đẩy vào TODO/ticket; 6 bug B1–B6 được sửa trong ngày nhờ tài liệu rà soát
  `RA_SOAT_DASHBOARD_2026-10-01.md`, không nhờ điểm. Bản 2: khoản `chan`/`lon` **bắt buộc** `fix` + `effort`, thêm `--report` (vì sao / sửa gì / ai làm / ưu tiên) và gom "một việc – nhiều khu vực".

### 1.5 (e) Thang có bắt được B1–B6?
| # | Bug (01/10) | 26/09 (code đã có?) | 01/10 | Điểm trừ 01/10 |
|---|---|---|---|---|
| B1 🔴 | Khâu Claude "khác" không có `max_tokens` riêng → luôn bị chặn | đã có (mặc định 32k), **không ai trừ** | có (Ngân sách, Bước 1, Bước 3) | −3 −3 −1 (7) |
| B2 🔴 | `look_trust` chia sai mẫu số → có thể tự bỏ cổng storyboard | đã có (W8, 25/09), **không ai trừ** | có (Chạy tự động, Chẩn đoán) | −3 −3 (6) |
| B3 🟠 | Không kiểm tỉ lệ ảnh tham chiếu video | đã có (W10), **không ai trừ** | có (Bước 4) | −2 |
| B4 🟡 | `CTA_TEXT` coi là nhân vật | chưa có (S11.2 ra 01/10) | có (Bước 1, chung khoản trừ với B1) | −3 |
| B5 🟡 | 6 ảnh Kho mất file | diag từ 28/09 | có (Lõi) | −2 |
| B6 🟡 | Dò cờ bỏ sót `FEATURE = "…"` | chưa có (thêm sau) | có (AI Dev System) | −2 |
Tổng 19 điểm (đã bỏ trùng: một khoản ở Bước 1 nhắc cả B1 và B4) trên 16 × 100 = **1,2 %**; mỗi bug 🔴 chỉ −3/30 trong một khu vực, ngang một nhãn thiếu (−2). 01/10 "bắt được" vì **phiên chấm chính là phiên rà soát** (cùng ngày, điểm là đầu vào của rà soát, tài liệu
nhắc lại cả hai); không phải do thang. Thang/dữ liệu thiếu: (1) **mức nghiêm trọng**; (2) khái niệm "lỗi đã chứng minh" (bằng chứng chạy được) tách khỏi "việc còn mở";
(3) **checklist loại lỗi** (khai báo chung lệch nơi dùng, công thức đo sai, ràng buộc bên ngoài, diễn giải đầu ra model, dữ liệu mất, bộ đo bỏ sót);
(4) tiêu chí độ tin cậy; (5) trích code gửi người chấm chỉ gồm chữ ký hàm + dòng khớp từ khóa (`_MARK`) nên không có thân công thức — B2 chỉ thấy vì phiên đọc thêm file ngoài dữ liệu.

### 1.6 (f) Giao diện được chấm thế nào
- `dashboard_ui` 92/100 (01/10): 7 điểm trừ = 2 `chuc_nang` + 2 `bang_chung` + 3 `trai_nghiem` + 1 `tai_lieu`; `bang_chung` được điểm nhờ `docs/DASHBOARD_REVIEW_2026-09-23.md` — không phải số đo.
- Toàn hệ thống: 19 khoản trừ `trai_nghiem` (33 điểm), **0** khoản dẫn tương phản / click / thời gian / cỡ chữ; chúng là "49 cờ chỉ sửa được bằng .env", "menu 11 mục", "file > 900 dòng".
- Công cụ có sẵn nhưng devsys không dùng: `tools/ui_v2_acceptance.py` (số click, khóa widget mất, rerun +% — in ra chữ, mã thoát 0/1, không lưu), `tools/ui_contrast_audit.js` (chuỗi trong console trình duyệt),
  `tools/ui_snapshot.py` (ảnh). `devsys/*.py` + `tools/devsys_*.py` không nhắc tới chúng. Độ phủ test giao diện chỉ đo bằng "module có test import tới" (AppTest được nhận qua `_app_screens`).
- Hệ quả đã xảy ra: 02/10 đo thật mới thấy chữ sáng trên nền sáng 1,03–1,43:1 và các luật `data-baseweb` chết — nằm ngoài mọi điểm.

### 1.7 (g) Trọng số 30/20/15/15/10/10 và tiêu chí thiếu
| Tiêu chí | Tối đa | TB 01/10 | Độ lệch chuẩn (điểm) | Phần phương sai điểm tổng |
|---|---|---|---|---|
| `chuc_nang` | 30 | 26,1 | 1,69 | 10 % |
| `bang_chung` | 20 | 17,1 | 2,45 | **29 %** |
| `test` | 15 | 13,9 | 2,90 (chủ yếu do khu vực Tài liệu bị giới hạn 3) | 23 % |
| `tuan_thu` | 15 | 14,1 | 1,43 | 13 % |
| `trai_nghiem` | 10 | 7,9 | 1,34 | **18 %** |
| `tai_lieu` | 10 | 9,0 | 0,87 | 7 % |
Trọng số cao nhất lại ít phân biệt nhất. Thiếu hẳn: (1) **độ tin cậy & an toàn khi lỗi** (nuốt lỗi — 84 chỗ `except Exception` im lặng trong mã hiện tại; thử lại tốn tiền; dừng sạch);
(2) **bảo mật & quyền** — `core/access.py` (đợt F 02/10, kiểm quyền theo dự án) và `core/auth.py` chưa có tiêu chí nào; (3) **khả năng bảo trì** (8 file > 900 dòng, hàm dài/phức tạp mới chỉ là một dòng "file giao diện > 900"
trong `trai_nghiem`); (4) **hiệu năng** (chỉ có ở `ui_v2_acceptance`); (5) **dữ liệu thật / đo chất lượng đầu ra phim** — `bang_chung` hỏi "có chạy thật" chứ không hỏi "đầu ra đo ra sao".

## 2. Thang bản 2 — thay đổi và lý do

### 2.1 Tiêu chí và trọng số (tổng 100)
| Tiêu chí | Bản 1 | **Bản 2** | Lý do |
|---|---|---|---|
| `chuc_nang` | 30 | **26** | ít phân biệt; phần TODO còn mở thành khoản trừ tự động |
| `bang_chung` | 20 | **16** | thêm "đo chất lượng đầu ra phim"; phần "cờ BẬT chưa thử thật" thành khoản trừ tự động |
| `test` | 15 | **12** | bão hòa; thêm độ phủ module/hàm do code đo |
| `tuan_thu` | 15 | **8** | phần lớn đã thành luật code (sổ chi, ước tính); thêm dấu hiệu "lời gọi tốn tiền không guard" |
| `tin_cay` (mới) | — | **12** | lỗi, tiền, quyền, bí mật; `except` nuốt lỗi do code đếm |
| `bao_tri` (mới) | — | **8** | file/hàm dài, độ phức tạp do code đo; khai báo trùng lặp (B1) |
| `trai_nghiem` | 10 | **10** | giữ; thêm số đo giao diện thật và số điều khiển mỗi màn |
| `tai_lieu` | 10 | **8** | ít phân biệt |

### 2.2 Mức nghiêm trọng — điểm do code gán (chống "chạm trần")
Người chấm ghi `muc` ∈ `chan` / `lon` / `nho` và `loai`; **không ghi số điểm** (nếu ghi, giữ lại ở `claimed_points`, code bỏ qua). Điểm trừ = 35 % / 12 % / 4 % điểm tối đa của tiêu chí
(`chuc_nang` 26: −9,1 / −3,1 / −1,0). Lý do: bug 🔴 như B2 phải đắt gấp 3 lần nhãn thiếu, thay vì ngang nhau. Ràng buộc do code:
- `chan` phải có bằng chứng **`file:dòng` kiểm được hoặc `test:`**; chỉ `absent:`/`flag:`/TODO → hạ thành `lon` (ghi vào `code_caps`).
- `chan`/`lon` bắt buộc `feedback.fix` (≥ 10 ký tự) + `feedback.effort` — khoản trừ không thành việc sửa thì bị từ chối.
- Còn lỗi chặn thì giới hạn khu vực: ≥ 1 → ≤ 89; ≥ 2 → ≤ 79.

### 2.3 Khoản trừ tự động do code đo (`devsys/metrics.py`) — người chấm không trừ lại
| Luật | Tiêu chí | Đo | Mỗi / tối đa |
|---|---|---|---|
| `file_dai`, `ham_dai`, `ham_phuc_tap` | `bao_tri` | `ast`: file > 900 dòng, hàm > 150 dòng, độ phức tạp > 30 | 1,0/3 · 0,4/2 · 0,4/2 |
| `todo_mo` | `chuc_nang` | dòng `TODO.md` còn mở gán cho khu vực (không tính "chờ người dùng") | 0,3/3 |
| `co_bat_chua_thu` | `bang_chung` | cờ của khu vực BẬT mà `verified=False` | 0,5/4 |
| `nuot_loi` | `tin_cay` | `except`/`except Exception` chỉ pass/continue/return hằng, không log, không raise | 0,4/4 |
| `tien_khong_qua_so` | `tuan_thu` | lời gọi `submit`/`generate_*` trong hàm không có từ khóa ngân sách/sổ chi/ước tính (dấu hiệu) | 0,5/2 |
| `module_khong_test`, `ham_khong_test` | `test` | module không test import tới; hàm công khai không được test nhắc tên (≥ 5 hàm, dấu hiệu) | 0,6/3 · 1–3/3 |
| `man_nhieu_nut` | `trai_nghiem` | file màn hình > 60 điều khiển Streamlit | 0,5/3 |
| `tuong_phan`, `chu_nho`, `ui_nhieu_click`, `ui_cham` | `trai_nghiem` | đọc `devsys/data/ui_metrics.json` (kết quả `ui_v2_acceptance.py` + `ui_contrast_audit.js`), chỉ khu vực `"ui_metrics": true` | 0,1/2 · 0,05/1 · 1/1 · 1/1 |
Mọi khoản có bằng chứng `file:dòng` / `TODO.md:n` / `flag:` kiểm được; khoản "dấu hiệu" được gắn nhãn. Số đo thô (nuốt lỗi, hàm không test…) hiện ở web, trang Sức khỏe, và trong dữ liệu gửi người chấm.
Đo thử trên repo hiện tại: **84 chỗ `except` nuốt lỗi** (Bước 1: 18, Dashboard: 13), 8 file > 900 dòng, 0 lời gọi tiền thiếu guard (kết quả tốt: các sửa 26/09 đã đủ), khoản trừ tự động 0–16 điểm/khu vực (TB ≈ 7).

### 2.4 Checklist loại lỗi đã gặp (chống bỏ sót)
10 mã `K1…K10` (xem `devsys/rubric.md`): khai báo chung lệch (B1, B6), công thức đo sai (B2), ràng buộc bên ngoài (B3), diễn giải đầu ra model (B4), dữ liệu mất (B5), bộ đo sót (B6), tiền ngoài sổ,
im lặng, quyền/bí mật (mới), giao diện chưa đo. Người chấm phải trả lời **đủ 10** cho mỗi khu vực (`co`/`khong`/`khong_ap_dung` + ghi chú ≥ 8 ký tự đã tìm ở đâu); `co` phải có khoản trừ cùng `loai`. Thiếu → hỏi lại một lần,
vẫn sai thì lỗi. Tác dụng: ép nhìn từng lớp lỗi và biến mỗi "có" thành một khoản trừ/việc sửa.

### 2.5 Ổn định giữa các lần chấm
- Dữ liệu gửi kèm điểm lần trước + các khoản trừ cũ (nếu cùng thang). Điểm **chưa tính khoản trừ tự động** không được lệch quá **5 điểm** nếu không có `giai_thich_chenh`
  (`{criterion, why, evidence}`); không có → từ chối và hỏi lại. `scores.stability()` / `--stability` đo độ lệch trung bình và số cặp "lệch dù dấu vân tay không đổi".
- Phần đo tự động tách riêng khỏi phần người chấm nên thay đổi do code không bị tính là "người chấm lệch".

### 2.6 Mô phỏng trên dữ liệu 01/10 (ước lượng, không phải chấm thật)
Giả định: khoản trừ cũ quy đổi theo tỉ lệ 26/30…; bỏ các khoản sẽ thành tự động (dựa `flag:`, chỉ TODO, file > 900 dòng); thêm khoản trừ tự động đo trên mã hiện tại + cờ máy chính; `dashboard_ui` bị giới hạn 6/10 vì chưa có số đo UI.
Kết quả: trung bình **88,2 → 88,5**, độ lệch chuẩn 5,3 → 5,3, khoảng 79–96 → 78–97, số khu vực ≥ 90 giữ 7. Khu vực đổi nhiều: Ngân sách 88 → 82, Dashboard 92 → 87, Tài liệu 81 → 90, AI Dev System 95 → 91.
Ý nghĩa: **phần đo tự động + trọng số mới không tự hạ trần**; hạ trần đến từ `chan` (−9,1 và giới hạn 89/79) và checklist khi chấm thật. Ví dụ nếu B1 và B2 xếp `chan`: Ngân sách ≈ −6 thêm, Chẩn đoán bị giới hạn 89 (từ ~95).

### 2.7 Thay đổi mã
| File | Việc |
|---|---|
| `devsys/rubric.md` | thang bản 2 (2026-10-03); bản 1 giữ ở `devsys/rubric_v1.md` (đổi `rubric_hash` → điểm cũ hiện "khác thang") |
| `devsys/scores.py` | `FORMAT_V2`, `CRITERIA_V2`, `normalize` chia bản 1 (đóng băng) / bản 2; mức nghiêm trọng, khoản trừ tự động, checklist, giới hạn chan/UI/test, quy tắc ổn định; `stability`, `compare_rounds`, `recurring`, `action_report`; `load_all` đọc cả hai bản |
| `devsys/metrics.py` (mới) | số đo `ast`/grep (nuốt lỗi, hàm dài/phức tạp, tiền không guard, độ phủ module/hàm, điều khiển), khoản trừ tự động, đọc/phân tích số đo giao diện |
| `devsys/scorer.py` | gửi số đo + điểm lần trước + checklist; giả lập trả lời bản 2; nhập/chạy truyền `prev` (ổn định); dấu vân tay gồm file đo UI |
| `devsys/app.py` | trang Sức khỏe: bảng số đo bản 2; trang Chấm điểm: nhãn Chặn/Lớn/Nhỏ/🤖, checklist, độ ổn định, tải báo cáo, bảng bản 1 ↔ bản 2 |
| `tools/devsys_score.py` | `--export all`, `--report`, `--compare`, `--stability` (đọc file điểm, 0 USD) |
| `tools/devsys_ui_metrics.py` (mới) | lưu số đo UI thật (`--run-acceptance` / `--acceptance` / `--contrast`) |
| `devsys/areas.json` | `version` 2; file mã/test mới; `dashboard_ui` có `"ui_metrics": true` |
| `devsys/feedback_format.md` | ghi `fix`/`effort` bắt buộc cho `chan`/`lon` (không thuộc `rubric_hash`) |
| `tests/test_devsys_v2.py` (mới) | 25 test (xem mục 5) |

## 3. Rủi ro và hạn chế
1. **Chỉ số heuristic có dương tính giả**: `ham_khong_test` (tên hàm xuất hiện trong test), `tien_khong_qua_so` (từ khóa guard trong cùng hàm), `nuot_loi` (một số `except` best-effort có chủ ý). Có trần và nhãn "dấu hiệu"; người chấm được yêu cầu xác minh.
2. **Khuyến khích sai**: `todo_mo` có thể làm người ta xóa TODO thay vì làm; trần −3 để giới hạn. `file_dai` có thể khuyến khích tách file máy móc.
3. **Người chấm vẫn là mô hình**: có thể hạ mức (đánh `nho` cho lỗi nặng). Biện pháp: `chan` chỉ khi có bằng chứng kiểm được, checklist ép nhìn, độ ổn định ép giải thích; vẫn nên chấm 1–2 khu vực bằng hai người chấm khác nhau để đo chênh.
4. **Không so thẳng bản 1 ↔ bản 2**: tổng cùng /100 nhưng tiêu chí khác; lần bản 2 đầu là mốc mới. Chưa có điểm bản 2 trước đó nên quy tắc ổn định chỉ bắt đầu ở lần thứ hai.
5. **Số đo UI phải chạy tay**: `--run-acceptance` (vài phút, 0 USD, nhà cung cấp giả) và dán kết quả `ui_contrast_audit.js` vào file rồi `--contrast`. Chưa có thì `trai_nghiem` của `dashboard_ui` ≤ 6/10.
6. **Phụ thuộc máy chạy**: `co_bat_chua_thu` đọc `dashboard.env` — phải đo ở `D:\AI-Video-Pipeline` (máy chính); ở worktree không có `dashboard.env` nên cờ coi như theo mặc định (không BẬT thừa). Diag đọc `data/manifest.sqlite` cũng ở máy chính.
7. **Chi phí chấm API tăng nhẹ**: câu trả lời dài hơn (feedback bắt buộc + checklist) → ước tính token ra 3000 → 4500; vẫn có `--yes` + ước tính + trần Claude như cũ; một lần hỏi lại (lệch/checklist) tính trong `usd_max`.
8. **Chưa làm**: độ phủ dòng (`coverage.py` chưa cài, nặng), quét bảo mật tĩnh (bandit), đo thật độ chính xác QC/chất lượng đầu ra phim (vẫn do người chấm theo bằng chứng báo cáo), đo hiệu năng ngoài giao diện.

## 4. Cách so điểm cũ ↔ mới và chạy lần chấm bản 2
**Điểm cũ không mất**: file bản 1 (`devsys-score/1`) vẫn đọc và giữ nguyên số đã tính; web hiện "khác thang" và nhãn "bản 1". `latest_by_area` lấy file mới nhất theo khu vực nên khi có bản 2, điểm hiện hành đổi sang bản 2.
`py tools/devsys_score.py --compare` in từng khu vực: điểm bản 1 · bản 2 · chênh, **% điểm tối đa theo từng tiêu chí chung** (vd. `chuc_nang:83→88%`) và tiêu chí chỉ bản 2 có (`tin_cay`, `bao_tri`) — nên so theo % chứ không so số thô.

Quy trình đề xuất (chạy ở `D:\AI-Video-Pipeline`, sau khi gộp nhánh):
```
py tools/devsys_collect.py --tests                       # ≈ 4 phút: lần chạy test mới (không thì test bị giới hạn 6,4/12)
py tools/devsys_ui_metrics.py --run-acceptance           # 0 USD: số click/khóa/rerun giao diện v2
py tools/devsys_ui_metrics.py --contrast contrast.txt    # sau khi chạy tools/ui_contrast_audit.js (AUDIT_MODE='all') và lưu kết quả
py tools/devsys_score.py --export all                    # ghi devsys/data/exports/<khu_vực>.md (16 file) cho người chấm ngoài
py tools/devsys_score.py --import <file.json> --scorer claude-code-session    # mỗi khu vực một file JSON theo thang bản 2
py tools/devsys_score.py --compare ; py tools/devsys_score.py --stability ; py tools/devsys_score.py --report
```
Khuyến nghị: dùng ≥ 2 người chấm khác nhau cho 2–3 khu vực (nhập với `--scorer` khác nhau) để đo chênh giữa người chấm; sau ~1 tuần chấm lại bản 2 để quy tắc ổn định có dữ liệu.

## 5. Kiểm thử
`tests/test_devsys_v2.py`: 25 test mới (thang, mức nghiêm trọng, `chan` cần bằng chứng và giới hạn, `fix` bắt buộc, checklist, khoản trừ tự động, giới hạn test/UI, độ lệch, đọc cả file bản 1 + bản 2, đo `ast`,
đọc đầu ra UI, luồng người chấm giả lập + người chấm Claude giả (transport mock, hỏi lại khi lệch), nhập ngoài, báo cáo/so sánh/ổn định/`--export all`, đo thử toàn repo). `tests/test_devsys.py` giữ nguyên 37 test, tất cả còn qua
(bản 1 đóng băng nên không phải sửa). Không có lời gọi Claude API trả tiền ở bất kỳ test nào.
