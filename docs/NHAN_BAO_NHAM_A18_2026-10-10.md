# Bảng gán nhãn báo nhầm — khóa nhận diện A18 (10/10)

Thẩm định 4 lỗ hổng #1 + thẩm định 5 #4/#5: luật A18 "mọi món must_keep phải có chữ trong prompt" chưa đo báo nhầm. Bảng này lấy
từ chạy khô #22 + #24 (prompt ảnh thật trong CSDL, BYĐ `data_out/k0b_p<id>/byd_shot*.json`), sinh bằng `tools/nhan_bao_nham_a18.py` — chạy lại ra đúng bảng.

**Ngưỡng nhận:** Mục 9 kế hoạch chỉ có ngưỡng cho LỚP CLAUDE: báo nhầm ≤ 10 % trước khi chặn, cỡ mẫu ≥ 50 mục trên ≥ 2 dự án. Lớp CODE A18 có ngưỡng riêng — **người dùng chốt 10/10 (A25): báo nhầm ≤ 10 % trên n ≥ 30 mục, lấy từ ≥ 2 dự án (#22 + #24)**. Chưa đạt → `CHAN_DO = False` (thiếu chữ = VÀNG, không chặn).

## Số đo trước / sau lọc theo BYĐ (từng dự án)

| Dự án (số shot) | món `thieu` trước → sau | món bị báo (thieu + thieu_mau + sai_mau) trước → sau | thieu_mau / sai_mau sau | shot có món bị báo trước → sau | món `khong_can` sau |
|---|---|---|---|---|---|
| #22 (9) | 18 → 13 | 18 → 13 | 0 / 0 | 8 → 5 | 5 |
| #24 (9) | 34 → 24 | 36 → 26 | 0 / 2 | 9 → 9 | 17 |

(Đối chiếu: summary.json của chạy khô — đã lọc theo BYĐ — ghi số `thieu`: #22 = 13, #24 = 24; khác cột "sau" nghĩa là CSDL đổi sau lần chạy khô.)

## Gán nhãn (mỗi mục một chạm)

Cột cuối: ghi **đúng lỗi** (prompt thật sự thiếu / sai món đó, ảnh dễ vẽ sai) hoặc **báo nhầm** (món có trong khung đúng hoặc không
cần chữ ở shot này). Kết quả code: `thieu` = không có chữ món; `thieu_mau` = có món, thiếu màu chính; `sai_mau` = màu ngược khóa.
Chọn mục: chia đều giữa các dự án, trong một dự án xoay vòng theo shot. Mục đã chọn mỗi dự án: #22 = 13/13, #24 = 17/26 (tổng 30).

| # | Dự án | Shot (cỡ) | Nhân vật | Món (màu khóa) | Kết quả code | Mức | Trích prompt (≤ 15 từ) | Agent đề xuất (lý do ≤ 20 từ, độ chắc cao/vừa/thấp) | Người dùng: đúng lỗi / báo nhầm |
|---|---|---|---|---|---|---|---|---|---|
| 1 | #22 | 4 (MCU) | MAXIM KL | hair (white/grey) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up from mid-chest up, no legs, inside … | **đúng lỗi** — MCU thấy rõ tóc, prompt không tả tóc; ảnh 527 vẫn đúng xám bạc nhờ ảnh ref (vừa) | |
| 2 | #22 | 5 (MCU) | KELLY | crop top (white) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up, Kelly (dark brown bob haircut, blunt … | **đúng lỗi** — chỉ ghi 'yellow tracksuit'; áo crop trắng thấy rõ ở ảnh 528 (vẽ đúng nhờ ref) (vừa) | |
| 3 | #22 | 7 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | two stylized young characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — prompt không gọi tên/tả Maxim; WS thấy tóc; ảnh 556 đúng nhờ ref (vừa) | |
| 4 | #22 | 8 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | same two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — prompt không gọi tên/tả Maxim; WS thấy tóc; ảnh 557 đúng nhờ ref (vừa) | |
| 5 | #22 | 9 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP over … | **đúng lỗi** — prompt không gọi tên/tả Maxim; WS thấy tóc; ảnh 558 đúng nhờ ref (vừa) | |
| 6 | #22 | 7 (WS) | KELLY KL | skirt (black) | thieu | VÀNG | two stylized young characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — WS thấy rõ chân váy da đen (ảnh 556); prompt chỉ 'red dinosaur outfits' (đúng nhờ ref) (vừa) | |
| 7 | #22 | 8 (WS) | KELLY KL | hair (brown) | thieu | VÀNG | same two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — S7 có câu khóa tóc Kelly, S8 mất; ảnh mẫu 417 tóc trắng-đỏ dễ lẫn (ảnh 557 vẫn đúng) (cao) | |
| 8 | #22 | 9 (WS) | KELLY KL | hair (brown) | thieu | VÀNG | two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP over … | **đúng lỗi** — S7 có câu khóa tóc Kelly, S9 mất; ảnh mẫu 417 tóc trắng-đỏ dễ lẫn (ảnh 558 vẫn đúng) (cao) | |
| 9 | #22 | 7 (WS) | KELLY KL | stockings (black/red) | thieu | VÀNG | two stylized young characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — tất lệch đỏ/đen thấy rõ ở WS (ảnh 556), prompt không tả; món là tất ngắn (thấp) | |
| 10 | #22 | 8 (WS) | KELLY KL | skirt (black) | thieu | VÀNG | same two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — WS thấy rõ chân váy đen (ảnh 557); prompt không tả (đúng nhờ ref) (vừa) | |
| 11 | #22 | 9 (WS) | KELLY KL | skirt (black) | thieu | VÀNG | two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP over … | **đúng lỗi** — WS thấy rõ chân váy đen (ảnh 558); prompt không tả (đúng nhờ ref) (vừa) | |
| 12 | #22 | 8 (WS) | KELLY KL | stockings (black/red) | thieu | VÀNG | same two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP … | **đúng lỗi** — tất lệch đỏ/đen thấy rõ (ảnh 557), prompt không tả (thấp) | |
| 13 | #22 | 9 (WS) | KELLY KL | stockings (black/red) | thieu | VÀNG | two stylized characters in red dinosaur (both with the black shark-tooth mask worn UP over … | **đúng lỗi** — tất lệch đỏ/đen thấy rõ (ảnh 558), prompt không tả (thấp) | |
| 14 | #24 | 1 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | **đúng lỗi** — WS toàn thân, giày thấy rõ (ảnh 623), prompt không nói giày trắng (vừa) | |
| 15 | #24 | 2 (WS) | KELLY | hair (brown) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | **đúng lỗi** — S1/S4 có 'short dark bob', S2 không; WS nghiêng thấy tóc (ảnh 632 đúng nhờ ref) (vừa) | |
| 16 | #24 | 3 (MS) | KELLY | hair (brown) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | **đúng lỗi** — qua vai sau lưng: tóc chiếm lớn khung, prompt không tả (ảnh 634 đúng nhờ ref) (vừa) | |
| 17 | #24 | 4 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | **đúng lỗi** — ngã ngồi, chân duỗi về giếng — giày thấy rõ (ảnh 639), prompt không nói (vừa) | |
| 18 | #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | **đúng lỗi** — prompt 'red sash' ngược Kho (đai gai đen khóa tam giác đỏ); ảnh 636 vẽ khăn đỏ — SAI (cao) | |
| 19 | #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | **đúng lỗi** — prompt 'red sash' ngược Kho; ảnh 637 lần này đúng nhờ ref, lần S5 đã sai (vừa) | |
| 20 | #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | **đúng lỗi** — MLS đai gai khóa tam giác đỏ thấy rõ (ảnh 629); prompt không tả (vừa) | |
| 21 | #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | dress (black) | thieu | VÀNG | Close-up, eye level, slow push-in, Free Fire in-game 3D render style, the comic-style black-faced creature … | **đúng lỗi** — quỳ ôm mặt, váy đen chiếm nửa khung (ảnh 640), prompt không tả váy (vừa) | |
| 22 | #24 | 9 (WS) | KELLY | hair (brown) | thieu | VÀNG | Kelly small seated on the ground on the left | **đúng lỗi** — WS Kelly nhỏ nhưng tóc vẫn đọc được; prompt không tả (ảnh 633 đúng) (thấp) | |
| 23 | #24 | 2 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | **đúng lỗi** — nghiêng, áo khoác mở thấy áo trắng bên trong (ảnh 632); prompt không tả (vừa) | |
| 24 | #24 | 3 (MS) | KELLY | tracksuit (yellow) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | **đúng lỗi** — qua vai: áo khoác vàng chiếm nửa khung (ảnh 634); prompt S3 không nhắc (vừa) | |
| 25 | #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | hands (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | **đúng lỗi** — tay đen móng đỏ thấy rõ (ảnh 629); prompt chỉ tả biến hình (thấp) | |
| 26 | #24 | 9 (WS) | KELLY | crop top (white) | thieu | VÀNG | Kelly small seated on the ground on the left | **đúng lỗi** — áo trắng trong áo khoác thấy được dù Kelly nhỏ (ảnh 633); prompt không tả đồ (thấp) | |
| 27 | #24 | 2 (WS) | KELLY | tracksuit (yellow) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | **đúng lỗi** — WS bộ thể thao vàng chiếm thân (ảnh 632); prompt S2 không nhắc (vừa) | |
| 28 | #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings (black/red) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | **đúng lỗi** — chân chuyển đỏ thấy rõ (ảnh 629); prompt không tả (thấp) | |
| 29 | #24 | 9 (WS) | KELLY | tracksuit (yellow) | thieu | VÀNG | Kelly small seated on the ground on the left | **đúng lỗi** — bộ vàng nổi bật (ảnh 633); prompt S9 không tả đồ Kelly (vừa) | |
| 30 | #24 | 2 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | **đúng lỗi** — giày trắng thấy rõ (ảnh 632); prompt không tả (vừa) | |

9 mục bị báo khác chưa đưa vào bảng (giới hạn 30).

## Món bị lọc (`khong_can`) — để người dùng xem lọc có che lỗi thật không

| Dự án | Shot (cỡ) | Nhân vật | Món | Lý do |
|---|---|---|---|---|
| #22 | 1 (MS) | MAXIM | sneakers | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #22 | 3 (MCU) | MAXIM | sneakers | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #22 | 5 (MCU) | KELLY | sneakers | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #22 | 6 (MCU) | KELLY KL | skirt | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'skirt' ở 45 % — ngoài khung |
| #22 | 6 (MCU) | KELLY KL | stockings | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| #24 | 1 (WS) | KELLY | choker | quay lưng (BYĐ thay = lung|nghieng): 'choker' ở mặt trước thân, khuất khi không quay mặt |
| #24 | 1 (WS) | KELLY | crop top | quay lưng (BYĐ thay = lung|nghieng): 'crop top' ở mặt trước thân, khuất khi không quay mặt |
| #24 | 2 (WS) | KELLY | choker | món nhỏ 'choker' chỉ vài điểm ảnh ở cỡ WS — không đòi chữ (ảnh tham chiếu giữ món) |
| #24 | 3 (MS) | KELLY | choker | quay lưng (BYĐ thay = lung|nghieng): 'choker' ở mặt trước thân, khuất khi không quay mặt |
| #24 | 3 (MS) | KELLY | crop top | quay lưng (BYĐ thay = lung|nghieng): 'crop top' ở mặt trước thân, khuất khi không quay mặt |
| #24 | 3 (MS) | KELLY | sneakers | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #24 | 4 (WS) | KELLY | choker | quay lưng (BYĐ thay = lung|nghieng): 'choker' ở mặt trước thân, khuất khi không quay mặt |
| #24 | 4 (WS) | KELLY | crop top | quay lưng (BYĐ thay = lung|nghieng): 'crop top' ở mặt trước thân, khuất khi không quay mặt |
| #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MLS chỉ chứa 75 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | belt | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'belt' ở 45 % — ngoài khung |
| #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | hands | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'hands' ở 45 % — ngoài khung |
| #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | legs | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'legs' ở 60 % — ngoài khung |
| #24 | 9 (WS) | KELLY | choker | món nhỏ 'choker' chỉ vài điểm ảnh ở cỡ WS — không đòi chữ (ảnh tham chiếu giữ món) |

## Giới hạn / chưa có
- #22 không có shot_specs viết tay: BYĐ dựng từ chữ kịch bản (`spec_from_scene` — size / angle / characters / blocking),
  mọi ô ghi `suy_tu_chu` trong `data_out/k0b_p22/byd_shot*.json`. Nhân vật mặc bộ Khủng Long ('… KL'): khóa = tóc/mặt/mắt
  của nhân vật (Kho 33 / 23) + món của trang phục (Kho 416 / 417, mô tả tiếng Việt — món suy từ chữ, có thể sai).
- Món KHÔNG nhận ra (`khong_nhan_ra` trong summary.json: vd bomber / quần của Maxim, 'Hoodie đỏ…' của Kho 416) không được
  kiểm → không có trong bảng; tỉ lệ báo nhầm chỉ đo trên món code nhận ra.
- Lọc chưa chỉnh theo tư thế (ngồi / quỳ / bò đổi phần thân trong khung) và chưa thấy vật che (bàn, thành giếng) — K1a.
- `segment`: hai nhân vật cùng từ đánh dấu (hai dạng yêu nữ cùng 'creature'; 'MAXIM' với 'MAXIM KL' khi chỉ ghi 'Maxim')
  → mệnh đề thuộc CẢ HAI (sửa 10/10, ca `test_segment_shared_marker_belongs_to_both_forms`). Đoạn tả 'biến hình từ dạng
  A sang dạng B' vẫn tính cho cả hai dạng → màu của dạng kia có thể ra `sai_mau` (người dùng gán để đo).

## Agent đề xuất (10/10)

Agent gán 30/30 mục (nhãn ĐỀ XUẤT, người dùng duyệt cột cuối): **đúng lỗi 30 / báo nhầm 0** → tỉ lệ báo nhầm ước **0 %** (n = 30; ngưỡng A25 ≤ 10 %). Độ chắc thấp: 7 mục.

⚠ Thẩm định 6: bảng này được CHỌN LẠI sau khi sửa A26 (b) và cùng các mục đã dùng để sửa → số trên là số TRONG MẪU, KHÔNG dùng làm số đo A25. A25 chỉ tính trên bộ GIỮ RIÊNG (dự án K1a, chưa dùng để chỉnh luật).

| Dự án | đúng lỗi | báo nhầm | tỉ lệ báo nhầm |
|---|---|---|---|
| #22 | 13 | 0 | 0 % |
| #24 | 17 | 0 | 0 % |

### So sánh trước / sau sửa A26 (b)

| Dự án | món bị báo sau lọc BYĐ: trước → sau sửa | mục báo nhầm cũ (bảng 30) đã hết | mục đúng lỗi cũ còn bị báo |
|---|---|---|---|
| #22 | 26 → 13 | 8/8 | 7/7 |
| #24 | 35 → 26 | 7/7 | 8/8 |

- 15/15 mục báo nhầm cũ hết (tay áo → hands 4, câu nhóm 'both' 3, 'pure-black' / 'faceless' 3, lưng-nghiêng 3, MCU 'no legs' + vòng cổ ở WS 2); 15/15 mục đúng lỗi cũ vẫn bị báo (không che lỗi thật). Ngoài bảng hết thêm 10 mục cũ chưa gán: Kelly KL hands S8–9 + mask S7–9, áo crop #24 S3, vòng cổ #24 S9, và `dress` #22 S7–9 (đổi thành `skirt`).
- Món MỚI bị báo: #22 S7–9 `skirt` (3) — trước là `dress` cùng chỗ (đổi tên món, không tăng). Không có mục mới nào khác.
- Bảng 30 mục mới: agent gán 15 mục chưa có nhãn → **30/30 đúng lỗi, 0 báo nhầm (0 %, n = 30)**. Trên TOÀN BỘ 39 mục bị báo (gán thêm 9 mục ngoài bảng): **6 báo nhầm / 39 ≈ 15 %** — vẫn trên ngưỡng A25 (≤ 10 %), giữ `CHAN_DO = False`.
- Độ chắc 'thấp' ở mục mới: tất #22 S7–9, tay / tất dạng 1 #24 S7, áo crop #24 S9 (Kelly nhỏ), 3 mục dạng 2 #24 S9.
- Luật mức A26 (c) đã vào code: kể cả bật `CHAN_DO`, chỉ `sai_mau` (#24 S5/S6 'red sash') và món dấu hiệu khai_bao_chu lên ĐỎ.

Kiểu báo nhầm CÒN LẠI sau sửa A26 (b) (gợi ý — chưa sửa code):

- **Shot biến hình — hai dạng cùng khóa sân khấu** (4 mục, #24 S7, ngoài bảng): BYĐ chỉ có 'yeunu'; kịch bản liệt kê cả dạng 1 + dạng 2 → món dạng 2 bị đòi khi ảnh vẽ dạng 1. Gợi ý: BYĐ tách khóa từng dạng, hoặc shot 'shifting from … into …' chỉ đòi dạng đầu.
- **Bị che theo tư thế** (2 mục, #24 S9 dạng 2, ngoài bảng): quỳ ôm mặt — mặt / eo bị tay, tóc che. Lọc chưa theo tư thế (K1a).
- **Lưu ý 'đúng lỗi'**: mọi mục đúng lỗi mới (váy, tất, bộ thể thao, giày…) ảnh vẫn vẽ đúng nhờ ảnh tham chiếu — đúng A26 (c): giữ VÀNG.
