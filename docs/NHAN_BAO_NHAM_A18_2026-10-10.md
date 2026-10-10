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

| # | Dự án | Shot (cỡ) | Nhân vật | Món (màu khóa) | Kết quả code | Mức | Trích prompt (≤ 15 từ) | Agent đề xuất (lý do ≤ 20 từ, độ chắc cao/vừa/thấp) | Người dùng: đúng lỗi / báo nhầm |
|---|---|---|---|---|---|---|---|---|---|
| 1 | #22 | 4 (MCU) | MAXIM KL | hair (white/grey) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up from mid-chest up, no legs, inside … | **đúng lỗi** — MCU thấy rõ tóc, prompt không tả tóc; ảnh 527 vẫn đúng xám bạc nhờ ảnh ref (vừa) | |
| 2 | #22 | 5 (MCU) | KELLY | crop top (white) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up, Kelly (dark brown bob haircut, blunt … | **đúng lỗi** — chỉ ghi 'yellow tracksuit'; áo crop trắng thấy rõ ở ảnh 528 (vẽ đúng nhờ ref) (vừa) | |
| 3 | #22 | 6 (MCU) | KELLY KL | dress (black) | thieu | VÀNG | Free Fire in-game 3D render, stylized proportions, medium close-up from mid-chest up, no legs, inside … | **báo nhầm** — MCU 'mid-chest up, no legs': váy ngắn ở hông ngoài khung thiết kế; 'váy' bị ghép thành dress (vừa) | |
| 4 | #22 | 7 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **đúng lỗi** — prompt không gọi tên/tả Maxim; WS thấy tóc; ảnh 556 đúng nhờ ref (vừa) | |
| 5 | #22 | 8 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **đúng lỗi** — prompt không gọi tên/tả Maxim; WS thấy tóc; ảnh 557 đúng nhờ ref (vừa) | |
| 6 | #22 | 9 (WS) | MAXIM KL | hair (white/grey) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **đúng lỗi** — prompt không gọi tên/tả Maxim; WS thấy tóc; ảnh 558 đúng nhờ ref (vừa) | |
| 7 | #22 | 7 (WS) | MAXIM KL | hands (black/red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **báo nhầm** — 'tay áo đen' (ống tay) bị đọc thành hands; prompt có nói 'red dinosaur outfits' (cao) | |
| 8 | #22 | 8 (WS) | MAXIM KL | hands (black/red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **báo nhầm** — 'tay áo đen' (ống tay) bị đọc thành hands (cao) | |
| 9 | #22 | 9 (WS) | MAXIM KL | hands (black/red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **báo nhầm** — 'tay áo đen' (ống tay) bị đọc thành hands (cao) | |
| 10 | #22 | 7 (WS) | MAXIM KL | mask (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **báo nhầm** — prompt có 'both with the black shark-tooth mask worn UP' — nói chung cho hai người (cao) | |
| 11 | #22 | 8 (WS) | MAXIM KL | mask (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **báo nhầm** — prompt có 'both with the black shark-tooth mask' — code không gán được vì không gọi tên (cao) | |
| 12 | #22 | 9 (WS) | MAXIM KL | mask (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **báo nhầm** — prompt có 'both with the black shark-tooth mask' — code không gán được vì không gọi tên (cao) | |
| 13 | #22 | 7 (WS) | KELLY KL | hands (black/red) | thieu | VÀNG | not a realistic shooter game KELLY KL keeps Kelly's OWN hair from her reference picture: … | **báo nhầm** — 'tay áo sọc đen' (ống tay) bị đọc thành hands (cao) | |
| 14 | #22 | 8 (WS) | KELLY KL | hair (brown) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **đúng lỗi** — S7 có câu khóa tóc Kelly, S8 mất; ảnh mẫu 417 tóc trắng-đỏ dễ lẫn (ảnh 557 vẫn đúng) (cao) | |
| 15 | #22 | 9 (WS) | KELLY KL | hair (brown) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | **đúng lỗi** — S7 có câu khóa tóc Kelly, S9 mất; ảnh mẫu 417 tóc trắng-đỏ dễ lẫn (ảnh 558 vẫn đúng) (cao) | |
| 16 | #24 | 1 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | **báo nhầm** — có 'yellow-white-black tracksuit'; ảnh 623 Kelly quay lưng đi về giếng, áo crop không thấy (thấp) | |
| 17 | #24 | 2 (WS) | KELLY | hair (brown) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | **đúng lỗi** — S1/S4 có 'short dark bob', S2 không; WS nghiêng thấy tóc (ảnh 632 đúng nhờ ref) (vừa) | |
| 18 | #24 | 3 (MS) | KELLY | hair (brown) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | **đúng lỗi** — qua vai sau lưng: tóc chiếm lớn khung, prompt không tả (ảnh 634 đúng nhờ ref) (vừa) | |
| 19 | #24 | 4 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | **báo nhầm** — prompt 'seen from behind'; ảnh 639 lưng, áo crop không thấy (cao) | |
| 20 | #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu_mau | VÀNG | … the near rim, a female creature whose face is a smooth featureless pure-black mask with … | **báo nhầm** — có 'face is a smooth featureless pure-black mask' — màu viết 'pure-black' code không nhận (cao) | |
| 21 | #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu_mau | VÀNG | … 3D render style, a female creature whose face is a smooth featureless pure-black mask with … | **báo nhầm** — có 'face is a smooth featureless pure-black mask' — màu viết 'pure-black' code không nhận (cao) | |
| 22 | #24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | **báo nhầm** — tả gián tiếp 'faceless dark female creature'; ảnh 629 mặt đen đúng (vừa) | |
| 23 | #24 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | dress (black) | thieu | VÀNG | Close-up, eye level, slow push-in, Free Fire in-game 3D render style, the comic-style black-faced creature … | **đúng lỗi** — quỳ ôm mặt, váy đen chiếm nửa khung (ảnh 640), prompt không tả váy (vừa) | |
| 24 | #24 | 9 (WS) | KELLY | hair (brown) | thieu | VÀNG | Kelly small seated on the ground on the left | **đúng lỗi** — WS Kelly nhỏ nhưng tóc vẫn đọc được; prompt không tả (ảnh 633 đúng) (thấp) | |
| 25 | #24 | 1 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | **đúng lỗi** — WS toàn thân, giày thấy rõ (ảnh 623), prompt không nói giày trắng (vừa) | |
| 26 | #24 | 2 (WS) | KELLY | choker (black) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | **báo nhầm** — WS cao nhìn xuống, vòng cổ chỉ vài điểm ảnh — món nhỏ không cần chữ ở cỡ này (thấp) | |
| 27 | #24 | 3 (MS) | KELLY | choker (black) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | **báo nhầm** — máy sau lưng Kelly: cổ bị tóc che, vòng cổ không thấy (ảnh 634) (cao) | |
| 28 | #24 | 4 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | **đúng lỗi** — ngã ngồi, chân duỗi về giếng — giày thấy rõ (ảnh 639), prompt không nói (vừa) | |
| 29 | #24 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | **đúng lỗi** — prompt 'red sash' ngược Kho (đai gai đen khóa tam giác đỏ); ảnh 636 vẽ khăn đỏ — SAI (cao) | |
| 30 | #24 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | **đúng lỗi** — prompt 'red sash' ngược Kho; ảnh 637 lần này đúng nhờ ref, lần S5 đã sai (vừa) | |

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

