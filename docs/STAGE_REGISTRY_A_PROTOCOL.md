# Registry A — hợp đồng thuần v1 (Đ18.4a)

Chỉ schema/resolve JSON trong bộ nhớ; không storage, head/latest, DB transaction,
ACL/CAS, migration, adapter, flags, runner, UI, ID generator hoặc render.
4b chịu trách nhiệm cấp IDs và đọc một transaction nhất quán trước khi gọi API.
Fixture giả chứng minh hợp đồng, chưa thử chất lượng hình/video hoặc dữ liệu #24/#27.

## Wire protocol

Bundle bắt buộc: `schema_version=1`, `project_id` số nguyên dương (manifest),
và năm danh sách `stages`, `segments`, `states`, `cameras`, `shots`.
ID aggregate chuỗi ASCII chữ/số/gạch dưới/gạch ngang, dài 1–128; opaque, không
đổi theo nhãn/idx. Index theo `(id, revision)` trong loại aggregate; lịch sử
cùng ID nhiều revision hợp lệ. Không trùng cặp. Mọi ref là `{id, revision}`,
revision nguyên dương, không bool; null chỉ tại trường được khai nullable.
ID số của manifest và revision nằm trong `1..2**63-1` để tương thích INTEGER SQLite; không để số tràn tới lớp lưu.
`source_asset_id`, `asset_id`, `look_id` dùng số nguyên dương ID Kho hiện có;
4a chỉ kiểm kiểu, quyền và asset FK thật thuộc service 4b, không đọc Kho.
Không tự sinh, sửa tên, chọn revision mới nhất hay suy state theo idx.

Mọi revision bắt buộc envelope: `schema_version`, `project_id`, `id`,
`revision`, `parent_revision` (null hoặc số nhỏ hơn revision), `author_id`,
`created_at_utc` ISO có Z, `reason` không rỗng, `source`, `provenance`,
`_user_locked`. Ba trường cuối là object; source/provenance chứa fingerprint
và lịch sử/raw nguồn; payload legacy lạ chỉ đặt trong `provenance.raw` hoặc
`geometry.raw`. Lock map đường field→`{author_id, created_at_utc, reason}`.
Snapshot giữ nguyên lock; 4b mới kiểm quyền mở khóa và enforcement apply.
Envelope parent_revision mô tả lịch sử lưu; không phải parent_state truyện.

Các key aggregate bắt buộc (không nhận extra key):

| Loại | Keys ngoài envelope |
|---|---|
| stage | source_asset_id, asset_revision, world_frame, geometry, spots, objects |
| segment | stage, time `[start,end]`, initial_state, continuation_from_state nullable |
| state | segment, parent_state nullable, story_time, beat, patches |
| camera | stage, state, spot_id nullable, location, target, lens_mm, sensor_mm, aspect, angles, pov_subject_id nullable, move nullable |
| shot | scene_id nguyên dương stable manifest, stage, segment, state_start, state_end, spot_id nullable, camera nullable, private_camera nullable, beats danh sách state pins, time_clip |

`world_frame`: units=m, east=+x, north=+y, up=+z,
facing=clockwise_from_+y, scale=`{value,confidence,source}`. Scale null phải
unknown; không thế factor=1. geometry=`{dimensions,confidence,source}`;
dimensions null phải unknown, hoặc vector ba số dương mét. Các optional
geometry: shapes, transform (ma trận phẳng 16 số), stand_in, raw. Shapes và
stand_in là mô tả/provenance chưa được solver diễn giải trong 4a; không claim
mesh/ray/collision/visibility measured. Confidence measured/assumed/unknown;
measured bắt buộc source không rỗng. Known coordinates không suy measured.

Spot bắt buộc id, xyz vector ba mét, facing độ; optional label, region,
transform (16 số), provenance. Object definition bắt buộc id/kind
(actor/prop/structure), optional label, asset_id+asset_revision,
look_id+look_revision, height mét hoặc null, geometry, provenance, actor_id.
Mọi ID spot/object độc nhất trong stage revision. Height thiếu chưa xác minh.

