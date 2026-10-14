# Đề bài Đ18 việc 4 — Registry A dùng chung sân khấu theo đoạn

Ngày 14/10/2026; đối chiếu code tại `46ac70ba`. **NGƯỜI DÙNG ĐÃ DUYỆT trong chat sau commit đề `64452104`; bắt đầu build 4a trên nhánh riêng.** Phần lưu/migration/UI/callers vẫn triển khai theo thứ tự và nghiệm thu từng bước; duyệt đề không cho phép API trả phí hoặc ghi dữ liệu thật.

Người dùng đã chọn A ngày 13/10; thư TODO 14/10 18:09 yêu cầu viết đề chi tiết. Quyết định 14/10 18:01: `anchor_by_spot` GIỮ TẮT; shot `own_camera` không nhận ảnh neo storyboard. Các lựa chọn kỹ thuật dưới đây đã được duyệt làm cơ sở build, nhưng không được coi là code đang có hay tính năng đã nghiệm thu.

## 1. Phạm vi và nguồn

A là nguồn chuẩn của sân khấu, đoạn truyện, trạng thái người/vật theo thời gian và máy từng shot. Editor/Camera/animatic/bộ góc máy cùng đọc/ghi A. B bổ sung proxy, mesh và phép đo trên A khi được duyệt; không có editor 2D riêng hay registry B cạnh tranh. Tấm nhìn từ trên/projection 2D là chế độ xem hoặc fallback có nhãn của cùng bàn đạo diễn.

Nguồn: `KE_HOACH_SAN_KHAU_DOAN_2026-10-12.md` mục 1–5; `THIET_KE_BAN_DUNG_3D_D11.md` mục 5, 9–9c; `PHUONG_PHAP_SAN_KHAU_3D.md` mục 2, 9, 11–14; `CODEX_TASKS.md` Đ11/Đ18; `handoff/TONG_HOP_CODEX_2026-10-14.md`; thư TODO 14/10 18:09/18:01. Nội dung A/B/C “chờ chọn” trong kế hoạch 12/10 và thiết kế 9a đã bị quyết định chọn A 13/10 thay thế. Thiết kế mục 5 về `stage_editor/scenes/.../revisions` được thay bằng kho A ở mục 3 dưới đây: **không giữ hai current pointer**. Không sửa rộng các tài liệu lịch sử trong việc này.

Đ18 việc 1–3 đã lên main theo thư 14/10 16:51; việc đó không tạo registry A. **Tại base đọc, chưa có registry A triển khai.** Tài liệu không xác minh runtime/cờ/job hay dữ liệu thật #24/#27; các ca lịch sử là nguồn thiết kế, không phải kết quả thử lại.

## 2. Điểm nối code thật

Số dòng chỉ có giá trị tại base đọc; trước build mở lại caller và cập nhật số dòng.

| Nguồn đang có | Điểm tái dùng / giới hạn |
|---|---|
| `core/stage_grid.py:23,96–112,118,145,694,734` | Gốc O, model↔relative↔scene, phương vị, axis side, frame_eval/check_spec. Dùng đúng transform; không viết phép chiếu/hệ tọa độ thứ hai |
| `core/stage_solver.py:24,48,356,499,555` | objects + beat overrides, objects_from_blocking, solve_shot/end_spec/solve_scene. Key solver hiện chỉ chữ/số; adapter cần bảng object ID↔key riêng, không ép ID registry thành tên Blender |
| `core/stage_facts.py:41,77,382,390,542` | stage_of/missing_reason/context/derive/for_shot; hiện đọc stage_camera trong scene. Adapter ON dùng snapshot A; không hiểu nhầm facts hiện có là registry |
| `core/blockout.py:34,143,214` | Kiểm schema/geometry/to_props; khối tạm không phải mesh đo thật |
| `core/blockout_sheet.py:108,218,229,266` | Top-view + location_pack adapter; output/pack là projection/version nguồn, không nguồn vị trí độc lập |
| `core/blockout_clay.py:9,42,59` | Config/clay/projection. `render_config` dùng máy đã truyền trước camera_for, người chuyển qua whitebox; adapter phải kiểm hoán đổi trục, pose và chiều cao |
| `core/plate_camera.py:367,404,428` | project/from_stage/plan_cameras. Máy stage riêng được giữ nguyên; không gom shot này vào setup/neo chỉ vì cùng cảnh |
| `core/camera_plan.py:130–152,418,513,690` | Plan JSON hiện dưới `<data_dir>/<pid>/plates/camera_plan.json`, nhóm story_scene/place, apply/before/after plates. Chỉ còn dữ liệu dẫn xuất/ý đồ khi A ON, không current registry thứ hai |
| `tools/stage_grid.py:1267,1308,1508,1532,1653` | blender_props/v2, review_stage_round/v3, ghi blocking/specs từng vòng. CLI cần adapter A và chế độ proposal; không tạo thêm bộ giải/editor |

