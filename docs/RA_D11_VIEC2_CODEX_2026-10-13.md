# Đ11 việc 2 — bản làm và tự kiểm 13/10/2026

Nhánh `codex/d11-viec2-clay`, base `e513a567`, chưa commit/push/gộp.
Hai cờ `blockout_clay_sheet` / `director_blockout` OFF, OPT_IN_ONLY; areas version giữ 68.
Chi nhà cung cấp 0 USD, chỉ Claude/bpy/ảnh/CSDL giả; Blender thật do root điều phối trên fixture.

## Phạm vi và hợp đồng caller

- `core/blockout_clay.py`: config không model, dùng `blockout.to_props`, `plate_camera.camera_for` khi chưa có máy;
  máy đã giải được giữ nguyên; 3 góc bổ sung, topview và ảnh tham chiếu thành một tấm.
- `tools/render_plates.py`: nhánh config `blockout_clay` dựng sàn/khối bằng `add_props`, vật liệu `clay_material`;
  người đứng từ `whitebox.plan` + `add_actor`, không bộ dựng mới. Nhánh model cũ giữ nguyên.
- Lỗi/thiếu Blender → projection pinhole 2D + lý do loại lỗi; không in raw exception/config/khóa.
  URL/UNC bị chặn trước khi đọc; mỗi render thư mục tạm mới, chưa cache. `tru/cot` topview là ellipse.
- `stage_director.build_prompt/validate_answer` thêm JSON enum/geometry chỉ khi cờ bật và cảnh dùng Nhánh C.
- V3 đọc `assets.profile.model3d`: có model thật → prompt/validator/render V3 cũ; hồ sơ thiếu/hỏng dừng trước paid call.
- ON: một lời gọi đầu + tối đa hai sửa, tổng ≤3 `complete`; cùng fingerprint lỗi ĐỎ lặp hai lần dừng/hỏi;
  estimate trước mỗi call, `tagged` và client có ledger;
  tắt retry mạng trong call rồi khôi phục, không ask_json retry ngầm. Retry đổi input bằng lỗi/answer/lượt sửa.
- Validator giữ schema cũ, kiểm blockout, khóa/kế thừa, map props vào blocking và chạy `stage_solver.solve_scene`;
  numeric/camera fail được phản hồi trong cùng ngân sách 3 call. Nhánh C không đòi model qua `v2_main`.
- Render CLI dùng cam `at/aim/lens` đã giải, người đúng nhịp đầu của shot đầu và aspect dự án.
  File numeric ghi `measurement=numeric_only`, in rõ chưa đo che khuất/khung Blender.
- Input cần `same_space: bool`, `previous_end: blockout` khi liên tục, `locked_blocks: {id:{field:value}}`,
  `cho_dung: list`, `vat_kich_ban: list`, `blockout_reference` đường cục bộ nếu có.
  Thiếu danh sách → VÀNG; khóa hỏng/kế thừa thiếu/mâu thuẫn → ĐỎ; không tự suy liên tục từ tên cảnh.

## Bằng chứng đỏ → xanh

- Ban đầu collection ĐỎ do thiếu hai module. Nhóm đầu 82 qua/1 hỏng; fixture khóa khai id wall nhưng box là a:
  sửa fixture thành wall, giữ nguyên assert. Có đỏ caller ON vì v2 đòi model; sửa caller dùng solver chung.
