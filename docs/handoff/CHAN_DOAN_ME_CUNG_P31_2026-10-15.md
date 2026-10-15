# Chẩn đoán đặt máy nền 3D — #31 cảnh 2–4 (Cổng Trời / mê cung, đêm) — 15/10

Phiên chẩn đoán (0 USD, CHỈ ĐỌC): CSDL thật mở `?mode=ro`, gọi khô `core.location_pack.plan(conn, 31)` (không render, không ghi),
đối chiếu cache `_plates3d/cong_troi/20261015_172739_bea2` (lần render gần nhất, khớp từng máy với lần gọi khô) và ảnh nhìn
thẳng từ trên mê cung đã có (`maze_top2/plate_top_c.png`, máy (−622; −75) cao 42 m, ống 24 mm, 1000 px ≈ 62,9 m → 0,063 m/px,
phải ảnh = +x đông, trên ảnh = +y bắc; kiểm chéo: bệ giữa ảnh rơi đúng `trung_tam_me_cung` (−621,5; −74,6)).
Hướng (bearing) theo quy ước `plate_choice.bearing`: 0° = bắc (+y), 90° = đông, 270° = tây. **Biệt thự (anchor −676,5; −74,5) nằm
đúng hướng 270° từ mọi điểm trong mê cung.**

## 1. Hình học mê cung (đo từ ảnh nhìn trên, sai số ≈ ±0,5 m)

```
              y −55,5 ┌──────────── hàng rào ngoài (cao ≈ 2,1 m: bệ đá + cây) ────────────┐
                      │  HÀNH LANG 1 bắc  y −60,3  (x −637,7 … −605,3, rộng ≈ 3,5 m)      │
                      │   ┌─────── vòng 2 ──────┐ khe x −621,6 ┌──────────────┐           │
                      │   │ HÀNH LANG 2 bắc y −66,5                           │           │
 KHE TÂY  ═══ y −74,7 │ HL1│HL2  ┌─ chữ C trong ─┐   HL2│HL1 ═══ KHE ĐÔNG (x −605…−602,5)│ ← lối đi lát đá
 (về biệt thự)        │tây │tây  │  BỆ TÂM       │   đông│đông                             │   x −603…−600
                      │−635,8 −629,5  khoảng trống −613,3 −607,2                          │ ← BÃI CỎ: me_cung (−598; −75)
                      │   │      x −625,5…−617,5, y −70,6…−78,2, mở đông/tây             │      = NGOÀI mê cung
                      │   │ HÀNH LANG 2 nam y −82,9                           │           │
                      │   └──────────── khe x −621,6 ──────────┘              │           │
                      │  HÀNH LANG 1 nam  y −88,8  (x −637,7 … −605,3)                    │
              y −93,9 └───────────────────────────────────────────────────────────────────┘
                     x −640,4                                                         x −602,5
```

- Mê cung ≈ 38 × 38 m, tâm (−621,5; −74,6). Khe vào ngoài: ĐÔNG và TÂY ở y ≈ −74,7. Vòng 2 mở ở BẮC và NAM (x ≈ −621,6).
  Chữ C trong mở ĐÔNG/TÂY vào khoảng trống tâm (≈ 8 × 7,5 m, có bệ cỏ ở giữa). Đường đi thật từ khe đông tới tâm:
  HL1 đông → rẽ lên bắc (hoặc nam) → HL1 bắc → khe vòng 2 (x −621,6) → HL2 bắc → rẽ đông/tây → xuống y −74,6 → vào tâm. Có rẽ
  trái/phải đúng như shot 6 tả.
- Hàng rào chỉ cao ≈ 2,1 m (`clearance.background_top_m` = 2,12 ở shot 5) → **từ BẤT KỲ điểm nào trong mê cung, nhìn về 230–310°
  (tây) thì biệt thự cao lù lù phía trên hàng rào** (ảnh toàn shot 7: biệt thự chiếm nửa trên khung). Nhìn đông/bắc/nam: chỉ
  hàng rào + cây thông/đá → "trong mê cung" đúng nghĩa.
- Các tọa độ đề xuất dưới đây đã lấy mẫu màu trên ảnh nhìn trên: đều rơi vào nền lát đá (lối đi), không vào hàng rào.

