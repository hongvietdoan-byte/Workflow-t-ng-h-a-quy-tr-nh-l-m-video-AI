# Quy tắc nguồn thông tin nhân vật — một chủ cho mỗi loại thông tin (02/10/2026)

**Vấn đề:** thông tin một nhân vật nằm ở nhiều nơi (mô tả trong Kho, 3 khối tự động trong mô tả, Hồ sơ chuẩn, Lock của dự án, hồ sơ kỹ năng,
`knowledge/ff_character_skills_visual.md`), cập nhật vào lúc khác nhau nên "ai ghi sau thì thắng" làm đè và mâu thuẫn nhau.
**Nguyên tắc:** KHÔNG dùng thời gian cập nhật để phân thắng thua. Mỗi loại thông tin có đúng MỘT chủ; nguồn khác chỉ là đầu vào / nháp /
dự phòng và không ghi đè chủ.

| Loại thông tin | Chủ (nguồn duy nhất) | Nguồn khác chỉ là | Ai được ghi |
|---|---|---|---|
| Ngoại hình (tóc, mặt, từng món đồ + màu, phụ kiện, chiều cao, vóc dáng) | **Hồ sơ chuẩn đã duyệt** (`assets.profile`) | Nháp Claude soạn từ ảnh đã duyệt; Lock của dự án (bản sao, hồ sơ duyệt luôn thắng — đã có ở `standard_for`) | Người duyệt. Công cụ tự động chỉ tạo NHÁP, không bao giờ đè hồ sơ đã duyệt; sửa hồ sơ đã duyệt phải kèm lý do (đã có `history`) |
| Ảnh tham chiếu | Ảnh trạng thái **approved** + vai trò đã gắn | Ảnh từ đồng bộ thư mục / website / render 3D (vào "chờ duyệt") | Người duyệt |
| Hình dạng hiệu ứng kỹ năng | **Hồ sơ kỹ năng** `data/skills/<TÊN>` (xem video, người dùng xác nhận) | `knowledge/ff_character_skills_visual.md` (suy luận từ chữ — chỉ dùng khi chưa có hồ sơ kỹ năng); khối `[Phân tích video kỹ năng]` (nháp) | Dựng bằng `skill_dossier_build`, người dùng xác nhận |
| Cơ chế kỹ năng, tiểu sử, tính cách, Chủ động/Bị động | Khối **`[ff.garena.com]`** (chính thức; Chủ động/Bị động theo `isActive` của game) | — | Chỉ công cụ đồng bộ website, chỉ ghi khối của nó |
| Giọng | `data/voices_vi.json` | — | Người dùng |
| Tên gọi khác, ghi chú tay | Phần chữ của người dùng ở đầu mô tả | — | Người dùng |

**Ba khối tự động trong mô tả** (`[ff.garena.com]`, `[AI đọc ảnh]`, `[Phân tích video kỹ năng]`): mỗi công cụ chỉ ghi khối của mình và giữ nguyên
phần còn lại (`assets.replace_block`, 02/10 — trước đó mỗi công cụ cắt mô tả tại dấu của mình nên ghi khối `[ff.garena.com]` xóa mất hai khối
sau nó). Thứ tự khối cố định.

**Khi hai nguồn lệch nhau:** không tự chọn theo thời gian. Chủ thắng; nguồn lệch được hiện cảnh báo để người dùng quyết (sửa chủ nếu chủ sai).

**Đề xuất làm tiếp (chờ duyệt):**
1. Khi nhân vật ĐÃ có hồ sơ chuẩn duyệt, bản mô tả gửi Director bỏ khối `[AI đọc ảnh]` (ngoại hình lấy từ hồ sơ, không lặp, không lệch).
2. `🩺 Sức khỏe kho` thêm cột "lệch": hồ sơ nói một màu/món đồ mà khối `[AI đọc ảnh]` hoặc ảnh mới nói khác.
3. Khi hồ sơ kỹ năng có, bỏ đoạn kỹ năng tương ứng của `ff_character_skills_visual.md` khỏi prompt cho nhân vật đó.