Hợp đồng legacy `blocking` của solver không đồng nghĩa trường blocking văn bản `scenes.data`. Không tự parse câu vị trí thành số đo. Không đọc thư mục dự án thật trong lúc viết/build/test giả.

## 3. Kho chuẩn, API và quyền — đề xuất

Đề xuất lưu registry trong các bảng mới của manifest SQLite hiện có (cùng connection do caller cấp), theo scope project; migration schema sau cờ riêng có nghiệm thu. Lợi ích: cập nhật revision/current, liên kết scene, audit, proposal và invalidation cùng transaction, tránh hai tệp ghi nửa chừng. Tệp render/export chỉ là artifact có snapshot hash dưới project root từ `data_dir` được truyền; không là nguồn ghi ngược. Tên bảng/API cụ thể chốt ở việc 4a; không khẳng định migration này đã tồn tại.

Revision bất biến; mỗi aggregate stage/segment/state/camera có revision và một head trong kho A. Một lệnh ghi gồm `project_id`, ID do server cấp, `expected_revision`, `request_id`, patch có schema, lý do và actor lấy từ phiên xác thực phía server. Transaction: kiểm ACL + scope + foreign keys + khóa tay + CAS → insert revision/audit/proposal → cập nhật head và liên kết scene → commit. CAS thất bại trả conflict/diff, giữ draft; không last-write-wins. Worker chỉ publish artifact khi snapshot/revision vẫn khớp. Undo tạo revision mới dựa trên bản đích, giữ audit, kiểm lại ACL/CAS và tác động, không xóa lịch sử.

`request_id` duy nhất trong project+operation: retry cùng payload trả kết quả cũ; cùng ID khác payload báo xung đột. Sự cố/exception rollback toàn bộ; invalidation ngoài DB dùng outbox ghi trong transaction, xử lý idempotent. Đường dẫn artifact resolve trong project root, không nhận arbitrary path từ UI/Tiểu Nhị. Không ghi model/token/header vào audit.

Lệnh sửa nhiều aggregate gửi tập `expected_revisions` và kiểm tất cả trong cùng transaction; không chỉ CAS stage rồi ghi state/camera bên ngoài. Resolver đọc các head trong một read transaction nhất quán hoặc dùng tập revision đã pin, không ghép head đọc ở các thời điểm khác nhau. Bảng/schema A chỉ bootstrap qua thao tác được cho phép khi triển khai tính năng; không tạo bảng/backfill khi OFF hoặc chỉ mở Dashboard.

| Vai | Đọc | Ghi qua cùng service A |
|---|---|---|
| Runner/render/QC | Snapshot của đúng project/job đã chốt | Artifact/diag/provenance; không đổi vị trí/máy/head, không tự duyệt |
| Director | Stage/source/locked state + snapshot | Proposal theo segment/beat/shot, không ghi đè `_user_locked`, không tự xuất bản Kho |
| Editor | Revision/diff/dependency của dự án có quyền | Draft/apply/undo có ACL phía server và CAS |
| Màn Camera | State và setup revision cùng A | Camera/spec/move riêng, sửa setup thành proposal cho shot phụ thuộc; không dời actor |
| Tiểu Nhị | Các tool cùng ACL của người yêu cầu | Gọi đúng service apply/propose/undo, không SQL/path riêng, không nâng quyền |
| Owner Kho | Nguồn và revision asset được cấp quyền | Publish mẫu/location_pack qua hành động riêng có diff; quyền sửa project không suy ra quyền sửa Kho |

Tài khoản đồng nghiệp chỉ sửa dự án/bản sao được cấp. Mọi read/write kiểm scene thuộc project, tham chiếu asset hợp lệ và quyền; UI ẩn nút không thay kiểm server.

## 4. Lược đồ và bất biến — đề xuất

