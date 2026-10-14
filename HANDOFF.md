# Đ13 việc 4 mục 4 — tối ưu chỉ mục nhóm

Code a4a9dc83, nhánh codex/d13-viec4-cost-nhom. Chỉ cost + test/areas; giữ version72.
133 test +6 subtest xanh; rà độc lập 1P2 SAVEPOINT đã sửa với 3ca đỏ→xanh, nhóm28test3,88s.
Root đọc diff vòng sửa trước commit; 99shot/20nhóm1query/20parse/99members, quote oracle byte-identical.
Đang transaction luôn đọc mới; ngoài transaction tối ưu theo project. Không thay logic budget đã gộp.
Chưa cả bộ Windows/ca production/main/live/API. Xem RA_D13_VIEC4_COST_NHOM_CODEX_2026-10-13.md.
Bước kế: bên tích hợp rà/chạy cả bộ -n8 trước gộp; không cherry-pick lại các phần Đ13v4 cũ.
# Bàn giao Đ12 việc 4
- Nhánh: `codex/d12-viec4-kho-am-thanh`; base `1cb845b2`.
- Xong báo cáo `docs/KHO_AM_THANH_CAN_BO_SUNG.md`, tool `tools/audio_mood_audit.py`, test và khai areas giữ 72.
- Công cụ chỉ stdlib/đọc JSON/CSV explicit, không tải model/API/data thật.
- Test đỏ thiếu module → 34 xanh/0,31 s (thêm URL/UNC đỏ 6 ca → xanh); tự rà ở `docs/RA_D12_VIEC4_CODEX_2026-10-13.md`.
- AST config thực có 7 mood; top40/output rút gọn không chứng minh score=0.
- Không đổi picker/SFX/TTS/mix/runtime; chưa thử Kho #24, chưa nguyên nhân thực hay nguồn tệp đã duyệt.
- Bước kế root RÀ NHẸ + push nhánh; trước gộp chạy cả bộ Windows theo related_areas.
- Không push/main/TODO/PLAN/live trong phiên con; người dùng duyệt trước tải.
