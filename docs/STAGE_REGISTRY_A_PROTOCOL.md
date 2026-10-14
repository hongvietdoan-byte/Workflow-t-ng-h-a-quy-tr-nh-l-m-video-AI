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