## 2. Bảng từng shot (máy = kết quả gọi khô plan(), khớp cache)

| Shot | Cảnh | Chỗ đứng (tọa độ) | plate_view | Máy → nhìn | Kết luận | Lý do |
|---|---|---|---|---|---|---|
| 5 WS push_in | 2 | `me_cung` (−598; −75) | 270 | (−595,9; −75) → tây, 24 mm | **SAI** | Chỗ đứng là BÃI CỎ NGOÀI mê cung (phía đông, sau lối lát đá); nhìn 270° = qua khe đông thẳng vào biệt thự. Ảnh: cỏ tiền cảnh, lối lát, hàng rào, biệt thự. |
| 6 MLS high track | 2 | `me_cung` (−598; −75) | 270 | (−596,6; −75) → tây, cúi −30° | **SAI** | Cùng chỗ bãi cỏ ngoài mê cung; không ở lối nào, không có ngã rẽ; nền vẫn là biệt thự. |
| 7 MS | 2 | `trung_tam_me_cung` | 270 | (−620,4; −74,5) → tây | **Vị trí ĐÚNG, hướng SAI** | Đứng đúng tâm, nhưng 270° = biệt thự chiếm nửa khung phía trên hàng rào (ảnh toàn `k3fa757…`). Why ghi "máy cùng phía trục nhìn về cũi" — không cần nhìn về tây. |
| 8 CU cũi | 2 | `trung_tam_me_cung` | 270 | (−620,7) → tây, 65 mm | **Vị trí ĐÚNG, hướng nên đổi** | Cận 65 mm ít thấy nền nhưng vẫn là mảng tường biệt thự; đổi cùng 7, 9 cho một sân khấu. |
| 9 MS | 2 | `trung_tam_me_cung` | 270 | như 7 | **Vị trí ĐÚNG, hướng SAI** | Như 7. |
| 10 MS low | 3 | `trung_tam_me_cung` | 90 | (−622,6) → đông | **ĐÚNG** | Nền: khe đông chữ C, hàng rào, cây thông, không biệt thự (ảnh toàn `kbe5785…`). |
| 11 CU high | 3 | `trung_tam_me_cung` | 90 | (−622,3) → đông, cúi −35° | **ĐÚNG** | Nhìn xuống bệ. |
| 12 MS | 3 | `trung_tam_me_cung` | 90 | như 10 | **ĐÚNG** | |
| 13 GAME_TPS | 4 | `me_cung` (−598; −75) | 270 | (−594,4; −74,7) cao 2,6 m → tây | **SAI** | Đánh 4 địch trên bãi cỏ NGOÀI mê cung, nền biệt thự. Kịch bản: "giữa sương mù mê cung… misty maze clearing, hedge maze walls fading into fog behind". |
| 14 GAME_TPS | 4 | `me_cung` | 270 | như 13 | **SAI** | Như 13. |
| 15 MLS | 4 | `me_cung` | 90 | (−599,4) → đông | **SAI** | Vẫn bãi cỏ ngoài mê cung (nền đông = cỏ/đá ngoài mê cung, không phải "giữa 4 kẻ địch đã gục" trong mê cung). |
| 16–18 | — | Phòng hai cửa (Kho 448) | — | — | ngoài phạm vi | Không phải mê cung — phiên A (luật máy lọt tường) lo. |
| 19–22 | — | Tháp Đồng Hồ `duong_bac` | 173 | — | ngoài phạm vi | Không phải mê cung. |

## 3. Gốc lỗi

**Chủ yếu do DỮ LIỆU, code chỉ "mù" nên không chặn được.**

1. **Chỗ đứng `me_cung` đăng ký sai chỗ** (Kho #265, `model3d.spots.me_cung` at (−598; −75), label "mê cung cây xanh phía đông",
   `view` (−621; −75)): nằm trên bãi cỏ NGOÀI mê cung ≈ 4,5 m về phía đông của hàng rào ngoài, và điểm cảnh quan `view` trỏ qua tâm
   mê cung → hướng 270° = đúng hướng biệt thự (anchor 270,4°). Mê cung KHÔNG có chỗ đứng nào trong lối (chỉ `trung_tam_me_cung` thêm
   15/10). Đạo diễn chỉ thấy tên + nhãn, chọn `me_cung` cho mọi shot "mê cung" và lấy `scenery` 270° làm "gia đình hướng" cho cả cảnh
   (why shot 5: "chọn azimuth theo scenery_bearing_deg (270°)… không có mốc xa để dùng" — SAI: mốc biệt thự nằm đúng 270°).