Patch bắt buộc object_id, op=spawn/update/despawn. Optional xyz, facing,
pose chuỗi không rỗng, hidden bool, relation map in/cover/held_by→object ID
hoặc null. Despawn không có field khác. Mỗi state chỉ một patch/object.
Spawn khai rõ sự xuất hiện; definition không làm vật xuất hiện trước event.
Update vật chưa spawn hoặc đã despawn lỗi; tái xuất hiện cần explicit spawn.
Relation null xóa riêng quan hệ; xyz mới không tự xóa `in` (adapter 4d phải
dịch đúng legacy at/in). Hidden giữ object/state nhưng đánh dấu không hiện;
adapter visibility 4d mới loại khỏi danh sách hiển thị. Despawn xóa presence;
relation tới vật không hiện hữu hoặc chu trình quan hệ bị resolver chặn.

Parent state cùng segment revision. Root kế thừa continuation_from_state
của segment, cùng stage revision; continuation giữ pin nguồn và lineage cũ.
Initial_state của segment phải thuộc segment đó và không có parent_state.
Graph parent+continuation kiểm DAG lặp, không đệ quy. Story-time trong
khoảng segment, không giảm theo parent; continuation không sau đầu segment.

Camera location/target/angles là vector 3 số; angles=[roll,yaw,pitch] độ,
lens_mm dương, sensor_mm=[width,height] dương, aspect dương. Move gồm
end_location/end_target vector3, seconds dương, path danh sách vector3.
State/spot/POV subject refs cùng stage revision; POV phải hiện hữu đầu shot.
Shot dùng chính xác một camera setup pin hoặc private_camera có tám field
camera spec (location…move), không envelope. Setup thay đổi không dời actor.
Shot start/end/beats cùng segment pin. Beats là state mốc đầu/đỉnh/cuối có
story_time, pose/event đã resolve; không phải hệ keyframe nội suy mới.

## API và snapshot

`validate_bundle(bundle, max_nodes=50000, max_depth=48, max_string=4096)`
trả `{errors:[], warnings:[]}`. Error `{path,code,message}` tiếng Việt,
path chỉ tên schema/chỉ số, không echo ID/unknown key/payload. Mã gồm type,
field, number, scope, pin, reference, duplicate, cycle, units, time, budget.
Kiểm cấu trúc/pins/FK/DAG; kiểm presence/quan hệ theo thời gian tại resolver.
4b phải gọi resolver cho state/shot chịu tác động trước apply, không chỉ dùng
structural validator để nhận patch lifecycle. Inputs JSON cây; Python alias
container/cycle bị từ chối. Quét iterative giới hạn nodes/depth/string trước
deepcopy/hash; không nhận NaN/Infinity hoặc bool ở vị trí số.

`resolve_state(bundle,state_id,revision)` trả schema_version/project_id,
state pin, story_time, beat, objects map (có definition), locks,
dependencies, warnings, measurement và hash. `resolve_shot` thêm scene_id,
shot pin, start/end/beats, camera. Cả hai raise `RegistryValidationError`
(errors đã sanitize) khi thiếu pin/scope hoặc lifecycle/relation không hợp lệ.
Không đọc file/DB/env/provider; không mutate input; mọi output là deepcopy.

Dependencies gồm toàn bộ envelope revision thực sự đọc: source fingerprints,
geometry/transforms/spots/object definitions/poses/beats/locks/camera/move,
lineage state/segment/stage. SHA256 JSON canonical keys sorted, dependencies
sorted theo loại/id/revision; reorder bundle không đổi hash. Mọi thay đổi
trong dependency đổi hash; snapshot cũ độc lập với bundle và snapshot khác.
Không hash head/latest hoặc dữ liệu sản xuất. Job ID/approval/publication do
4b/4e gắn sau, chưa có trong API thuần. Warning unknown được giữ, measurement
unknown nếu có warning, ngược lại unverified; không tự claim đã đo.

Giới hạn hiện tại: shapes/object geometry/pose là mô tả nguồn thuần, chưa có
mesh/pose skeleton validator hay nội suy; chưa round-trip legacy mét (4d),
chưa enforcement locks/store consistency (4b), chưa chạy thật/UI (4e/f).


## Bổ sung sau RÀ KỸ độc lập 14/10 (chưa gộp)

