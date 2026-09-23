# QC đồng bộ cả bộ ảnh (Bước 2 · 🎨 Kiểm tra đồng bộ cả bộ ảnh)

Đính kèm MỘT tấm ghép các ảnh đã duyệt của dự án, theo thứ tự cảnh, mỗi ô có nhãn "S01", "S02"…; kèm World Bible và danh sách cảnh (nhóm cảnh, địa điểm, giờ).
Rà theo knowledge/set_consistency_qa.md (dấu vân phong cách + 3 lớp: trung thành tham chiếu, đồng bộ cả bộ, dùng được). Các cảnh cùng nhóm/cùng địa điểm và giờ phải liên tục về ánh sáng, màu, phong cách; một nhân vật phải trông giống nhau ở mọi ô.
Chỉ nêu cảnh lệch rõ ràng (ngoại lệ so với cả bộ), không bắt lỗi vặt. `fix`: câu mệnh lệnh tiếng Anh đưa thẳng vào lần gen lại ảnh đó.
Chỉ trả về **một JSON hợp lệ**:
```json
{"ok": true, "summary": "", "issues": [{"idx": 3, "problem": "ánh sáng ban ngày trong khi cả nhóm là đêm", "fix": "Night scene lit by ..."}]}
```
