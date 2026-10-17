# Kế hoạch V2V cắt đoạn tại cú vòng máy — previs shot 6–9 #31 (16/10, chờ duyệt)

Người dùng 16/10: "Dùng ref depth, cắt đoạn gen tại các cú vòng máy; lên kế hoạch + ước tính giá trước." Chưa code, chưa gọi API.

## 1. Vì sao

Hai lượt thử 5 s (bản đánh giá `docs/DANH_GIA_CHIA_VAI_SAN_KHAU_2026-10-16.md` mục 4, tổng $2,76):
- ref clay: model theo động tác + góc sau lưng, KHÔNG theo cỡ khung lẫn đường máy;
- ref depth: model theo CỠ KHUNG + BỐ CỤC (máy sát sau vai, xe nôi đúng chỗ), vẫn KHÔNG theo cú vòng máy (previs +840 px,
  kết quả quét ngược).

→ Mỗi đoạn gen chỉ nên có máy ỔN ĐỊNH so với Kelly (đứng / bám đều); cú vòng thành điểm cắt giữa hai đoạn.

## 2. Đo cú vòng trên previs đã duyệt (20,7 s)

Góc máy quanh Kelly so với hướng chạy (180° = sau lưng), mỗi 0,5 s, từ `…_7sau_trai_plan.json`:

| Khoảng | Góc máy quanh Kelly | Khoảng cách | Nghĩa |
|---|---|---|---|
| 0,0–2,0 s | −48…+23° (trước mặt) | 0,8–1,4 m | shot 6, máy trước mặt Kelly |
| **2,0–3,6 s — V1** | 23° → 175° (~150°) | 1,3–1,7 m | máy vòng ra sau lưng (orbit 60 + chuyển giàn) |
| 3,6–13,0 s | 195–220° (dao động ±30° ở khúc rẽ) | 1,2–1,9 m | shot 7 + đầu shot 8: bám sau lưng chếch trái, Kelly chạy mê cung → khựng trước xe nôi |
| **13,0–15,4 s — V2** | 197° → 90° (~105°) | 1,2 → 0,9 m | chuyển shot 8 → 9: máy vòng từ sau lưng sang ngang hông |
| 15,4–20,7 s | 90° cố định | 0,94 m | shot 9: máy ngang hông, Kelly chạm xe nôi |

Luật: Seedance 2.5 ra 4–30 s (số nguyên); video tham chiếu ≥ 3 s, 720×1280, SAR 1:1 (đã có ở `previs_v2v_test.py`).

## 3. Chia đoạn đề xuất (ref depth, cắt cứng tại cú vòng)

| Đoạn | Previs | Ra | Máy trong đoạn | Ghi chú |
|---|---|---|---|---|
| Đ1 | 0,0–4,0 s | 4 s | trước mặt → **V1** → sau lưng | KHÔNG tránh được V1: trước V1 chỉ có 2,0 s máy ổn định (< 4 s tối thiểu) — xem câu hỏi 1 |
| Đ2 | 4,0–13,0 s | 9 s | bám sau lưng chếch trái | đoạn chính, đúng kiểu lượt depth đã đạt cỡ khung |
| Đ3 | 15,4–20,4 s | 5 s | ngang hông, đứng yên | bỏ V2 (13,0–15,4 s) → cắt cứng sau lưng → ngang hông; phim còn 18 s (mất 2,4 s) |

Ghép: 3 đoạn nối cắt cứng (ffmpeg), cùng 4 ảnh Kho (plate đêm theo shot của đoạn + Kelly 23/10 + bóng mờ 427/1 + xe nôi 442/2), cùng
khuôn prompt depth của lượt 2 (tả hướng máy riêng từng đoạn).

## 4. Ước tính giá (sổ chi `cost.seedance_estimate`, đã gồm giây video tham chiếu; ×1,25 = dự phòng trần)

| Đoạn | 480p | 720p |
|---|---|---|
| Đ1 4 s | $0,49 (0,62) | $1,11 (1,38) |
| Đ2 9 s | $1,11 (1,38) | $2,49 (3,11) |
| Đ3 5 s | $0,62 (0,77) | $1,38 (1,73) |
| **Cộng 3 đoạn** | **$2,21 (2,77)** | **$4,98 (6,22)** |
| (Đ3 giữ V2: 13,0–20,7, 8 s — thay Đ3) | $0,97 (1,21) | $2,17 (2,71) |

