# Bàn dựng 3D — Đợt 11 việc 1

Ngày 12/10/2026 · **Thiết kế + prototype offline, chưa phải tính năng Dashboard.**
Nguồn: `CODEX_TASKS.md` Đ11; `PHUONG_PHAP_SAN_KHAU_3D.md` mục 2, 12b, 13, 14;
`THIET_KE_TIEU_NHI_LAO_DAI_D7.md` mục 6. Không sửa sân khấu, dữ liệu hay ảnh thật #24.

## 1. Người xem cảnh có sẵn, chỉ chỉnh khi cần

Bước 1, cạnh Đạo diễn, mở Bàn dựng. Đạo diễn khai khối + vị trí/hướng/tư thế đầu–đỉnh–cuối BYĐ
cho từng cảnh; code kiểm khai báo rồi bộ giải đặt máy. Thiếu vật, kích thước, sàn, nguồn Kho hoặc BYĐ:
hiện lý do thiếu, không lặng lẽ bịa số. Người lật trước/sau, so cuối cảnh trước với đầu hiện tại,
xem nhìn từ trên hoặc từ camera; không phải dựng sân khấu tự do từ đầu.

Chọn cảnh → chọn nhịp/nhân vật → kéo hoặc nhập `(x,y,z)`, tên ô, hướng mặt, tư thế → kiểm số tức thì
→ xem trước → ghi lý do và lưu revision mới. Mục tiêu việc 3: dời nhân vật 1 m và xem kiểm số ≤2 bấm
(kéo + xem); nhập/lưu lý do và duyệt lan được đo riêng, chưa nghiệm thu chỉ bằng mockup.
Ca minh họa: giếng tâm `(-0,50;0)`, bán kính 0,50 m, mép phía Đông x=0; yêu nữ bò tới
x=1,25 m tức cách mép 1,25 m (không nhầm tâm), Kelly lùi y=-1,50 → -2,10 m. Đây là fixture
dựng lại ý lỗi #24, không phải snapshot sản xuất hay số đo hiện trường.

`manual_lock` là tên hiển thị prototype. Hợp đồng backend cần ánh xạ khóa `_user_locked`/`lock_user`
của nguồn tương ứng, khóa theo field + nhịp + đối tượng, không chỉ một boolean cả cảnh. Chạy lại Director
phải nhận khóa làm ràng buộc, giữ nguyên field tay. Cuối cảnh trước kế thừa vào đầu cảnh sau chỉ khi cùng
không gian/đối tượng; cảnh đổi bối cảnh/thời gian phải có ngoại lệ rõ, không suy đoán liên tục.

## 2. Lan đề xuất, không ghi đè cảnh khác

Lưu một cảnh tạo diff cuối cảnh → đầu từng cảnh phụ thuộc; lan theo chuỗi scene/shot thực, không nhân
cùng số vào mọi cảnh. Đề xuất chứa scene đích, field cũ/mới, lý do, source revision/hash, khóa liên quan.
Mỗi cảnh có **Chấp nhận / Bỏ**; xem lại kiểm số trước khi nhận. Nhận cảnh kế làm mới các đề xuất xa hơn
theo đầu/cuối mới; bỏ một cảnh giữ số cũ và cảnh báo đứt liên tục, không tự ép các cảnh sau.
Cảnh đã duyệt chỉ cảnh báo `layout_drift`/“ảnh cần vẽ lại”, giữ baseline, ảnh, máy và dữ liệu duyệt.
Muốn đổi phải bỏ duyệt có chủ ý qua luồng duyệt hiện có, rồi xin báo giá gen lại; editor không tự gen.
Khóa tay cảnh đích cần quyết định cụ thể “thay khóa này” với diff, không tự gỡ.

## 3. Màn camera