## Agent đề xuất (10/10)

Agent gán 30/30 mục (nhãn ĐỀ XUẤT, người dùng duyệt cột cuối): **đúng lỗi 15 / báo nhầm 15** → tỉ lệ báo nhầm ước **50 %** (n = 30; ngưỡng A25 ≤ 10 %). Độ chắc thấp: 3 mục.

| Dự án | đúng lỗi | báo nhầm | tỉ lệ báo nhầm |
|---|---|---|---|
| #22 | 7 | 8 | 53 % |
| #24 | 8 | 7 | 47 % |

Kiểu báo nhầm lặp lại (gợi ý sửa luật A18 — CHƯA sửa code A18):

- **Ghép món sai từ mô tả Kho tiếng Việt** (4/15): 'tay áo đen' / 'tay áo sọc đen' (ống tay áo) bị đọc thành `hands`. Gợi ý: 'tay áo' → sleeves (không phải hands).
- **Câu tả chung cho nhóm không gán được cho nhân vật** (3/15): 'both with the black shark-tooth mask' khi prompt không gọi tên ai → đoạn nhân vật rỗng → mọi món 'thiếu'. Gợi ý: câu có 'both / two characters / each' tính cho mọi nhân vật trong khung; prompt không gọi tên nhân vật nào nên là MỘT lỗi riêng ('không gọi tên'), không phải N món thiếu.
- **Màu / món tả gián tiếp** (3/15): 'pure-black' (từ ghép gạch nối) không ra màu black; 'faceless dark …' không ra face/black. Gợi ý: tách từ ghép gạch nối khi tìm màu; nhận 'faceless' như món face, 'dark' gần nghĩa black.
- **Món không thấy do hướng máy / vật che** (3/15): áo crop khi quay lưng (S1, S4), vòng cổ khi máy sau lưng (S3). Gợi ý: BYĐ 'lung' → bỏ món chỉ thấy phía trước (crop top, choker, mặt trước áo); prompt 'from behind' cũng nên tính là lưng.
- **Cỡ cảnh / món nhỏ** (2/15): MCU 'no legs' vẫn đòi váy ('váy da đen ngắn' ghép thành `dress` nên vị trí món tính như áo, không lọc theo cỡ); vòng cổ ở WS nhìn cao. Gợi ý: tách skirt khỏi dress (vị trí hông); món phụ kiện nhỏ (choker…) chỉ bắt buộc từ MS trở vào.
- **Lưu ý về 'đúng lỗi'**: 14/15 mục đúng lỗi có ảnh vẽ ra VẪN ĐÚNG nhờ ảnh tham chiếu; chỉ #29 (#24 S5 đai) có bằng chứng ảnh sai. Prompt thiếu chữ là rủi ro thật nhưng mức hại thấp khi ảnh ref có món → hợp lý giữ VÀNG (`CHAN_DO = False`); riêng `sai_mau` (chữ ngược Kho) đã gây ảnh sai → đáng nâng mức trước.