Envelope mọi revision: `schema_version`, `project_id`, `id`, `revision`, `parent_revision`, `author_id`, `created_at_utc`, `reason`, `source`, `provenance`, `_user_locked` theo đường field; lock chứa người/lúc/lý do. Phân biệt revision lưu và state thời gian truyện. Đổi nhãn/idx không đổi ID.

| Aggregate | Nội dung tối thiểu |
|---|---|
| Stage | `stage_id`, `source_asset_id`, `asset_revision`/content hash, `world_frame`, `geometry`, `spots`, `objects` definitions, source/approval revision |
| Geometry | Sàn, khối, lối mở, bounding dimensions, shape, mặt/phía tường, stand_in, transform; mỗi số có đơn vị, nguồn, độ tin `measured/assumed/unknown`. Không có mesh/tia thì visibility/collision chưa đo |
| Spots | `spot_id`, stage_id, label, xyz, facing, vùng và transform được xác minh. plate_spot legacy→spot ID có bảng mapping; không gộp hai spot vì tên gần giống |
| Objects/actors | `object_id` ổn định, kind, asset/look ID + revision, label, geometry/height có nguồn. Cast có actor ID gắn object, không tên hiển thị làm key; weapon/prop quan hệ dùng ID |
| Segment | `segment_id`, stage_id, story-time interval, `initial_state_id`, liên kết đoạn nguồn nếu quay lại/đổi thời gian; sequence chỉ là tổ chức dựng |
| State | `state_id`, segment_id, `parent_state_id`, beat/story_time, patches theo object ID: spawn/despawn, xyz, facing, pose, hidden, relation (in/cover/held_by). Field không patch kế thừa; null/xóa phải khai rõ |
| Actor beats | Actor ID, đầu/đỉnh/cuối và mốc giây/keyframe tối thiểu, đường/pose/event, state đầu/cuối. Tư thế gục có hướng đầu→chân và kích thước nguồn; không lấy trụ đứng làm người gục |
| Shot binding | Stable `scene_id`, stage/segment ID, spot ID, state_start/state_end revisions, time_clip; camera_setup_id/revision hoặc camera riêng; spec và actor beat refs |
| Camera/setup | Setup ID thuộc stage; camera location/target xyz, lens mm, sensor mm, aspect, roll/yaw/pitch độ, size intent, POV subject ID, move đầu/cuối/path/giây. Setup revision khóa state/spot/transform liên quan; override shot không mutate setup chung |
| Snapshot | Revision dependencies đã resolve + objects world-space đầu/đỉnh/cuối + máy + facts/provenance/locks + source fingerprints, job ID; snapshot đã gửi bất biến |

Tọa độ chuẩn A là mét so với O, +x Đông/+y Bắc/+z lên; facing độ theo chiều kim đồng hồ từ +y, lens/sensor mm, thời gian giây; ô K11 chỉ nhãn, không làm tọa độ. Legacy `stage_grid` lưu relative model rồi nhân factor khi ra scene: migration giữ nguyên raw units/factor/lift/origin; adapter chứng minh round-trip sang mét, không nhân factor hai lần. Không biết scale hoặc transform → unknown + lỗi thiếu đầu vào, không tự giả factor=1. Tọa độ màn hình u/v và trái/phải frame chỉ là projection theo camera, không world-side.

IDs server sinh, scope project; stage↔source revision, segment↔stage, state↔segment và parent cùng scope, shot↔scene FK, camera↔stage/state/spot hợp lệ. State graph DAG: chặn self-parent, cycle, orphan, cross-project/stage; story-time không tự suy từ thứ tự idx. Cắt xen rồi quay về shot 1–3↔11–12 dùng cùng đoạn/state lineage nếu thời gian nối tiếp; nhảy thời gian có segment/state mới và quan hệ nguồn rõ. Đổi góc chỉ camera, không reset đồng đội gục.

Khi đoạn mới kế thừa đoạn cũ cùng sân khấu, khai `continuation_from_state_id` cùng revision nguồn và resolve initial snapshot rõ ràng; quan hệ này khác parent trong đoạn và cũng kiểm chu trình/phạm vi. Không ép mọi đoạn thành một chuỗi idx, không sao chép trạng thái thiếu provenance, không dùng state của stage khác khi chưa có phép chuyển được xác minh.

Clone: cấp IDs/scope mới, remap toàn bộ refs/parent/setup/scene, giữ nguồn asset revision được phép; bỏ approval, job snapshot/cache/derived pointers của dự án cũ, tái xác nhận khóa người và quyền trong scope mới. Reorder giữ stable scene/state IDs, remap idx legacy/continuity_from qua bảng đối chiếu; chèn shot không làm mất state. Duplicate ID/ambiguous mapping trả conflict để người quyết.

