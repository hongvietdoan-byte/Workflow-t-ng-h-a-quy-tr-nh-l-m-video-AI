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

## Việc mở
- Bước 2: luật L1–L10 + ứng viên 24 hướng × 3 độ cao; ngưỡng ⚙ cần so trên shot người dùng đã chê/khen.
- Chưa gắn vào luồng Dashboard/cờ nào; chưa sửa spot `plaza_front` (z sai 0,45 m) — cần người dùng duyệt vì đổi cache plate mọi dự án.
