# M1.5 — Thiết kế Kho chủ thể, 20/10/2026

Trạng thái: **đề xuất thiết kế Cấp 1, chưa triển khai, chưa thử thật**. Nguồn code đối chiếu tại `7c41073c`, nhánh `codex/d19-viec4-subjects`. Không thay code, CSDL, cờ, môi trường hay provider. D03b là chính sách, không phải quyền code/xóa; D03 cũ đã bị thay. Cấp 2 cần duyệt phạm vi build; migration, bật production, API/pilot cần Cấp 3 riêng theo master §4b.

> **Cập nhật C-FIX-D19 (cloud-B, 20/10)** theo rà C-RA-D19 + sổ `v31-cap3-items-decided-2026-10-20` (C3-3 CHỈ DUYỆT DRY-RUN):
> 1. **Mọi xóa asset = DRY-RUN + duyệt riêng TỪNG lần.** Thay đoạn "Apply sau phê duyệt production" (§4): không có scheduler / worker tự apply. Mỗi
>    `cleanup_plan` (bất biến, có `plan_hash`) cần NGƯỜI duyệt trên Dashboard (`approved_by`, `approved_at`, `plan_hash` khớp); apply chỉ nhận plan đã duyệt,
>    chưa hết hạn, fingerprint không đổi; một lần duyệt = một plan (không duyệt chung cho các lần sau). Tới khi người dùng đổi C3-3, code xóa chỉ chạy được
>    bằng nút duyệt của người. Test: `apply_refuses_unapproved_plan`, `apply_refuses_changed_plan_hash`, `approval_is_single_use`.
> 2. **Vô hiệu đường xóa tự động của cờ cũ `subject_auto_cleanup` TRƯỚC / CÙNG LÚC sửa G59.** Hiện tự dọn cũ (`core/subjects.py:run_auto_cleanup:396`,
>    gọi từ `schedule_auto_cleanup:432` ← `core/delivered.py:67`, `core/archive.py:65`) không xóa được CHỈ vì G59 ("chưa cấu hình Kho chủ thể"). Cờ có
>    `verified: True` (`core/features.py:47`) → sửa G59 đơn lẻ sẽ làm nó XÓA THẬT ngay khi giao / cất (không 3 ngày, không dry-run) — trái C3-3. Thiết kế:
>    cùng commit sửa G59, `run_auto_cleanup` chuyển sang chế độ CHỈ LIỆT KÊ: lập `cleanup_plan` (asset, dự án, lý do, phụ thuộc) + diag `subject_cleanup_plan`
>    + một dòng 📥 "chờ duyệt xóa", KHÔNG gọi `library.delete_many`; đường xóa chỉ còn qua apply plan đã duyệt (mục 1). Test bắt buộc ĐỎ→XANH:
>    `g59_fix_keeps_legacy_cleanup_dry_run` (provider Kho giả + cấu hình đủ → 0 lời gọi delete, có plan), `delivery_and_archive_never_delete`.
>    Không đổi giá trị cờ trên máy chính (Cấp 3); ghi quyết định khi người dùng chốt.
> 3. **Job không cần ảnh Kho không vào hàng chờ sức chứa (THẤP, D03b "chỉ chặn tác vụ thực sự cần Kho").** Gói không có ảnh nào cần Kho chủ thể (gen thẳng
>    không ref người / chỉ ảnh đánh dấu hợp lệ / Kling) → không xin reservation, không `QUEUE_CAPACITY`, gửi như thường. Test: `job_without_subject_refs_skips_capacity_queue`.


## 1. Bằng chứng và khoảng trống

Số **185 ảnh từng vào Kho, 95 khung đầu, #31 = 84** lấy từ audit `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md:132–134`; đây là số lịch sử trong sổ, không phải occupancy hiện thời. Phiên này không đọc DB thật và không đo lại. Giới hạn cơ sở hiện có là `LIBRARY_LIMIT = 100` (`core/adapters/clipai_subjects.py:28`); chưa có bằng chứng 4–5 dự án luôn vừa Kho, hay chia cứng 60 BỀN/40 TẠM là tối ưu.

