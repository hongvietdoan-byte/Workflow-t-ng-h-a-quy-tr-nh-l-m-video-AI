# A/B hành động S4.6 — kết quả chạy thật 2026-09-29

Dự án thử **#10** ("A/B hành động S4.6 · Chia đôi"), 3 shot của kịch bản K bản A × 3 cách, mỗi clip 4 s, 720×1280, 24 fps.
Người dùng nâng trần 43,10 → **49,10 USD**, ảnh 135 → **141**. Chi thật: khung Deepix **0,26 USD / 5 ảnh** (ước tính 0,16 / 3 ảnh — shot 2
bị gửi lại trong lúc vẽ, chưa rõ vì sao) + 9 clip **5,16 USD** = **5,42 USD**. Sau lượt: đã chi 48,27 / 49,10, ảnh 137 / 141.

Clip + tờ khung (ngoài git): `D:\AI-Video-Output\2026-09-29_ab-hanh-dong-s4-6\` (`shotN_<cách>.mp4`, `ab_shotN.jpg` = 3 hàng P2m / P2m25 / S2 × 6
khung trên 4 s, `frames10.jpg` = 3 khung đầu, `s1p2m_face.jpg` = lỗi dấu đỏ).

## Lưu ý về cách gửi (sửa lại bàn giao)
Bàn giao ghi P2m/P2m25 là "ref-only", nhưng `tools/experiments/group_test.py` `build()` gửi **ảnh storyboard của shot là Image 1**
("Shot starts with exactly this composition") + ảnh nhân vật đã đánh dấu. Vậy cả 3 cách đều bám khung đầu → lỗi khung đầu (xem dưới) ảnh
hưởng cả 3 cách, không riêng Kling.

## Lỗi ở khung đầu (Deepix, trước video)
- Shot 1 (chỉ có KELLY) và shot 2 (chỉ có KENTA): **cả 3 nhân vật** trong hình — ảnh nhân vật của dự án bị kéo vào dù shot chỉ ghi 1 người.
- Shot 3: Maxim ngồi **trước** tường gloo, không nấp sau; tường không có vệt chém.

## Số đo chuyển động (trung bình |Δ| điểm ảnh giữa 2 khung liên tiếp, 180×320 xám; "đầu→cuối" = khác khung đầu và cuối)
| Shot | P2m (Seedance 2.0 Fast) | P2m25 (Seedance 2.5) | S2 (Kling 3.0 Omni, khung đầu) |
|---|---|---|---|
| 1 chạy | 3,89 · đầu→cuối 33,5 | 3,49 · 20,1 | **9,73 · 53,5** |
| 2 chém kỹ năng | 0,52 · 2,7 | 0,26 · 1,7 | 1,87 · 14,9 |
| 3 phản ứng | 0,40 · 4,8 | 1,08 · 25,2 | 1,98 · 15,3 |

## Chấm bằng mắt (tờ khung 1,5–6 khung/giây; chưa nghe tiếng)
| Tiêu chí | P2m (Fast) | P2m25 (2.5) | S2 (Kling) |
|---|---|---|---|
| Chuyển động tự nhiên | Shot 1 chạy được; shot 2–3 gần đứng yên | Shot 1 chạy tại chỗ (máy theo); shot 2 **đứng yên**; shot 3 máy đẩy vào (shot ghi static) | **Tốt nhất shot 1** (máy theo, chạy thật); shot 2 chỉ máy trôi nhẹ; shot 3 Maxim co người |
| Chân chạm đất | Được | Được, bóng khớp chân | Được, bóng khớp chân, nhịp chạy đúng |
| Kỹ năng Kenta (vòng gió dưới chân, vệt gió bay tới tường, vệt chém đỏ trên tường) | **Không có** | **Không có** | **Không có** — cả 3 cách chỉ giữ tay giơ kiếm năng lượng |
| Giữ nhân vật | **LỖI NẶNG: dấu chữ thập đỏ (dấu đánh dấu ảnh tham chiếu P2m) hiện trên mặt Kelly suốt clip** | Giữ tốt; shot 1 tự bỏ 2 nhân vật thừa | Giữ khá; shot 3 cái bánh bao nhỏ dần (đạo cụ trôi) |
| Làm đúng hành động kịch bản | Shot 1 không phanh trước tường | Shot 1 không tới tường | Shot 1 chạy ra khỏi tường thay vì phanh trước tường |

## Kết luận (từ 1 lượt, 3 shot — là bằng chứng, chưa phải luật)
1. **Dấu đỏ đánh dấu ảnh tham chiếu bị Seedance 2.0 Fast vẽ vào video** (trước đây ở #8 chưa thấy — lần này ảnh Kelly là ảnh tham chiếu duy
   nhất cùng khung đầu có mặt nhỏ). Phải có kiểm bằng code: soi khung video tìm mảng đỏ bão hòa trùng vùng mặt → QC lớp 0 báo lỗi. P2m25 không bị.
2. **Hiệu ứng kỹ năng không model nào tạo ra** chỉ từ prompt chữ + 1 khung đầu. Hướng sửa để thử: khung đầu **đã có** hiệu ứng (vẽ vòng gió
   trong ảnh storyboard) + khung cuối có vệt chém trên tường (Kling đầu–cuối), hoặc ghép hiệu ứng ở khâu dựng. Chưa thử (tốn tiền).
3. **Chạy / di chuyển lớn: Kling khung đầu tốt nhất và rẻ nhất (0,32 USD / 4 s)**. Seedance 2.5 (0,92) không hơn Fast về chuyển động trong
   lượt này; hơn ở chỗ giữ nhân vật sạch.
4. Shot có động tác nhỏ (chém, co người): cả 3 gần đứng yên → prompt hành động cần ghi động tác theo nhịp giây (Seedance 2.5 đọc mốc giây theo
   tài liệu ClipAI — chưa dùng trong lượt này).
5. Khung đầu thừa nhân vật là lỗi của khâu vẽ khung (Deepix nhận ảnh cả 4 tài sản của dự án), cần sửa trước lần chạy K.

## Việc tiếp (chờ người dùng quyết — đều cần tiền nếu thử lại)
- Có tắt dấu đỏ cho Seedance Fast (dùng khung chữ "CHARACTER SHEET" không dấu trên mắt) hay chuyển hẳn sang 2.5 / Kling?
- Có thử lại shot 2 với khung đầu có sẵn hiệu ứng + Kling đầu–cuối (~0,05 ảnh + 0,32 clip) không? Trần còn 0,83 USD, 4 ảnh.

---

# Vòng 2 (29/09 chiều) — thu gọn theo người dùng: mỗi câu hỏi một phép thử

Trần 49,10 → **53,10 USD**, ảnh 141 → **147**. Chi thật **3,46 USD** (10 ảnh ≈ 0,52 — 5 khung + 1 toàn cảnh + 2 QC vẽ lại ở cảnh 2, 1 khung +
1 bị hủy ở cảnh 3; 4 clip 2,94; 2 lần bị từ chối lúc tạo = 0) + 3 câu TTS. Sau vòng: 51,73 / 53,10 USD, ảnh 147 / 147.
Công cụ `tools/experiments/s46_round2.py`. Clip + tờ khung: `D:\AI-Video-Output\2026-09-29_ab-hanh-dong-s4-6\vong2\`
(clip khớp môi đã ghép track giọng: `khop-moi_*_co-giong.mp4`, `khop-moi_so-sanh_trai-ingame_phai-ta-thuc.mp4`).

## Sửa miễn phí trước vòng 2 (có bằng chứng chạy thật)
- **Khung 1 người không còn vẽ cả 3 người**: storyboard ghi "(in frame: KELLY)" cho từng khung + câu "Only KELLY is in this frame; KENTA, MAXIM
  are NOT…" (`core/scene_storyboard.cast_note`). Cảnh 2 (5 khung, cả cảnh có 3 người): **5/5 khung đúng người** (vòng 1: 2/3 khung sai).
- **QC clip lớp 0 bắt dấu đỏ lọt vào clip** (`clip_measure.ref_mark`): clip lỗi vòng 1 17/17 khung; 0 báo trên 158 clip khác của #8/#10
  (áo đỏ của Maxim bị loại nhờ điều kiện vuông + tay chữ thập mỏng). 2 clip khớp môi vòng 2 (Seedance 2.5, dấu trên mắt): 0/21.
- Bước vẽ khung của công cụ thử dừng kèm lý do khi trần ảnh chặn lần vẽ lại (trước: treo im lặng).

## 1 · Dấu đánh dấu ảnh tham chiếu với Seedance 2.0 Fast
| Kiểu dấu | Kết quả |
|---|---|
| Chỉ băng chữ (M_banner) | **Bị từ chối lúc tạo**: `InputImageSensitiveContentDetected.PrivacyInformation` — ảnh 1 (khung storyboard) "may contain real person"; 0 USD |
| Băng chữ + dấu đỏ ở góc (M_corner) | **Bị từ chối** như trên; 0 USD |
| Dấu đỏ trên mắt (vòng 1) | Qua bộ lọc, nhưng Fast **vẽ dấu vào clip** (1/3 clip vòng 1) |

→ Với Fast, dấu phải **nằm trên mặt** mới qua bộ lọc; đổi lại có rủi ro dấu lọt vào clip. Cách dùng: (1) ưu tiên Seedance 2.5 / Kling cho shot
có mặt nhân vật in-game; (2) nếu dùng Fast thì QC lớp 0 `ref_mark` bắt và gen lại (đã có); (3) hướng lâu dài S4.7 kho chủ thể (bỏ mẹo dấu).

## 2 · Hiệu ứng kỹ năng Kenta — vẽ sẵn vào khung đầu + khung cuối, Kling 3.0 Omni std (0,32 USD / 4 s mỗi clip)
- **Vòng gió + chém** (khung đầu: vòng gió dưới chân + tay giơ lưỡi năng lượng; khung cuối: tay vung hết, vệt gió bay tới tường): vòng gió
  **giữ được** nửa đầu clip, lưỡi năng lượng vung có vệt sáng, có luồng gió bung ra giữa clip — **tốt hơn hẳn vòng 1** (không có gì). Lỗi:
  khung cuối vẽ gần hơn → máy tự đẩy vào giữa clip; cuối clip Kenta như cầm thêm katana đã rút (kỹ năng thật: katana nằm yên trong vỏ);
  vệt gió tới tường còn mờ.
- **Vệt chém đỏ trên tường** (khung đầu tường trơn, khung cuối có vệt chém — Deepix vẽ khung cuối **ngược chiều**, đã lật ngang cho khớp):
  vệt đỏ chéo **hiện ra ~2 s**, tường đứng nguyên, Maxim giật mình. Lỗi: lóe sáng + nền trôi giữa clip.
→ **Hiệu ứng kỹ năng: vẽ vào ảnh khung (đầu + cuối), model video nội suy.** Điều kiện: hai khung cùng cỡ cảnh, cùng chiều; ghi rõ "katana stays
sheathed" trong cả prompt video. Chưa thử: ghép hiệu ứng ở khâu dựng.

## 3 · Khớp môi phương án (c) — một clip cả đoạn thoại (3 câu, 3 người nói, 5 s), Seedance 2.5, track giọng + câu & mốc giây trong prompt
Track: MAXIM 0,3–1,7 s · KENTA 2,1–2,8 s · KELLY 3,2–3,9 s. Soi 5 khung/giây vùng mặt:
| | In-game | Tả thực 3D |
|---|---|---|
| Đúng người mở miệng đúng lượt | Có: Maxim 0,2–1,6 s, Kenta 2,0–2,4 s, Kelly ~3,0–3,4 s; người không nói ngậm miệng | Có, cùng thứ tự; Kelly **đứng thẳng dậy** trước câu của mình (tự thêm động tác), nói ~3,2–4,0 s (hơi trễ) |
| Giữ nhân vật / bố cục | Giữ đúng khung storyboard, 3 người ở yên chỗ | Máy quay lệch, Kelly ra khỏi tư thế chống gối |
| Hình | gần giống nhau — cả hai đều theo ảnh khung (3D khá thật); bản "tả thực" không thật hơn rõ rệt | |
| Clip có tiếng? | Không (generate_audio tắt — giọng ghép ở khâu dựng, đúng thiết kế) | Không |
→ **(c) cho đúng lượt người nói** — điều pipeline từng khớp môi từng shot (#8) không làm được với 2+ người trong khung. Khớp từng âm tiết:
cần nghe / xem kèm tiếng (file `_co-giong`) và đo bằng mốc môi (S4.5, đang giao agent khác). In-game giữ bố cục tốt hơn tả thực ở lượt này.
Chưa so trực tiếp với (a) trong vòng này (mốc so = 4 shot khớp môi #8).

## Việc tiếp theo đề xuất (chờ người dùng)
- S4.2: dùng (c) cho đoạn thoại có ≥ 2 người trong khung (in-game) — sau khi người dùng xem file `_co-giong` xác nhận khớp.
- Hiệu ứng kỹ năng trong K: vẽ khung đầu + cuối có hiệu ứng, Kling; thêm câu "katana stays sheathed" vào prompt video của Kenta.
