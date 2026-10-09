# HANDOFF — Bước 0 Sân khấu 3D (09/10, nhánh `stage-grid-s0` từ origin/main, chưa push)

Theo `docs/PHUONG_PHAP_SAN_KHAU_3D.md` (mục 2–6, 10) + `docs/KE_HOACH_DAT_MAY_3D_2026-10-09.md` "ĐỔI HƯỚNG 09/10 tối". 0 USD.

## Đã làm
- `core/stage_grid.py` (thuần Python, Blender nạp theo đường dẫn): tên ô theo mục 2.3 (N = 20, c = 1 → O ở góc Tây-Nam ô K11),
  model ↔ scene ↔ so với O (factor/LIFT_Z), phương vị, `measure` (đường đo từ O), `offset`, `look`, `project`/`in_frame`/`ray_dir`,
  `fov`, `horizon_w`, `frame_distance`, `camera_at` (mục 5), `axis_side`, `angle_at`, `floor_status`, `slope_deg`, `median`,
  phân nhóm `group_by_name` / `group_by_shape` / `group_by_hit`. Test `tests/test_stage_grid.py` (14).
- `tools/stage_grid.py`: máy chủ đọc model3d bối cảnh (CSDL chỉ đọc) → chạy Blender Store nền (lượt Blender chung) → bắn tia lưới
  (vùng diễn 6×6 m quanh O + quanh giếng 4×4 tia/ô, ngoài 3×3; so 3×3 ở vùng diễn), dựng giếng + người nộm, render trực giao + 2 góc
  thử + clay Workbench, lưới tia 36×64 từ máy, số kiểm hình học; vẽ `topgrid.png` (lưới 1 m + phụ 0,25 m, màu bậc/tầng/vật chắn/mái,
  O, Bắc, tháp, giếng, người, máy + nón nhìn, trục) và `view_a/b_clay.png` (nhãn, lưới sàn chiếu, 1/3, chân trời w_h, headroom, vùng 15 %).
- Lệnh: `py tools/stage_grid.py --db D:/AI-Video-Pipeline/data/manifest.sqlite --out D:/AI-Video-Pipeline/data/projects/24/stage_s0`
  (`--draw-only` vẽ lại từ JSON). Kết quả #24 ở `data/projects/24/stage_s0/` (ngoài git). Blender ≈ 22 s.
- Khai file vào khu `plates3d` của `devsys/areas.json` (không tăng version).

## Phát hiện (đo thật #24)
- Spot `plaza_front` z = 9,38 nhưng sàn chạm tia ở đó z = 9,83 (model): spot thấp hơn sàn 0,45 m → luồng plate cũ đặt chân nhân vật dưới mặt quảng trường.
- Cả quảng trường + tường thấp (0,95 / 1,43 / 1,68 m) + bậc là MỘT mesh `CLK_OUT_Base002_LOD0_plan` (bbox 187×195 m); mọi tên object kết thúc
  `_plan` → tên chỉ tách được tháp (`CLK_OUT_Tower001`), nhà (`CMO_OUT_HugeHouse001`), cây (`Greentree`); trong mesh nền phải phân theo điểm trúng
  (cao độ so với sàn + pháp tuyến: `group_by_hit`).
- Quảng trường là bản sàn rỗng: dưới mặt có tầng −6,18 m (tia xuyên đáy khối trùng mặt sàn đọc nhầm tầng dưới — đã đo chân đế trước khi dựng khối).
- Hướng Bắc: CHƯA có nguồn trong game; đang dùng +y model (quy ước facing của plate_camera). Kelly H = 1,7 m (Kho 23), không phải 1,75.

## Bước 1–2 (nhánh `stage-s1`, 09/10, 0 USD)
- `core/stage_grid.py`: `point_state` (nhãn hình phác: in / blocked = chấm rỗng "(bị che bởi …)" / out = mũi tên xám sát mép +
  "… ngoài khung" / behind = không vẽ), `FRAMING` (khớp plate_camera, có test), `layer_heights`, `size_frame`, `candidates`
  (24 hướng × 3 độ cao, mục 5), `RULE_TH` (mọi ngưỡng ⚙ TẠM, có lý do), `check_rules` (L1–L10, luật hỏng + câu có số),
  `background_group`, `rank_score`. Test mới `tests/test_stage_rules.py` (15) + `tests/test_stage_grid.py` (14) = 29 xanh.
- `tools/stage_grid.py`:
  - `fix-spot --place <id> --spot <tên> [--apply]` (tia từ trên xuống; không --apply chỉ in; --apply ghi qua `location_pack.set_model3d`,
    giữ mọi khóa khác). Đo: plaza_front z cũ 9,380 → sàn 9,830 (CLK_OUT_Base002, n_z 1,0), +0,450 m. CHƯA --apply (chờ phiên chính).
  - `s1 --db … --out …`: MỘT lượt Blender (≈ 56 s, đo 25 s): 3 yêu cầu mẫu #24 × 72 ứng viên (lưới thô 18×32, top-3 đo lại 36×64)
    + 9 shot hiện có (camera từ `location_pack.plan`) → `s1.json`, `<R>_top3.png`, `<R>_topgrid.png` (nón nhìn), `shots24_clay.png`.
  - Nhãn mới áp cho cả hình phác Bước 0 (`draw_labels`). `--db` mặc định = `<ROOT>/data/manifest.sqlite` (không theo cwd).
- Kết quả #24 ở `data/projects/24/stage_s1/` (ngoài git). R1 toàn cảnh 10/72 đạt, R2 qua vai cúi 2/72, R3 góc ngược 7/72.
- Phát hiện: camera plan hiện tại tính theo spot z cũ → máy thật thấp hơn 0,45 m (shot 1 "ngang" chỉ cao 0,34 m trên sàn) và đỉnh đầu
  Kelly ra ngoài mép trên ở 8/9 shot; shot 3 khai eye_level nhưng pitch −35° (L7); shot 4 máy rơi vào khối giếng GIẢ ĐỊNH (Bước 0
  đặt giếng 1,6 m hướng 350°) → bảng shot 4 không dùng để hiệu chỉnh. "Tường cao che" (shot 4/5) KHÔNG tái hiện được với camera
  plan hiện tại (vật cản 0 %) → ảnh người dùng chê có thể từ camera cũ khác.

## Việc mở
- Phiên chính chạy `fix-spot … --apply` (đã được duyệt), rồi đo lại `s1` (camera plan sẽ lên 0,45 m).
- Hiệu chỉnh ngưỡng `RULE_TH` khi có shot người dùng khen/chê cùng camera đã render; L5 "thấy mặt/lưng" và L8 bỏ nhóm người là
  cách hiểu của Bước 2 (ghi trong docstring).
- Chưa gắn vào luồng Dashboard/cờ nào; Director chọn ứng viên = Bước 3.