- Cách A — gen thẳng 720p: ≈ $4,98, trần đề xuất $6,5.
- Cách B — nháp 480p cả 3 đoạn → người dùng duyệt → 720p chỉ đoạn đạt: ≈ $2,21 + tới $4,98 (tối đa ≈ $7,2). 480p chỉ để duyệt, không
  làm bản giao (memory feedback_never_upscale_480p).

## 5. Việc code (0 USD, sau khi duyệt)

- `tools/experiments/previs_v2v_test.py`: thêm `--seg Đ1|Đ2|Đ3` (CUT + ảnh nền + câu tả máy riêng từng đoạn, tên method riêng), trần dự
  án thử #32 nâng theo cách chọn; bước `join` nối 3 đoạn (ffmpeg, cắt cứng) + ảnh ghép so previs.
- Đo mỗi đoạn như lượt 2 (ORB + affine: pan / zoom so previs depth; ảnh ghép mốc 0,5 s), ghi bản đánh giá mục 4.

## 6. Câu hỏi cần người dùng chọn

1. Đ1 chứa V1 (không có đủ 4 s máy ổn định trước V1): (a) giữ nguyên, chấp nhận model có thể không vòng; (b) sửa previs shot 6 bỏ
   orbit (máy sau lưng ngay từ đầu, render lại 0 USD) rồi mới gen; (c) bỏ Đ1, gen từ 4,0 s.
2. V2: bỏ (Đ3 15,4–20,4, phim 18 s) hay giữ (Đ3 13,0–20,7, 8 s, rủi ro như V1)?
3. Cách A (720p thẳng, ≈ $4,98) hay cách B (nháp 480p ≈ $2,21 rồi 720p đoạn đạt)?

## 7. Người dùng duyệt + kết quả nháp 480p (16–17/10)

Duyệt 16/10: (1) sửa previs shot 6 máy sau lưng; (2) bỏ V2, cắt cứng; (3) nháp 480p trước.
- Previs mới `--rig 6:sau_trai --rig 7:sau_trai` (không orbit; `…_them7s3_6sau_trai_7sau_trai_{clay,depth}.mp4`): hết V1, máy sau lưng
  ổn định 0,5–13,1 s → **0–13 s thành MỘT đoạn** (trước đây cắt ở 4 s chỉ vì V1; giá không đổi). Sửa kèm: khung 0 máy cách Kelly
  0,45 m (giàn sau lưng chưa có đường đã đi) → lùi tiếp theo hướng ngược hướng đứng, dừng trước ô rào / mép lưới; test.
