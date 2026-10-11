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