| Thao tác/hiển thị | Hợp đồng triển khai |
|---|---|
| Góc nhìn đạo diễn | Sàn, khối, O, trục, lưới 1 m + phụ 0,25 m, nhân vật, camera, nón nhìn, đường đầu→cuối |
| Góc nhìn camera | Clay từ đúng máy, tỉ lệ dự án; 9:16 có safe area UI nền tảng, chân trời và mắt % khung; không có Blender thì hình chiếu 2D + lý do |
| Vị trí | Kéo/nhập x,y,z hoặc tên ô; `cell_name` chỉ tên, không làm mất tọa độ liên tục |
| Hướng | Yaw 0° Bắc +y, tăng theo chiều kim đồng hồ; pitch dương ngửa, âm cúi; chuyển sang location/look_at, không lưu hai nguồn mâu thuẫn |
| Quang học | Cao so sàn, tiêu cự mm, cỡ WS/MS/MCU/CU, ngang mắt/thấp/cao/qua vai/POV; cỡ/góc là yêu cầu solver, không thay nhãn để giả đạt |
| Đường máy | static/push/pull/pan/follow, điểm đầu/cuối; xem đường và kiểm theo nhịp. camera_move UI chuyển sang schema `stage_camera.move` thật khi tích hợp |
| Kiểm | `clearance_fix`, khoảng cách tối thiểu, máy thấp không ngửa quá; `frame_eval`/`check_spec`, facts, chồng lấn, tia che khuất. Không đo được → VÀNG, không “đạt” |
| Sửa | ĐỎ/VÀNG có đề xuất số + xem diff; nhấn sửa giữ manual lock, tính lại, cảnh đã duyệt không bị đổi |

Khung an toàn không phải một chuẩn cố định: preset TikTok/Reels + phiên bản vùng che, có thể tắt,
không cắt dữ liệu hình học. Prototype dùng vùng minh họa 10% trái/trên, 15% phải, 20% dưới,
chưa hiệu chỉnh. “Giải máy” tái dùng solver hiện tại, không viết solver JavaScript mới.
White model video theo đường máy là tùy chọn sau: Blender cục bộ, 0 USD nhà cung cấp, có thời gian/máy;
chưa nằm trong việc 1. Không đưa khối xám vào ảnh nền cho model chép thành chi tiết thật (`stand_in`).

## 4. API thực đã mở và đối chiếu

Số dòng tại base `08c11b4`; tham chiếu tên hàm là chính. **Bảng là điểm nối dự kiến, không tuyên bố đã nối.**

| File:dòng / API thật | Dùng lại |
|---|---|
| `core/stage_grid.py:23 make_stage`, `:61 cell_name`, `:79 cell_centre` | O cố định, 20×20, ô 1 m; O góc Tây-Nam K11, tâm (0,50;0,50); +x Đông/+y Bắc/+z lên |
| `core/stage_grid.py:694 frame_eval`, `:734 check_spec` | Chiếu/khung và luật số, ngưỡng có nguồn |
| `core/stage_solver.py:356 solve_shot`, `:555 solve_scene` | Bộ giải sẵn có; solve_scene(specs, blocking, aspect, marks=None, grid_cells=None, stage=None) |
| `core/plate_camera.py:144 camera_for`, `:250 clearance_fix`, `:100 vfov` | Đặt máy thông thường, kiểm độ hở, FOV; không dùng camera_for ghi đè máy đã giải/khóa |
| `core/plate_camera.py:339 project`, `:307 horizon_y`, `:376 from_stage` | Chiếu pinhole, chân trời, dùng máy stage đã khóa |
| `core/stage_facts.py:390 derive`, `:281 horizon`, `:542 for_shot` | Sự thật chung cho prompt/QC/editor; derive trả `{facts, missing}`; missing phải hiển thị |
| `core/blockout.py:143 check_geometry` | Kiểm khối, chỗ đứng và vật kịch bản |
| `core/blockout_sheet.py:53 render_top_view`, `:146 to_location_pack`, `:157 read_location_pack` | Tấm nhìn từ trên; gói blockout có người duyệt/ngày/phiên bản/SHA; đọc báo luật đổi |
| `tools/stage_grid.py:1308 v2_main`, `:1024 run_blender` | CLI v2 đọc blocking/specs/stage/grid, gọi solve_scene, ghi setups, đo Blender; --solve-only không Blender |
| `tools/stage_grid.py:1508 review_stage_round`, `:1522 v3_main` | Review nối finding khi cờ bật; v3 Director tốn tiền phải báo giá, không gọi từ prototype |

`tools/stage_grid.py` là CLI có ghi file/DB, không đưa argv do trợ lý tạo tự do vào Dashboard. Việc 3
cần tách/bọc service có ACL/revision/path kiểm, tái dùng các hàm thuần trên, giữ CLI y nguyên.
Chưa có service editor apply/undo/queue trong việc 1; không tạo API giả rồi nói đã chạy backend.
R1 đọc lại dàn cảnh từng nhịp; R2 đọc lại máy bằng số + hình; mỗi điểm ≤2 vòng, thiếu/mâu thuẫn hỏi
Director bằng `advice`/`can_hoi`. Lời gọi Director tốn tiền chỉ sau báo giá, qua sổ chi. R3 QC so ảnh
với chuẩn thật, sửa đầu vào trước gen lại, không dùng mockup thay phép đo.

