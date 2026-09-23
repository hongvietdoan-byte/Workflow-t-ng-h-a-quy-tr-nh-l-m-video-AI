# Rà motion prompt (Bước 3 · 🔍 Rà motion prompt)

Rà từng motion prompt theo checklist knowledge/motion_prompt_lint.md (ý đồ, nhất quán thực thể, blocking, đạo cụ, máy quay, thời gian, ngôn ngữ, model đọc được không). Cảnh `camera_complexity: "complex"` BẮT BUỘC qua 4 kiểm tra mơ hồ: tỉ lệ, vị trí, đường máy, mốc thời gian.
Mỗi cảnh ghi `video_model` (model sẽ dùng) — mục "Seedance đọc được không" chỉ áp cho cảnh Seedance.
Cảnh đạt thì `ok: true` và không cần bản sửa. Cảnh có lỗi: liệt kê lỗi cụ thể (tiếng Việt) và viết `revised_prompt` (cùng ngôn ngữ với prompt gốc) giữ nguyên ý đồ, chỉ sửa chỗ lỗi, trong giới hạn độ dài của model.
Chỉ trả về **một JSON hợp lệ**:
```json
{"scenes": [{"idx": 1, "ok": false, "issues": ["Đường máy: chưa nói điểm kết thúc"], "revised_prompt": ""}]}
```
