# Hướng dẫn thử Bối cảnh 3D (tháp đồng hồ — Đảo Quân Sự) trên máy người dùng

> Viết 2026-09-24 (GĐ-E0b của `docs/KE_HOACH_TONG_2026-09-24.md`). Dành cho **phiên làm việc chạy trực tiếp trên máy** có file 3D và
> Blender 5.0.1 (phiên cloud không có file của bạn). Code đã có sẵn và đã chạy thật với `bpy 5.0.1` (cùng phiên bản Blender của bạn) trên
> một tháp khối hộp giả; phiên trên máy chỉ việc chạy, đo, chỉnh và ghi kết quả.

## 1. Vì sao dùng 3D
Ảnh chụp map in-game chỉ có **một góc máy** (thường từ trên cao). Model ảnh chép luôn góc máy đó và cỡ người tí hon khi ghép làm nền (lỗi R7 ở GĐ6).
Trong 3D, camera đặt được **đúng góc của shot** (ngang tầm mắt, góc thấp, góc cao) và kích thước là **mét thật**. Ta render **nền trống người**
rồi dùng làm ảnh tham chiếu **kiến trúc/vật liệu** (không điều khiển cỡ người). Không AI, không tốn credit ở bước render.

## 2. Có gì trong code
| Thành phần | Việc |
|---|---|
| `tools/render_plates.py` | Script chạy **bên trong Blender**: nhập file 3D, chuẩn hóa tỉ lệ (m), thêm mặt đất, trời A/B/C, camera theo preset hoặc JSON, render ảnh nền + ảnh độ sâu, ghi `manifest.json` (số tam giác, thời gian nhập, thời gian render từng ảnh, thông số camera, đường chân trời) |
| `core/plates3d.py` | Phía Dashboard: tìm Blender, liệt kê file trong `MODEL3D_DIR`, dựng kế hoạch, chạy Blender nền (timeout, `render.log`), ghép trời in-game (cách C), đưa ảnh vào **📥 Ảnh chờ duyệt** của Kho với vai trò theo góc máy + ghi thông số camera vào `set_analyses` (khỏi trả tiền Claude đọc ảnh) |
| ⚙ → 📁 Kho tài nguyên → **🏗 Bối cảnh 3D** | Chọn file, trời, giờ nắng, góc máy, % tam giác, khung → "▶ Render nền" → xem → "📥 Đưa vào hộp chờ duyệt" |
| `tests/test_plates3d.py` | Test với Blender giả + test chạy Blender thật khi đặt `BPY_PYTHON` |

