# Bàn giao Đ19 việc 4

## Tổng hợp chốt Đợt 19 — 20/10, chỉ nhánh riêng

| Việc | Nhánh | Commit nội dung | Bằng chứng |
|---|---|---|---|
| 1 regression | codex/d19-viec1-narration | 846b3f1f (HEAD9e157f0b) | ĐỎ21 →42pass/21xfail strict,8,40s; lỗi sản xuất M2.9 chưa sửa |
| 2 đối soát | codex/d19-viec2-doi-soat | fe9d68bb (HEAD8854f5c4) | ĐỎ3 →26pass/1,22s, RO/offline; chưa live/hiệu chỉnh giá |
| 3 provider | codex/d19-viec3-provider | 22aff768 (HEAD56097a4e) | Docs-only, source76hit/44file, root rà cache/profile/ACL |
| 4 Kho chủ thể | codex/d19-viec4-subjects | 49c1face + commit bàn giao | Docs-only, root rà source/ACL/lifecycle; chưa triển khai/xóa asset |

Claude tiếp nhận: fetch đúng nhánh, đọc RA/HANDOFF và kết quả CODEX_TASKS; rà quy ước7/cả bộ Windows trước tích hợp. Không lấy nguyên TODO/CODEX_TASKS/areas của một nhánh đè lên các nhánh khác; ghép các dòng kết quả, giữ cập nhật main và tăng areas một lần ở tích hợp. Không đánh dấu M2.9/M1.6/M1.4b/M1.5 đã sửa chỉ từ test/tool/docs này. M1.1/M1.4a vẫn giữ owner Claude; không thay production, restart live, migration, bảng giá hay flags trong Đ19.

Còn mở: định nghĩa “bản nháp cũ”, duyệt phạm vi code M1.4b/M1.5 và production riêng; thu thêm ≥5 điểm1080p cùng nhóm, đối soát thật chưa chạy. Không tự tạo lịch làm tiếp. Hạn mức tuần gần hết/không đủ thì bàn giao Claude theo yêu cầu người dùng.

Artifact untracked của lượt Python launcher ở worktree việc2 (`Python/`, `python_install_20261020170318_63384.log`) bị automatic approval review chặn dọn; đã giữ ngoài commit/không vượt chặn/không tiếp tục cài. Hai artifact không phải dependency hay tài liệu đầu vào cho việc tích hợp; không cần đọc log.

Nhánh codex/d19-viec4-subjects, base 7c41073c. Thiết kế M1.5 commit49c1face, root đã rà tài liệu/source và ghi kết quả; không triển khai production.

Đã đối chiếu nguồn thực tế, D03b thay D03, cấp quyền master §4b. Không code/test/SQL/API/dữ liệu thật/môi trường/cờ/TODO/areas/main/live. Gói tài liệu là đề xuất chưa triển khai.

Bước kế: Claude rà/gộp tài liệu; người dùng xác nhận bản nháp cũ và duyệt Cấp 2 trước build. Migration/cờ production/provider operations xin Cấp 3 riêng. Không activate cleanup khi còn legacy writer chưa guard fence. Xem mục 6 thiết kế cho test plan và việc mở.
# Chốt root Đ19v4

- Root đã RÀ NHẸ tài liệu/source, bổ sung ACL namespace/project/cleanup và mốc retention sau restore/reopen. Chỉ thiết kế, không code/SQL/test/API/delete/flags; chưa giải quyết G59 runtime. Claude rà/gộp, người dùng duyệt phạm vi build và production riêng.