`author_id` là chuỗi danh tính User/email TEXT (tối đa 320, không rỗng hoặc
control character), khác opaque aggregate ID; lỗi không echo giá trị.
Lock path chỉ tên field của aggregate và các nhánh `.field`/`[index]`, không
nhận đường filesystem hoặc field ngoài hợp đồng. Source/provenance/raw là
payload nguồn có budget, chưa có adapter giải nghĩa; không tự đọc đường dẫn.

Geometry stage/object đều dùng dimensions/confidence/source và optional
shapes/transform/stand_in/raw; stand_in bool. Shapes là list descriptor
`{kind,dimensions,confidence,source}` với optional transform/raw. Kind là mô
tả nguồn, chưa được solver diễn giải; extra keys không được nhận, chưa kiểm
mesh/ray/skeleton. Missing height/object geometry, assumed/unknown dimensions
hoặc scale đều VÀNG; không claim measured từ các tọa độ đang có.

Mọi root trong segment phải đúng initial_state; shot start→beats→end phải
thuộc cùng lineage theo thứ tự, không nhận sibling/reversed path. Camera setup
state phải đúng pin state_start. time_clip vẫn là thời gian riêng clip, không
so trực tiếp với story_time toàn truyện. Relative/generic camera adapter thuộc 4d.

Cổng nhận dữ liệu service 4b là
`validate_registry(bundle, max_work=100000)` trong resolver: kiểm cấu trúc
và materialize mọi state để kiểm lifecycle/presence/relation, cùng POV shot.
`validate_bundle` là validator cấu trúc/FK/DAG/lineage; không thay thế cổng
semantic. Các resolve API nhận cùng keyword max_work. Work budget dương,
trần 1000000; vượt budget trả lỗi sanitize, không snapshot một phần. Scan input
trần 50000 nodes/48 depth/4096 string; số nguyên wire tối đa 1024 bit.
Ancestor traversal có trần 4×max_nodes. Cache chỉ trong một lần resolve, các
objects/locks/beat snapshot được copy độc lập; chi phí materialization tính
cả payload dependencies/definitions, không chỉ số state. Chưa benchmark nhiều
project Dashboard, chưa cam kết latency production.

Warning snapshot chỉ lấy stage dependency thực sự dùng, path canonical
`$.stage...` và pin stage đi kèm; reorder collection/unrelated stage không
đổi hash. Không có thay đổi flags hoặc caller thật, module mới chưa nối ON.

Bằng chứng review target: 10 failed/29 passed (ĐỎ, 0,69s), sau sửa 39 passed
(0,74s), mở rộng malformed/cache/semantic guard: 49 passed (0,55s).
Một guard request-pin malformed được chuyển trước cache lookup sau lượt cuối;
root cần xác nhận lại trong lượt kiểm phần sửa/integration. Chưa fullsuite,
chưa dữ liệu thật, chưa chất lượng ảnh/video, chưa #24/#27 nghiệm thu.

## Store transaction opt-in v1 (Đ18.4b, chưa gộp)

`core.stage_registry_store.StageRegistryStore(p, opt_in=True)` mượn chính
`p.conn` manifest server; danh tính lấy `p.user`, không nhận actor từ payload.
Mỗi thao tác đọc lại `features.on("stage_registry_a")` và `opt_in is True`; mặc định OFF,
OPT_IN_ONLY. Import/constructor/OFF không tạo bảng, không sửa PRAGMA/env/path.
Không nối Pipeline.init/db.py/startup/UI/runner hoặc adapter/importer.

`bootstrap(project_id)` là lệnh DDL rõ, cần cờ ON + opt-in + quyền edit dự án.
Bảng prefix stage_registry_: schema v1, revisions, heads, requests, audit,
outbox. DDL từng execute trong BEGIN IMMEDIATE, không executescript.
Revisions PK(project_id,kind,id,revision); heads PK(project_id,kind,id).
Triggers cấm UPDATE/DELETE revisions/audit/requests; không delete lịch sử.
Schema khác phiên bản/cột/constraints hoặc missing/replaced/extra triggers trả lỗi rõ, không tự migration; chỉ nhận đúng DDL v1 đã bootstrap.
Đây là guard service; không đổi chính sách SQLite toàn connection của caller.

