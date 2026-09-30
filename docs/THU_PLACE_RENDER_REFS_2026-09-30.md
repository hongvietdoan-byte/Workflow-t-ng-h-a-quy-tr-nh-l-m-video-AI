# Thử cờ `place_render_refs` + ánh sáng ấm — 2026-09-30 (0 USD, không gửi ảnh nào đi)

Người dùng 29/09: "6 ảnh Kho chưa chắc hợp mọi góc — pipeline cần góc khác thì render mới được không" + "tối ưu để model vẽ chuẩn hơn";
30/09: "các cảnh nên tông ấm, ban ngày trời nắng". Ghép phông xanh vẫn bỏ (`location_plates` tắt, #8). Cờ mới render 3D **đúng góc máy
từng shot** làm **ảnh tham chiếu** cho model vẽ cả cảnh (`core/place_refs.py`).

## 1. Chạy khô trên dự án #8 (33 shot, Tháp Đồng Hồ #263)
Cách chạy: bản sao CSDL (sao chép bằng API backup của SQLite — xem mục 4), `FEATURE_PLACE_RENDER_REFS=1` trong tiến trình (không sửa
`dashboard.env`), provider ảnh giả (`MockImageProvider`), `ImageRunner._submit_args` dựng đúng prompt + ảnh tham chiếu sẽ gửi.

| Kiểm | Kết quả |
|---|---|
| Render đúng góc từng shot (Blender) | 33/33, 0 lỗi (2 lượt Blender: 9 góc đêm + 20 góc ngày; ~5 phút) |
| Shot nhận ảnh `place_render` thay ảnh Kho của nơi | 33/33 (ảnh toàn cảnh của cảnh vẫn giữ) |
| Prompt có câu số đo (ống kính, độ cao máy, khoảng cách, đầu–chân %, chân trời, hướng nắng) | 33/33 |
| Chỗ đứng tên cũ của bản FFXN (`level_26_0`) | 3 shot (S05, S11, S20) — rơi về chỗ khác **có báo** |

**Số gốc — khung #8 đã vẽ trước đây có khớp bản đồ thật không** (`background_match`: F1 đường nét nền, trừ ô nhân vật; 1 = trùng kiến trúc,
< 0,35 = model vẽ lại kiến trúc): 19 khung đo được — **trung bình 0,073**, cao nhất 0,176, **19/19 dưới 0,35**. Đúng với lỗi đã thấy ở #8
(tháp nhiều tầng, nền bịa): #8 vẽ từ ảnh bản fan + chữ. Khung cận (CU / MCU) đa phần không đo được (nền render gần như trời / tường trơn).
Lần thử trả tiền với cờ bật sẽ so với số này.

## 2. Lỗi tìm ra nhờ chạy khô — đã sửa
1. **Độ cao máy sai trong câu số đo** (shot cận ghi "camera 4.9 m above the ground"): độ cao lấy từ thông số render — tính SAU khi nâng mô hình
   cho đáy về 0 (Tháp nâng ~3,3 m) — trừ độ cao chỗ đứng tính theo toạ độ gốc. Sửa: cả hai theo toạ độ gốc (máy ảo của shot). Test.
2. **33/33 shot đứng cùng một chỗ (`plaza_front`)** dù kịch bản ghi "khu nhà ở dưới chân tháp", "góc khuất gần khu nhà", "chiến trường…":
   `plate_spot` chỉ được Director viết khi thấy danh sách chỗ đứng, mà danh sách chỉ đưa khi bật ghép phông xanh. Sửa: (a) Director thấy danh
   sách chỗ đứng (tên + mô tả, đánh dấu "trong nhà") cả khi bật `place_render_refs`; (b) shot không có `plate_spot` → `location_pack.auto_spot`
   chọn chỗ có mô tả trùng nhiều chữ nhất với nơi / chữ của shot (chỗ trong nhà chỉ khi shot nói trong nhà); không khớp → mặc định; tên chỗ
   lạ (FFXN) → chỗ khớp chữ, có báo. Test.

