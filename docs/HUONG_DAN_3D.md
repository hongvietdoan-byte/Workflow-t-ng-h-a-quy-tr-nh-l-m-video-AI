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
