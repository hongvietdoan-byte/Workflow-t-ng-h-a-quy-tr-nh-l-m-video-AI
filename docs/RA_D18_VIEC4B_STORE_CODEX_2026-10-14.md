# RÀ KỸ độc lập Đ18.4b STORE — sửa gom 14/10/2026

Nhánh codex/d18-viec4b-store; base 2c605888 + dependency4a23b9fa51 cherry-pick50ccc97b. Reviewer không xây 4b; chỉ nạp store/tests/schema/resolver/protocol/diff flags/areas và related_areas. Đã báo HẾT danh sách cho root trước sửa. Không commit/push/TODO/PLAN/main/live/API/data thật.

## Finding, cách sửa và regression (dòng theo file sau sửa)

1. P1 opt-in truthy bypass: core/stage_registry_store.py:96 — đổi gate thành opt_in is True, giữ đọc feature mỗi operation. test_review_optin_exact_true + disable giữa constructor/call; preset experimental vẫn OFF.
2. P2 replay unlock lấy body head mutable: store:320/352 — hash command undo/unlock (kind/id/CAS/target/path/reason), apply giữ body caller trong intent; ACL fresh trước replay. test_review_unlock_retry_after_later_edit; existing actor collision/revocation và undo retry giữ nguyên.
3. P2 bỏ provenance âm thầm: store:369 — payload apply khác provenance hiện tại bị từ chối; undo/unlock giữ provenance head. test_review_provenance_not_silently_dropped.
4. P2 lock giả author/time, path không thật; indexed diff quá rộng: store:75/371 + core/stage_registry_schema.py:109 — stamp lock mới theo actor/time server, validate actual path/index, list diff từng index kể cả append/truncate. test_review_lock_author_is_server_and_path_exists, invalid_lock_target_rejected, append_outside_indexed_lock, duplicate_unlock_sanitized. Không có automatic unlock; existing lock map chỉ đổi qua explicit unlock/edit ACL.
5. P2 schema guard thiếu constraints/trigger body, head thiếu/nonlatest: store:106/172/186 — canonical DDL constraints, đúng đủ 6 append-only triggers, reject extra triggers; head phải phủ aggregate và latest contiguous 1..N, body metadata/parent đúng PK. test_review_schema_and_head_corruption 4 ca + unknown_trigger_rejected_before_write. Bootstrap rõ trong tx; không auto DDL/read migration.
6. P2 corrupt JSON/metadata reads và SQL errors: store:51/60/135/259/409/430 — JSON duplicate keys/nonfinite/invalid Unicode bị reject; metadata đúng shape/project/operation/pins, request/audit/outbox có bounds; owned tx SQL lỗi rollback và sanitize, borrowed reads không commit/rollback caller. test_review_corrupt_metadata_reads 3 bảng (restore trigger trước đọc để test validator thật), stored_json_strict, cycle_alias_and_unicode_rejected, borrowed_read_preserves_pending.
7. P2 I/O/memory history trước budget, FK all inactive history chặn việc mới: store:167/217/242 — preflight COUNT/bytes, cap 5000 revisions/16MB + metadata10000; semantic materialize active/projected/exact-pin closure, external scope chỉ candidate live closure; write không được vượt trần đọc. History giữ metadata và pins sau detach, không delete. test_review_history_bound_before_load, inactive_source_does_not_block_new_stage, old_snapshot_survives_asset_detach, new_live_source_must_be_attached, proposed_history_limit_no_unreadable_commit.
8. Hardening test-only fault: store:316 — production _point no-op, không runtime callback; fake tests monkeypatch _point giữ injection đủ revision/head/audit/outbox/request. test_review_future_callback_attribute_has_no_production_effect và existing test_fault_atomic.

9. P2 root đọc lần2 phát hiện metadata chỉ kiểm dung lượng hiện tại: store:382 — tạo saved_json trước mọi phase ghi, kiểm +1 count và +saved_bytes cho cả requests/audit/outbox trước INSERTrevision. Không commit kết quả khiến reads/retry vượt cap. test_review_projected_metadata_bytes_before_commit 3 bảng dùng fake JSON padding hợp lệ sáttrần; **3 RED/1.39s →116 GREEN/5.89s**. Root cho thêm run có lý do sau finding mới; không nới test. Ack kiểm SQLite int0/1.

## Bằng chứng

- Builder3 lượt đã ghi trong Kết quả/HANDOFF; root baseline **82 passed/1.94s**.
- Reviewer3 lượt: collection quote error trong SQL fixture → sửa bằng parameter, **20 failed +84 passed/4.13s (ĐỎ thật)** → **113 passed/4.44s (XANH)**.
- Lệnh: py -m pytest -q tests/test_stage_registry_store.py tests/test_stage_registry_schema.py tests/test_stage_registry_resolver.py --tb=no -p no:cacheprovider. Không nới test, không broad/fullsuite.
- Root đọc lần2: finding9 được root yêu cầu sửa thêm; 2 lượt narrow được phép (3 RED mới → **116 passed/5.89s**). Tổng reviewer5 lượt gồm3 lượt vòng gom ban đầu +2 lượt finding root mới; không giấu lượt collection error.
- git diff --check sạch ngoài CRLF warning. tests patch.object thay OBJECT os.environ dict fake trước imports/calls/thread work; fake SQLite/assets/users/flags. Không đọc/in/assert env/header/token/credentials hoặc showlocals.
- related_areas (chạy dưới fake env) báo plates3d/coreinfra + assets/step1/2/3/4/5/autopilot/budget/diag/knowledge/lipsync/dashboard dictionaries. rg xác nhận chưa caller StageRegistryStore ngoài module; feature metadata mới OFF/OPT_IN_ONLY, không thay hành vi caller cũ. Slow/fullsuite bắt buộc khi integration, chưa chạy nhánh.
- New store/test đã khai areas, version **80** giữ. Root phải đọc diff sửa lần2 trước commit.

## Domain và giới hạn còn mở

- look_id=None không thuộc nullable wire: schema4a yêu cầu numeric/pair đúng; valid look pin mới bị gate do mapping chưa chốt.
- look_id mapping chưa được người dùng chốt; không tự coi là assets hay 1 asset_images. Candidate write có look pin **explicit fail closed** (test_review_pending_look_mapping_fails_closed), history metadata giữ pin. Không claim hoàn tất domain Kho.
- assets chưa có backing revision table: asset_revision hiện pin metadata khai báo, membership/ownership kiểm thật trên fake DB; chưa chứng minh physical immutable bytes/source version. Pin ảnh/hash + adapter/domain cần user chốt, không tự tạo schema Kho/migration4c.
- SQL transaction/CAS atomic áp dụng các service operation trên connection riêng; direct DB writer có quyền drop triggers/DDL có thể phá store, service chỉ fail closed khi quan sát schema/head mismatch. Caller giữ connection chỉ cho một thread; không giả CAS ngoài SQLite.
- Bounded preflight vẫn quét metadata history; closure giảm materialization history nhưng chưa benchmark 4–5 projects/editor mouseup. Vượt cap trả lỗi rõ, chưa pagination/archive4c.
- User None/local giữ trusted-system semantics access hiện có, không thêm bypass locks; edit watcher được unlock workflow theo protocol, không quyền manage toàn Kho.
- Chưa dữ liệu thật/caller/UI/renderer/paid provider/fullsuite Windows; chưa nghiệm thu ảnh/video hoặc domain bộ dạng.
