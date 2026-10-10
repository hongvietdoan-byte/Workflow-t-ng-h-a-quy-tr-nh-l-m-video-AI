# Bảng gán nhãn báo nhầm — khóa nhận diện A18 (10/10)

Thẩm định 4 lỗ hổng #1 + thẩm định 5 #4/#5: luật A18 "mọi món must_keep phải có chữ trong prompt" chưa đo báo nhầm. Bảng này lấy
từ chạy khô #22 + #24 (prompt ảnh thật trong CSDL, BYĐ `data_out/k0b_p<id>/byd_shot*.json`), sinh bằng `tools/nhan_bao_nham_a18.py` — chạy lại ra đúng bảng.

**Ngưỡng nhận:** Mục 9 kế hoạch chỉ có ngưỡng cho LỚP CLAUDE: báo nhầm ≤ 10 % trước khi chặn, cỡ mẫu ≥ 50 mục trên ≥ 2 dự án. Lớp CODE A18 có ngưỡng riêng — **người dùng chốt 10/10 (A25): báo nhầm ≤ 10 % trên n ≥ 30 mục, lấy từ ≥ 2 dự án (#22 + #24)**. Chưa đạt → `CHAN_DO = False` (thiếu chữ = VÀNG, không chặn).

## Số đo trước / sau lọc theo BYĐ (từng dự án)

| Dự án (số shot) | món `thieu` trước → sau | món bị báo (thieu + thieu_mau + sai_mau) trước → sau | thieu_mau / sai_mau sau | shot có món bị báo trước → sau | món `khong_can` sau |
|---|---|---|---|---|---|
| #22 (9) | 31 → 26 | 32 → 26 | 0 / 0 | 8 → 6 | 6 |
| #24 (9) | 35 → 31 | 39 → 35 | 2 / 2 | 9 → 9 | 9 |

(Đối chiếu: summary.json của chạy khô — đã lọc theo BYĐ — ghi số `thieu`: #22 = 26, #24 = 31; khác cột "sau" nghĩa là CSDL đổi sau lần chạy khô.)

## Gán nhãn (mỗi mục một chạm)

Cột cuối: ghi **đúng lỗi** (prompt thật sự thiếu / sai món đó, ảnh dễ vẽ sai) hoặc **báo nhầm** (món có trong khung đúng hoặc không
cần chữ ở shot này). Kết quả code: `thieu` = không có chữ món; `thieu_mau` = có món, thiếu màu chính; `sai_mau` = màu ngược khóa.
Chọn mục: chia đều giữa các dự án, trong một dự án xoay vòng theo shot. Mục đã chọn mỗi dự án: #22 = 15/26, #24 = 15/35 (tổng 30).

| # | Dự án | Shot (cỡ) | Nhân vật | Món (màu khóa) | Kết quả code | Mức | Trích prompt (≤ 15 từ) | Người dùng: đúng lỗi / báo nhầm |
|---|---|---|---|---|---|---|---|---|
| 1 | #22 | 4 (MCU) | MAXIM KL | hair (white/grey) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up from mid-chest up, no legs, inside … | |
| 2 | #22 | 5 (MCU) | KELLY | crop top (white) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up, Kelly (dark brown bob haircut, blunt … | |
| 3 | #22 | 6 (MCU) | KELLY KL | dress (black) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up from mid-chest up, no legs, inside … | |
| 4 | #22 | 7 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 5 | #22 | 8 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 6 | #22 | 9 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 7 | #22 | 7 (WS) | MAXIM KL | hands (black/red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 8 | #22 | 8 (WS) | MAXIM KL | hands (black/red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 9 | #22 | 9 (WS) | MAXIM KL | hands (black/red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 10 | #22 | 7 (WS) | MAXIM KL | mask (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 11 | #22 | 8 (WS) | MAXIM KL | mask (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 12 | #22 | 9 (WS) | MAXIM KL | mask (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 13 | #22 | 7 (WS) | KELLY KL | hands (black/red) | thieu | VÀNG | not a realistic shooter game KELLY KL keeps Kelly's OWN hair from her reference picture: … | |
| 14 | #22 | 8 (WS) | KELLY KL | hair (brown) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 15 | #22 | 9 (WS) | KELLY KL | hair (brown) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 16 | #24 | 1 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | |
| 17 | #24 | 2 (WS) | KELLY | hair (brown) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 18 | #24 | 3 (MS) | KELLY | hair (brown) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | |
| 19 | #24 | 4 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | |
| 20 | #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu_mau | VÀNG | … the near rim, a female creature whose face is a smooth featureless pure-black mask with … | |
| 21 | #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu_mau | VÀNG | … 3D render style, a female creature whose face is a smooth featureless pure-black mask with … | |
| 22 | #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | |
| 23 | #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | dress (black) | thieu | VÀNG | Close-up, eye level, slow push-in, Free Fire in-game 3D render style, the comic-style black-faced creature … | |
| 24 | #24 | 9 (WS) | KELLY | hair (brown) | thieu | VÀNG | Kelly small seated on the ground on the left | |
| 25 | #24 | 1 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | |
| 26 | #24 | 2 (WS) | KELLY | choker (black) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 27 | #24 | 3 (MS) | KELLY | choker (black) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | |
| 28 | #24 | 4 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | |
| 29 | #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | |
| 30 | #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | |

31 mục bị báo khác chưa đưa vào bảng (giới hạn 30).

## Món bị lọc (`khong_can`) — để người dùng xem lọc có che lỗi thật không

| Dự án | Shot (cỡ) | Nhân vật | Món | Lý do |
|---|---|---|---|---|
| #22 | 1 (MS) | MAXIM | sneakers | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #22 | 3 (MCU) | MAXIM | sneakers | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #22 | 4 (MCU) | MAXIM KL | hands | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'hands' ở 45 % — ngoài khung |
| #22 | 5 (MCU) | KELLY | sneakers | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #22 | 6 (MCU) | KELLY KL | hands | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'hands' ở 45 % — ngoài khung |
| #22 | 6 (MCU) | KELLY KL | stockings | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| #24 | 3 (MS) | KELLY | sneakers | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MLS chỉ chứa 75 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | belt | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'belt' ở 45 % — ngoài khung |
| #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | hands | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'hands' ở 45 % — ngoài khung |
| #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | legs | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'legs' ở 60 % — ngoài khung |

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