- Đoạn gen: Đ1 0–13 s (13 s, ảnh nền shot 6/7/8) + Đ2 15,6–20,6 s (5 s, ảnh nền shot 9); ref depth; Seedance 2.5 480p.
  Sổ chi $1,60 + $0,62 = **$2,21** (dự án thử #32 tổng $4,98). Task `cgt-20261017004442-blw9u`, `cgt-20261017004449-55ooc`.
- **Đ1 ĐẠT bám máy**: suốt 13 s máy thấp sau lưng Kelly như previs; rào lướt qua sát máy ở 1/2/8 s trùng tường previs; xe nôi hiện
  bên trái ở 10–12 s đúng chỗ khối trụ; Kelly giữ cỡ khung. ORB: zoom +0,47, pan dọc +0,44, pan ngang −0,15 (nhân vật trong suốt làm
  nhiễu điểm đặc trưng — ảnh ghép khớp rõ hơn số).
- **Đ2 nội dung đúng, máy KHÔNG đứng yên**: Kelly bước tới, đưa tay chạm xe nôi; máy lùi ra. Gốc: khung previs shot 9 máy cách Kelly
  0,94 m, thân Kelly che kín khung, không thấy xe nôi (lỗi khung đã ghi ở bản đánh giá mục 4 "Còn thấy") → model tự lùi để thấy hành
  động. Muốn giữ máy đứng: sửa khung shot 9 trước (chạy cảnh 2 qua luồng chia vai / đặt lại máy shot 9), rồi gen lại.
- Bản giao `D:\AI-Video-Output\2026-10-15_du-an-31\previs\v2v_thu_16-10\`: `nhap480_D1_0-13s.mp4`, `nhap480_D2_15.6-20.6s.mp4`,
  `nhap480_noi_D1-D2_18s.mp4` (nối cắt cứng), ảnh ghép `so_sanh_D1/D2_previs_tren_nhap_duoi.png`.
- Bước kế (CHỜ người dùng duyệt): 720p Đ1 ≈ $3,59 (×1,25 = $4,49); Đ2 720p ≈ $1,38 — nên sửa khung shot 9 trước. Trần dự án thử #32
  hiện $6,5 (đã chi $4,98) → cần nâng khi duyệt 720p.

## 8. Lượt 2 nháp 480p (17/10 08:25, người dùng duyệt gen lại + nâng trần $9,5)

Người dùng xem lượt 1: (1) cục chỉ hướng trên đầu, (2) dáng đi bộ không chạy, (3) Đ2 sai skin + chữ lỗi lưng áo. Gốc + sửa (0 USD,
commit 7ec95453): mũi người nộm lọt vào ref → previs ẩn mũi (cả khóa biến thể); người nộm không chân → prompt tả chạy nước rút; chỉ
gửi ảnh mặt trước → thêm Kho 23/15 lưng + 23/16 hông, áo lưng trơn không chữ. Gửi lại: task `cgt-20261017091948-7oa10` (Đ1),
`cgt-20261017091956-ajh7s` (Đ2), sổ chi $2,21 (dự án thử #32 tổng $7,19). Bản giao `nhap480_r2_*` cùng thư mục.
- Nhìn sơ bộ (chờ người dùng kiểm): Đ1 máy vẫn bám sau lưng như previs, không còn cục trên đầu, có khung nhấc cao gối; 10–12 s lưng áo
  còn vệt hoa văn tối. Đ2 máy ĐỨNG YÊN (khác lượt 1) nhưng toàn cảnh xa (previs đặt sát), Kelly bước tới chạm xe nôi; tóc trông mờ.

## 9. Lượt r3 (17/10 08:56, người dùng duyệt $3,50 + trần $12; sổ chi $3,50, dự án thử #32 tổng $10,69) — DỪNG nhánh V2V tới hết tập 2

+ Kho trời 428/2 + biệt thự 265/3 + 2 clip in-game người dùng làm video ref 2–3. Task `cgt-20261017094409-4ak0q` (Đ1),
`cgt-20261017094419-v12c1` (Đ2). Bản giao `nhap480_r3_*`.
- Đ1: BIỆT THỰ hiện sau rào, trời có mây, cảnh rõ hơn hẳn; Kelly chạy sải bước + vệt sáng đỏ; máy vẫn bám sau lưng như previs.
  Lỗi: từ ~4 s dạng bóng mờ nhạt dần (Kelly gần như áo vàng đặc).
- Đ2: HỎNG — model chép clip in-game (dải la bàn HUD trên khung, máy theo clip game, Kelly không bóng mờ, xe nôi quá to). Gốc: đoạn
  ngắn 5 s trong khi 2 clip game dài 10,4 s → ref game lấn ref depth.
- Bài học (nếu làm tiếp sau tập 2): clip in-game chỉ dùng khi ngắn hơn ref depth và đã CẮT SẠCH HUD; hoặc chỉ dùng ảnh tĩnh từ clip
  (trời, biệt thự) + prompt dáng chạy. Người dùng 17/10 bật chế độ siêu nhanh → không thử trả tiền mới, không sửa code nhánh này.
- Người dùng xem r3 (17/10 09:12): "Lỗi hiện HUD, không nhất quán nhân vật trong các cảnh, việc sử dụng nhiều ref khiến cho lỗi nhiều hơn."
  → Bài học: NHIỀU ref (10 ảnh + 3 video ở Đ1) làm model trộn nguồn — lộ HUD từ clip game, Kelly đổi dạng (bóng mờ ↔ áo vàng đặc)
  giữa các đoạn. Lần sau: ít ref nhất có thể, mỗi ref một vai rõ, KHÔNG gửi clip / ảnh còn HUD; giữ cùng bộ ref nhân vật cho mọi
  đoạn để nhất quán.
