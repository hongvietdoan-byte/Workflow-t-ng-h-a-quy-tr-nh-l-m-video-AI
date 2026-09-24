# Chuẩn xây dựng — luật bắt buộc cho mọi thay đổi pipeline (2026-09-24)

Vì sao có tài liệu này: đợt thử thật GĐ6 lặp lại đúng những lỗi mà các phiên trước **đã định hướng tránh** (Bible sai ảnh tham chiếu,
gen lại không chủ đích, layout sai). Rà soát (`docs/KE_HOACH_TONG_2026-09-24.md`) cho thấy lỗi nằm ở **cách xây dựng**: biện pháp có
trong tài liệu nhưng không có trong code, lớp mới không kế thừa lớp cũ, thiếu đầu vào mà không báo, "đã sửa" chỉ dựa vào test giả lập.
Mọi phiên (người hoặc Claude) sửa pipeline phải theo 8 luật dưới đây. Mục "Việc phải làm lại MỖI LẦN" trong `TODO.md` dẫn tới đây.

## 1. Không im lặng khi thiếu đầu vào
Một biện pháp cần dữ liệu (ảnh tham chiếu, Lock, hồ sơ bối cảnh, khung cuối, giá…) mà dữ liệu không có → **báo lỗi rõ hoặc dừng**, không chạy
tiếp như không có gì. Mỗi lần gọi model ghi lại "đã dùng gì" (ví dụ "Director thấy 0/3 ảnh", "gửi 2 ảnh tham chiếu + khung cuối") vào
`diag` hoặc vào job. Cắt bớt ảnh/chữ vì giới hạn model → phải báo. *Ví dụ đã gây lỗi:* đường dẫn ảnh tương đối → Director thấy 0 ảnh → bịa
lại "Kelly đuôi ngựa".

## 2. Ma trận luồng — lớp mới phải kế thừa biện pháp cũ
Mỗi biện pháp liệt kê các luồng áp dụng: bấm tay · autopilot · v2 (mỗi cảnh một clip) · v3 từng shot · multi-shot · nhân bản dự án · chạy lại
Director. Thêm luồng/lớp mới → điền bảng kế thừa (bên dưới) trước khi merge, có test cho từng luồng. *Ví dụ:* multi-shot ép Kling đã ghi đè
luật "≥ 3 người → Seedance"; nhân bản chép Lock cũ.

## 3. Giả định phải thành điều kiện kiểm trong code
"Layout chỉ đúng khi ảnh nền cùng góc máy", "Seedance không nhận khung đầu kèm ảnh tham chiếu", "prompt Kling multi-shot ≤ 512 ký tự" —
viết thành guard/assert/bảng luật (`data/provider_rules.json` khi có), không chỉ viết trong tài liệu.

## 4. Một nguồn chuẩn cho nhân vật và bối cảnh
Thứ tự ưu tiên: **ảnh tài nguyên (kho) > hồ sơ chuẩn ở kho > Bible dự án > Lock**. Dữ liệu máy sinh (Lock, mô tả) tự sinh lại khi nguồn đổi;
phần người sửa tay được đánh dấu và không bị ghi đè. Mọi bước (Director, Lock, gen ảnh, QC) dùng **cùng một bộ ảnh** do một hàm chọn.

## 5. Thang kiểm thật trước khi gen hàng loạt
Chữ thật → 1 ảnh/nhóm → người xem → 1 cảnh video → mở rộng. Test giả lập chỉ chứng minh **luồng**, không chứng minh **chất lượng**. Tính
năng có mục "thử thật" chưa đóng thì **không bật mặc định và không đưa vào autopilot**.

## 6. Chẩn đoán trước khi gen lại
Gen lại chỉ khi **đầu vào đổi** (câu sửa vào prompt, ảnh khác, model khác…); tối đa 2 lần/ảnh/clip (người dùng chốt). Cùng lỗi 2 lần → dừng
shot, báo lớp cần sửa. Autopilot không tắt cổng duyệt, không tự duyệt thứ QC đánh dấu dưới sàn, khi QC chưa hiệu chỉnh.

## 7. QC chỉ so với chuẩn thật
QC so với **ảnh tài nguyên/hồ sơ chuẩn**, không so với sản phẩm của pipeline (layout, "số đông" của bộ ảnh). Câu sửa của QC phải qua kiểm
(không nhắc nhân vật ngoài shot, không đổi tên). Tiêu chí đã đo được lỗi hệ thống (bố cục, tỉ lệ) phải có mức sàn.

## 8. "Đã sửa" phải kèm bằng chứng chạy thật
Mục "đã sửa" trong TODO/tài liệu ghi rõ: test hồi quy dựng từ dữ liệu thật (fixture GĐ6) **và** lần chạy thật xác nhận (hoặc ghi rõ "chưa
thử thật"). Không viết "đã sửa" chỉ vì N test pass.

## Luật chi phí
- Mọi lời gọi Claude đi qua **một client có sổ chi** + nhãn công đoạn (`stage`) + `project_id`; không có đường gọi nào ngoài sổ/trần.
- Mọi nút/lệnh tốn tiền (ảnh, video, âm thanh, Claude hàng loạt) **hiện ước tính trước** (trên nút hoặc câu hỏi xác nhận).
- Sổ chi video đối chiếu với nhà cung cấp (task không được tạo → bỏ khỏi sổ; `cost` thật khi quy đổi được).
- Không gửi lại một job trả tiền khi chưa chắc lần trước không chạy (tránh trả 2 lần).

## Bảng kế thừa khi thêm luồng/lớp mới (điền trong PR)
| Biện pháp | bấm tay | autopilot | v2 cảnh | v3 từng shot | multi-shot | nhân bản | chạy lại Director | test |
|---|---|---|---|---|---|---|---|---|
| Ảnh tham chiếu nhân vật đúng người/đúng look | | | | | | | | |
| Hồ sơ chuẩn/Lock đúng nguồn, sinh lại khi nguồn đổi | | | | | | | | |
| Cỡ cảnh/khung cắt trong prompt ảnh | | | | | | | | |
| Luật chọn model (≥ 3 người, look in-game → Kling…) | | | | | | | | |
| Cổng Bible / storyboard / không tự duyệt dưới sàn | | | | | | | | |
| Gen lại phải đổi đầu vào, tối đa 2 lần | | | | | | | | |
| Sổ chi + trần + ước tính trước | | | | | | | | |
| Giữ phần người sửa tay | | | | | | | | |
