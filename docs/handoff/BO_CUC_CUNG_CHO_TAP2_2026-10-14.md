# Giữ bố cục cho cảnh nhiều shot cùng chỗ đứng — rà + sửa trước tập 2 (14/10/2026, phiên cloud)

Người dùng 14/10: "nghi ngờ vẫn còn lỗi trong quá trình giữa các khâu và việc sử dụng tối ưu bàn đạo diễn 3D để định hình, chốt góc
quay giữ được bố cục trong cảnh có nhiều shot quay cùng 1 điểm". Rà code 0 USD (không có CSDL thật ở cloud), bằng chứng từ nhật ký
thử D6 (`docs/handoff/THU_D6_NHAT_KY_2026-10-14.md`) và kiểm thật #30 (`docs/handoff/KIEM_THAT_TAP2_2026-10-14.md`).

## 1. Ba chỗ hở đã tìm

| # | Chỗ hở | Bằng chứng | Đã làm |
|---|---|---|---|
| 1 | Shot đứng ở chỗ KHÁC chỗ của ảnh neo cả cảnh bị coi là "máy riêng" (`scene_storyboard.other_spot`) → KHÔNG ảnh nào nối các shot cùng chỗ đó với nhau | #28/#29: shot 1 rộng ở A = neo; shot 2–5 cùng ở B đều `storyboard_anchor_skipped` → tường keo / Kelly / tháp mỗi ảnh một kiểu | **Sửa** (mục 2) |
| 2 | Sơ đồ máy G0 (`director_camera_plan`) gom cả cảnh thành MỘT sơ đồ, tính mốc / trục 180° / chiều cao từ chỗ của shot ĐẦU — cảnh đi A → B thì các góc máy ở B tính theo A | `camera_plan.groups` lấy `spot_for(shot đầu)` | **Sửa** (mục 2) |
| 3 | Bàn đạo diễn 3D "thật" (máy đã giải + khối đạo cụ trong render, trường `stage_camera`) CHỈ ghi được bằng script thử (#24); đạo cụ sơ đồ G0 (tường keo) chỉ lưu, không dựng thành khối khi render; ô `continuity_from` không prompt nào yêu cầu Đạo diễn điền, ô sửa tay (`continuity_from_ui`) TẮT | `stage_camera` chỉ do `tools/experiments/stage_v2_p24/apply_v4.py` ghi; `prompts/` không có `continuity_from` | **Không sửa ở đây** — việc Codex Đ18 việc 4 (registry A) + Đ11 việc 3 (Trình sửa sân khấu). Tập 2 KHÔNG trông bàn 3D khóa góc máy |

## 2. Đã sửa (nhánh `claude/wonderful-fermi-am712r`, 0 USD)

- **`anchor_by_spot` định nghĩa lại** (`core/scene_storyboard.group_of`, cờ vẫn TẮT mặc định, OPT_IN_ONLY):
  - shot ở chỗ khác chỗ của neo cả cảnh (cả hai khai `plate_spot`) mà chỗ đó có ≥ 2 shot → nhóm theo chỗ, **neo = shot RỘNG nhất tại chỗ**
    (`anchor_of`, như luật cả cảnh — bản Codex cũ lấy shot ĐẦU nhóm). Ảnh neo gửi vai `previous_scene` ("cùng nơi, giữ bố cục và bên
    trái/phải của từng người, góc máy MỚI, không chép ảnh");
  - shot ở chỗ của neo cả cảnh, shot không khai chỗ, shot đứng MỘT MÌNH ở một chỗ → **giữ nhóm cả cảnh như main** (shot một mình vẫn máy
    riêng + phiên storyboard riêng — đúng câu người dùng hỏi trước, không thành ảnh đơn);
  - cờ TẮT mà shot ở chỗ khác có bạn cùng chỗ → diag `storyboard_anchor_skipped` lên **VÀNG** + gợi ý bật cờ (trước: info im lặng).
- **G0 một sơ đồ mỗi chỗ đứng** (`core/camera_plan.groups`): cảnh qua nhiều chỗ của cùng bối cảnh → khóa `<cảnh>@<chỗ>`, mỗi chỗ tính
  từ đúng chỗ của nó; cảnh một chỗ giữ khóa cũ (sơ đồ đã lập vẫn dùng). Sơ đồ cũ cả cảnh của cảnh hai chỗ không còn nhóm → không xem lại,
  không ước tính nhầm (`after_plates`). `_story_scene` đọc được khóa `@`.
- **Công cụ kiểm 0 USD** `py tools/scene_layout_audit.py --project <id>` (`core/layout_audit.py`): đọc BẢN SAO CSDL, in mỗi shot: chỗ
  đứng, góc máy, nền, máy 3D giải, ảnh neo; **🔴 shot cùng chỗ với shot khác mà không dây nối nào** (neo / máy chung / `continuity_from`),
  🟡 neo chưa duyệt. Lưu `data/projects/<id>/layout_audit.md`; mã thoát 1 khi có 🔴.
- Test đỏ → xanh: `tests/test_anchor_by_spot_d18.py` (viết lại theo ca #28: A rộng + 3 shot ở B; 9 đỏ trên code cũ),
  `tests/test_camera_plan_g0.py` (2 ca mới), `tests/test_layout_audit.py` (4 ca). Cả bộ Linux 5434 qua, 6 hỏng sẵn như main.

## 3. Việc máy chính TRƯỚC khi gen ảnh tập 2 (0 USD trừ G0)

1. `git pull`, khởi động lại 8501/8502 (areas.json v79), cả bộ test Windows.
2. Ở 🧪 (sao lưu `data/feature_settings.json` trước): **bật `anchor_by_spot`**. **`director_camera_plan`**: bật nếu muốn Đạo diễn lập bộ
   góc máy dùng lại cho cảnh nhiều shot (MỘT lượt Claude có ảnh / chỗ đứng / cảnh — báo giá hiện trước; chỉ chạy khi cảnh CHƯA có ảnh).
3. Sau Bước 1 (Đạo diễn chia shot), TRƯỚC ▶ Gen ảnh: `py tools/scene_layout_audit.py --project <tập 2>` → gửi bảng cho người dùng; còn 🔴
   thì sửa (cùng `camera_setup`, hoặc `continuity_from`, hoặc tách chỗ đứng) rồi chạy lại tới khi hết 🔴.
4. Khi duyệt ảnh: duyệt ẢNH NEO mỗi chỗ trước (shot rộng nhất tại chỗ) — các shot cùng chỗ vẽ theo nó.

## 4. Chưa làm / giới hạn
- Chưa thử thật trên Dashboard (cloud không có CSDL / Blender / khóa API). "Đã sửa" ở đây = test; nghiệm thu thật ở bước 3 trên dự án tập 2.
- Vị trí tường keo giữa các shot vẫn dựa vào ảnh neo + chữ; khối thô trong render 3D chờ Codex Đ18 việc 4 / Đ11 việc 3.
- Cùng chỗ nhưng góc máy rất khác (ngược 180°): ảnh neo cho vị trí người/vật, không cho nền — nền theo render 3D của shot (như cũ).
