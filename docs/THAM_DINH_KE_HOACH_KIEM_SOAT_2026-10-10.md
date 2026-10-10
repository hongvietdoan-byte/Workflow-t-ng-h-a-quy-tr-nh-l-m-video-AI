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