## 5. Dữ liệu, quyền, revision và render (thiết kế việc 3)

CLI hiện đọc `stage.json`, `grid.json`, `blocking.json`, `shot_specs.json`, ghi `setups.json` trong
thư mục `stage_v2_*` người vận hành chọn. Không sửa trực tiếp bộ đó. Đề xuất editor lưu bản sao
`data/projects/<pid>/stage_editor/scenes/<scene_id>/revisions/<revision>/` gồm blocking/specs/setups,
`revision.json` chứa parent revision, baseline SHA, actor user id, UTC, lý do, nguồn Director/Kho,
lock theo field, dependency revisions, camera/block hash, trạng thái duyệt. Revision bất biến;
current pointer đổi nguyên tử sau ACL + expected_revision/CAS. Tranh chấp → giữ draft, trả diff
để người xử lý; không last-write-wins. Đường dẫn resolve dưới project root, ID từ server, không nhận
path từ Tiểu Nhị. Nếu ghi dữ liệu thật phải sao lưu trước theo AGENTS.

Đồng nghiệp có quyền sửa dự án chỉ sửa bản sao dự án được cấp; xác minh quyền phía server mỗi apply.
Kho chung/location_pack chỉ Owner, qua hành động riêng có diff và người duyệt. Không suy quyền từ nhãn
UI. Hoàn tác nhiều bước tạo revision mới tham chiếu revision đích, có ai/lúc/lý do, giữ audit và
khóa tay; undo cũng tái kiểm baseline ảnh/đề xuất lan và ACL. Prototype RAM không có bảo đảm bảo mật
hay bền vững; nút Kho bị vô hiệu hóa không phải triển khai ACL.

Render clay: một worker cục bộ, queue theo project/scene/revision; debounce kéo, render khi thả hoặc
bấm xem. SHA256 JSON chuẩn hóa máy đầu/cuối + toàn bộ khối/poses/nhịp + stage transform + aspect +
resolution + renderer/mesh/material version (không chỉ camera); cache hit dùng ảnh + metadata nguồn.
Yêu cầu trùng hash hợp nhất; cũ bị thay trong queue, job đã chạy không xuất vào revision mới. UI:
đang chờ/đang render/xong/lỗi/hủy/cache hit, tuổi ảnh/hash/revision; lỗi/thiếu Blender hiện lý do +
projection 2D, không gắn nhãn clay thật. 0 USD không có nghĩa không tốn CPU; không tự gọi API dự phòng.

## 6. Tiểu Nhị và thao tác nhanh

Tiểu Nhị “nâng máy 0,3 m để không thấy miệng giếng” tạo proposal cho một scene/revision cụ thể,
không quyết thay người. Tool adapter tương lai đọc snapshot + khóa + facts; dry-run dùng cùng
`frame_eval`/`check_spec` và `stage_facts.derive`, solver dùng `solve_scene`; projection dùng
`plate_camera.project`/`horizon_y`. Người xem số trước/sau, kiểm và giá 0 USD rồi duyệt qua **cùng
service editor** (chưa triển khai), server kiểm quyền/CAS lần nữa. `review_stage_round` dùng để
báo `layout_drift`, không phải công cụ apply. Tool không chạy v3/Blender/ghi Kho trực tiếp, không
nhận shell/path, cảnh approved chỉ warning. Không có server identity → chỉ cho xem đề xuất.

Phím ←/→ lật cảnh, Ctrl+Z undo (bỏ qua khi nhập), X/Y khóa trục, Esc bỏ khóa; snap CU/MCU=0,05 m,
MS=0,10 m, WS=0,25 m. Chép máy sang shot/cảnh kế chưa duyệt chỉ sau bấm dán, cần so bố cục/khóa,
không tự lan; ảnh đã duyệt vẫn cảnh báo. Tất cả thao tác qua một luồng revision ở ứng dụng thật.

## 7. Tần suất × công sức và thứ tự

F là giả thuyết theo ca #24 11/10, chưa telemetry; công S=1, M=3, L=6 theo D7 mục 6, điểm F/công.