2. **Hướng 270° chép sang cả cảnh 2** (shot 5–9 cùng 270 để "giữ gia đình hướng") → mọi máy nhìn biệt thự. Hàng rào thấp 2,1 m nên
   trong mê cung mà nhìn tây vẫn thấy biệt thự.
3. **Cảnh 4 (13–15) dùng lại `me_cung`** thay vì khoảng trống tâm (vừa có cũi → súng ở cảnh 3) — chỗ duy nhất trong mê cung đủ rộng
   cho 4 địch "vây quanh".
4. **Code (mù, đúng như memory reference_plate_camera_blind):** `plate_camera.camera_for` (core/plate_camera.py:146) đặt máy từ
   chỗ đứng + hướng + cỡ cảnh; Blender clearance chỉ xử lý vật cản trên đường nhìn, không biết "chỗ đứng có thuộc khu vực shot nói
   (mê cung) không" hay "nền đang là mốc mà why bảo không có mốc". Không có kiểm nào báo:
   - `location_pack.spot_problem` (core/location_pack.py:158) chỉ báo tên chỗ đứng không tồn tại;
   - `plate_choice._contradicts_why` (core/plate_choice.py:113) chỉ bắt why "mốc sau lưng máy" (`LANDMARK_BEHIND_CAMERA`,
     core/plate_view_check.py:36), không bắt "không có mốc / no landmark" trong khi nền chĩa đúng mốc (shot 5 lọt);
   - `director_block` (core/location_pack.py:186–211) chỉ in tên + nhãn chỗ đứng, không in hướng mốc từ mỗi chỗ đứng → Đạo diễn
     không biết 270° = biệt thự; Kho #265 cũng chưa có `model3d.landmark` (chữ prompt rơi về "the landmark").

## 4. Nhánh `origin/claude/p31-plate-rules` có giải quyết không?

**Không giải quyết lỗi mê cung** (chỉ phát hiện được một phần):
- `camera_problem` (máy NGOÀI phòng) dựa vào clearance `outside` — cho máy trong nhà không trần; ngoài trời mê cung không kích hoạt.
- Nâng sáng đêm (`plate_env` FINISH_VERSION) — giúp độ tối, không liên quan vị trí.
- `stage_report` / `_stage_hold` (autopilot): cảnh 2 có 2 chỗ đứng (`me_cung` shot 5–6, `trung_tam_me_cung` 7–9) → DỪNG một lần ở
  cổng plates cho người xác nhận. Nhưng docstring lấy chính ví dụ "đi từ mép mê cung vào tâm" làm hợp lệ → dễ bị bấm xác nhận cho
  qua. Cảnh 4 chỉ 1 chỗ đứng (`me_cung`) → không dừng. Sau khi sửa dữ liệu (mục 5) cảnh 2 vẫn nhiều chỗ đứng (lối vào → ngã rẽ →
  tâm) — đó là di chuyển có chủ đích, xác nhận được.

## 5. Cách sửa (phiên chính, qua Dashboard — sao lưu CSDL trước)

### 5a. Kho #265 — thêm chỗ đứng trong lối (group `me_cung`) + sửa nhãn cũ

| Tên đề xuất | at (x; y; z) | Dùng cho | Ghi chú |
|---|---|---|---|
| `me_cung_loi_vao_dong` | (−607,2; −74,7; 67,884) | shot 5 | HL1 đông, ngay sau khe vào đông. Lối chạy bắc–nam dài ≈ 35 m. |
| `me_cung_nga_re_bac` | (−621,6; −60,3; 67,884) | shot 6 | Ngã ba HL1 bắc × khe vòng 2 (rẽ trái xuống HL2). |
| (giữ) `trung_tam_me_cung` | (−621,5; −74,6; 67,884) | shot 7–15 | Khoảng trống tâm 8 × 7,5 m. |