`apply(pid, [(kind,row),...], expected_revisions, request_id=..., reason=...)`:
kind là tên collection số nhiều; expected map `(kind,id) -> revision|None`
phải đúng toàn bộ head bị chạm. None dành aggregate mới revision 1.
Server cấp revision N+1, parent N, author/time/reason; IDs caller cung cấp phải
opaque hợp protocol. Không cấp lại ID theo idx/nhãn. BEGIN IMMEDIATE khóa ghi,
kiểm ACL trong transaction rồi CAS toàn bộ, semantic validate_registry closure
active heads + proposed rows + exact historical pins. Scene và asset dependencies
của candidate live phải thuộc dự án/project_assets; asset private không khác dự án.
Read lịch sử chỉ metadata, không đòi asset còn gắn với dự án hiện tại. Không fallback latest ref.
Không sửa assets, không publish Kho, không actual submit/worker.

Revision/head/audit/request/outbox cùng transaction; exception rollback toàn
bộ. `_point(name)` là điểm monkeypatch test ở revision/head/audit/outbox/request, không payload; production không nhận runtime callback fault.
Request unique(project,operation,request_id), hash JSON canonical bounded;
exclude envelope actor/time/revision/parent/reason server từ hash, vẫn hash
lý do command. Apply hash body caller đầy đủ; undo/unlock hash command keys,
expected CAS, target/path và lý do, không hash body head được đọc lại. Retry recheck edit ACL; cùng actor/hash trả result lưu, khác
actor/hash conflict. Operation apply/undo/unlock là namespace riêng.

Connection đang có transaction ngoài: **write/bootstrap/ack từ chối rõ**,
không commit/rollback pending writes caller. Reads dùng transaction đọc hiện
có; nếu không có thì tạo transaction đọc cho cả lịch sử và resolve snapshot.
Caller có trách nhiệm kết thúc transaction ngoài trước write và giữ connection
chỉ cho một thread. Nhiều writer dùng connection riêng cùng SQLite file.

`head/history/snapshot/request/audit/outbox` đều need_view và scope project.
Snapshot nhận shot/state pin chính xác, mọi history pin giữ độc lập head mới.
`ack(pid,event_id)` need_edit, event phải cùng project; ack lại idempotent.
Outbox chỉ metadata invalidation cho future consumers, không gen/submit.

Khóa workflow: apply giữ metadata lock và provenance hiện tại, cấm đổi map
lock âm thầm; actual diff paths so cả ancestor/index với paths đã bảo vệ.
`unlock(pid,kind,id,paths,expected_revision,request_id,reason)` cần edit dự án,
phải chỉ rõ các path có khóa + lý do; tạo revision/audit. Watcher edit được
mở khóa workflow; không được quản trị tài nguyên toàn Kho. Trusted-system
`p.user=None` kế thừa access hiện có, **vẫn phải mở khóa rõ** khi muốn đổi field.
`undo(...,target_revision,expected_revision,...)` tạo revision mới từ target,
giữ khóa/provenance head hiện tại, actor/time server hiện tại; CAS và cùng
cổng semantic/diff/ACL, không khôi phục author/time cũ hay xóa lịch sử.

Giới hạn: preflight SQL COUNT/tổng bytes trước JSON decode; trần 5000 revision
và 16 MB mỗi project, JSON 2 MB/payload, metadata 10000 dòng/16 MB. Store
từ chối cả write nếu revision mới sẽ vượt trần đọc, không tạo head không đọc được.
Chỉ materialize exact dependency closure, theo node/work budget 4a; chưa benchmark
nhiều project. History/audit append-only không bị xóa để vượt giới hạn. Chưa migration/restore thật,
chưa caller/provider thật, chưa fullsuite Windows, chưa chất lượng ảnh/video.


## Sau RÀ KỸ store và sửa gom (14/10, chưa gộp)

Lock path phải trỏ tới field/index thực sự có trong row; indexed lock chỉ chặn
thay đổi tại index/ancestor liên quan, không chặn append sibling ngoài khóa.
Lock mới được stamp author/time server; existing lock metadata giữ nguyên.
Thêm/sửa khóa trên existing aggregate không có API ngầm; policy v1 chỉ unlock
rõ bởi edit/owner/system được ACL hiện có cho phép, tạo revision/audit. Provenance
existing giữ bất biến: payload khác bị từ chối, không silently drop.

