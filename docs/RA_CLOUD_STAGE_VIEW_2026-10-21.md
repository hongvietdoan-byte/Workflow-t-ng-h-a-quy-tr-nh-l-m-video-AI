# C-STAGE-VIEW — Màn XEM sân khấu 3D trên Dashboard (chỉ đọc) (cloud-C, 21/10)

- Nhánh: `cloud/v31-stage-view`, tạo từ origin/main.
- Cờ mới: **`stage_view_ui`**. Mặc định TẮT, `verified: False`, nhãn "Xem sân khấu 3D (chỉ đọc)…", không phát sinh chi phí. Cờ đã được thêm vào `tests/golden/package_inputs.json` với giá trị `false` cho cả image và video.

## Đã làm
- **`dashboard/stage_view_ui.py`**
  - `collect(p, pid, data_dir)`: thuần, chỉ đọc. Gom dữ liệu theo cảnh truyện (`story_scene`).
  - `render(p, pid, data_dir)`: vẽ bằng Streamlit, mỗi cảnh một expander. Cờ tắt thì trả về ngay, không đọc gì.
  - Nội dung mỗi cảnh:
    1. **Tấm clay / khối**: ảnh `blockout_sheet.png` mới nhất, mặt cắt K1 `top_cut.png`, clip `*_clay.mp4` (tệp nhỏ hơn 25 MB).
    2. **Nền 3D từng shot**: ảnh nền (thu nhỏ còn 480 px, làm trong bộ nhớ), hướng nền `plate_view`, vị trí máy `camera.location`.
    3. **Sơ đồ world map 2D**: SVG tĩnh nhìn từ trên. Chấm cam = người, ô xám = vật, tam giác tím = mốc, chấm xanh + tia = máy. Không gọi Blender.
    4. **Người nộm** (khi cờ `whitebox_height_dummy` bật): chiều cao trong hồ sơ Kho + tầm mắt. **Câu vị trí gợi ý** (khi cờ `world_map_sentences` + `world_map` bật): `world_map.position_sentence`, chỉ hiện để xem.
    5. **Cảnh báo**, dùng đúng hàm cổng có sẵn:
       - nền cũ: `place_refs.stale` — cùng hàm mà cổng Bước 2 `batch.image_gates` dùng; chỉ chạy khi cờ `place_render_refs` bật, cờ tắt thì nói rõ là không so;
       - nền hỏng / chờ hướng máy: `location_pack.plate_failed` / `plate_needs`;
       - map cũ: `invalidated`, hoặc `world_map.stale` so nguồn hiện tại với nguồn lúc dựng map (BYĐ không so: map 3D không dựng từ BYĐ);
       - hướng nền: `plate_view_check.warnings`;
       - thiếu tệp: báo "chưa có nền 3D shot N — chạy `py tools/location_pack.py render --project N`", "chưa có sân khấu 3D cảnh X — chạy `py tools/stage_auto.py --project N --scene X --dry`", "chưa có world map — dựng bằng core.world_map.refresh", "chưa có tấm clay…".
- **`dashboard/steps/step2.py`**: thêm một dòng gọi `stage_view_ui.render(p, pid, C.DATA)`, đặt ngay trên khối gen ảnh.
- **Luật cứng:**
  - Không có nút nào (có test bảo đảm không có `st.button`).
  - Không render / gửi / ghi.
  - Không ghi `data/` hay CSDL. Test so mtime của mọi tệp dưới `data/` và sha của CSDL trước / sau, chạy cả khi cờ `place_render_refs` bật lẫn tắt.
  - Mọi đường dẫn lấy theo `data_dir` của pipeline (có test chạy với cwd khác).
  - Ảnh: giới hạn 25 MB và thu nhỏ trong bộ nhớ.

