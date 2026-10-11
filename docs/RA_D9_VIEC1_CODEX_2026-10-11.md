# Rà Đợt 9 việc 1 — kho phiếu

11/10/2026 · nhánh `codex/d9-viec1-kho-phieu`, base `f7c423` · chưa commit/gộp.

Rà độc lập theo HANDOFF, CODEX_TASKS Đ9 việc 1 và THIET_KE_TIEU_NHI_LAO_DAI_D7 mục 2/4. Nhóm ban đầu: 16 passed / 0,84s, gồm SHA ảnh ghi đè.

## Ba lỗi đã sửa cùng một vòng

- P1 transaction: ba mutator dùng `with conn` commit/rollback cả transaction caller. Chuyển sang SAVEPOINT riêng: ticket + event + audit nguyên tử; RELEASE tự commit khi không có transaction ngoài, giữ quyền commit/rollback cho caller khi đã có transaction.
- P1 snapshot: ảnh mất/quyền đọc lỗi hoặc package/refs sai kiểu gây exception ngoài catch. Kiểm kiểu dict/list, bắt lỗi đọc/hash từng dự án, warning đã lọc và bỏ gen_done của dự án đó; tiếp tục snapshot không ghi DB.
- P2 bằng chứng: đường dẫn `C:/...` và `//server/share/...` lọt bộ lọc. Chuẩn hóa slash khi kiểm drive/UNC; giữ relative refs và SHA.

## Bằng chứng kiểm

Thêm 11 ca: 3 mutator giữ transaction caller; audit failure rollback riêng phiếu/events; 2 dạng đường dẫn; 5 dạng bằng chứng hỏng (missing, permission, package list, refs null, refs object) trên connection query_only.

Lần đầu đỏ 11 / xanh 16, trong đó 5 fixture snapshot thiếu created_at. Sửa fixture NOT NULL rồi chạy đỏ lại đúng lỗi production: 11 failed / 16 passed / 1,46s. Sau sửa production: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_tickets.py` → **27 passed / 1,10s**. Không nới assertion cũ.

Tự rà diff: schema CREATE IF NOT EXISTS không phá bảng cũ; event UPDATE/DELETE có trigger chặn; CAS revision bảo vệ merge/chuyển/gia hạn; state code/budget/shared_asset tách đúng; Identity Owner phải được caller resolve từ session server; projection fail closed theo project; fingerprint gồm project; UTC/due gốc không đổi; snapshot không import runner, không khởi tạo bảng hold/ledger, pending_unknown vẫn True; gen_done kiểm motion + SHA approved image và không job đang hoạt động. Ba sửa không đổi schema/feature/snapshot fields.

Không full suite, API, dữ liệu thật, env, TODO/PLAN, file #24, commit hoặc push. Cả bộ Windows và bước gộp do phiên điều phối thực hiện. Snapshot v1 đủ bàn giao cho Đ9 việc 2/3 trong phạm vi hợp đồng hiện tại; không chứng minh gen/render sản xuất hay ACL adapter tương lai.