Head map phải phủ mọi aggregate, luôn ở revision lớn nhất; số revision liên tục
1..N, body/PK/project/parent metadata phải khớp. Schema/triggers được so với DDL
v1 canonical; không repair tự động trên read. JSON lưu từ chối duplicate keys,
NaN/Infinity/Unicode lỗi. Request/audit/outbox kiểm result shape + project/operation
và revision tồn tại, có budget trước decode; lỗi SQLite sanitize, rollback owned
transaction, không rollback borrowed pending caller.

Read head/snapshot/history chỉ tải closure được hỏi với exact pins và semantic
validate; apply kiểm projected active-head closure và riêng candidate dependency
closure cho live scene/assets. Asset từng gắn rồi detached không phá snapshot
metadata cũ; candidate mới dùng source detached vẫn bị từ chối. Preflight và kiểm
head integrity vẫn quét metadata lịch sử bounded; không hứa latency production
vô hạn hoặc phân trang/archive tự động (giao thức tương lai riêng).

**Domain Kho còn CHỜ:** repo assets chưa có backing revision store để chứng minh
asset_revision là version bytes bất biến; service hiện chỉ kiểm asset identity,
project ownership/attachment và pin metadata được khai báo. look_id không tự
coi là assets.id hay asset_images.id: adapter bộ dạng/ảnh và pin/hash cần người
dùng chốt. Đường write candidate có look_id explicit fail closed; pure 4a/history
metadata vẫn giữ pin, không sinh entity Kho/migration. Không claim domain đã nghiệm
thu hoặc đã khóa immutable source file từ bộ test fake.

Bằng chứng reviewer: 1 collection error quote trong test đã sửa parameter SQL;
**20 failed/84 passed (RED,4.13s) →113 passed (GREEN,4.44s)**, đúng 3 lượt target
store+schema+resolver, --tb=no. Root đã xác nhận builder baseline 82 passed/1.94s.
Không nới test: fault vẫn inject đủ 5 phase, đổi từ runtime callback sang monkeypatch.
Cờ OFF/OPT_IN_ONLY; chưa caller/live/API/data thật/fullsuite. areas version 80 giữ.


Root đọc fix lần2: projected metadata phải cộng cả result JSON mới và +1 count
trong mỗi requests/audit/outbox **trước** INSERTrevision. Cùng transaction,
fail closed nếu result sẽ vượt cap, không tạo revision khiến retry/read hỏng.
Trần16MB metadata áp vào JSON result/payload; actor/time/reason còn có giới hạn
chuỗi/row riêng, không claim toàn bộ DB/index footprint16MB. Ack kiểm SQLite int0/1.
look_id None không là wire nullable: optional pair look_id/look_revision vẫn phải
là số nguyên dương; gate chỉ thêm từ chối mapping chưa chốt cho valid look pin.
Root cho thêm2lượt cho finding mới: 3 RED/1.39s → **116 GREEN/5.89s**, target3files.

## Đ18.4c PARTIAL — inventory/dry-run offline (chưa gộp)

`core.stage_registry_import` chỉ dùng thư viện chuẩn; không import store,
validator/provider/credential, không SQLite, UI, network hoặc đọc environment.
Không có apply/import-commit/activate/approve, không thêm migration startup.
SourceSpec(kind,legacy_key,relative_path,round_id=None) là nguồn explicit:
kind stage/grid/blocking/shot_specs/setups/scene_data/approvals/binary.
Không glob/scan mọi project, không chọn latest stage_v2 hoặc suy approved round.
Caller phải truyền root tuyệt đối của fixture/bản sao và project ID stable.

`dry_run(root,project_id,sources,migration_version=1,...)` read-only, trả
DryRunReport immutable gồm raw sources, mappings proposals, diagnostic issues.
RawSource giữ bytes nguyên bản (UTF-8 BOM/whitespace/unknown fields/binary)
và SHA256; không diễn giải lại scene approvals hay xóa field legacy.
Tất cả report có status PARTIAL và ready_for_apply=False, kể cả đủ metadata.
Mapping theo project + migration version + kind + legacy key + raw hash →
candidate_id opaque/proposed_revision=1. Đây là **proposal source ID**, chưa
ID aggregate A stable hoặc Kho ID; nguồn đổi tạo proposal khác, không đè A.
Inventory hash gồm project/version và danh sách kind/key/relative path/round/
source_hash canonical sorted; không gồm timestamp/root tuyệt đối/mtime.
Reorder input không đổi report; bytes nguồn đổi (kể cả whitespace) đổi hash.