| Nguồn thực tế: hàm:dòng | Hành vi và phần cần thay khi được duyệt |
|---|---|
| `core/subjects.py:picture_sha:124`, `picture_row:133`, `_save_picture:140`, `ensure_picture:168` | cache SHA toàn cục; processing ghi trước upload, tìm lại theo tên; non-timeout có thể quên attempt. Chưa có namespace và quan hệ nhiều dự án đầy đủ |
| `core/subjects.py:picture_refs:209` | all-or-nothing refs nhưng upload từng ảnh; lỗi trả None để caller dùng ảnh đánh dấu; cần giữ nguyên thứ tự mà chuyển sang QUEUE rõ ràng |
| `core/subjects.py:_projects_of_picture:244`, `library_overview:251` | suy dự án bằng tên/path đầu-cuối, đọc characters + deliveries; không đủ chứng minh mọi shared ref. failed phân loại trước in_use: không dùng category hiện tại làm quyền xóa |
| `core/subjects.py:delete_assets:303` | chặn in_use, gọi delete_many, rồi xóa cache/liên kết; chưa có fence new-ref/delete hay bảo vệ unknown đầy đủ |
| `core/subjects.py:rejected_frame_assets:351`, `_rejected_unused_frame:379` | suy job từ tên file; bảo vệ character, shared owner, video còn giữ; thiếu tuổi/quan hệ chuẩn |
| `core/subjects.py:run_auto_cleanup:396`, `schedule_auto_cleanup:432` | gọi factory trong nền; lock `_RUNNING` chỉ trong tiến trình; chưa có kế hoạch bất biến, reservation hay outbox |
| `core/delivered.py:mark:59` và `:67`; `core/archive.py:_move:44` và `:65` | ghi giao/cất rồi schedule xóa khung bị loại ngay; cần lifecycle timestamp chuẩn và lịch xét đủ tuổi |
| `core/runner.py:_hosted_pictures:1637`, điểm factory `:1657`, `picture_refs:1667` | tài liệu gói gọi là `_subject_refs`, nhưng base thực tế tên `_hosted_pictures`; lỗi Kho trả None → ảnh đánh dấu. `_on_refused` vùng `:2161–2184` đổi route khi Seedance từ chối: phải tránh kích hoạt do Kho đầy |
| `core/adapters/factory.py:subject_library:42` | đọc SUBJECT_PROVIDER/VIDEO_PROVIDER từ env, từ đó from_env; nguyên nhân G59 theo audit §3.1, diag 1860/1861; phiên này không truy vấn diag thật |
| `core/adapters/clipai_subjects.py:list_assets:67`, `get:82`, `upload:86`, `delete:128`, `delete_many:139` | GET phân trang; upload multipart + đợi processing; delete POST + list xác minh; retry 1130 qua call_rate_limited; chưa phải giao thức exactly-once |
| `core/send_claim.py:claim:44`, `take:62`, TTL `:20`; `core/runner.py:419` | claim job liên tiến trình và đọc lại trước gửi; TTL 900 giây không chứng minh provider chưa nhận. Cần phối hợp, không sao chép TTL làm quyền giải phóng pin |

## 2. Phân loại và hợp đồng dữ liệu đề xuất

**BỀN**: nhân vật, form/outfit và tài nguyên đã xác minh dùng chung; **TẠM**: khung/nháp của shot với provenance rõ. Loại asset không tự cấp quyền xóa. Không có mặt người không chứng minh là nền an toàn: đồ chơi, lưng, che mặt vẫn có thể cần Kho. Routing theo role + provenance + metadata đã xác minh và hợp đồng provider; detector khuôn mặt chỉ là tín hiệu phụ. Unknown → giữ/QUEUE, không bypass review. Chưa bật quy tắc gửi thẳng ảnh không mặt của audit.

Schema dưới đây là hợp đồng dự kiến, không phải SQL đã chạy:

| Bảng | Khóa / trường và bất biến |
|---|---|
| library_scope | scope_id, provider, account_ref ổn định, library_ref, config_version, capacity, snapshot_version/time/completeness. Không dùng token làm khóa; không lưu token/header |
| logical_asset | asset_id nội bộ, SHA256 bytes thực sự upload, role/provenance/class, version; unique(scope_id, SHA). Chuyển kích thước ảnh làm SHA mới; tên/path không phải quyền sở hữu |
| provider_asset | scope_id + provider_asset_id unique, logical_asset_id, status, revision, fence_token, last_verified_at; unknown/processing/deleting/quarantine vẫn chiếm chỗ |
| asset_project_ref | asset + project + source_kind/source_id unique, active, revision; ghi mọi nhân vật, forms, copy/import/restore, dự án dùng chung |
| asset_job_ref | asset + job + generation unique, frozen_payload_hash, pin_state, submit_attempt; danh sách bất biến theo lần gửi, không đọc lại refs mutable khi retry |
| capacity_reservation | scope + logical_asset unique, reservation_id, owner_epoch, job, state, lease_at, next_retry_at; SHA chung chỉ giữ một chỗ; nhiều job gắn cùng reservation |
| upload_attempt | attempt_id unique, scope/SHA, deterministic_name, owner/fence, request_state, acknowledged_asset, evidence, retry_at; unknown không xóa dấu vết |
| cleanup_plan / cleanup_outbox | immutable plan_id/hash, asset revision, ref versions, policy/config/snapshot version, reasons, timestamp, fence, state, attempt/evidence; mỗi target có kết quả riêng |
| project_lifecycle_event | project, event_id/version, delivered_final_at/archived_at/restored_at UTC, nguồn đã xác minh; không lấy file mtime hay cache updated_at làm tuổi |

## 3. Cấp chỗ chung và gửi

ACL đề xuất phải ở service: người xem không tạo refs/reservation/cleanup; `need_edit` chỉ gắn ảnh và tạo job trong dự án được phép, không nhận quyền xóa Kho toàn tài khoản. Owner công bố namespace/config và policy được duyệt; worker cleanup nhận quyền hạn hẹp theo plan/fence phía server, không tin asset/project/scope do payload tự khai. Báo cáo dự án chỉ hiện refs của dự án đó và tổng sức chứa được phép, không lộ tên/payload dự án khác. Thay phân loại BỀN/TẠM không vượt veto refs/retention; quyền Owner cũng không bỏ qua asset đang dùng hoặc unknown.

Mọi tiến trình dùng một DB và scope; không chia quota theo process/project. GET snapshot đủ trang ngoài transaction, ghi completeness/tuổi; thiếu trang, lỗi hoặc chưa xác minh account → QUEUE_UNKNOWN_CAPACITY, không suy zero. Scope không đồng nhất giữa các máy → không bật allocator cho tới khi dùng một coordinator chung.

Trong transaction ngắn **BEGIN IMMEDIATE**: đọc lại job/generation, claim và scope revision; đối soát snapshot với provider asset đã biết; tính union asset đã thấy + upload/unknown đang giữ chỗ chưa thấy (không cộng đôi processing đã xuất hiện); dedupe SHA; kiểm đủ chỗ cho toàn bộ gói mới; ghi reservation + frozen refs + upload intent; commit. Nếu thiếu thì không upload một phần, trả QUEUE_CAPACITY với needed/free/unknown/retry/reason. Dung lượng chưa xác minh không được giả là trống. Không giữ transaction qua HTTP.

Sau commit worker sở hữu fence mới được upload; upload đầy bất ngờ (web/ngoài hệ thống) → đóng snapshot, giữ attempt phù hợp và queue, không đổi model/đánh dấu. Bộ ảnh chỉ READY khi tất cả provider refs active và đúng frozen hash; kiểm lại pins/fences trước submit. Submit intent phải bền trước HTTP, CAS theo generation và phối hợp send_claim; một attempt chưa rõ kết quả không được gửi lần hai dù claim TTL hết. Provider không hỗ trợ idempotency thì không hứa exactly-once: chặn gửi lại tới đối soát/manual resolution. Không gửi gói thiếu ảnh.

FIFO theo scope với round-robin project và tuổi chờ, không ưu tiên dự án mới mãi; giới hạn số reservation/project và inflight upload đo sau, không hardcode 60/40. Gói lớn hơn tổng sức chứa chuyển NEEDS_ACTION, không chờ vô hạn. Queue backpressure có next_retry_at, jitter/backoff, reason code và cảnh báo starvation; GET refresh dùng chung snapshot, không poll mỗi job. 4–5 dự án được luân phiên công bằng, không cam kết đồng thời fit.