| Tính năng | F | Công | Điểm | Lý do/cổng |
|---|---:|---|---:|---|
| Lật/so cảnh dựng sẵn | 4 | S | 4,00 | Xem nhanh trước sửa, cao nhất trong editor |
| Chỉnh BYĐ/vị trí + khóa tay | 4 | M | 1,33 | 0,25→1,25 m sau động tác bị mất |
| Đề xuất lan từng cảnh | 4 | M | 1,33 | Không phá bố cục đã duyệt; sau revision/ACL |
| Approved baseline/diff/audit/undo | 4 | M | 1,33 | Cổng trước apply, ưu tiên hơn điểm |
| Camera/solver/clay | 3 | L | 0,50 | Máy thấp vẫn vẽ thấy lòng giếng; tái dùng API |
| Cache/queue một worker | 3 | M | 1,00 | Sau camera, bảo toàn revision/hash |
| Phím tắt/khóa trục/chép máy | 3 | S | 3,00 | Sau apply an toàn; không vượt cổng dữ liệu |
| Tiểu Nhị đề xuất máy | 3 | M | 1,00 | Sau service + identity, không tool ghi tự do |

Thu 30 ngày loại thao tác/thời gian/số lần sửa/cache hit/undo rồi chấm lại. Đ11v1 chỉ thiết kế;
v2 kiểm/render thật; v3 sau #24 xong và thiết kế được duyệt. Cờ stage_editor TẮT mặc định.

## 8. Prototype và tiêu chí kiểm

`mockup/ban_dung_3d.html`: native HTML/CSS/SVG, offline, fixture 3 cảnh; không DB/API/Blender/CDN.
Có lật/so, nhịp BYĐ, kéo nhân vật/máy, nhập mét/ô/hướng/tư thế, khóa trục/snap, undo nhiều bước,
camera đầu/cuối/yaw/pitch/lens/cỡ/góc/chuyển động, pinhole preview/chân trời/mắt/safe area, cảnh báo
minh họa và sửa cao máy, nhận/bỏ đề xuất riêng, approved chỉ đọc, reason/version RAM, copy/paste.

Giới hạn rõ: khóa boolean cả cảnh; đề xuất fixture chép cuối cảnh đang xem vào đầu cảnh được nhận,
chưa tính chuỗi phụ thuộc thật; undo RAM, refresh mất; không auth/CAS/hash cache/worker; chưa
ray tracing/clearance đầy đủ/stage_facts; cỡ/góc/move là khai báo, chưa solver/animation thật.
Nút solver/render/Kho tắt. Không claim nghiệm thu 12b.4, ngưỡng 2 bấm, chất lượng hay quyền backend.
Ca thật và cả bộ Windows phải chạy ở bước tích hợp/triển khai theo AGENTS.

Test đỏ trước file thiếu; sau đó Playwright Chrome mới headless, profile tạm, chặn mạng ngoài file:
1440/1280, kéo thật, nhập số, undo, nhịp cuối, accept/reject riêng, approved không đổi, lens làm
preview đổi, nút fix, so cảnh, console/overflow; ảnh hai góc lưu `docs/images/d11/`.

## 9. Đối chiếu Clip AI — bảng đánh giá Đ11 việc 1b, chờ chốt

Ngày 13/10/2026, base `3d6004bb`. Đã xem cả ba ảnh `clipai_ref_xoay_goc_nhin.png`,
`clipai_ref_nhan_vat.png`, `clipai_ref_camera_toan_canh.png` trong `docs/images/d11/`.
Ảnh chứng minh bố cục màn hình và nhãn điều khiển; không chứng minh thuật toán/API/chất lượng render
của Clip AI. Không cần gọi Clip AI để đối chiếu này. Mail 12/10 11:41 và luật chung (c) yêu cầu
người dùng chốt bảng trước khi dựng mockup. Bản dưới là **đề xuất**, chưa được duyệt.

Tần suất Cao/Vừa/Thấp là giả thuyết từ lỗi #24/#27 đã ghi trong đề, chưa có telemetry.
Công S/M/L là so sánh tương đối cho nâng prototype offline; backend/render/ACL ghi riêng,
không phải cam kết ngày công. Lợi ích chưa đo click/tiền: không gán số tiết kiệm giả.