## 5. Migration không mất dữ liệu — đề xuất

Dry-run mặc định trên fixture/bản sao; không tự chạy trên production. Đợt production cần người dùng cho phép + sao lưu DB/tệp vào data/backup trước và kế hoạch restore. Chọn project/nguồn rõ, không scan/backfill mọi dự án. Registry rỗng không kích hoạt migration khi mở Dashboard.

1. Inventorize nguồn được truyền: `stage_v2_*/stage.json/grid.json/blocking.json/shot_specs.json/setups.json`, các vòng Director, `scenes.data`, metadata approval; ghi hash/map đầy đủ. Nhiều vòng không dùng “tệp mới nhất” làm approved; không biết bản duyệt → conflict.
2. Import raw source bất biến + trường chưa nhận biết trong legacy payload; lập mapping source hash + legacy key→A IDs, revision, migration version. Không xóa/ghi đè tệp cũ/scene fields/job/ảnh/clip. Giữ #24/#27 gồm props, người trong giếng/gục, beats, subject.id, end_actor/end state, stage_camera/move/POV, user locks, spec overrides và source approvals với provenance; approval legacy là lịch sử, không tự duyệt bản A mới.
3. Thiếu actor ID/units/state hoặc blocking chỉ là văn bản → unresolved có lý do và cần người ghép, không bịa số/ID Kho. Nhịp hidden/at/in giữ đúng nghĩa solver; spawn tường shot15 phải event, không có ở shot trước.
4. Transaction ghi raw+mappings+revision+links khi dry-run được duyệt; idempotency theo source hash/migration version, chạy lại không nhân bản. Nguồn đổi tạo proposal/revision mới, không đè bản đã chỉnh. Crash giữa chừng rollback; chạy lại/restore trên bản sao phải chứng minh không mất trường.
5. Activate A chỉ cho project đã reconcile; project chưa migrate vẫn legacy. Khi A ON, legacy artifacts ghi bởi adapter là derived, không consumer nào sửa trực tiếp để tạo nguồn thứ hai. OFF không chuyển ngầm sang A. Rollback cờ về OFF giữ legacy nguyên bản; không xóa lịch sử A.

## 6. Resolver, nguồn ưu tiên và lan sửa — đề xuất

Một resolver trả snapshot cho prompt/render/facts/QC/package/Editor/animatic. Chuẩn nhận diện: ảnh Kho > hồ sơ Kho > Bible > Lock; state hình học dùng revision A đã duyệt/khóa người. Nguồn khác nhau theo vai dữ liệu, không dùng render proxy thay ảnh thật QC. Director chỉ proposal; legacy chỉ input migration/đường OFF, không fallback âm thầm ghi đè A. Thiếu A/source/transform khi ON → báo thiếu rõ và giữ tại cổng cần dữ kiện, không gen như đủ.

Dependency graph: asset revision/transform→stage→state descendants→shot snapshot→plate/projection/facts/prompt→image/video. Camera đổi chỉ ảnh hưởng shot dùng camera/setup ấy; state đổi ảnh hưởng hậu duệ liên quan; source image layout hash đổi ảnh hưởng shot dùng nguồn. Invalidation theo toàn bộ dependencies, không theo mỗi lens/scene label. Job đang chạy tiếp tục giữ snapshot đã gửi, kết quả gắn bản đó, không publish vào bản mới.

Sửa vị trí/tư thế/máy tạo diff, liệt kê cảnh sau và trường bị ảnh hưởng. Shot chưa duyệt: proposal cần chấp nhận/bỏ từng shot hoặc nhóm hợp lệ; lock bị đụng phải người có quyền mở rõ. **Cảnh đã duyệt chỉ `layout_drift` VÀNG**, giữ snapshot/ảnh/clip/take/approval, không tự áp state mới, không tạo job, không regen. Duyệt proposal không là đồng ý gen tốn tiền. Replan Director giữ khóa người, không sửa state chỉ vì máy đổi; undo cũng sinh diff/drift.

Giữ `anchor_by_spot` TẮT, không dependency REQUIRES vào nó. `own_camera` dùng render đúng máy, không neo storyboard; layout_from/continuity_from là đề xuất riêng có nguồn duyệt/fingerprint và không vượt luật own_camera. Không tự thêm ảnh neo khi thiếu render. Đ18v3 nguồn trước/sau hiện có vẫn kiểm self/cycle/existence.

