# Knowledge pack — Lỗi thường gặp của ảnh AI và cách sửa (v0.1, dùng cho QC Agent và người duyệt)

| Lỗi | Dấu hiệu | Cách sửa trong prompt gen lại |
|---|---|---|
| Tay/ngón sai | thừa/thiếu ngón, tay dính vào vật | mô tả tay cầm gì ("right hand holding a sword hilt"), giảm chuyển động, cỡ cảnh xa hơn |
| Mặt méo/không nhất quán | mắt lệch, mặt khác giữa các cảnh | lặp nguyên văn mô tả khuôn mặt từ Character Bible; dùng close-up/medium thay vì wide |
| Đổi trang phục | áo/giáp khác màu giữa các cảnh | nêu màu và chất liệu trang phục trong mọi prompt của nhân vật |
| Thừa người | xuất hiện người lạ | thêm "only one person"/"exactly two people"; "no extra people" |
| Chữ/logo lạ | ký tự vô nghĩa trên biển hiệu | thêm "no readable text, no logos"; giảm biển hiệu trong khung |
| Sai bố cục | cỡ cảnh/góc máy không đúng thông số | nêu rõ "wide shot"/"low angle" ở đầu prompt |
| Sai ánh sáng/mood | cảnh đêm nhưng sáng như ngày | nêu nguồn sáng ("cold moonlight from the left") và giờ trong ngày |
| Vật thể hợp nhất | vũ khí dính vào người/nền | tách bằng ánh sáng viền, mô tả vị trí rõ |
| Quá tối | mất chi tiết | thêm nguồn sáng nhỏ chiếu lên chủ thể ("faint rim light on face") |
| Trùng IP | giống nhân vật nổi tiếng | mô tả lại nguyên bản (bỏ vòng tay/dây/khiên đặc trưng), đổi màu chủ đạo |

## Quy tắc chấm điểm gợi ý (thang 0–1 cho từng tiêu chí trong `data/qc_checklist.json`)
- 0.9–1.0: không có lỗi nhìn thấy; 0.7–0.89: lỗi nhỏ không ảnh hưởng ý nghĩa; 0.4–0.69: lỗi rõ, cần gen lại; <0.4: sai nghiêm trọng.
- Mỗi điểm dưới 0.9 phải kèm một mục cụ thể trong `issues` (dạng "hands: extra finger on left hand") để đưa vào prompt gen lại.