| # | Dòng Clip AI / nhu cầu | Tần suất | Lợi ích cụ thể | Công mockup / backend | Rủi ro | Khuyến nghị và bản tối thiểu |
|---|---|---|---|---|---|---|
| 1 | Dựng tay từ trống → Đạo diễn dựng sẵn | Cao | Xem trước sửa, giữ liên tục | S / L | Giả có Director production | **LÀM**: fixture dựng sẵn; không thêm nút dựng cảnh trống |
| 2 | Khung camera nổi | Cao | Kéo và thấy khung cùng lúc | M / M | Preview cũ bị tưởng render mới | **LÀM**: khung thu/phóng, tên/hướng/safe area; ghi projection và trạng thái nguồn |
| 3 | Toàn cảnh / nền map / phông xanh | Vừa | Nhận biết đúng vùng máy quay | M / L | Panorama 2D bị coi map 3D thật | **LÀM BẢN GỌN**: chọn lớp nền fixture/phông xanh, nhãn nguồn; tải panorama để sau |
| 4 | Hướng ánh sáng | Vừa | Thấy lệch giờ/thời tiết | S / M | Một slider không mô phỏng đèn/map | **LÀM BẢN GỌN**: nguồn giờ/thời tiết + chỉnh nâng cao, cảnh báo minh họa |
| 5 | Nhiều camera/góc phủ | Vừa | Dùng lại góc khi đối thoại | M / L | Đồng nhất camera với shot | **LÀM BẢN GỌN**: máy chính + góc phụ fixture; chọn setup, không nhân toàn bộ scene |
| 6 | Vị trí/đích/roll/FOV → ngôn ngữ nghề | Cao | Sửa bằng cỡ cảnh/nhìn vào người | M / M | Cỡ cảnh không tương đương lens tự động | **LÀM BẢN GỌN**: mm↔FOV với sensor/aspect rõ; cỡ cảnh là yêu cầu solver, target tên/số; roll nâng cao có lý do |
| 7 | Dùng góc hiện tại / về mặc định / giải máy | Vừa | Chỉnh ít thao tác, hồi phục đề xuất | M / M | Orbit vô tình đổi máy, ghi đè khóa | **LÀM BẢN GỌN**: chép có diff/xác nhận; mặc định là baseline Director; solver chưa nối thì nút tắt có lý do |
| 8 | Nhân vật tên/màu/XYZ/xoay/tỉ lệ | Cao | Không sai người hoặc kéo cao tùy ý | S / M | Thiếu hồ sơ mà bịa chiều cao | **LÀM**: cast fixture ID ổn định, chiều cao có nguồn/unknown, ẩn scale tùy ý |
| 9 | Tư thế theo đầu/đỉnh/cuối BYĐ | Cao | Thấy động tác không bị mất | M / L | Tư thế proxy khác cơ thể thật | **LÀM BẢN GỌN**: ba nhịp, thư viện fixture và nhãn chưa đo |
| 10 | Vật thể Kho/stand_in | Cao | Đúng kích thước/vật che | M / L | Khối tạm bị gửi thành chi tiết thật | **LÀM BẢN GỌN**: đạo cụ fixture có provenance; stand_in chỉ xem |
| 11 | Nút Hoạt ảnh | Vừa | So đầu→cuối thay ảnh tĩnh | S / L | Trùng dòng timeline #18 | **LÀM BẢN GỌN**: chỉ một nút phát nối #17, không dựng hệ hoạt ảnh thứ hai |
| 12 | Lưu preset thư viện | Thấp–Vừa | Dùng lại góc có chủ đích | M / L | Mang state/duyệt/quyền giữa dự án | **ĐỂ SAU**: cần revision/ACL/remap; mockup mới không có nút lưu giả thành công |
| 13 | Ảnh kết quả vào Gói gửi kèm | Cao | Không tải xuống rồi tải lên tay | M / L | Gói mockup bị coi payload provider | **LÀM BẢN GỌN**: bảng xem lớp/nguồn sẽ gửi; nút gửi thật tắt, không thêm auto-gen |
| 14 | Phím V/R/S/F/T/Q/Del/Esc/Undo, panel | Vừa | Tập trung khung xem | M / M | S phá chiều cao; Del xóa state | **LÀM BẢN GỌN**: V/R/F/T/Q/Esc/Undo/←→, panel; S chỉ xem kích thước, Del cảnh báo không hỗ trợ; không giữ phím nguy hiểm chỉ để giống Clip AI |
| 15 | Orbit/pan/zoom góc người xem | Cao | Thấy vật sau tường, không đổi máy | L / L | Prototype SVG giả orbit; clipping chưa đo | **LÀM BẢN GỌN**: orbit/pan/zoom fixture, T/Q/F và góc nhanh; nhớ theo scene; không claim chống xuyên map khi chưa đo |
| 16 | Setup dùng chung nhiều shot, không trần 10 | Cao | Chỉnh một góc và xem các shot phụ thuộc | M / L | Lan máy ghi đè approved/state | **LÀM BẢN GỌN**: registry setup fixture + danh sách shot dùng; diff trước áp, approved chỉ VÀNG; cuộn ảo để sau khi có đo danh sách lớn |
| 17 | Keyframe vật/người/máy theo giây | Vừa | Kiểm lộ ra/move đúng thời điểm | L / L | Sinh editor animation đầy đủ; model không nhận keyframe | **LÀM BẢN GỌN**: keyframe mặc định BYĐ/move, chọn/kéo mốc và phát proxy; thêm/xóa/chép/K/curve nâng cao **ĐỂ SAU**; không giả phép đo speed/collision |
| 18 | Map + clay, xuất lớp và che khuất | Cao | Phân biệt xem với nguồn thật gửi model | M / L | Clay/stand_in lọt refs; nền render sai camera | **LÀM BẢN GỌN**: ba lớp xem + nhãn sẽ gửi/chỉ xem, thiếu map VÀNG; ray/LOD/Blender/render cuối thuộc v2/3 |
| 19 | Người bị che, H, visibility/ý đồ/QC | Cao | Kelly không hiện ra sai phía tường | M / L | Tia proxy thiếu mesh vẫn tuyên bố chính xác; bỏ ref người sẽ lộ giữa clip | **LÀM BẢN GỌN**: fixture che/partial/lộ giây 2, H chỉ viewer; nhãn unknown khi chưa đo. Dịch prompt/ref/QC thật **ĐỂ SAU** adapter v2/3 |
| 20 | Xuất/nhập JSON + ảnh | Thấp | Chuyển fixture kiểm được | M / L | Path/schema/asset IDs khác scope; import ghi thật | **ĐỂ SAU**: chốt schema/revision/ACL trước; xuất ảnh fixture từ #2 đủ cho duyệt giao diện |

