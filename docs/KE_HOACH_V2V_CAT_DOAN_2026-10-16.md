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