## 3. Ánh sáng ngày tông ấm, trời nắng (người dùng 30/09)
A/B trên 2 góc mỗi khu (đo màu trung bình nửa dưới = nhà + nền, nửa trên = trời):

| Phương án | Nhà + nền (R−B) | Trời | Nhận xét |
|---|---|---|---|
| 0 hiện tại (29/09) | −7 … −10 (ngả xanh) | xanh | lạnh |
| Chỉ đổi màu nắng | ≈ không đổi | xanh | mặt nhìn thấy nhận ánh trời xanh — màu nắng không đủ |
| Cân bằng trắng 8500–9500 K | +13 … +19 | **xám nhạt** | ấm nhưng mất trời nắng |
| **E: ánh trời hắt vào cảnh nhuộm ấm + dịu, trời máy nhìn thấy giữ xanh (0,18), nắng vàng 6, WB 7000 K** | **+22 … +23** | **xanh đậm** | **chọn** |

**Góp ý tiếp của người dùng (30/09): E ấm nhưng tối, như xế chiều — ảnh làm tham chiếu cần đủ sáng để model đọc rõ chi tiết.** A/B lần 2
(đo trên nửa dưới ảnh = nhà + nền; "vùng tối" = phân vị 10 % độ sáng; trời = B−R của dải trên cùng):

| Phương án | Sáng TB (Tháp / Cổng Trời) | Vùng tối p10 | Ấm R−B | Trời xanh đậm | Nhận xét |
|---|---|---|---|---|---|
| E (ấm chiều) | 103 / 75 | 32 / 45 | −1 / +20 | — | tối, bóng chìm chi tiết |
| G (trưa sáng) | 138 / 121 | 64 / 81 | −4 / −1 | 78 | sáng nhưng mất ấm, trời nhạt |
| **J (trưa nắng ấm) — CHỌN** | **129 / 117** | **60 / 75** | **0 / +16** | **97 / 102** | sáng rõ, ấm nhẹ, trời xanh đậm |

J: mặt trời 58°, phơi sáng +0,1, ánh trời 0,2 nhuộm [1, 0,83, 0,64], trời nhìn thấy 0,14, nắng 5,6 màu [1, 0,87, 0,68], cân bằng trắng
7600 K. Lưu `light.day` của #263 / #265 (thay E). Còn: nước hồ bơi hơi trắng do phản chiếu trời sáng — chỉnh sau nếu cần.

Cơ chế mới trong `render_plates.setup_world`: `camera_strength` (trời máy nhìn thấy) tách khỏi `strength` × `ambient_tint` (ánh trời chiếu
vào cảnh) bằng nút Light Path "Is Camera Ray"; thêm `white_balance`. Lưu vào `model3d.light.day` của #263 và #265 (có trong khoá đệm nền —
render lại tự động). Ghi chú: chiều cân bằng trắng của Blender — số K cao hơn = ảnh ấm hơn (4500 K xanh nhất).

## 4. Sự cố sao lưu CSDL — đã sửa cách làm
CSDL chạy chế độ WAL: thay đổi mới nằm ở `manifest.sqlite-wal`. Các bản sao lưu tạo bằng `cp` ngày 29/09 tối (`before_surroundings`,
`before_indoor`) và sáng 30/09 (`before_kho_3d`) **thiếu phần thay đổi chưa gộp** — không dùng để khôi phục những bước đó. Dữ liệu thật
không mất. Từ nay sao lưu bằng API backup của SQLite (`sqlite3.Connection.backup`); bản đúng: `data/backup/manifest.after_kho_3d_2026-09-30.sqlite`,
`manifest.before_warm_light_2026-09-30.sqlite`.

## 5. Kho sau khi thay (người dùng duyệt 29/09)
#263 Tháp và #265 Cổng Trời: mỗi mục 6 ảnh render 3D đã duyệt (vai trò ngang mắt / thấp / cao / chi tiết). Ảnh cũ (13) sao lưu ở
`data/backup/kho_anh_cu_2026-09-29/` + `asset_images_da_go.json`; #84 gộp vào #265 (alias "Khu vực - Cổng Trời mới"); nguồn Drive
"in-game all map image" bỏ qua "cong troi moi". Ảnh Kho sẽ được thay bằng bản ánh sáng ấm khi render lại xong.

