# Bảng gán nhãn báo nhầm — khóa nhận diện A18 (10/10)

Thẩm định 4 lỗ hổng #1: luật A18 "mọi món must_keep phải có chữ trong prompt" chưa đo báo nhầm. Bảng này lấy từ chạy khô #24
(prompt ảnh thật trong CSDL, BYĐ `data_out/k0b_p24/byd_shot*.json`), sinh bằng `tools/nhan_bao_nham_a18.py` — chạy lại ra đúng bảng.

**Ngưỡng nhận:** Mục 9 kế hoạch chỉ có ngưỡng cho LỚP CLAUDE: báo nhầm ≤ 10 % trước khi chặn, cỡ mẫu ≥ 50 mục trên ≥ 2 dự án. Lớp CODE A18 chưa có ngưỡng riêng → tạm dùng ≤ 10 % (thẩm định 4 đề n ≥ 30) — **chờ người dùng chốt**. Chưa đạt → `CHAN_DO = False` (thiếu chữ = VÀNG, không chặn).

## Số đo trước / sau lọc theo BYĐ (#24, 9 shot)

| | Trước lọc | Sau lọc |
|---|---|---|
| món `thieu` | 38 | 34 |
| món bị báo (thieu + thieu_mau + sai_mau) | 42 | 38 |
| shot có món bị báo | 9 | 9 |
| món `khong_can` (lọc, có lý do) | 0 | 9 |

(summary.json cũ ghi 34 món `thieu` — số "trước lọc" ở đây chạy lại cùng hàm trên CSDL hiện tại.)

## Gán nhãn (mỗi mục một chạm)

Cột cuối: ghi **đúng lỗi** (prompt thật sự thiếu / sai món đó, ảnh dễ vẽ sai) hoặc **báo nhầm** (món có trong khung đúng hoặc không
cần chữ ở shot này). Kết quả code: `thieu` = không có chữ món; `thieu_mau` = có món, thiếu màu chính; `sai_mau` = màu ngược khóa.

| # | Shot (cỡ) | Nhân vật | Món (màu khóa) | Kết quả code | Mức | Trích prompt (≤ 15 từ) | Người dùng: đúng lỗi / báo nhầm |
|---|---|---|---|---|---|---|---|
| 1 | 1 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | |
| 2 | 1 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot, Free Fire in-game 3D render style, Kelly in her yellow-white-black tracksuit with black … | |
| 3 | 2 (WS) | KELLY | hair (brown) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 4 | 2 (WS) | KELLY | choker (black) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 5 | 2 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 6 | 2 (WS) | KELLY | tracksuit (yellow) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 7 | 2 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot, high side view looking down at Kelly and the well, Free Fire in-game … | |
| 8 | 3 (MS) | KELLY | hair (brown) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | |
| 9 | 3 (MS) | KELLY | choker (black) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | |
| 10 | 3 (MS) | KELLY | crop top (white) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | |
| 11 | 3 (MS) | KELLY | tracksuit (yellow) | thieu | VÀNG | Over-the-shoulder shot from behind Kelly, dutch angle, Free Fire in-game 3D render style, Kelly in … | |
| 12 | 4 (WS) | KELLY | crop top (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | |
| 13 | 4 (WS) | KELLY | sneakers (white) | thieu | VÀNG | Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire … | |
| 14 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu_mau | VÀNG | … the near rim, a female creature whose face is a smooth featureless pure-black mask with … | |
| 15 | 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | |
| 16 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu_mau | VÀNG | … 3D render style, a female creature whose face is a smooth featureless pure-black mask with … | |
| 17 | 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | sai_mau | VÀNG | … with a jagged hem and a red sash at the waist, black arms covered in … | |
| 18 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | face (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | |
| 19 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | belt (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | |
| 20 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | hands (black) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | |
| 21 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings (black/red) | thieu | VÀNG | the faceless dark female creature standing in front of an ancient eight-sided stone well in … | |
| 22 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | face (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 23 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | hair (white) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 24 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | dress (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 25 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | belt (white/black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 26 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | hands (black) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 27 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | legs (red) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 28 | 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 2 | glitch (—) | thieu | VÀNG | (đoạn prompt của nhân vật rỗng) | |
| 29 | 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | dress (black) | thieu | VÀNG | Close-up, eye level, slow push-in, Free Fire in-game 3D render style, the comic-style black-faced creature … | |
| 30 | 9 (WS) | KELLY | hair (brown) | thieu | VÀNG | Kelly small seated on the ground on the left | |

8 mục sau mục 30 chưa đưa vào bảng (giới hạn ≤ 30).

## Món bị lọc (`khong_can`) — để người dùng xem lọc có che lỗi thật không

| Shot (cỡ) | Nhân vật | Món | Lý do |
|---|---|---|---|
| 3 (MS) | KELLY | sneakers | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'sneakers' ở 95 % — ngoài khung |
| 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| 5 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | stockings | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'stockings' ở 60 % — ngoài khung |
| 6 (MS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MS chỉ chứa 55 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| 7 (MLS) | YÊU NỮ TÀ LINH DẠNG 1 | heels | cỡ MLS chỉ chứa 75 % thân từ đỉnh đầu; 'heels' ở 95 % — ngoài khung |
| 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | belt | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'belt' ở 45 % — ngoài khung |
| 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | hands | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'hands' ở 45 % — ngoài khung |
| 8 (MCU) | YÊU NỮ TÀ LINH DẠNG 2 | legs | cỡ MCU chỉ chứa 35 % thân từ đỉnh đầu; 'legs' ở 60 % — ngoài khung |

## Chưa có
- #22: repo chưa có dữ liệu chạy khô (không có `data_out/` cho #22) — chưa đưa vào bảng; cỡ mẫu hiện < 30 / 1 dự án, chưa
  đủ mẫu số mục 9 (≥ 50 mục, ≥ 2 dự án).
- Lọc chưa chỉnh theo tư thế (ngồi / quỳ / bò đổi phần thân trong khung) và chưa thấy vật che (bàn, thành giếng) — K1a.
- Mục có trích "(đoạn prompt của nhân vật rỗng)": `segment` chia prompt theo từ đánh dấu; hai dạng yêu nữ dùng chung
  'creature' nên chữ thuộc dạng nhắc trước — 'thieu' ở dạng kia có thể là báo nhầm do tách đoạn (người dùng gán để đo).
