# Thẩm định độc lập kế hoạch kiểm soát (10/10/2026)

Người dùng yêu cầu "một agent minh bạch công bằng rà soát và chấm điểm file kế hoạch". Agent độc lập, chỉ đọc, không biết ý kiến tác giả;
đối chiếu với code thật. Đối tượng: `docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` (commit 378c25c). Ghi lại nguyên kết quả.

## Bảng điểm

| Tiêu chí (trọng số) | Điểm | Lý do chính |
|---|---|---|
| A. Đúng gốc vấn đề (15) | 7,5 | 3 gốc có bằng chứng code; chưa tách "model lờ prompt đúng" khỏi "prompt sai"; N2 (sinh, không chép tay) có thể làm chất lượng giảm (#22 đẹp nhờ câu viết tay) mà không bàn |
| B. Độ phủ (20) | 7 | có L1–L15 + V1–V4, T1–T3, L15 mở; video mỏng (một dòng), ma trận mục 3 L11 không kiểm sau, không ca vàng video; shot không có sân khấu 3D thì ② trống |
| C. Chặt chẽ nội bộ (15) | 5 | mâu thuẫn sau các lần vá: N2/2.1/mục 8 "mô tả thêm không kiểm" ↔ mục 11; 11.2 "Claude khai vô lý" ↔ N4/12.1; mục 6 lấy ca vàng làm thước ↔ 9b.5 |
| D. Khả thi kỹ thuật (15) | 6 | tái dùng đúng (shot_specs, FACTS, qc_team enum + shadow); đo code L1/L4/L6/L10 chưa có; Tổ QC chỉ có C1; `contradictions` là regex → chặn thật trái N7; decisions.json là sổ điểm quyết định, không phải sổ khâu |
| E. Đo lường (10) | 5,5 | thiếu chỉ số độ phủ theo cấu trúc, mẫu số "báo nhầm" chưa rõ, K4 không có tiêu chí, không đo chất lượng prompt sinh |
| F. Chi phí, vận hành (10) | 5 | mục 5 chưa tính lại sau mục 10–12; câu hỏi "cố ý hay lỗi" không có trần; người dùng vẫn duyệt BYĐ 9 shot |
| G. Lộ trình (5) | 6 | thứ tự hợp lý; K0 quá tải; ca vàng cần BYĐ mà BYĐ ở K1; không điểm dừng đo chất lượng giữa K2–K3 |
| H. Đáp ứng yêu cầu (10) | 7 | đáp ứng phần lớn; "ảnh và video chặt như nhau" mới là tuyên bố |

**Tổng = (7,5×15 + 7×20 + 5×15 + 6×15 + 5,5×10 + 5×10 + 6×5 + 7×10) / 100 ≈ 6,2 / 10**

## Khẳng định ↔ code
ĐÚNG: shot_specs V3 (`prompts/29_director_stage_specs.md:55-67`, `core/stage_solver.py:90-114`, beats có `tu_the`); stage_facts FACTS +
contradictions (`core/stage_facts.py:300-347, 413`); qc_spec đọc chữ bằng regex (`core/qc_spec.py:20-25`); qc_team enum + học việc (chỉ C1,
`core/qc_team.py:236`); QC ≈ 0,019–0,020 USD/khung ~12 mệnh đề (`core/qc_team.py:283`); decisions.json thiếu 4 khâu (84 mục); cờ thật.
MỘT PHẦN SAI: stage_facts làm "lớp code chắc chắn" — regex, chỉ shot có stage_camera, đạo cụ chỉ khối trụ. CHƯA CÓ: embedding mặt, Pose,
phát hiện vật, tách vùng màu; `tests/golden/`, `knowledge/checks/`. Ca vàng hiện 8 ca, toàn chữ + máy. Bỏ sót tái dùng: dấu vân tay
(`core/storyboard_gate.py:103`, `core/autopilot.py:651-685`), `ReplayClient` (`core/qc_team.py:6-8`).

## Lỗ hổng (mức)
1. CAO — tài liệu tự mâu thuẫn (N2/N4, 2.1, 8, mục 9 cũ, 9b.2) → hợp nhất một bản.
2. CAO — rủi ro chất lượng N2 → K2 thêm so A/B có trả tiền, trần nhỏ, người dùng chấm; chỉ số vào mục 6.
3. CAO — chi phí + gánh nặng chưa tính lại → mục 5 theo mệnh đề/shot × giá C1, tách ảnh/video; trần câu hỏi "cố ý hay lỗi"/dự án.
4. CAO — video chưa chặt ngang ảnh → bảng video riêng L1–L15 + V1–V4 trên khung lấy mẫu; ca vàng video; tiêu chí K4 cụ thể.
5. TRUNG — chặn thật dựa regex → kiểm mâu thuẫn ở mức trường BYĐ; regex trên mô tả thêm chỉ vàng.
6. TRUNG — phụ thuộc K0 ↔ K1 (ca vàng cần BYĐ) → K0 chốt định dạng + schema BYĐ tối thiểu; ca cũ nhập BYĐ tay `ca_vang_tay`.
7. TRUNG — đo code L1–L15 phần lớn chưa có, C2/C3 chưa xây → cột "hiện có / phải xây / đợt nào"; test hợp đồng không tính học việc chưa có cách đo.
8. TRUNG — luật T2 từ một câu "cố ý" có thể khái quát quá → gắn phạm vi (vật + ngữ cảnh + dự án), hạn dùng, nút gỡ.
9. THẤP — độ hạt sổ → `devsys/stages.json` (L1–L16) trỏ id decisions.
10. THẤP — ghi tái dùng dấu vân tay + ReplayClient.

## Điểm mạnh thật
Chẩn đoán "kiểm không nhìn đúng gói" có code xác nhận; "model khai, code kết luận" có tiền lệ chạy thật; khuôn FACTS là nền đúng cho
10.1; mục 12 T1 > T2 > T3 xử lý ví dụ lơ lửng mà không biến lẽ thường thành luật cứng; N7, N9, nút Bỏ qua khớp các quyết định trước.

## Câu hỏi cho người dùng
1. Chấp nhận khoản nhỏ có trần (≤ 1 USD) so ảnh prompt sinh vs prompt Đạo diễn trước K3?
2. Trần câu hỏi "cố ý hay lỗi"/dự án? Luật "cố ý" áp phạm vi nào?
3. Duyệt BYĐ 9 shot dạng một dòng/shot, hay chỉ duyệt ô bị đánh dấu?
4. Dự án không có sân khấu 3D thì BYĐ thế nào? Bắt buộc sân khấu 3D cho dự án mới?
5. Âm thanh, phụ đề, dựng có trong "mọi khâu" không, hay hoãn có chủ đích?
6. 9b.2 đã chốt chưa?

## Kết luận
**Sửa rồi mới build K0; không cần viết lại toàn bộ.** Viết lại: hợp nhất mâu thuẫn; mục 5 chi phí; mục 6 nghiệm thu; tách K0; xử lý phụ
thuộc ca vàng ↔ BYĐ. Build khi tài liệu còn mâu thuẫn thì test hợp đồng sẽ khóa theo bản chưa nhất quán.

---

# Lần 2 — thẩm định bản hợp nhất v2 (commit 92fc872): **7,1 / 10** (v1: 6,2)

Agent độc lập mới, chỉ đọc, cùng thang + trọng số. Tổng = (8×15 + 7,5×20 + 6,5×15 + 6×15 + 7×10 + 6,5×10 + 6,5×5 + 8×10) / 100 ≈ 7,1.

| Tiêu chí | v1 | v2 | Ghi chú v2 |
|---|---|---|---|
| A gốc vấn đề | 7,5 | 8 | tách "model lờ ý đúng"; chưa coi code đang tự ghép prompt nhiều tầng (`core/runner.py:1811`) là nguồn lệch |
| B độ phủ | 7 | 7,5 | đủ cột ảnh/video/âm-chữ; âm/chữ/dựng còn mỏng; V4 ghi "có" nhưng chưa có |
| C nhất quán | 5 | 6,5 | mâu thuẫn v1 đã gỡ; mới: N2/A12 trái code đang chèn chữ (`build_image_prompt`, `looks.clean_prompt`, `stage_facts.prompt_block`); 3.3 cho Claude khai "nói trái" (trái N4); vòng 3.3 tác động mà không học việc (trái N8); N11 "không tả lại ngoại hình" trái Identity lock F1-C (#22) |
| D khả thi | 6 | 6 | A10 phụ thuộc Nhánh B (87/90 bối cảnh không 3D) nằm gọn trong K1; vân tay gói phải viết mới; K5 cần Pose/bộ phát hiện/embedding |
| E đo lường | 5,5 | 7 | A/B chỉ 3 shot ảnh; chưa đo hội tụ vòng 3.3 |
| F chi phí | 5 | 6,5 | nhận 10–20 % vượt A3 nhưng chưa quyết; đơn giá ③ chưa đo; chưa có trần tổng thao tác người dùng |
| G lộ trình | 6 | 6,5 | K1 quá tải; video phải chờ K4 |
| H đáp ứng chốt | 7 | 8 | A12 chưa đối chiếu code; A10 gần như chặn dự án mới tới khi Nhánh B xong |

Lỗ hổng v1: #2, #6, #7, #8, #9 đã xử lý; #1, #4, #5 phần lớn / mâu thuẫn mới; #3, #10 một phần.

**Còn lại:** CAO — (1) thêm mục 3.3b "chữ hệ thống" (mỗi phần code đang ghép: bỏ → dữ kiện / giữ thành phần cố định khai báo + kiểm /
chuyển sang ảnh tham chiếu; Identity lock vào A/B); (2) tách K1a (BYĐ trên bối cảnh có 3D) / K1b (Nhánh B, nghiệm thu lệch chiếu ngược
≤ 3 % trên ≥ 3 bối cảnh) + chọn cách chờ; (3) 3.3: Claude khai (trường, giá trị enum, trích), code so; lớp Claude học việc trước khi tự
trả lỗi. TRUNG — vân tay gói viết mới ở K2; quyết định chi phí 10–20 % trước K3; trần tổng thao tác + định nghĩa "ô đáng ngờ"; A/B 3 shot
phủ 3 kiểu. THẤP — gộp `tests/fixtures/stage_facts_golden.json` vào `tests/golden/`; V4 "xây ở K4"; `LLM_STAGE_TOKENS` qc (6000, 900)
→ output ~5000 (ước thấp ~5 lần, không phải 40 %); lớp code ④ video lên K3.

**Câu hỏi người dùng:** (1) chữ hệ thống giữ thành phần cố định khai báo hay chuyển hết cho Đạo diễn? (2) chờ Nhánh B: chỉ 3/90 bối cảnh có
3D, hay tạm cho ② trống → VÀNG? (3) chi phí kiểm 10–20 %: nâng ngưỡng hay cắt lớp Claude ở shot dễ? (4) lớp code ④ video lên sớm ở K3?

**Kết luận: SỬA NHỎ RỒI BUILD K0a** — sửa tài liệu #1, #3, #2 trước khi khóa test hợp đồng; mục 4–9 sửa trước K2/K3.

---

# Lần 3 — kế hoạch sau A14–A17 + phần K0a đã build (main eaf2370): kế hoạch **7,6 / 10**, K0a **7,5 / 10**

Tổng = (8,5×15 + 8×20 + 7×15 + 7×15 + 7×10 + 7×10 + 7×5 + 8,5×10) / 100 ≈ 7,6 (lần 1 6,2 · lần 2 7,1).

| Tiêu chí | L2 | L3 | Ghi chú |
|---|---|---|---|
| A gốc | 8 | 8,5 | 3.3b chỉ đúng dòng code tự ghép |
| B độ phủ | 7,5 | 8 | video 2 lớp code; âm/chữ/dựng (K6) còn một dòng, chưa ca hồi quy âm/chữ |
| C nhất quán | 6,5 | 7 | còn: N11 "chữ không tả lại ngoại hình" ↔ 3.3b "bắt buộc must_keep + màu"; khai báo bắt buộc phát hiện bằng Claude đang học việc → không chặn được; A14 "khai báo tiếp" không trần ↔ N2 ≤ 2 vòng; lối `dot` của test chưa ghi ở 3.9 |
| D khả thi | 6 | 7 | K1a/K1b, 2 bối cảnh; K5 công cụ đo vẫn chưa có |
| E đo lường | 7 | 7 | chưa cỡ mẫu "báo nhầm ≤ 10 %"; số "9 khâu đọc chữ tự do" SAI — sổ cho 11 |
| F chi phí | 6,5 | 7 | đơn giá QC 0,019 USD/khung (01/10) có thể ước thấp 2–6 lần (10/10 output ~5k token ≈ 0,06 USD/lần chấm) |
| G lộ trình | 6,5 | 7 | K1b sau K4 → 2 bối cảnh kéo dài |
| H chốt | 8 | 8,5 | A4 âm/chữ/dựng mới trên bảng |

**K0a 7,5/10 — đạt có điều kiện.** Đạt: điều kiện xong mục 8; trang đỏ đúng 8 khâu; enum BYĐ khớp shot_specs có test; ca hồi quy đúng định dạng;
không đổi hành vi ngoài ước qc. Kẽ hở: L8 "kiểm trước: chay" sai (d85 là bộ SINH, d84 chỉ cấu trúc); d86 chỉ chạy trong change_audit
(khi có thay đổi); chỉ 4/21 dòng gắn cờ (L3, L6, L8, L9 phụ thuộc `stage_camera` chưa gắn); error_types tính "học việc" khi cờ tắt và
bỏ qua `bat:false` → "6/23 chỉ xây" ước thấp; `dot` không hết hạn; hợp đồng không cấm id kiem_chung / id bộ sinh trong kiem_truoc; 8 ca
hồi quy đều L7 chữ+máy, `byd: null`, không `goi.refs`; `from_shot_spec` chưa chuyển beats → hanh_dong.

**Còn lại:** CAO — bật `collab_prompt` mất Identity lock mà chỗ thay còn học việc (lỗi #22 có thể quay lại) → kiểm khai báo bắt buộc
bằng code (so tên + màu món Kho, ĐỎ) hoặc chỉ bật khi lớp Claude 3.3 đạt ngưỡng; N11 viết lại. TRUNG — gắn cờ cho dòng phụ thuộc; `dot_hien_tai`;
kiểm loại id; xác định đơn giá QC khung/cảnh trước K3; ≥ 2 ca hồi quy âm/chữ ở K0b. THẤP — sửa 9 → 11; cỡ mẫu n ≥ 50, ≥ 2 dự án.

**Câu hỏi người dùng:** (1) khi lớp Claude vòng viết còn học việc, Identity lock giữ kiểu code chèn (tạm trái A14) hay chặn bằng code so
tên + màu món Kho? (2) Đạo diễn có phải viết màu + món must_keep vào prompt (quyết N11 ↔ 3.3b)?

**Kết luận:** kế hoạch sẵn sàng cho K0b (sửa N11, khoảng hở 3.3b, đơn giá QC trước K2/K3). K0a sửa nhanh (0 USD) trước K0b: L8 → khong_co
+ ghi chú d86; cờ stage_camera; test cấm id kiem_chung + dot_hien_tai; error_types không tính bat:false / học việc khi cờ tắt; 9 → 11.

---

# Lần 4 — kế hoạch + phần build K0a + K0b (main 2aa5095): kế hoạch **7,9 / 10**, build **8,0 / 10** — CHƯA đạt cổng A21

Agent độc lập mới, cùng thang + trọng số. Chạy 6 tệp test chỉ định: **128 qua** (12 s). Đọc `data_out/k0b_p24/summary.json` + bằng chứng.
Kế hoạch = (8,5×15 + 8×20 + 7,5×15 + 7,5×15 + 7,5×10 + 7,5×10 + 7,5×5 + 8,5×10) / 100 ≈ 7,9 (L1 6,2 · L2 7,1 · L3 7,6).
Build = (8,5×15 + 7,5×20 + 7,5×15 + 8×15 + 7,5×10 + 9×10 + 8×5 + 8×10) / 100 ≈ 8,0 (K0a L3 7,5).

**Lỗ hổng lần 3:** ĐÓNG có code/test — L8 `khong_co` + ghi chú d86 (`devsys/stages.json:59`, `tests/test_devsys_stages.py:86`); cờ dòng phụ thuộc
`stage_camera` (`:161`); chỉ id `vai: kiem` (`:72`); `dot_hien_tai` quá hạn → đỏ (`:101`); error_types không tính cờ TẮT / `bat:false` (`:248`);
9 → 11 (kế hoạch dòng 306); n ≥ 50 / ≥ 2 dự án (dòng 349); N11 viết lại theo A19 (dòng 72); A14 ≤ 2 vòng (dòng 27); đơn giá QC đo thật
0,018 USD/khung (dòng 323); khóa nhận diện chặn bằng CODE (A18) — `core/identity_declare.py:331` có test + chạy CSDL thật 0 món bỏ im lặng;
≥ 2 ca âm/chữ/dựng, ≥ 3 ca BYĐ + gói (16 ca). CHƯA ĐÓNG — `from_shot_spec` vẫn không chuyển beats → hanh_dong (`core/shot_intent.py:191-198`).

| Tiêu chí | KH L3 | KH L4 | Build L4 | Lý do + bằng chứng |
|---|---|---|---|---|
| A gốc | 8,5 | 8,5 | 8,5 | chạy khô xác nhận gốc 2 (gói không ai xem); lộ gốc mới chưa vào kế hoạch: `jobs` KHÔNG lưu prompt đã gửi (BANG_CHUNG:34) |
| B độ phủ | 8 | 8 | 7,5 | #24: 2/9 lỗi bắt trước tiền, 5 chưa bắt (BANG_CHUNG:56); "ảnh mẫu Kho bẩn", "mô tả Kho ↔ ảnh mẫu" (BANG_CHUNG:74–77) chưa thành dòng kế hoạch; 10/16 ca là L7 |
| C nhất quán | 7 | 7,5 | 7,5 | N11/A14 gỡ; còn: dòng 8 trạng thái cũ ("build K0a"); mục 12 dòng 382 vẫn "tái dùng vân tay" ↔ 3.3 "VIẾT MỚI"; ca hồi quy `lop_phai_bat: d85` (vai SINH, `p24_shot8_block_byd.json:144`) và `d26` cho world_rules (`t2_luat_vat_x…json:30`) trái luật vai sổ; `knowledge/checks/L4.md:6` enum TU_THE cũ |
| D khả thi | 7 | 7,5 | 8 | identity_declare / world_rules / shot_intent chạy được, có test; Pose model có (28° vs 41°, 2 ảnh); bộ phát hiện vật CHƯA thử; A18 "mọi món phải có chữ" sẽ đỏ 7/9 shot (BANG_CHUNG:32–35) mà QC thấy trang phục đúng |
| E đo lường | 7 | 7,5 | 7,5 | L11 tính "co" bằng `plate_layout_qc` (`devsys/error_types.json:47`) dù chạy khô đo là MÙ (BANG_CHUNG:49) → số "có cách kiểm" bị thổi; A18 chặn ngay không có ngưỡng báo nhầm (N8 chỉ miễn cho lớp "chắc chắn"); kỳ vọng `am_chu`/`dung`/`do_tu_the` của ca không lớp nào chạy |
| F chi phí | 7 | 7,5 | 9 | đơn giá đo thật dòng 323–337; ③④ còn ước, đo ở K2/K3 có ghi; build 0 USD đúng cam kết |
| G lộ trình | 7 | 7,5 | 8 | K1b song song sau K2 (dòng 318); K0b ghi ✅ nhưng tiêu chí "công cụ đo ≥ 20 khung" (dòng 307) chưa đạt: YuNet 18 ảnh, Pose 4, phát hiện vật 0; `dot_hien_tai` còn "K0a" (`devsys/stages.json:9`) |
| H chốt | 8,5 | 8,5 | 8 | A18/A20/A22 bước 1 có mã + số; `identity_declare`, `world_rules` chưa có id trong `devsys/decisions.json` → sổ không trỏ được khi nối |

**Lỗ hổng còn lại (chặn 8,5 trước):**
1. CAO — A18 chặn ngay mà chưa đo chính xác: luật "mọi món must_keep" đỏ 37 món / 7 shot #24. Việc: kế hoạch A18 lọc món theo BYĐ
   (`co`, `thay`, món nhìn thấy) + ngưỡng báo nhầm đo trên prompt #22/#24 (người gán 1 chạm, n ≥ 30) trước khi CHẶN, chưa đạt → VÀNG;
   code: `identity_declare.check` nhận bộ lọc món + ca hồi quy chống báo nhầm (giày ở MCU, lưng). **+0,25 KH / +0,2 build** (C, D, E).
2. CAO — gói đã gửi không được lưu → không kiểm được "prompt gửi thật", vân tay, ca hồi quy có `goi`. Việc: kế hoạch đưa "lưu gói gửi
   (prompt cuối + refs + vai + model + sha)" vào K1a (0 USD, ghi thêm, không đổi hành vi) + test. **+0,15 KH** (A, E).
3. CAO — sổ đo phải trung thực trước khi dùng số làm cổng: L11 `plate_layout_qc` → `hoc_viec`/không tính tới khi đo đúng ≥ 1 bối cảnh;
   thêm id cho identity_declare + world_rules (vai kiem, `bat:false`); test `lop_phai_bat` ⊂ vai kiem; `dot_hien_tai` = K0b. **+0,2 build** (C, E).
4. TRUNG — kết thúc K0b đúng tiêu chí: Pose đo góc thân ≥ 20 khung #22/#24 → ngưỡng "ngã ngửa" hoặc ghi không dùng được; thử bộ
   phát hiện vật; kỳ vọng ca chưa có lớp đánh dấu `chua_co_lop` + đợt (test cấm kỳ vọng "chết"). **+0,15 build** (B, G, D).
5. TRUNG — đưa bài học chạy khô vào kế hoạch: 5 lỗi #24 chưa bắt → mỗi lỗi một loại + đợt + câu nghiệm thu (trăng/nguồn sáng L12,
   màu vật L10, nền mẫu L11, ảnh mẫu Kho bẩn + mô tả Kho ↔ ảnh mẫu ở L5 trước tiền); sửa dòng 8, dòng 382, L4.md. **+0,2 KH** (B, C).
6. THẤP — `from_shot_spec` chuyển beats → hanh_dong (carry lần 3); `knowledge/world_rules.json` mới 1 luật. **+0,05**.

**Kết luận: CHƯA ĐẠT A21** (KH 7,9, build 8,0). Tối thiểu để ≥ 8,5: #1 (kế hoạch + code bộ lọc + đo báo nhầm), #2 (kế hoạch), #3 (sổ),
#5 (kế hoạch); #4 nên làm cùng (0 USD). Ước sau sửa: KH ≈ 8,5–8,6, build ≈ 8,5. Tất cả 0 USD; không cần dữ liệu mới ngoài gán nhãn ≤ 30 mục.

# Lần 5 — kế hoạch + build K0a/K0b + đợt đóng lỗ hổng 4 (main 0bd1b60): kế hoạch **8,1 / 10**, build **8,3 / 10** — CHƯA đạt cổng A21

Agent độc lập mới, cùng thang + trọng số, chỉ đọc. 8 nhóm test (identity_declare, devsys_stages, knowledge_checks, world_rules, shot_intent,
devsys_decisions, slow_marker, golden): **125 qua** (15,6 s).
Kế hoạch = (8,5×15 + 8,5×20 + 7,5×15 + 8×15 + 8×10 + 7,5×10 + 8×5 + 8,5×10) / 100 ≈ 8,1 (L1 6,2 · L2 7,1 · L3 7,6 · L4 7,9).
Build = (8,5×15 + 8×20 + 8×15 + 8,5×15 + 8×10 + 9×10 + 8×5 + 8,5×10) / 100 ≈ 8,3 (L4 8,0).

**Lỗ hổng lần 4:** (1) MỘT PHẦN — lọc món BYĐ (`core/identity_declare.py:360-405`), `CHAN_DO=False` → VÀNG, 2 ca chống báo nhầm; nhưng bảng
gán nhãn 0/30, sau lọc vẫn 38 VÀNG / 9 shot; kế hoạch dòng 160 vẫn ghi "ĐỎ"; ngưỡng ghi 3 kiểu (A18 n ≥ 30 · NHAN_BAO_NHAM:6 · mục 9 ≥ 50).
(2) ĐÓNG — `jobs.sent_package` vào K1a (dòng 221-234, 341). (3) ĐÓNG — L11 học việc, d95/d96 `bat:false`, `dot_hien_tai` K0b.
(4) MỘT PHẦN — `chua_co_lop` có test; Pose 32 khung → chỉ VÀNG; bộ phát hiện vật chưa thử. (5) ĐÓNG — mục 4b + R1. (6) MỘT PHẦN —
`from_shot_spec` xong (`core/shot_intent.py:193-218`); world_rules mới 1 luật. A23 (1a/2a) có code + test.

| Tiêu chí | KH L4 | KH L5 | Build L5 | Lý do |
|---|---|---|---|---|
| A gốc | 8,5 | 8,5 | 8,5 | gốc "gói không lưu" vào K1a; tiền đề A18 "mọi món phải có chữ" chưa chứng minh (38/70 món báo, QC thấy đúng) |
| B độ phủ | 8 | 8,5 | 8 | 4b + R1 phủ 5 lỗi; build: phát hiện vật 0 khung, 1 luật thế giới |
| C nhất quán | 7,5 | 7,5 | 8 | mới: dòng 160 ↔ A18; ngưỡng 3 kiểu; Nhánh C chưa vào kế hoạch; TODO "A1–A22" |
| D khả thi | 7,5 | 8 | 8,5 | `sent_package` đúng chỗ gửi; bộ lọc BYĐ chạy; `from_shot_spec` xong |
| E đo lường | 7,5 | 8 | 8 | sổ trung thực; báo nhầm A18 chưa đo (0 nhãn, ngưỡng chưa chốt, chưa có #22) |
| F chi phí | 7,5 | 7,5 | 9 | không đổi; 0 USD |
| G lộ trình | 7,5 | 8 | 8 | K0b 🟡 trung thực; còn phát hiện vật + nhãn |
| H chốt | 8,5 | 8,5 | 8,5 | A23 vào kế hoạch + code; Nhánh C chưa có dòng A |

**Lỗ hổng còn lại:**
1. CAO — A18 chưa đo báo nhầm: người dùng gán 30 nhãn; chốt MỘT ngưỡng (n ≥ 30, ≤ 10 %) ở A18, NHAN_BAO_NHAM:6, mục 9; báo nhầm > 10 % →
   chỉ đòi món `dau_hieu` / màu tương phản, còn lại giao ảnh tham chiếu. +0,15 KH / +0,15 build.
2. CAO — mâu thuẫn kế hoạch: dòng 160 → VÀNG tới khi đo đạt; thêm A24 Nhánh C + đợt ở mục 8 (K1b nhánh B và C); hàng 4b #3 (dòng 287):
   bối cảnh khối Nhánh C, vai "nền" không phải render (12b.3) → L11 không ĐỎ oan; A15 dòng 30 + rủi ro dòng 409; TODO "A1–A23". +0,25 KH.
3. TRUNG — kết thúc K0b: thử phát hiện vật ≥ 20 khung hoặc ghi chính thức hoãn sang K5 (thiếu trọng số), sửa dòng 340; K0b ✅, `dot` → K1a. +0,1 build.
4. TRUNG — chạy khô #22 cho A18 (`tools/nhan_bao_nham_a18.py`) để đủ ≥ 2 dự án. +0,1 build.
5. THẤP — world_rules ≥ 3 luật từ #22/#24; ca hồi quy `segment` tách sai khi 2 dạng yêu nữ chung 'creature'. +0,05.

**Kết luận: CHƯA ĐẠT A21** (KH 8,1, build 8,3). KH ≥ 8,5 cần #2 (tài liệu) + #1 (nhãn + chốt luật); build ≥ 8,5 cần #1, #3, #4. Ước sau sửa
KH ≈ 8,5, build ≈ 8,6. 0 USD; cần người dùng gán 30 nhãn + quyết tải trọng số bộ phát hiện vật.

# Lần 6 — sau A24–A27, chạy khô #22, gộp Codex đợt 1 (main b582b13): kế hoạch **8,4 / 10**, build **8,5 / 10** — CHƯA đạt cổng A21

Agent độc lập, cùng thang + trọng số, chỉ đọc. 8 nhóm test: **207 qua** (12,6 s).
KH = (9×15 + 8,5×20 + 7,5×15 + 8,5×15 + 8×10 + 8×10 + 8×5 + 9×10) / 100 = 8,35 ≈ 8,4 (L1 6,2 · L2 7,1 · L3 7,6 · L4 7,9 · L5 8,1).
Build = (9×15 + 8,5×20 + 8×15 + 8,5×15 + 8×10 + 9×10 + 8,5×5 + 8,5×10) / 100 = 8,50 (L4 8,0 · L5 8,3).

**Lỗ hổng lần 5:** (1) ĐÓNG về đo đếm — n = 39 từ #22 + #24, 6/39 ≈ 15 %, ngưỡng duy nhất A25, `CHAN_DO=False`, luật mức A26 có code; giữ VÀNG khi
chưa đạt là đúng. (2) MỘT PHẦN — A24 + A15 + dòng 164 sửa nhưng A26 (c) sinh mâu thuẫn mới. (3) MỘT PHẦN — phát hiện vật hoãn K5, K0b ✅
nhưng `dot_hien_tai` vẫn K0b. (4) ĐÓNG — `data_out/k0b_p22/`. (5) ĐÓNG — 6 luật thế giới + ca `segment`.

| Tiêu chí | KH L5 | KH L6 | Build L6 | Lý do |
|---|---|---|---|---|
| A gốc | 8,5 | 9 | 9 | A26 tìm gốc thật: 14/15 "thiếu chữ" ảnh vẫn đúng nhờ ảnh tham chiếu, chỉ `sai_mau` làm ảnh sai |
| B độ phủ | 8,5 | 8,5 | 8,5 | + Nhánh C, blockout, #22, 6 luật; chưa kế hoạch cho biến hình 2 dạng + che theo tư thế |
| C nhất quán | 7,5 | 7,5 | 8 | A18/A20/dòng 164 ↔ A26 (c); trạng thái + TODO cũ |
| D khả thi | 8 | 8,5 | 8,5 | blockout, solver tư thế nằm (prompt 29 hoãn có lý do), plate_layout_qc thiếu đo → VÀNG |
| E đo lường | 8 | 8 | 8 | trung thực (15 % > 10 %) nhưng đo TRONG MẪU (cùng mục dùng để sửa), nhãn agent |
| F chi phí | 7,5 | 8 | 9 | 0 USD; thiếu chữ luôn VÀNG bớt gánh người dùng |
| G lộ trình | 8 | 8 | 8,5 | K0b đóng; K1a chưa nhận việc nối A27 |
| H chốt | 8,5 | 9 | 8,5 | A24–A27 có nguồn + bằng chứng |

**Lỗ hổng:** (1) CAO — A26 (c) chưa lan sang A18 (KH:33), A20 (:35), 3.3b (:164), mục 9 (:386). (2) CAO — 15 % đo trong mẫu; "0 %" của bảng
chọn lại không phải số đo → A25 chỉ tính trên bộ giữ riêng (dự án K1a). (3) TRUNG — K1a thiếu việc A27: BYĐ tách dạng, `identity_declare` đọc
`tu_the`, đo lại. (4) TRUNG — trạng thái cũ KH:8–10, KH:344, TODO. (5) THẤP — `dot_hien_tai` K0b ↔ ghi chú "đổi khi xong đợt". (6) THẤP — ai
điền `khai_bao_chu`, đợt nào (R1). Ước sau sửa: KH ≈ 8,7, build ≈ 8,6.

**Đã sửa ngay (phiên chính, 10/10 khuya, 0 USD):** (1) A18 + A20 + 3.3b + mục 9 khớp A26 (c); (2) mục 9 + tool `nhan_bao_nham_a18.py` ghi rõ số
trong mẫu không dùng cho A25, đo trên bộ giữ riêng K1a; (3) K1a thêm việc (i)–(iv) nối A27; (4) dòng trạng thái KH, hàng K0b, TODO; (5) ghi chú
`devsys/stages.json`: giữ K0b tới khi qua cổng A21; (6) R1: Claude đề xuất `khai_bao_chu`, người dùng duyệt, K1a. → thẩm định lần 7.

# Lần 7 — sau sửa 6 lỗ hổng lần 6 (main e457c09): kế hoạch **8,5 / 10**, build **8,5 / 10** — ĐẠT cổng A21 (sát ngưỡng)

Agent độc lập, cùng thang, chỉ đọc. 3 nhóm test: **103 qua**.
KH = (9×15 + 8,5×20 + 8×15 + 8,5×15 + 8,5×10 + 8×10 + 8,5×5 + 9×10) / 100 = 8,50 (6,2 · 7,1 · 7,6 · 7,9 · 8,1 · 8,4).
Build = (9×15 + 8,5×20 + 8×15 + 8,5×15 + 8×10 + 9×10 + 8,5×5 + 8,5×10) / 100 = 8,50 (8,0 · 8,3 · 8,5).
Lỗ hổng lần 6: (1)(2) MỘT PHẦN (A18 dòng 33 + A25 dòng 40 còn trỏ #22 + #24); (3)–(6) ĐÓNG.
Còn lại: TRUNG — A18/A25 trỏ bộ trong mẫu; TRUNG — A25 đòi ≥ 2 dự án nhưng K1a chỉ 1 dự án thử (cần người dùng chốt); THẤP — tool luôn in
"TRONG MẪU" (cần cờ giữ riêng); THẤP — docstring identity_declare, TODO, A27 gọi 6/39 là nhãn A25; THẤP — nghiệm thu K1a thiếu (i)–(iii).
Agent: không cần thẩm định 8 nếu chỉ sửa đúng các mục này. **Đã sửa cùng ngày:** A18/A25 trỏ bộ giữ riêng; **A28** (người dùng: bộ giữ riêng =
dự án thử K1a + dự án kế; ĐỎ A18 sớm nhất sau dự án 2); `tools/nhan_bao_nham_a18.py --giu-rieng` + test
`test_nhan_bao_nham_giu_rieng_flag_changes_a25_note`; docstring; A27 ghi 6/39 là số trong mẫu; nghiệm thu K1a (i)–(iv). → **Mở K1a.**
