# #31 — Rà đầu vào gen ảnh + motion (0 USD, 16/10)

Cách rà: `tools/replay_payload.py --project 31` dựng lại ĐÚNG gói mà job ảnh sẽ gửi model (prompt cuối + ảnh tham chiếu), trên bản sao dữ liệu, không gọi model. 36 shot (kịch bản sửa v2, Đạo diễn chạy lại 16/10).

## Kết luận nhanh
- **Motion prompt: CHƯA CÓ** — viết sau khi ảnh khung đầu được duyệt (job cũ đã xóa khi Làm lại). Rà lại khi có ảnh.
- **Ảnh: 6 nhóm lỗi**, chưa nên gen trước khi sửa.

## Lỗi theo nhóm (SAI → cách sửa)

| # | Shot | SAI | Lý do | Cách sửa |
|---|---|---|---|---|
| 1 | tất cả 36 | Prompt có đoạn **tiếng Việt** | Nhãn chỗ đứng Kho (vd "góc nhìn thứ nhất Kelly — thấy CẢ 2 cửa… máy tại 'at' cao mắt 1,55 m…", "cận cửa 2 … máy đi vào cửa") bị chép nguyên vào câu "Setting:" — model ảnh đọc ghi chú máy quay tiếng Việt | Sửa code: câu Setting dùng mô tả tiếng Anh của chỗ đứng (hoặc bỏ ghi chú máy), không chép nhãn Kho |
| 2 | 10–15 | Tóc Kelly **"black chin-length bob"** | Kho Kelly: tóc **nâu sẫm** (dark brown); prompt_formula đã cảnh báo brown ↔ black | Sửa prompt 10–15 về "dark brown" (một nguồn: hồ sơ Kho) |
| 3 | 32 | Keo tả **"patterned skin… just starting to rise"** | Quyết định 13–14/10: skin **thang máy** = dạng (b) Kho #367, tường **CONG, xuất hiện ngay**, không mọc; ảnh Kho #367 không được gửi kèm | Sửa prompt: skin thang máy, tường cong hai đầu về phía người ném, đã đứng sẵn; gắn ảnh Kho #367 (variant b) |
| 4 | 4, 34 | **Không có ảnh nền 3D** | Máy nền lọt ngoài phòng (4) / bị giữ (34) → nền vẽ tự do | Chờ sân khấu 3D đặt lại máy rồi render lại nền |
| 5 | 14, 15, 33 | **Ảnh render 3D không gửi được** (missing_reference) → quay về tả nền bằng chữ | Shot có máy sân khấu bị giữ / chưa có nền khớp | Như #4 — sau sân khấu 3D + render lại |
| 6 | 36 (hậu kỳ) | HUD xếp hạng Kho #446 vẫn là **"#48/50"** | Kịch bản mới 15/15 | Làm HUD mới "#15/15 ĐỪNG ĐẺ TRỨNG NHÉ!" (ghép hậu kỳ) |

## ĐÚNG (đã kiểm)
- Shot 1–3 POV không có Kelly (đúng góc nhìn thứ nhất); 4 trở đi có ảnh Kelly ×2 (bộ chuẩn + 3D).
- Dạng bóng mờ (ghost) đúng cảnh song song: 6–18, 23–29 (27–29 đầu cảnh 7 còn bóng mờ, 30 chuyển về thực tại); cảnh 5 và 8 hình thường (shot 32 chữ "translucent" là tường keo, không phải Kelly).
- Đạo cụ: cũi #442 ở cảnh 2–3, SKORP từ shot 10, xác bay #443 cảnh 6, AWM cảnh 7; địch đúng người ở 14–16, 30, 31–36.
- Ảnh toàn cùng trục gửi kèm ở các shot ngoài trời có nền.

## Việc kế
1. Sửa code nhóm 1 (tiếng Việt trong Setting) — giao phiên code.
2. Sửa chữ shot 10–15 (tóc) + 32 (keo) trên Dashboard; gắn Kho #367 cho 32.
3. Sau sân khấu 3D (ngoại tuyến) → render lại nền → chạy lại rà này → mới gen ảnh.
4. HUD 15/15 cho hậu kỳ.