## 3. Cài đặt (một lần)
Thêm vào `dashboard.env` (xem `dashboard.env.example`):
```
MODEL3D_DIR=D:\AI-Video-Pipeline\model 3D
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe
```
(Để trống `BLENDER_PATH` thì Dashboard tự tìm trong `C:\Program Files\Blender Foundation\Blender 5.0\`.) **File 3D không bao giờ đưa lên GitHub.**

## 4. Chạy thử trực tiếp bằng dòng lệnh (không cần Dashboard)
Tạo `plan.json` (đường dẫn Windows dùng `\\` hoặc `/`):
```json
{"model": "D:/AI-Video-Pipeline/model 3D/<file tháp>.glb", "out_dir": "D:/AI-Video-Pipeline/plates_test/lan1",
 "resolution": [1280, 720], "engine": "auto", "samples": 16, "real_height_m": null, "decimate": 1.0, "ground": true,
 "presets": ["eye_000", "eye_090", "eye_180", "eye_270", "low_000", "high_045"], "depth": true,
 "sky": {"mode": "A", "sun_elevation": 35, "sun_azimuth": 140}}
```
```
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b --factory-startup -P tools\render_plates.py -- --config plan.json
```
Kết quả trong `out_dir`: `plate_*.png`, `depth_*.png`, `manifest.json`. Lần đầu **chỉ cần 1 preset + khung nhỏ** để đo file:
`"presets": ["eye_000"], "resolution": [640, 360]`.

## 5. Quy trình thử tháp đồng hồ (ghi kết quả vào `docs/RESEARCH_3D_PREVIZ.md`)
1. **Đo file** (1 preset, 640×360): ghi dung lượng, số tam giác, thời gian nhập (`manifest.json → model`), RAM lúc Blender chạy (Task Manager),
   cấu hình máy (CPU, RAM, GPU). File > 1 triệu tam giác hoặc nhập > 60 s → thử `"decimate": 0.2`.
2. **Tỉ lệ:** xem `manifest.json → bbox_m.size` và `scale_factor`. Nếu tháp không cao cỡ 25–40 m, đặt `"real_height_m"` = chiều cao thật
   (hoặc ước theo cửa ~2 m) rồi chạy lại. Dashboard: ô "Chiều cao thật phần cao nhất".
3. **Trời:** chạy 3 lần, cùng góc máy:
   - **A** trời vật lý (mặc định) — chỉnh `sun_elevation` / `sun_azimuth` cho giống giờ của cảnh; quá sáng/tối: `"exposure"` (mặc định −0,5),
     `"strength"` (0,35), `"sun_strength"` (2,5) trong `sky`.
   - **B** HDRI: tải 1 file 2K miễn phí bản quyền (Poly Haven, CC0), `"hdri": "D:/.../file.hdr"`, xoay bằng `"hdri_rotation"`.
   - **C** nền trời trong suốt + ghép **ảnh trời chụp in-game Đảo Quân Sự** (Dashboard: ô "Ảnh trời chụp in-game") — hợp look in-game.
4. **3 shot chuẩn:** `eye_000` (toàn cảnh ngang tầm mắt nhìn về tháp), `low_000` (góc thấp dưới chân tháp), `high_045` (góc cao). Ghi thời
   gian render từng ảnh (`render_sec`) và cả lượt (`total_sec`).
5. **Vào Kho:** Dashboard → "📥 Đưa vào hộp chờ duyệt" → duyệt ảnh đạt (vai trò đã điền theo góc máy).
6. **Thử với model ảnh (TỐN CREDIT — xin phép người dùng trước):** ~5–6 ảnh Deepix, 2 look (in-game / anime):
   (i) nền 3D trống người + prompt chữ, (ii) thêm ảnh độ sâu (chỉ khi Deepix có vẻ bám theo), (iii) cách không-3D (hồ sơ bối cảnh bằng chữ, B1–B3).
   So: đúng cỡ người so với tháp, đúng góc máy, giữ kiến trúc, có bị "chép" bố cục sai không. Bật tạm gửi ảnh nền cho model bằng cờ tương ứng
   trong `core/features.py` nếu cần (mặc định tắt tới khi thử đạt).
7. Ghi bảng kết quả + ảnh so sánh vào `docs/RESEARCH_3D_PREVIZ.md`; đạt thì đánh dấu `verified` + ngày trong `core/features.py`.

| Mục cần ghi | Giá trị |
|---|---|
| File (định dạng, MB, tam giác, texture?) | |
| Máy (CPU / RAM / GPU) | |
| Nhập file (s) · RAM đỉnh | |
| Render 1 ảnh 1280×720 EEVEE (s) — A / B / C | |
| Tỉ lệ (`scale_factor`, `bbox_m.size`) đúng chưa | |
| Ảnh Deepix: cỡ người / góc / kiến trúc (i / ii / iii) | |

## 6. Map nặng (hàng triệu tam giác, texture vài GB)
- Không mở cả map mỗi lần gen: render **một lần** bộ nền chuẩn (các preset) cho mỗi khu → lưu vào Kho → dự án sau chỉ dùng ảnh.
- `decimate` 0,1–0,2 (ảnh nền chỉ là tham chiếu kiến trúc); texture lớn: giảm trong Blender (File → External Data) nếu RAM thiếu.
- Cắt khu: mở file trong Blender, xóa phần ngoài khu cần dùng, lưu `.blend` riêng vào `MODEL3D_DIR` (việc tự động cắt theo khu: để sau khi đo).

## 7. Lỗi thường gặp
| Hiện tượng | Xử lý |
|---|---|
| "không tìm thấy Blender" | đặt `BLENDER_PATH` đúng file `blender.exe` |
| Blender thoát mã âm, log có `EGL`/`OpenGL`/`GPU` | máy không có ngữ cảnh GPU cho EEVEE → Dashboard tự chạy lại bằng Cycles (CPU, chậm hơn); hoặc `"engine": "cycles"` |
| Ảnh quá sáng/tối | chỉnh `exposure`, `strength`, `sun_strength` trong `sky` |
| Tháp tí hon / khổng lồ | sai đơn vị: đặt `real_height_m` |
| Nhìn ra khoảng trống ngoài model | giữ `"ground": true`, tránh hướng camera ra rìa (chọn preset khác hoặc camera JSON riêng) |
| Tên node/engine khác (bản Blender khác) | script tự dò (`BLENDER_EEVEE`/`BLENDER_EEVEE_NEXT`, kiểu trời mới nhất có sẵn), lỗi trời thì dùng màu trời phẳng và ghi `warnings` |

## 8. Đã chạy thật trên cloud (2026-09-24, `bpy 5.0.1`, không GPU, Mesa phần mềm)
Tháp khối hộp 34 m lưu theo cm: tự nhận ×0,01; 6 ảnh nền 320×180 + 6 ảnh độ sâu trong ~48 s (EEVEE phần mềm, 2–20 s/ảnh — **máy có GPU sẽ nhanh
hơn nhiều**); camera ngang tầm mắt: pitch 0°, đường chân trời 0,5; trời C trong suốt đúng. Số liệu thật của file tháp: **chưa có** — cần phiên trên máy.

## 9. Gói bối cảnh (kế hoạch V4, 2026-09-25) — nền đúng 100% cho cả video

**Ý tưởng:** AI chỉ vẽ nhân vật (trên phông xanh), nền là **pixel thật** render từ mô hình 3D theo đúng máy ảo của từng shot, rồi ghép
bằng code. Làm tay **một lần cho mỗi khu vực** (đăng ký mô hình + chỗ đứng); mọi shot, mọi dự án sau dùng lại (bộ nhớ đệm chung).

**Luồng (cờ `location_plates`, TẮT tới khi thử thật — bật thử `FEATURE_LOCATION_PLATES=1`):**
1. `tools/location_pack.py register --asset <id khu vực> --model <file 3D> --anchor x y z [--spot tên x y z hướng] [--min-level z]`
   — gắn mô hình vào hồ sơ khu vực (`assets.profile.model3d`); không đưa `--spot` thì tự dò mặt phẳng đi được (Blender bắn tia xuống)
   và đề xuất chỗ đứng quay lưng về công trình. **Từ 2026-09-29 dùng file 3D chính thức của game** (mục 10): Tháp Đồng Hồ (#263)
   và Cổng Trời (#265). Bản fan FFXN (`free_fire_clocktower_3d_model_by_ffxn.glb`, đăng ký 2026-09-25) **không còn dùng** — tọa độ / tên
   chỗ đứng cũ (`lower_yard`, `level_26_0`…) không khớp bản mới; shot cũ gọi tên cũ rơi về chỗ mặc định có báo.
2. Autopilot pha **plates** (trước ảnh): máy ảo từng shot (`core/plate_camera.py`: cỡ cảnh → khoảng cách + ống kính, góc máy → độ cao,
   `start_frame` trái/phải, cùng `camera_setup` = cùng máy) → render theo lô, mỗi khu vực + thời gian/thời tiết một lần gọi Blender
   (xếp hàng cả máy, bộ nhớ đệm `data/_plates3d/cache/`) → lớp nền, độ sâu, **bóng của hình nộm đúng chiều cao nhân vật**.
3. Thời gian/thời tiết (`core/plate_env.py`): đêm/hoàng hôn/bình minh = trời trong suốt + vẽ trời (sao, trăng); tuyết phủ mặt hướng lên,
   mặt đất ướt (trong Blender); **sương theo khoảng cách** (từ ảnh độ sâu — sương khối của EEVEE làm đen cả ảnh, đã thử); mưa/tuyết
   rơi, chớp (2D, phủ cả nền lẫn người); chỉnh màu theo giờ.
4. Bước ảnh gửi **chỉ ảnh nhân vật** + prompt phông xanh có máy, ánh sáng (hướng nắng/trăng tính từ render), thời tiết trên người.
5. Ghép (`core/composite.py`): tách xanh + khử viền, đặt đúng ô máy ảo tính, nền có bóng thật, vật gần hơn người thì đứng trước
   (ảnh độ sâu), chỉnh màu người theo giờ (60%) + theo nền, hòa sáng viền, sương theo khoảng cách người.
6. Video: **cách 1** ảnh ghép làm khung đầu; `core/plate_qc.py` chấm độ giống nền (mỗi 0,5 s, ngưỡng 0,90) — trượt thì pha
   **platefix** gen lại 1 lần bằng **cách 2** (video nhân vật trên phông xanh, ghép từng khung lên nền, `composite_video`).
7. Khu vực chưa có 3D nhưng có ảnh chụp trong game đã gắn vai trò (ngang mắt/thấp/cao) → **nền cấp 2** (cắt khung theo cỡ cảnh, chỉnh
   màu; không có bóng/độ sâu). Không có cả hai → cách cũ (AI vẽ + ảnh mốc), báo rõ.

**Số đo thật (2026-09-25, Blender 5.0.1 Store, tháp 71.925 tam giác):** nạp mô hình ~1,4 s; mỗi góc máy 1,2–5,7 s + lớp bóng ~1,5 s;
dò mặt phẳng (34.221 tia, bước 1,5 m) ra đúng quảng trường trên z ≈ 25,96 và sân dưới z ≈ 22,40. Dự án #7: 4 shot ở tháp → 1 lần render
đêm, 4 góc máy.

### Mẫu xin mô hình 3D chính thức từ team game
- Định dạng **FBX hoặc GLB**, **texture nhúng sẵn** (hoặc gửi kèm thư mục texture), **đơn vị mét**, trục Z hướng lên.
- **Chia theo khu vực** (mỗi file một khu như Tháp Đồng Hồ, Nhà Máy, Kho Quân Sự…) — cả map một file sẽ quá nặng; nếu chỉ có cả map thì
  báo số tam giác để mình dùng `decimate`.
- Nếu có: **bản mùa/thời tiết** (Snowfall, map đêm…), vị trí công trình nhận diện chính (tọa độ tâm), và **ảnh chụp trong game cùng góc**
  vài vị trí để chỉnh màu render cho giống game.
- Bỏ file vào `MODEL3D_DIR` (`D:\AI-Video-Pipeline\model 3D`), rồi chạy lệnh `register` ở trên (hoặc báo mình chạy).

**Chưa làm (ghi ở TODO):** màn hình đăng ký/sửa chỗ đứng trong ⚙ → Kho (GĐ6); bước "hòa ánh sáng bằng AI rồi dán lại nền thật" và Claude
chấm "ăn khớp" (tốn tiền — bật khi thử thật cho thấy cần); mô hình chiếu sáng lại người (IC-Light, cần GPU/torch — hỏi trước khi tải).

## 10. File 3D chính thức của game (2026-09-29) — Tháp Đồng Hồ + Cổng Trời, map Đảo Quân Sự

**File:** `D:\AI-Video-Pipeline\model 3D\Ingame_map_building\Ingame_map_building\<ClockTower|Peak>\T_30_XH_PCMAP_P16|P20\asset.fbx` (+ texture cùng thư mục, `showcase_0.jpg` = ảnh chụp trong game để so). Đơn vị mét, không cần `real_height_m`.
Không vào git.

**Bốn chỗ bản xuất sai — code tự sửa khi render (`tools/render_plates.py`):**
- **Mặt đất** (`fix_terrain`): vật liệu dán một texture đá kéo theo UV của cả đảo (ra loang xanh xám). Trong game mặt đất là *splat*:
  `AllTerrainMask.png` (cả đảo, cùng UV) — **G = cỏ** `Terrain_Ground_01`, **B = đất** `_02`, **R = đá** `_03`, đen = lòng sông. Code đọc mask
  theo UV rồi trộn 3 lớp lặp mỗi 6 m (đổi được trong plan: `"terrain": {...}`, `false` = để nguyên). Lớp cỏ `Terrain_Ground_01_D_nastc.png`
  (ảnh giải nén ASTC) có ngọn cỏ khô màu tím (3 % điểm ảnh) → kênh xanh dương kẹp ≤ kênh xanh lá (ngọn khô về vàng nâu, cỏ xanh giữ nguyên).
- **Nước** (`fix_water`): màu nước hồ bơi Cổng Trời là ảnh normal map gợn sóng (`norm_T_Water_Ripple…`, xanh tím) → nước xanh trong, bóng
  (áp cả khi thiếu texture).
- **Cỏ** (`fix_foliage`): tấm cỏ `plant_grass_B_New_D_A.png` là ảnh RGB, hình ngọn cỏ nằm ở mặt nạ riêng `…_M.png` mà FBX không nối →
  ở tầm mắt mọi tấm cỏ ra ô vuông đặc. Code nối mặt nạ làm độ trong suốt (xám → trong, trắng → đặc).
- **Ánh sáng** (hồ sơ khu vực `model3d.light.day`): chế độ màu mặc định AgX làm bạc màu → `view_transform: Standard` + `Medium High
  Contrast`, nắng ấm 4,5, trời 0,15, phơi sáng −0,5, mặt trời 50° (A/B 5 phương án, chọn v4). Chỉ áp cho nền ban ngày trời quang; đêm /
  thời tiết xấu giữ `plate_env`. Có trong khoá bộ nhớ đệm nền.

**Chỗ đứng:** ngoài mặt phẳng dò tự động (hay rơi sát tường / trên mái — **luôn xem ảnh kiểm**), đo độ cao mặt đất ở điểm tự chọn bằng
`plates3d.ground_heights(model, [[x, y], …])` (bắn tia xuống, bỏ qua cây / cỏ). Mỗi chỗ đứng có thể có `view` = điểm máy nhìn tới (cảnh
quan xung quanh, không phải công trình chính) và `group` (`chinh` / `canh_quan` / `trong_nha`).

**Trong nhà** (người dùng 29/09: "bổ sung cả những góc cảnh trong nhà"): đặt máy theo toạ độ đồ đạc hay rơi ra ngoài tường / dí sát
tường — dùng `plates3d.room_cameras(model, [{name, lo, hi, floor_z}])` (render_plates `rooms`): lưới điểm trong khung nhà ở tầm mắt, giữ
điểm có trần phía trên và tường gần kín xung quanh, chọn điểm xa tường nhất; `look_at` = hướng sâu nhất còn trong nhà, `look_out` =
hướng nhìn qua cửa ra ngoài. Độ cao sàn lấy theo đáy đồ đạc của tầng đó (bắn tia từ dưới trần hay trúng cầu thang / giường).
Chỗ đứng trong nhà mang `indoor` (sáng thêm +1,5 + đèn phụ 300 W giữa máy và điểm nhìn, chỉ cho máy đó) và `view_out`.
Kết quả thử: 29/31 góc đạt; 1 góc hỏng đã bỏ (tầng 2 biệt thự — máy dưới mái hiên).

| Khu vực | Tâm (anchor) | Chỗ đứng chính | Cảnh quan xung quanh |
|---|---|---|---|
| Tháp Đồng Hồ #263 | tháp `CLK_OUT_Tower001` (−217,07; 132,04), cao 9,5 → 47,9 m | `plaza_front` (mặc định), `level_9_4`, `level_2_3`, `level_2_3_a` | đồi tây + trạm gác (nhìn xuống cả thị trấn), đường cao tốc đồi tây + biển quảng cáo, đồng cỏ bắc, đồng cỏ tây nam, rặng dừa đông, nhà lớn đông, bãi xe van, dãy nhà mái đỏ nam · **trong nhà (11):** nhà 3 tầng quảng trường (3 tầng), nhà lớn đông (2), nhà nam (2), nhà vừa, nhà lớn tây (2), nhà gỗ nhỏ đông |
| Cổng Trời #265 | biệt thự `PKK_OUT_Building001` (−676,5; −74,5), nền ~68 m | `san_truoc` (cổng tây, mặc định), `san_dong`, 2 hồ bơi, mê cung | bãi xe có mái, biển quảng cáo, nhà kính, sườn dốc cột điện cao thế, đường đất đổ dốc tây, nhà thấp dưới dốc, rặng cây / đá · **trong nhà (5):** sảnh biệt thự, 2 nhà gỗ dưới dốc tây, nhà kính, nhà gỗ nhỏ bắc |

**Bộ ảnh + video chuẩn:** `py tools/tower_pack.py --asset 263|265 --out <thư mục>` — mọi chỗ đứng nhìn công trình (`_thap`), góc ngược
(`_nguoc`), góc cảnh quan (`_canh`), trong nhà (`_trong`, `_ra`), ngày + đêm, 3 video máy (đi bộ vào, vòng quanh, cần cẩu) bản texture +
bản khối trắng. `--only-indoor` = chỉ phần trong nhà. 0 USD. Kết quả 29/09: `D:\AI-Video-Output\2026-09-29_bo-boi-canh-thap-chinh-thuc\`,
`D:\AI-Video-Output\2026-09-29_bo-boi-canh-cong-troi\`.