Ma trận kế thừa phải có test cho bấm tay/autopilot/v2 cảnh/v3 shot/multi-shot/clone/replan; giữ bộ chọn ảnh Kho, tiền/ước tính, cổng duyệt, regen đổi input và giới hạn cũ. Autopilot chỉ được opt-in sau thử thật được duyệt, không tự kích hoạt bởi registry tồn tại.

## 7. Cờ OFF, render và UI — đề xuất

Đề xuất `stage_registry_a` OFF/OPT_IN_ONLY (tên chờ duyệt). `stage_editor`/Camera consumer yêu cầu A đã reconcile; không yêu cầu anchor_by_spot. OFF gọi nguyên nhánh legacy: prompt từng byte, refs/thứ tự, grouping, hash/cache, approvals, job/status, số paid calls giống baseline; không DB migration/Blender/Director mới. Không đủ chứng cứ chất lượng → không bật mặc định.

Tái dùng queue portable ở nhánh `codex/ban-dao-dien-hieu-nang` (dependency riêng, root cung cấp HEAD `22b13128`, code `149d65f6`/`8967fcc4`, benchmark `docs/BENCH_BLENDER_BURST_2026-10-14.md`) sau xác minh/gộp; không viết queue editor riêng. Mức nghiệm thu dependency: **5 active / 1 heavy worker**; **25 admission = 1 running + 24 pending trong fixture, không phải production max hay giới hạn toàn pipeline**. Tại base này nhánh queue chưa tích hợp; không suy production đang chạy mức đó. Đo hash/cache/debounce/coalesce/cancel/superseded, timeout/error và isolation nhiều project. Render khi thả/bấm xem, không mỗi mousemove. Hash gồm stage/asset/material/renderer/geometry/poses/beats/camera đầu-cuối/aspect/resolution; ảnh cũ không nhận nhãn revision mới. Thiếu Blender hiện projection + lý do, không claim ray/occlusion đã đo.

Đ11v3 dùng màn đã duyệt mục9: đủ 18 mục bản gọn, #12 preset library và #20 import/export để sau; bộ góc trong project vẫn cùng setup registry A. Một timeline BYĐ/keyframe, không hệ animation thứ hai. Camera orbit của viewer không đổi shot; chép view→camera phải diff; height unknown không bịa; stand_in chỉ xem; package ghi lớp/nguồn sẽ gửi. Animatic clay Đ11v5 và gói xuất khi được mở đọc đúng snapshot A, không tạo state/ID riêng. B mở rộng mesh/ray trên cùng geometry IDs/revisions.

Nghiệm thu UI 1440 và 1280, cả Góc đạo diễn/Góc camera, shot trước/sau, ba nhịp và trạng thái conflict/drift: 0 JS/console exception, không cuộn ngang, field/nút không bị che, nhãn revision/hash/tuổi preview và thiếu dữ kiện rõ. Đo thao tác theo cùng fixture/baseline; không hứa giảm click nếu chưa đo. Không bấm gửi model thật trong QA.

## 8. Chia việc nhỏ theo thứ tự — lộ trình đã được duyệt

| Mã | Phạm vi nhánh | Điều kiện nhận / bằng chứng |
|---|---|---|
| Đ18.4a | Schema/validator/resolver thuần + hợp đồng API, fixtures | IDs/FK/DAG/units/locks/unknown đỏ→xanh; chưa storage/live |
| Đ18.4b | Store transaction/CAS/ACL/audit/undo/outbox | 4a ổn; race hai writer, crash rollback, denied/cross-project, request retry đỏ→xanh; RÀ KỸ |
| Đ18.4c | Dry-run importer legacy + mapping/idempotency/restore | 4b ổn; fixture #24/#27 giả giữ mọi field/approvals gốc; RÀ KỸ dữ liệu, không migrate production |
| Đ18.4d | Adapters solver/grid/facts/blockout/camera_plan/CLI | 4c; một snapshot, transform round-trip, head riêng legacy bị loại khỏi ON; projection/facts không claim measured |
| Đ18.4e | Binding Director/runner + proposals/dependency/drift/OFF | 4d; caller matrix đường thật với provider giả, approved không regen, own_camera không neo; sửa runner tối thiểu có lý do, RÀ KỸ vòng đời/tiền |
| Đ18.4f / Đ11v3 | Editor/Camera/Tiểu Nhị qua service A, render queue đã tích hợp | 4e + queue dependency; 18 mục, ACL/CAS/undo, PNG1440/1280; không preset/import/export |
| Đ11v5/B tiếp | Animatic/bộ góc/gói và mesh/ray nâng cấp | Chỉ sau nguồn A nghiệm thu và phạm vi riêng được mở; không registry/editor thứ hai |

