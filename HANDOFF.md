# Đ13 việc 4 mục 4 — tối ưu chỉ mục nhóm

Code a4a9dc83, nhánh codex/d13-viec4-cost-nhom. Chỉ cost + test/areas; giữ version72.
133 test +6 subtest xanh; rà độc lập 1P2 SAVEPOINT đã sửa với 3ca đỏ→xanh, nhóm28test3,88s.
Root đọc diff vòng sửa trước commit; 99shot/20nhóm1query/20parse/99members, quote oracle byte-identical.
Đang transaction luôn đọc mới; ngoài transaction tối ưu theo project. Không thay logic budget đã gộp.
Chưa cả bộ Windows/ca production/main/live/API. Xem RA_D13_VIEC4_COST_NHOM_CODEX_2026-10-13.md.
Bước kế: bên tích hợp rà/chạy cả bộ -n8 trước gộp; không cherry-pick lại các phần Đ13v4 cũ.
