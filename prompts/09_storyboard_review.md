# Rà storyboard (previz 2D)

Ảnh đính kèm là **storyboard** của cả video: mỗi ô là layout của một shot theo thứ tự, chú thích dưới ô ghi số cảnh và nhóm cảnh. Người được vẽ bằng hình nộm màu (hoặc ảnh tách nền) có tên. Hãy rà như một script supervisor/biên tập dựng phim và chỉ ra **lỗi liên tục và lỗi bố cục** trước khi gen ảnh thật. Chỉ trả về **một JSON hợp lệ**, không giải thích.

## Kiểm tra
- **Trục 180° / hướng màn hình** trong cùng nhóm cảnh: người đổi bên trái/phải khung mà không có lý do; hướng di chuyển bị đảo giữa hai shot liền nhau.
- **Liên tục vị trí**: người biến mất/xuất hiện vô lý, nhảy chỗ giữa hai shot liền nhau cùng nhóm.
- **Bố cục**: người quá sát mép, bị cắt đầu/chân không chủ ý, chồng lên nhau, đứng lên vật (tường, mái), quá nhỏ/quá to so với cỡ cảnh ghi trong chú thích.
- **Nhịp hình ảnh**: nhiều shot liền nhau cùng một cỡ cảnh/góc máy gây nhàm (chỉ ghi khi rõ ràng).
- Không bắt lỗi màu sắc/chất lượng ảnh nền (đây chỉ là layout).

## Định dạng
`ok` = true khi không có lỗi đáng sửa. Mỗi lỗi: `idx` (số cảnh), `problem` (tiếng Việt, ngắn), `fix` (tiếng Việt, cụ thể: ai chuyển sang đâu, đổi hướng nhìn thế nào).
```json
{"ok": false, "issues": [{"idx": 3, "problem": "", "fix": ""}]}
```
