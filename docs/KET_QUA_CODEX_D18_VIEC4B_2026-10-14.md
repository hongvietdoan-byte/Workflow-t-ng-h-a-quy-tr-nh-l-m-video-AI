# Kết quả Codex Đ18 — việc 4b STORE (14/10/2026)

Phạm vi code/service fake-data, chi phí 0 USD; nguồn duy nhất SQLite manifest
qua p.conn. Chưa integration main, production QA, migration dữ liệu thật,
caller/UI/provider/model/render hoặc fullsuite Windows.

## Bằng chứng

ĐỎ module chưa tồn tại: 1 failed, 16 errors, 53 passed, 1.79s.
Lượt 2: 69 passed, 1 failed, 1.39s: indexed lock schema dependency.
Lượt 3: 79 passed, 1 failed, 3.53s: retry unlock hash envelope reason.
Sau lượt 3 sửa hash exclude reason server và bỏ constructor enabled override;
root xác nhận baseline **82 passed/1.94s**. Rà độc lập sửa gom: reviewer3 lượt
(collection-error quote →20RED/84GREEN →**113 passed/4.44s**), không nới test.
RA: docs/RA_D18_VIEC4B_STORE_CODEX_2026-10-14.md; root đọc fix lần2 trước commit.

## Tự rà 2b.5

- Quyền: reuse need_view/need_edit; real fake projects/watchers kiểm creator,
  owner, edit, view, denied; actor trusted server, retry recheck edit ACL.
- Dữ liệu/transaction: BEGIN IMMEDIATE, CAS touched đầy đủ, crash hook từng
  bước, hai connection file race một thắng; outer writes bị reject trước
  mutation; reads pinned transaction và không commit caller.
- Khóa: map cũ không tự clear; diff ancestor/index; system không bypass;
  unlock edit + lý do + audit; undo revision mới giữ locks/provenance.
- Scope: FK scenes/project_assets/assets private, no latest fallback;
  history/head/snapshot/request/audit/outbox cùng project ACL.
- Tiền/callers: không model/provider/network, outbox metadata only;
  feature OFF opt-in, không startup migration/caller/dashboard.
- Security test: patch.object thay object os.environ dict fake trước import
  và call; không clear env thật, không dashboard.env/data thật/secret logs.
- Giới hạn: all-history validation theo budget; chưa benchmark; SQLite
  trigger/service guard không thay bảo vệ filesystem hay quyền truy cập DB.
- Đã RÀ KỸ độc lập + sửa gom; còn root đọc diff lần2 + fullsuite Windows trước integration.
- CHỜ domain bộ dạng/pins ảnh/hash: write có look_id explicit gate, không tự mapping Kho; asset_revision chưa backing physical version, chưa đóng nghiệm thu domain.


Sau rà: gate exact True; lock server metadata/actual path/index diff; replay command
sau later edit; provenance khác bị reject; schema constraints/trigger/head integrity;
JSON/metadata/SQL sanitize; bounded preflight + exact dependency closure; historical
metadata không bị detach nguồn làm hỏng, candidate live vẫn kiểm source mới. Fault
production no-op, tests monkeypatch đủ5phase; toàn bộ 113 target xanh. areas80 giữ,
không caller/store startup DDL. Giới hạn và domain còn mở xem RA/protocol.


Root đọc lần2 phát hiện projected metadata bytes chưa cộng result mới; đã sửa
pre-write guard cả3bảng. Hồi quy sáttrần JSON padding hợp lệ: **3RED/1.39s →
116passed/5.89s**, 2lượt narrow thêm được root cho phép vì finding mới. Kết quả
cuối kỹ thuật116target xanh; domain bộ dạng/pins/hash vẫn CHỜ, không claimđóng.