## 4. Dọn an toàn và retention

D03b cho dự án xong/cất **TRÊN 3 ngày = elapsed > 72 giờ**, đúng 72 giờ chưa đủ. Chỉ dùng timestamp sự kiện UTC đã xác minh và clock được kiểm soát; thiếu giờ/múi giờ, clock lệch/lùi → giữ. Phải có bằng chứng mọi owner đã xong/cất đủ tuổi; một project active/restore là veto. Character đang liên kết luôn veto kể cả dự án xong. Không tự định nghĩa tuổi của **“bản nháp cũ”**: CHỜ người dùng xác nhận; vì vậy nhánh cleanup nháp chưa đủ policy thì không eligible. Không tự cho xóa TẠM ngay khi clip approved, không áp retention tùy ý cho active approved.

Dry-run tạo plan bất biến gồm scope, target IDs/SHA/revision, refs/jobs/generation/pin snapshot, lý do, nguồn timestamp, tuổi, chính sách và config version, snapshot completeness, fingerprint; chỉ đọc provider GET nếu sau này được cho phép, không DELETE. Hết hạn kế hoạch → lập mới, không sửa payload kế hoạch cũ. Không chứa credential hoặc raw request.

Đề xuất mốc tuổi thuộc lần vào trạng thái terminal hiện hành, sau lần restore/reopen gần nhất; không tái dùng mốc giao/cất cũ để vượt thời gian giữ sau khi dự án hoạt động lại. Lịch sử thiếu sự kiện hiện hành → UNKNOWN và giữ. Cách chọn mốc khi giao rồi cất là một phần policy cần duyệt trước build, không tự backfill theo updated_at.

Apply sau phê duyệt production: transaction đọc lại TẤT CẢ refs/pins/job reconciliation/character/shared projects và retention, so fingerprint + CAS asset revision, chuyển eligible → DELETE_FENCED và tạo outbox; commit rồi mới HTTP delete. **Mọi writer tạo/sửa refs, pin, submit, copy, restore, relink, upload và manual delete** bắt buộc kiểm fence trong cùng transaction và từ chối/queue asset deleting. Writer đến trước làm revision đổi và hủy plan; delete fence đến trước chặn writer tới khi tái tạo asset mới có generation mới. Như vậy không có cửa sổ new-ref sau revalidation trước HTTP. Chưa kiểm kê và guard hết legacy writers → không activate cleanup. Lock process hoặc GET trước DELETE không đủ.

Loại trừ tuyệt đối: in_use, unknown ownership, job chưa đối soát/submit unknown, characters còn liên kết, shared active project, processing/upload unknown, quarantine, pin chưa giải quyết. Provider failed cũng không vượt veto. Outbox chỉ đánh DELETED khi GET đầy đủ xác minh không còn đúng provider ID; không chỉ dựa HTTP 200. Ghi kết quả riêng từng asset, lỗi giữ nguyên mapping và quota. Giao/cất chỉ ghi event và wake scheduler, không xóa ngay.

## 5. Khôi phục, lỗi và môi trường

| Điểm lỗi | Xử lý đề xuất |
|---|---|
| 1130 retry after Ns | tôn trọng Ns, backoff+jitter có trần số lần và deadline, lưu retry_at, thả worker/DB lock; namespace dùng chung nhịp gọi; không đổi input/model vì capacity |
| Upload timeout / ack unknown | giữ quota + quarantine attempt; GET đủ trang theo scope, tên attempt và bằng chứng SHA/provenance. Trùng tên/không đủ proof → manual, không upload lại theo TTL |
| Processing | vẫn chiếm slot, pin, GET có backoff; quá deadline báo cần xử lý, không xóa như orphan |
| Submit unknown / worker mất | pin bất định vô thời hạn theo bằng chứng, quarantine, GET task khi có ID; không tìm thấy trong snapshot không chứng minh chưa submit. Hết lease chỉ đổi owner/epoch, không tự xóa hay gửi lại |
| Delete timeout / ack unknown | giữ fence/quota, GET đối soát; không phát capacity hoặc unlink trước xác minh. Chưa chắc delete an toàn/idempotent → không blind retry POST |
| Worker cũ sống lại | CAS owner_epoch/fence khi ghi và trước intent; worker hết lease không gửi HTTP mới; thao tác đã bay phải quarantine vì DB fence không hủy HTTP trên provider |
| Ref/file đổi khi chờ | frozen SHA/payload mismatch → generation mới, hủy reservation chưa có external effect; unknown attempt giữ riêng tới đối soát |