Mỗi nhánh tập trung đỏ→xanh test liên quan, không nới test, gom 2–3 lần chạy; file mã mới khai areas, integration tăng version một lần. Gộp từng bước nhỏ khi toàn bộ Windows xanh và rà theo mức của quy trình; integration cập nhật kế hoạch/TODO theo người điều phối. Không biến việc viết đề hiện tại thành quyền build/gộp/chạy thật.

## 9. Bộ kiểm bắt buộc khi build

- Thuần: sai ID/FK/self/cycle/NaN/scale/units, giữ raw unknown; meter↔legacy round-trip; field lock; spawn/despawn/hidden/in và state đầu/đỉnh/cuối, POV/end_actor/subject.id.
- Store: concurrent CAS chỉ một thắng, request id replay, ACL read/write/undo/publish, rollback tại từng bước, outbox retry; không path escape hoặc mất ghi.
- Snapshot nhiều aggregate không bị trộn revision khi writer commit giữa các lần đọc; CAS nhiều head thất bại phải rollback toàn bộ. Kế thừa đoạn giữ đúng nguồn state/revision, chặn chu trình qua cả quan hệ continuation.
- Migration: nhiều stage_v2 rounds, ambiguous approved, trường lạ, văn bản blocking, thiếu scale/asset, chạy hai lần, nguồn đổi sau user lock; bytes/hash nguồn không đổi và restore bản sao.
- Ca lịch sử dựng giả: 1–3↔11–12 đồng đội gục giữ ID/vị trí; S07 hai spot không trùng do gộp sai; Kelly đúng world-side của tường dù camera quay; tường chỉ từ event shot15; người gục và đi ra giếng cuối clip; đổi camera không dời actor.
- Callers thật/provider giả: tay/autopilot/v2/v3/multi-shot/replan/clone/reorder; snapshot immutable trong job; scene approved chỉ layout_drift, không submit/regen; facts/prompt/render cùng snapshot. OFF so từng byte/hash/order/status/call count với baseline.
- UI/render: debounce/coalesce/cache hit/5 active–1 worker/cancel/error/stale result, 25 admission chỉ fixture; 1440/1280 hai view/locks/conflict/drift/unknown, không gửi API.

An toàn test bắt buộc: `PYTHONUTF8=1`, `py -m pytest ... --tb=no -p no:cacheprovider`, không showlocals. Trước import/call/spawn dùng `patch.object` thay **OBJECT** `os.environ` bằng dict giả, không `patch.dict(clear=True)`; mock registry/credential/provider/model, teardown cho thiếu/có. Native subprocess explicit whitelist env giả. Không đọc/in/assert/repr môi trường thật, secrets/header/token/payload; DB/ASSET_DIR/DATA/flags/knowledge/credentials đều tạm; không dashboard.env/API/data thật.

Test giả chứng minh hợp đồng/luồng, chưa chứng minh chất lượng ảnh/video. Sau code: 1 ảnh/nhóm→người xem→1 clip→mở rộng chỉ khi báo trần từng paid call, qua sổ chi + ước tính và người dùng đồng ý. Không nhận “đã sửa lỗi #24/#27” từ test giả. Lần viết đề này không chạy pytest hoặc paid/model/render/data QA.

## 10. Phạm vi đã duyệt và giới hạn khi build

Người dùng đã duyệt trong chat: kho SQLite chung manifest và transaction/outbox; schema/ID/units/migration dry-run; API/CAS/ACL/locks; nguồn ưu tiên/proposal/drift và OFF; chia 4a→4f với nghiệm thu fake-data, queue dependency và giới hạn UI. Bắt đầu 4a, các bước kế tiếp tiếp tục theo dependency và phạm vi nghiệm thu. Chi phí API build/test giả dự kiến 0 USD; chưa đủ input/model/calls để đặt trần thử chất lượng thật, phải báo giá riêng. Chưa được phép ghi/migrate dữ liệu thật, API trả phí hoặc mở B/preset/import-export/full animation.