## 6. Đề xuất bước tiếp (cần người dùng duyệt — tốn tiền)
Bật `place_render_refs` cho **1 cảnh** (3–5 shot ở Tháp, ban ngày), vẽ ảnh toàn cảnh + ảnh shot bằng model đang dùng; so độ khớp nền với số
gốc 0,073 và xem bằng mắt. Ước tính: 1 ảnh toàn cảnh + 3–5 ảnh shot (giá theo `data/pricing` của model ảnh dự án).

## 7. S5.5' — thử trả tiền 1 cảnh (30/09 chiều, người dùng duyệt; dự án thử #13, **0,312 USD**, trần riêng 1 USD)
Cảnh "khu nhà dưới chân tháp" của #8 (shot 20–24, ban ngày) chép sang #13 (#8 không đổi); `tools/experiments/place_refs_trial.py`
(setup → plates → plan → frames → measure). Ảnh so sánh: `D:/AI-Video-Output/2026-09-30_thu-place-refs/`.

**Trước khi trả tiền — chạy khô tìm 1 lỗi, đã sửa + test:** `auto_spot` chọn chỗ đứng theo chữ riêng từng shot → cùng một cuộc nói
chuyện, shot 20/21/23 đứng ở chân tháp còn 22/24 ở đồng cỏ tây nam cách ~150 m. Sửa: chữ nơi của cảnh (`location` / `set`, giống nhau mọi
shot) quyết trước, chữ riêng shot chỉ khi nơi không khớp chỗ nào; chữ ở tên chính của chỗ (trước "—") nặng gấp đôi phần mô tả phụ. Sau sửa:
5/5 shot cùng chỗ `nha_lon_dong`, render rõ nhà mái đỏ / tường / bãi xe (góc ngược).

**Kết quả (1 ảnh toàn cảnh + 5 khung, gpt-image-2.5-sunburst):**
| | Kết quả |
|---|---|
| Ảnh toàn cảnh cảnh 4 (không có chữ tả nơi khác) | **khớp render** bằng mắt: nhà mái đỏ, tường chắn, bậc thang, bãi cỏ, xe hỏng |
| 5 khung shot | **0/5 theo render** — cả 5 vẽ quảng trường lát đá + tháp nhọn như khung #8 cũ; model theo CHỮ: prompt Director cũ của #8 ("stone plaza, the clock tower in background") + câu Setting chung ("tower stands on a wide flat stone plaza") mâu thuẫn ảnh render |
| Độ khớp nền (`background_match`) | mới 0,202 · khung #8 cũ cùng shot 0,208 — **số đo không phân biệt được** (cạnh mặt đất / cỏ trùng ngẫu nhiên); đọc bằng mắt, không dùng số này làm kết luận |

**Bài học → đã sửa (0 USD):** khi gửi render, prompt nói trước phần chữ rằng **render quyết định nơi chốn**, chữ về nền / nhà / tháp / tường
trái với render thì bỏ, chỉ lấy người, hành động, biểu cảm, ánh sáng từ chữ (`place_refs.PRECEDENCE`; chạy khô #13: 5/5 prompt có câu này).
Ở luồng thật, Director chạy lại với danh sách chỗ đứng sẽ viết chữ đúng nơi — lần thử này dùng prompt cũ của #8 nên mâu thuẫn nặng nhất.
Số `background_match` cần sửa trước khi làm thước đo (bỏ vùng cỏ / mặt đất, chỉ so đường nét kiến trúc) — ghi việc tồn.

**Chờ người dùng:** vẽ lại 5 khung #13 với câu mới (≈ 0,26 USD; tổng S5.5' ≈ 0,57 USD) — đổi đầu vào đúng luật, lần vẽ lại 1/2.