Trần hard: 64 tệp, 8 MiB/tệp, 32 MiB toàn inventory, 48 depth, 200000 nodes
tổng JSON, string/key 65536 ký tự. Caller chỉ được giảm trần. JSON key trùng,
NaN/Infinity, invalid UTF-8/malformed/deep hoặc source đổi lúc đọc fail closed
không trả report một phần. Binary phải kind explicit, không cố parse JSON.
Path relative canonical; từ chối absolute/drive/.. /backslash/ADS colon;
root và ancestors/source components không symlink/junction. Kiểm resolve scope
và ancestors ngay sau open và sau read, stat/fstat inode/device/size/mtime.
Không claim raceproof filesystem tuyệt đối trước tác nhân thay đổi path liên
 tục; caller dùng fixture/bản sao không có writer đồng thời.

Diagnostic không echo payload/path unknown: thiếu stage/actor ID, units/scale,
blocking văn bản, state/beat/hidden/at/in/POV/move/locks chưa reconcile được đánh
unresolved; raw vẫn giữ nguyên người gục/trong giếng, subject.id/end_actor,
beat/end state, spec overrides, source/approval history. Không chuyển at/in
hay tạo spawn tường từ mô tả, không tự nhân scale=1, không gán assets ID theo tên.
Valid look pin cũng look_domain_pending tới khi người dùng chốt bộ dạng/ảnh/hash.
Approvals source chỉ lấy field approved_round explicit cho diagnostic round;
không có/khác/nhiều round báo unknown/ambiguous, không làm approved A mới.

`restore_payloads(report)` chỉ trả tuple(relative_path,raw_bytes) đã kiểm
hash/path/trùng để caller đối chiếu restore trên bản sao; không ghi tệp/DB.
Test restore tạo thư mục tạm riêng và chứng minh byte-for-byte. Production
restore/import/write là bước riêng cần quyền, backup và reconcile được duyệt.

Bằng chứng fake #24/#27: lượt 1 ĐỎ 17 failed/4 errors (thiếu module); lượt 2
20 passed/1 skipped native symlink; lượt 3 27 passed/1 skipped; root quickread
sau lượt 3 bổ sung malformed kind + ancestor/link race checks; lượt xác nhận 4
**33 passed/1 skipped (0.90s)**. Skip do Windows thiếu quyền tạo symlink; có
mocked ancestor/link swap coverage. Không nới test, không QA data sản xuất.


### Sau rà độc lập inventory PARTIAL

Explicit specs được kiểm thuần trước root filesystemlookup. Root phải local,
không UNC/device/networkURL; paths portablecanonical còn reject reservedWindows
CON/NUL/PRN/AUX/COM/LPT, trailingdot/space/ADS và casefoldalias duplicate. Source
root/ancestors checks vẫn áp dụng, không claim chặn mọi mappednetworkdrive/race.
Mỗi read bounded theo remainingtotalbytes, không mở secondfile đã vượt budget.

restore_payloads còn kiểm report shape immutable/bounds/PARTIAL/readyFalse,
project/version/sortedmetadata, sourcebytes SHA/mapping và inventoryhash, rồi
trả bytes thuần. Identity digest là integrity **không phải chữ ký hoặc xác thực
người approve**; ai recompute report+hash cũng không được quyền write/activate.
Tuplesources/mappings/issues và byte/type/budget malformed fail sanitized trước
hash; JSON nguồn nonbinary vẫn theo trần depth/nodes chung. Không sourcewrite.

Unknown scaleobject(valueNone/confidenceunknown), invalidfalse/0/negative/empty
hoặc thiếu measuredsource rõ được missing_scale; malformedstableID cũng
unresolved, raw giữ nguyên. Numericpositive scale chỉ declaredlegacyvalue,
không nghiệm thu measured. Các diagnostics không semanticconvert hoặc approve.
Reviewer 22RED +12REDguards → **67passed/1skip/2.17s**,3targetedlượt1file;
không broad/fullsuite. PARTIAL vẫn là phạm vi của toàn công việc hiện tại.