- Sửa nhãn `me_cung` thành "bãi cỏ NGOÀI mê cung, phía đông (trước khe vào đông) — nhìn tây là biệt thự" (để Đạo diễn không
  chọn làm "trong mê cung"); có thể đặt `group: "ngoai_me_cung"`.
- Đặt `model3d.landmark` = "the villa (biệt thự)" cho Kho #265.
- z lấy theo mặt đất của `me_cung`/`trung_tam_me_cung` (67,884); nên chạy probe/top_view 0 USD kiểm lại trước khi ghi.

### 5b. Từng shot

| Shot | plate_spot | plate_view.background | Máy dự kiến | Nền sẽ thấy |
|---|---|---|---|---|
| 5 | `me_cung_loi_vao_dong` | **0** (bắc, dọc HL1 đông) | ≈ (−607,2; −76,8), trong lối | Hành lang cây hai bên chạy xa, góc rào, cây — không biệt thự (ống 24 mm dọc 9:16 rộng ≈ ±22°, biệt thự lệch 90°). |
| 6 | `me_cung_nga_re_bac` | **90** (đông; máy dẫn trước mặt, Kelly đi về tây rồi rẽ trái) | ≈ (−623; −60,3), cao, cúi −30° | Đỉnh rào + ngã rẽ, lối vừa đi qua; không biệt thự. (Nếu muốn máy bám SAU lưng thì nền = tây = biệt thự → không nên.) |
| 7, 8, 9 | `trung_tam_me_cung` | **90** (đổi từ 270) | ≈ (−622,6) → đông | Kelly bước ra từ khe đông chữ C (lối cuối) đi về phía máy, cũi trên bệ; nền rào + cây thông. Khớp cảnh 3 (10–12 cũng 90) → một sân khấu cho 7–12. Blocking 7 (Kelly trái khung, cũi phải khung) giữ nguyên được. |
| 10–12 | giữ | giữ 90 | — | ĐÚNG. |
| 13, 14 | **`trung_tam_me_cung`** (đổi từ `me_cung`) | **90** | TPS sau lưng ≈ (−625,1; −74,6) cao 2,6 m, vẫn trong khoảng trống (cạnh khe tây chữ C) | 4 địch ở nửa đông khoảng trống + khe đông, nền rào/cây — "misty maze clearing". |
| 15 | **`trung_tam_me_cung`** | ngược trục = **270** (sẽ thấy mái biệt thự trên rào) — hoặc **0/180** nếu không muốn biệt thự (xoay 90°, ghi lý do "Kelly xoay người ăn mừng") | 270: máy ≈ (−620,1) → tây | Người dùng chọn; khuyên 0 (bắc: chữ C trong ngay sau lưng 3 m, cây thông) cho nhất quán "không biệt thự". |

Sau khi sửa: các nền 5, 6, 7–9, 13–15 đổi key → render lại (0 USD, Blender). Kiểm ảnh toàn từng shot trước khi gen ảnh.

### 5c. Code (KHÔNG sửa ở phiên này — phiên nền 3D làm, đề xuất)

1. `core/location_pack.py:186–211` `director_block`: mỗi chỗ đứng in thêm "mốc ở hướng X° từ đây" (`plate_choice.bearing(at,
   anchor)`) và hướng `view` → Đạo diễn thấy 270° = biệt thự.
2. `core/plate_view_check.py:36` / `core/plate_choice.py:113` `_contradicts_why`: thêm mẫu "không có mốc / no landmark / không
   thấy mốc" → nền trong ±30–60° hướng mốc = báo (shot 5 sẽ bị bắt).
3. `core/location_pack.py:158` `spot_problem`: khi chữ cảnh/shot nói một khu vực có group trong Kho (vd "mê cung" ↔ group
   `me_cung`) mà `plate_spot` không thuộc group đó → VÀNG "chỗ đứng ngoài khu vực shot nói". Cần dữ liệu group (5a).
4. (Đã có ở nhánh p31-plate-rules) `stage_report`: không nên coi "mép → tâm" là ví dụ hợp lệ mặc định trong docstring.