## Bằng chứng
- `tests/test_v31_stage_view.py`: 12 test. Đã commit một lần khi cả 11 test còn đỏ, sau đó xanh. Fixture: thư mục data tạm + CSDL tạm, 2 cảnh, 3 shot:
  - shot 1: có đủ nền + camera;
  - shot 2: thiếu nền → báo "chưa có nền 3D … tools/location_pack.py";
  - cảnh 2: world map đã cũ (`invalidated: blocking_changed`) → cảnh báo.
- Các ca test:
  - cờ tắt: không lời gọi `st` nào, `collect` không chạy;
  - Bước 2 gọi đúng chỗ (phía trên `sb-gen`);
  - SVG có tên người;
  - thiếu sân khấu / map: báo kèm lệnh;
  - không ghi gì (2 biến thể cờ);
  - không phụ thuộc cwd;
  - ảnh thu nhỏ, tệp quá lớn bị từ chối;
  - không có nút / lệnh ghi;
  - người nộm + câu vị trí chỉ hiện khi cờ bật.
- Bộ test đầy đủ (cloud, Python 3.13): 6853 xanh. Còn đỏ: 25 golden (cần Python 3.14 máy chính), 4 lỗi nền đã biết (`recut_by_hand`, `punches`, `end_popup_p24`, `unreadable_picture`), và `test_devsys_plan_map` (M4.8 chưa map trong `devsys/plan_map.json` — đỏ sẵn trên origin/main, không do nhánh này).
- Test DP8 `test_nothing_in_the_gen_path_reads_the_map` (G2-4: không module nào ngoài world_map dùng map): thêm danh sách trắng có lý do cho `dashboard/stage_view_ui.py` (màn XEM chỉ đọc, không thuộc đường gen), kèm điều kiện cấm `world_map.refresh(` / `save(` / `build` / `_write(` trong màn này.

## Đường dẫn dữ liệu màn này ĐỌC (để phiên chính kiểm trên #31 thật)
| Dữ liệu | Đường dẫn (theo `data_dir` của pipeline, `<pid>` = 31) | Hàm |
|---|---|---|
| Shot + cảnh truyện | CSDL `scenes` (`data.story_scene`, `shot_no`, `plate_view`, `characters`) | SQL SELECT |
| Nền 3D từng shot | `<data>/31/plates/index.json` → trường `plate` (đường tuyệt đối), `camera`, `place`, `problem`, `needs` | `location_pack.index` / `plate_failed` / `plate_needs` |
| Nền cũ so kế hoạch | kế hoạch máy (`location_pack.stale_plates`) | `place_refs.stale` |
| Sân khấu | `<data>/31/stage/<stage>/k1_*/top_cut.png`, `…/doan_<cảnh>/r*/blockout_sheet.png`, `…/**/*_clay.mp4` | `stage_auto.segments`, `stage_auto.base_dir`, `glob` |
| World map | `<data>/31/world/scene_<cảnh>.json`, `plan2d_<cảnh>.json`; nguồn so: `k1_*/stage.json`, `grid.json`, `doan_<cảnh>/blocking.json`, `shot_specs.json` | `world_map.load`, `sources`, `stale`, `entities_at` |
| Chiều cao người nộm | hồ sơ chuẩn Kho `height_m` | `whitebox.heights_of` → `assets.standard_for` |

**Cần phiên chính kiểm trên #31 thật**, với cờ `stage_view_ui` bật:
- tên thư mục `stage/<stage>` và `doan_<cảnh>` có khớp `stage_auto.key_of(cảnh)` không;
- `top_cut.png` / `blockout_sheet.png` thật nằm ở đâu, vì công cụ CLI có thể ghi ra `--out` khác;
- cảnh 4 / 6 / 8 hiện đủ nền + sơ đồ chưa.

## Giới hạn
- Chưa chạy trên dữ liệu thật: cloud không có `data/`.
- Màn này không tự dựng world map / render. Muốn có dữ liệu thì làm qua CLI / API ghi trong thông báo.
