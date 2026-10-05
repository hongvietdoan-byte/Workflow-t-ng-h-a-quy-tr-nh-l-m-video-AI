# Thứ tự ưu tiên cảm xúc (trục Murch) — thang chung khi phải đánh đổi

> Nguồn: tách từ `knowledge/editor/editing.md` mục E1 "Nghệ thuật cắt" (Walter Murch "Rule of Six" — `knowledge/sources.md` [E1], [Đ12];
> đọc qua bài tóm lược, độ tin trung bình). Ở đó là thứ tự ưu tiên của **một điểm cắt**; file này mở phạm vi cho **Đạo diễn** (Bước 1) và **người viết
> motion prompt** (Bước 3) dùng chung một thang khi các yêu cầu đá nhau. Không chép lại phần còn lại của E1 — đọc E1 khi cần chi tiết dựng.
> Đây là **gợi ý có lý do**, không phải trần số: các con số % là trọng số Murch tự đặt để nói "cái nào nặng hơn", không phải điểm phải đạt.

## Thang (nặng → nhẹ)
1. **Cảm xúc** (Murch: 51 %) — người xem cảm thấy đúng điều khoảnh khắc này cần chưa?
2. **Câu chuyện** (23 %) — khoảnh khắc có đẩy truyện đi tiếp, người xem có hiểu chuyện gì vừa xảy ra?
3. **Nhịp** (10 %) — có rơi đúng lúc, đúng độ dài so với cụm shot quanh nó?
4. **Hướng mắt** người xem (7 %) — mắt người xem đang ở đâu trong khung, có bị kéo đi lạc?
5. **Mặt phẳng 2D** / trục (5 %) — hướng nhìn, hướng chuyển động trái/phải có giữ đúng?
6. **Liền mạch không gian 3D** (4 %) — vị trí, khoảng cách thật giữa người và vật.

Câu gốc giữ nguyên: **cảm xúc nặng hơn năm tiêu chí còn lại cộng lại; phải hy sinh thì bỏ từ dưới lên.**

Ràng buộc đã có, giữ nguyên: **ở khâu dựng, cảm xúc đứng dưới điều kiện nghe rõ thoại và đọc được chữ** (`editing.md` tầng 4) — không cắt
cho "đẹp nhịp" mà làm cụt câu hay mất chữ. Thoại nguyên văn và luật của nhà cung cấp (giới hạn model) là **điều kiện**, không nằm trên thang.

## Dùng thế nào
- **Chỉ dùng khi có đánh đổi thật.** Không có xung đột thì làm đủ cả sáu; thang chỉ nói *bỏ cái nào trước* khi không giữ được hết.
- **Bỏ từ dưới lên, và ghi lý do.** Ví dụ: shot phản ứng cần giữ mặt lâu cho người xem thấm (cảm xúc) nhưng làm lệch nhịp cụm → giữ mặt, ghi
  vào `tradeoffs` (Đạo diễn) hoặc `check_flags` (motion) điều đã hy sinh và vì sao.
- **Thang không gán nghĩa cho kỹ thuật.** Nó không nói "cận mặt = cảm xúc" hay "máy tĩnh = căng thẳng"; cùng một cú máy có thể phục vụ ý đồ
  khác nhau tùy cảnh. Thang chỉ xếp **mục tiêu**; chọn kỹ thuật nào để đạt mục tiêu vẫn là quyết định của cảnh, ghi `why`.
- **Bước 3 (motion):** khi yêu cầu chuyển động đá nhau (diễn xuất vs máy di chuyển vs giữ bố cục nền), giữ thứ phục vụ cảm xúc của shot
  trước; liền mạch không gian 3D (đường máy phức tạp, vòng cung, parallax) hy sinh trước tiên — nó cũng là thứ model I2V làm hỏng nhiều
  nhất (`knowledge/i2v_motion_discipline.md`).
- **Bước 1 (Đạo diễn):** thời lượng, số shot, tiền video là ràng buộc; trong khung đó, cảm xúc của khoảnh khắc chính được giữ trước
  câu chuyện phụ, nhịp đẹp và độ chính xác không gian.

## Căn cứ
- Murch: thứ tự và trọng số do ông đặt ra để quyết khi phải hy sinh, không phải công thức chấm điểm.
- Pipeline: tổng kết #8 (`docs/TONG_KET_DU_AN_8_2026-09-28.md` lỗi 1.9) — lỗi nặng nhất người dùng nêu là truyện cụt, cú ngoặt không có
  thiết lập (câu chuyện / cảm xúc), không phải độ chính xác không gian.
