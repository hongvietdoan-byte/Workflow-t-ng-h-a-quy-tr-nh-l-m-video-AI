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
