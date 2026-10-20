# Bàn giao ĐỢT 19 việc 3

## Chốt root — trạng thái mới nhất

Thiết kế commit `22aff768`, nhánh `codex/d19-viec3-provider`; source base7c41073c. Kết quả đã ghi CODEX_TASKS và TODO trên nhánh, chưa main; không coi đây là quyền triển khai M1.4b.

Root đã RÀ NHẸ độc lập source/tài liệu; thêm cache job/operation/profile, account rotation và ACL service vào đề xuất. Chỉ push nhánh, không code/SQL/test/API/migration hoặc nhận M1.4a của Claude. Docs-only không tạo test đỏ giả. Phạm vi code và production cần duyệt riêng; lỗi M1.4 chưa được coi đã sửa.

Nhánh `codex/d19-viec3-provider`, nền `7c41073c`; chưa commit theo chỉ đạo. Chỉ 3 file: thiết kế M1.4b, RA Đ19v3 và HANDOFF.md. Không areas/TODO/production/test/API/live.

Thiết kế đủ schema/revision/snapshot/legacy hold/factories+RPC/scope/cache/quota/ledger0USD/migration+rollback/testplan. Kiểm kê source76hit/44file; từng file:hàm:dòng trong phụ lục, image_block static phân biệt rõ. Không pytest vì docs-only.

Phiên kế: rà độc lập đặc biệt ma trận P/J/S, legacy NULL và down compatibility gate; gộp dependency M1.4a của Claude rồi quét lại source. Chỉ build sau duyệt Cấp2; migration/production/API cần Cấp3 riêng. Chưa triển khai M1.4b, chưa chạy migration hay xác minh runtime.