G59: đề xuất config resolver chia namespace, đọc cùng nguồn cấu hình được phép như Dashboard thành object frozen có version; factory nhận explicit scope/config, không âm thầm gọi global load_dotenv hoặc nhận toàn bộ os.environ. Chỉ cấp credential ClipAI cần thiết từ resolver tin cậy tại biên, không log/persist secret, không nạp ngầm Anthropic API key. Provider/config thiếu → QUEUE_CONFIG với cách sửa; không fallback CLI/API khác. Health probe chỉ GET, chứng minh đúng account/library và completeness, không upload/delete/submit. Khi code sau này được duyệt phải kiểm nguồn nạp Dashboard và background thực tế; đây chưa phải sửa G59.

## 6. Migration, rollback, nghiệm thu và việc mở

Legacy cache tên/path không đủ owners: import thành UNKNOWN, giữ, không backfill suy đoán rồi xóa. Migration Cấp 3: inventory chỉ đọc → dry-run báo mapping/conflict → backup nhất quán DB + refs + cấu hình không-secret → thử restore bản sao → duyệt → transaction migration. Các câu SQL ở thiết kế không chạy trên DB thật. DB là nguồn chuẩn của refs/attempt/fence; provider là nguồn trạng thái tồn tại, hai bên phải đối soát. Khôi phục backup DB không hoàn tác provider delete; tái upload có thể có ID/review mới, không hứa undo.

Cờ allocator/queue/cleanup mới mặc định OFF; chưa đổi cờ subject_auto_cleanup legacy (D03b keeps tới M1.5). Rollback ưu tiên dừng sender/cleanup và giữ fence/unknown/outbox, không thả quota rồi bật lại blind sender. Tắt cờ về legacy có nguy cơ ảnh đánh dấu → Kling và cleanup ngay khi giao/cất; phải nêu và duyệt đường rollback, không gọi legacy là an toàn. Schema additive giữ được evidence; không downgrade/xóa attempts còn unresolved.

Test plan offline sau duyệt build: hai writer hai connection/process tranh slot cuối; 4–5 project queue/fairness; cùng SHA hai project chỉ một reservation; snapshot thiếu/trễ và external upload; frozen refs đổi; new-ref/restore đối đầu delete fence cả hai thứ tự; legacy writer chưa guard chặn bật; processing/unknown lâu hơn TTL; lost worker/fence cũ/lease oversubscription; submit unknown không duplicate send; 1130 Ns; upload/delete ack unknown; delete một phần lỗi; shared characters; ảnh quay lưng/no-face không tự bypass; UTC đúng 72h/72h+epsilon/clock lệch/thiếu timestamp; migration dry-run/restore; flags OFF và rollback hazard. Fake provider/registry/credential/model, mạng cấm; nếu chạy Python dùng patch.object thay OBJECT os.environ trước import/call/spawn, không patch.dict(clear=True), không in env/header/payload bí mật, không py launcher trong env rỗng. Đ19 này không chạy test/audit Python.

Nghiệm thu dự kiến: 0 Kling do Kho đầy, 0 use-after-delete, 0 gói partial refs; không oversubscribe do allocator, 0 duplicate paid submit trong ca unknown; mọi queue/xóa có reason/evidence và snapshot version. Test offline chỉ chứng minh luồng, chưa chứng minh chất lượng/live.

Chờ chốt: định nghĩa “bản nháp cũ”; phạm vi Cấp 2 bao phủ mọi writer và phối hợp M1.4b; Cấp 3 migration/flags/provider operations; account identity đáng tin, freshness/completeness GET và idempotency provider; timestamp lịch sử đáng tin; quota/fairness đo workload trước chọn ngưỡng. Không dùng các đề xuất face-only, LRU xóa ngay hay 60/40 trong audit như quyết định đã duyệt.