Dòng #11 ứng với “Hoạt ảnh”; #17 là dòng KEYFRAME đầy đủ sau dòng setup. Hai dòng dùng cùng
một timeline, không bỏ sót hay nhân đôi. Đề có 20 dòng; bảng giữ đủ 20, gom tùy chọn phụ trong
chính dòng và ghi rõ phần để sau. **KHÔNG NÊN** kéo scale người tùy ý, xóa vật có phụ thuộc không
qua diff, hoặc coi panorama là map 3D; đây là phần bị loại trong các dòng 3/8/14.

### 9a. Mô hình chung với Đ18, không xây sân khấu riêng theo từng shot

Đối chiếu kế hoạch Đ18v1 `d52253e6`, `KE_HOACH_SAN_KHAU_DOAN_2026-10-12.md` mục 2–3
(bản nhánh nếu main chưa tích hợp): **stage_id** là sân khấu vật lý + nguồn/transform;
**segment_id** là đoạn hành động truyện; **state_id** là mốc/patch người và vật. Quay lại cùng chỗ
không tạo stage mới hoặc reset người gục. Gloo wall spawn tại state/event, không tồn tại từ đầu.
`camera_setup_id` là registry thiết lập máy thuộc stage, nhưng setup có phiên bản và tham chiếu
snapshot/target rõ; shot liên kết setup + state_start/end + keyframes. Đổi camera không dời người.
Thiết lập tương đối theo target phải resolve trên state của shot; hai state khác nhau không tự cho
khung giống nhau. Keyframe patch theo object ID trên khoảng thời gian shot, không đổi base map.
Chỉnh setup dùng chung chỉ tạo proposal tới shot phụ thuộc; shot approved chỉ cảnh báo. Preset
cross-project không mang approval, IDs hoặc state tạm; cần remap/provenance và quyền riêng.

Đ18 A/B/C vẫn chờ chốt; bảng này **không** ngầm chọn B hoặc cho phép Đ18v4/backend editor.
Nếu chọn A trước, viewer proxy/2D phải ghi rõ chưa có map/render thật; lớp visibility unknown,
không tự bật tính năng hình học chỉ để hình giống Clip AI.

