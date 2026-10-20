# Bàn giao Đ19 việc 4

Nhánh codex/d19-viec4-subjects, base 7c41073c. Chỉ tạo thiết kế M1.5 và báo cáo rà trong docs; chưa commit/push theo đề bài.

Đã đối chiếu nguồn thực tế, D03b thay D03, cấp quyền master §4b. Không code/test/SQL/API/dữ liệu thật/môi trường/cờ/TODO/areas/main/live. Gói tài liệu là đề xuất chưa triển khai.

Bước kế: phiên chính rà tài liệu; người dùng xác nhận bản nháp cũ và duyệt Cấp 2 trước build. Migration/cờ production/provider operations xin Cấp 3 riêng. Không activate cleanup khi còn legacy writer chưa guard fence. Xem mục 6 thiết kế cho test plan và việc mở.
# Chốt root Đ19v4

- Root đã RÀ NHẸ tài liệu/source, bổ sung ACL namespace/project/cleanup và mốc retention sau restore/reopen. Chỉ thiết kế, không code/SQL/test/API/delete/flags; chưa giải quyết G59 runtime. Claude rà/gộp, người dùng duyệt phạm vi build và production riêng.
