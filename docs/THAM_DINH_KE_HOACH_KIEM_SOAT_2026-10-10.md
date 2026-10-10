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