### 9b. Điểm nối đã mở code, chưa nối backend

Số dòng kiểm lại tại base `3d6004bb`; tên hàm là định danh chính.

| Nguồn/caller | Điểm nối và giới hạn |
|---|---|
| Plates/map | `core/location_pack.py:368 plan`; `core/plate_camera.py:146 camera_for`, `:404 from_stage`, `:428 plan_cameras` — render nền và setup phải cùng snapshot/camera. plate là ảnh dẫn xuất, không phải mesh map |
| Máy/kiểm | `plate_camera.py:102 vfov`, `:271 clearance_fix`, `:328 horizon_y`, `:367 project`; `stage_solver.py:555 solve_scene`; chưa có phép đổi cỡ cảnh↔lens bảo đảm đạt mà không giải hình học |
| Ánh sáng | `core/plate_env.py:44 time_of`, `:54 weather_of`, `:62 env_of`, `:67 blender_env` — môi trường đầu vào; không suy preset này đo được ánh sáng ảnh đã duyệt |
| Cast/Kho | `core/assets.py:1035 project_assets`, `:1639 scene_references` — nguồn tài nguyên/refs dùng chung; cast ở dữ liệu dự án, không tồn tại module `core/cast.py`; adapter cần lấy cùng ID/look, không danh mục mới |
| BYĐ/dữ liệu shot | `core/llm_io.py:445 update_scene`, `:426 update_scenes_bulk`; backend editor phải đi cùng quyền server và change_review, không ghi scene JSON từ HTML. Nhịp fixture chưa chứng minh Director production khai số |
| Facts/visibility | `core/stage_facts.py:390 derive`, `:542 for_shot` — facts+missing hiện có không đồng nghĩa đo đầy đủ đầu/mắt/vai/thân/chân mỗi keyframe; thiếu mesh/tia thì unknown VÀNG |
| Blockout/Kho chung | `core/blockout_sheet.py:53 render_top_view`, `:146 to_location_pack`, `:157 read_location_pack` — pack có duyệt/SHA, không dùng nút mockup làm ACL Owner |
| Gói gửi kèm | `core/runner.py:2602 sendable_references`, `:2901 _finish_args`; adapter tương lai cần lớp/provenance/hash và cùng giới hạn refs. Đ11v1b chỉ mô phỏng bảng gói, không sửa runner hoặc gửi provider |

### 9c. Phạm vi mockup đề nghị để người dùng chốt

Một cảnh đã dựng sẵn, ba shot dùng hai setup, hai nhân vật và tường/giếng fixture. Giữ cảnh
approved chỉ đọc. Mặc định chỉ khung xem + preview nổi + nhịp; chọn vật/máy mới mở bảng số,
Toàn cảnh/phím nâng cao/lớp gửi thu gọn. Giữ khóa tay/diff/undo RAM có nhãn rõ.

1. Kéo/orbit/pan/zoom viewer không đổi shot camera; nút chép góc mới cho diff. Xem camera đổi
   trực tiếp khi sửa máy/vật, chỉ projection fixture; lưu viewer theo cảnh, T/Q/F hoạt động.
2. Nhìn setup→shot; chọn nhịp/keyframe mặc định, kéo mốc, phát proxy minh họa. Tư thế/chiều cao
   có nguồn fixture; cỡ cảnh là yêu cầu, lens/FOV được đổi theo mô hình sensor có nhãn.
3. Hiện nguồn nền/lớp và trạng thái gửi; H/ghost không đi vào ảnh xuất. Ba ca người bị che dùng
   dữ liệu fixture, không tự tính tia rồi tuyên bố QC thật. Nút chưa nối solver/Blender/Kho/API tắt.
4. Sau chốt mới sửa HTML/test; kiểm offline 1440/1280 hai góc, ảnh thư mục d11; tests xuất ảnh
   vào thư mục tạm để không ghi đè ảnh tài liệu; chỉ cập nhật PNG có chủ ý trong bước nghiệm thu.

Nghiệm thu đo: số thao tác cho đổi setup/xem khung, baseline prototype cũ và mới cùng fixture;
0 console/overflow; orbit không đổi camera; H/lớp xem không lọt ảnh xuất; approved bất biến;
phím không xử lý khi nhập; refresh mất RAM được báo. Chưa có kết quả mới và chưa thử dữ liệu thật.