- Fixture stage ban đầu thiếu `cell_m`: bổ sung `stage_grid.make_stage`, không sửa/nới test solver.
- Nhóm cuối: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider --tb=no` với
  `test_d11_clay`, `test_blockout`, `test_blockout_sheet`, `test_stage_director`, `test_plates_f2`,
  `test_whitebox`, `test_devsys_stages`, `test_devsys_decisions`: **136 passed / 19,90 s**.
- SHA prompt OFF so với source tại base từng byte: `b44d4c04d5350e4c815e91e2df2885223054f096f1e82be916c8abb762e795ef`.
- Ba bối cảnh giả loại tường/cây/bậc dựng sheet + kiểm <120 s/ca; thiếu vật/chồng lấn bị bắt.
  Đây là kiểm luồng giả, không chứng minh bậc nhiều cao độ/7 trên 9 shot/chiếu ảnh ≤5%/duyệt một lần.
- `compileall` các module đổi, `git diff --check` sạch; không `--showlocals`, không gọi loader credential thật trong test mới.

## Tự kiểm và rà các khâu liên quan

Đã chạy `py tools/related_areas.py` cho các module đổi: plates3d + core_infra, callers stage_director/stage_grid,
whitebox/render_plates; các vùng dùng features (assets/step1–5/autopilot/budget/knowledge/dashboard/diag/lipsync).
OPT_IN_ONLY loại hai cờ khỏi bật hàng loạt; OFF giữ prompt hash/đường ask_json+v2 cũ; không tác động đường gửi job.
Tự kiểm skill 2b.5: không nới assert, path cục bộ/thư mục riêng, không default ON, không bỏ dấu khớp từ,
không auth/data thật/API/maintenance; lỗi nhận thiếu input ghi issue. Root điều phối rà độc lập theo CLAUDE 7.

| Biện pháp | V3 CLI Nhánh C | Dashboard / autopilot / v2 / multi-shot / nhân bản |
|---|---|---|
| Source Kho, model3d giữ đường cũ | Guard trước call | Chưa nối tính năng |
| JSON/schema + geometry + camera | Có, numeric chung | Luồng cũ giữ nguyên |
| Khóa/kế thừa | Input explicit, không ghi đè | Chưa adapter lấy khóa/chuỗi từ Dashboard |
| Estimate/ledger/retry thay input | ≤3 call, tagged/client ledger | Không phát sinh call mới |
| Clay/stand_in | Config local + metadata | Không xuất vào gói gửi job |

## RÀ KỸ độc lập và vòng sửa gộp

Ba nhóm finding đã sửa trong code, có hồi quy giả; QA Blender sau sửa do root xác nhận trước commit:

1. **P1 — người/vật theo nhịp thoát khỏi plan**, `core/director_blockout.py:81`, `tools/stage_grid.py:1599`:
   `blocking_from_plan` kiểm base và TẤT CẢ `beats` qua `objects_from_blocking`, bắt tâm người ngoài sàn/trong khối;
   vật từ plan giữ vị trí/z/cỡ, không tự giấu theo nhịp. Id khối không được trùng người/mốc.
   Giới hạn rõ: kiểm tâm XY, không toàn thân/tư thế; z khác mặt sàn vượt 5 cm dừng hỏi, chưa hỗ trợ đứng trên bậc/trong vật.
2. **P2 — camera PNG mất theo TemporaryDirectory**, `core/blockout_clay.py:94`:
   lưu `<stem>_camera.png` ngoài thư mục tạm, decode trước khi trả; metadata `camera_png`,
   `camera_kind=clay|projection_2d`. OFF không tạo sidecar mới. Test mở/decode sau return ở cả Blender giả/fallback.
3. **P2 — nhãn cắt/chồng/xuyên vật**, `core/blockout_sheet.py:109`, `core/blockout_clay.py:97`:
   clamp topview có `label_box`; clay dùng danh mục đầy đủ ID/mô tả dưới sơ đồ, metadata `legend`/`legend_only`.
   Không vẽ nhãn lên khối bằng tọa độ chiếu khi chưa biết che khuất. Canvas tăng chiều cao theo danh mục.

Đối chiếu thêm CHUAN mục 6: cùng fingerprint lỗi kiểm số lặp hai lần → dừng/hỏi, không gửi lượt thứ ba.
Test khóa sai cũ đổi từ kỳ vọng 3 sang 2 calls đúng luật này; lỗi ngoài sàn → trong khối → cao độ khác vẫn cap3,
mỗi prompt sửa mang câu trả lời trước/lỗi cụ thể mới. Không nới schema/geometry để làm test xanh.

- Đỏ vòng sửa: `test_d11_clay_review` **10 failed, 1 passed** (đúng geometry/sidecar/label).
- Lần xanh đầu còn 3 lỗi fixture V3 thiếu `pid`; bổ sung `pid=1` giả, không thay assert/solver.
- Nhóm cuối **154 passed / 20,20 s**: nhóm 136 của worker + `test_d11_clay_review` + `test_plate_camera_stage`;
  UTF8, `-q -p no:cacheprovider --tb=no`. Không fullsuite. `compileall` và `git diff --check` sạch.
- V3 CLI thật với client/estimate/ledger giả: sửa hợp lệ ở call2; cùng lỗi dừng2; lỗi đổi cap3;
  kiểm thứ tự estimate→tag→call và không ghi output dùng được khi thất bại.
- Test không gọi loader credentials thật; `client_from_env` được mock trước caller, không đọc/in/assert env/token/header bí mật.
- Registry thêm `tests/test_d11_clay_review.py`, version giữ **68**. OFF hash vẫn xanh.

## Việc mở

Chưa dựng tư thế khác đứng, sàn nhiều cao độ/chỗ đứng trên bậc; solver box dùng bán kính bao, chưa trace xoay/occlusion.
Chưa thử ảnh Kho thật/Claude thật/7 trên 9 shot/chiếu ≤5%/duyệt-lưu Kho/Dashboard. Root lưu riêng bằng chứng Blender fixture.
Chưa cả bộ Windows/gộp/restart; không cập nhật TODO/PLAN theo phân công root.

## Chốt rà và QA của root
Root đã đọc diff vòng sửa, 3 nhóm finding và luật lỗi lặp đã đóng. Rà cuối phát hiện hướng sáng clay cố định140° khác topview; sửa cục bộ1dòng lấy huong_sang với chuyển hệ compass→Nishita. 4ca hướng chính ĐỎ→nhóm cuối158passed/19,53s (10file), --tb=no, UTF8; không nới test.
Blender Microsoft Store thật trên3fixture tạm (không Kho/dự án thật): indoor8,29s, outdoor7,41s, steps7,40s; mỗi tấm4góc, 0issue hình học, camera sidecar decode được sau return. Root đã xem3tấm cuối + camera PNG; nhãn không bị cắt/xuyên vật và legend đủID. 6PNG docs/images/d11/d11_v2_{indoor,outdoor,steps}{,_camera}.png. Cùng một người đứng, bậc chỉ là khối cao độ, không chứng minh đứng trên bậc/7trên9/chiếu≤5%/duyệt một lần.
Cờ OFF/OPT_IN, areas.version68 giữ; không API/dữ liệu thật/credentials/main/live/fullsuite. Ghi đúng phạm vi V3CLI/backend; Dashboard/autopilot adapter sẽ thuộc việc sau, không coi đã nối sản xuất.
