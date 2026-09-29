# 12 — 刀光劍影 Knight Drama: 《剛離婚，首富老爸找上門》 (toàn tập)

- **URL**: https://www.youtube.com/watch?v=jSkLZnX5pV8
- **Thể loại**: AI short drama 9:16 hiện đại **"vả mặt" (打脸)** — chú rể mồ côi bị nhà gái đòi "phí hôn" tại tiệc cưới; người "làm vườn" hoá ra là cha tỷ phú.
  Thoại tiếng Trung + phụ đề Trung (chữ trắng giữa khung, không có phụ đề Anh) — mục 1.4 trong `MAU_S0_12.md`
- **Độ dài công bố**: 1:48:13 · file tải 360×640, 9:16
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0);
  - (2) yêu cầu 17:30–20:00 (tiệc cưới lật ngược: chú rể từ chối, bỏ đi) — file **160.0s**, bắt đầu sớm hơn yêu cầu ~10s (keyframe) → mốc gốc ≈ 17:20 + t
    **[ước tính]**; mốc trong bảng là giây của file.
- **Tổng đã đo**: ~340s / 6493s (~5%)
- **Đã tải**: `v12_seg1.webm`, `v12_seg2.webm`, khúc quét 144p 5:00–65:00 (1 khung/30s) — **tất cả đã xoá sau khi viết file này**.

## Cách chọn đoạn / kiểm lặp
Tờ quét 120 khung: tiệc cưới 5:00–20:00 → bệnh viện / văn phòng 20:30–33:00 → trung tâm thương mại 33:00–41:00 → công ty 41:00+. **Không thấy cảnh lặp**.
Thẻ "未完待续" thấy ở 44:00, 48:00, 50:30 (tập 2–4 phút). Chọn 17:30–20:00 vì khung 19:00 (CU đàn ông há hốc) + 20:00 (cô dâu hoảng) = điểm lật của tiệc cưới.

## Phương pháp
Như 11 (`motion_cv2b.py` đã sửa chiều zoom). `tools/audio_listen.py --lang zh` đoạn 1 giây 0–90, đoạn 2 giây file 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 75 | **2.07s** | 0.4–6.96s | 25.0 | tĩnh 83%, tịnh tiến 16%, zoom out 1% |
| Tiệc cưới lật ngược (file 160s) | 49 | **2.76s** | 0.43–14.13s | 18.4 | tĩnh 69%, tịnh tiến 20%, zoom in 4%, zoom out 2%, thiếu dữ liệu 4% |

- Âm thanh: LUFS **−10.3** / **−11.5** (to nhất trong 12 video đã đo), LRA **6.5** / **7.0 LU**; quãng lặng **0** / **4** (đoạn 2: 0–1.2s đầu file, 79.1–79.6,
  80.2–80.6, 111.3–112.2).
- Ranh giới tập: thẻ "未完待续" ở shot 41 (101.9–104.5s đoạn 1) và shot 40 (128.0–130.6s đoạn 2) → tập đầu ≈ 104s.

### Nghe bằng số (audio_listen)
- **Nhạc 100% (đoạn 1) / 99% (đoạn 2)**, tempo đo 103 / 92 BPM. Không có quãng lặng nào trong 3 phút đầu → "tường âm thanh" thoại + nhạc liên tục.
- **Đoạn 1**: nhạc to lên 3s (−26) dưới lời MC "mời chú rể hôn cô dâu", 11s (−20.5) khi mẹ vợ đứng dậy; **nhãn violin / bowed string 0.05–0.12 suốt 50–80s**
  dưới chuỗi câu sỉ nhục ("thằng mồ côi", "không có tiền thì đừng cưới"), to lên −20.7 dB ở 56s. Cắt sang vườn ở 86.6s đúng tiếng gọi "老爷" (85.9s).
- **Đoạn 2 (giây file)**:
  - Nhạc đều −26…−30 dB suốt màn lật (10–78s); to lên −22.9 / −13 ở 46s ↔ cắt 46.0 (cô dâu hỏi lại "anh nói gì").
  - **Nhạc tụt −54 dB ở 80s + lặng 79.1–80.6 ↔ cắt 80.2**, rồi **nhạc trồi −11.3 dB ở 84s** (tim đập 0.13) dưới shot 29 — cửa lớn sáng cháy 14.1s khi cha con bước ra.
  - Clang / Whoosh 0.14–0.18 ở 80s ↔ cắt 80.2. Lặng 111.3–112.2 ↔ cắt 112.2 sang văn phòng.

## Bảng shot — đoạn 1 (0:00–3:00, 75 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–2 | 0.0–4.5 | WS sảnh cưới đối xứng; MCU MC cầm micro | ngang | tịnh tiến×1, tĩnh×1 | "mời chú rể hôn cô dâu"; nhạc to lên 3s |
| 3–15 | 4.5–42.2 | MCU chú rể (**thẻ tên dọc** #3), mẹ vợ váy đỏ (**thẻ** #8), khách; insert nắm tay | ngang | tịnh tiến×4, tĩnh×9 | đòi "phí hôn 38 vạn 8" |
| 16–33 | 42.2–86.6 | MCU ↔ MCU 1.3–4.9s; bố vợ (**thẻ** #18), khách nữ (**thẻ** #21), cô dâu (**thẻ** #14) | ngang | tịnh tiến×2, tĩnh×16 | chuỗi sỉ nhục; violin, nhạc to lên 56s |
| 34–41 | 86.6–104.5 | WS vườn biệt thự; MCU quản gia (**thẻ** #34) ↔ người làm vườn | ngang | tịnh tiến×1, tĩnh×7 | "thiếu gia tìm thấy rồi"; **未完待续** ở #41 |
| 42–60 | 104.5–143.1 | MCU ↔ MCU quản gia / "người làm vườn" trong vườn | ngang | tịnh tiến×2, tĩnh×17 | tập 2: hé lộ người làm vườn là cha chú rể |
| 61 | 143.1–149.1 | CU người cha "đi gặp con trai ngay" (6.0s) | ngang | zoom out | — |
| 62–75 | 149.1–180.0 | MCU cô dâu / mẹ vợ / chú rể ở sảnh cưới | ngang | tịnh tiến×2, tĩnh×12 | quay lại tiệc: vẫn đòi tiền |

## Bảng shot — đoạn 2 (giây file; ≈ 17:20 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–12 | 0.0–34.2 | MCU người cha áo xanh công nhân; mẹ vợ; chú rể CU | ngang | tịnh tiến×3, zoom out×1, zoom in×1, tĩnh×7 | mẹ vợ đổi giọng "chỉ đùa thôi" |
| 13–24 | 34.2–69.1 | MCU chú rể ↔ cô dâu nài nỉ; người cha vỗ tay | ngang | tịnh tiến×1, tĩnh×11 | "miệng cô đắt quá, tôi không hôn nổi"; nhạc to lên ở cắt 46.0 |
| 25–28 | 69.1–80.2 | **WS sảnh — hai cha con đi ra**; MS cô dâu quỳ gục; insert giày | ngang; #25 cao | tĩnh×4 | "hối hận vì không thành cây ATM của nhà cô?" |
| 29 | 80.2–94.3 | **WS cửa lớn sáng cháy, bóng người đi vào ánh sáng — 14.1s** | ngang | tịnh tiến | **lặng 79.1–80.6 rồi nhạc trồi −11 dB ở 84s** |
| 30–32 | 94.3–112.2 | MS phụ nữ váy xám; cô dâu ngồi sàn (6.9 / 4.7 / 6.3s) | ngang | zoom in×1, tịnh tiến×2 | "đường là cô tự chọn" |
| 33–40 | 112.2–130.6 | văn phòng: CU bố cô dâu nghe điện thoại → ngã ra sàn; insert hộp đỏ | ngang; #37 cao | tịnh tiến×2, tĩnh×6 | "tôi bị đuổi việc?"; **未完待续** ở #40 |
| 41–49 | 130.6–160.0 | MCU mẹ vợ / cô dâu / phụ nữ váy xám | ngang | tịnh tiến×2, tĩnh×5, thiếu dữ liệu×2 | tập mới, quay lại sảnh |

## Kỹ thuật đáng học
1. **Thẻ tên dọc (tên + quan hệ) ngay lần đầu nhân vật xuất hiện** — 6 thẻ trong 90s đầu (shot 3, 8, 14, 18, 21, 34). Ý đồ **[có thể]**: bộ tám nhân vật của
   một tiệc cưới được "giới thiệu" không cần câu thoại giới thiệu. Độ tin: chắc về số đo. Cùng cách với 10 (LINDA HASTINGS, JULIAN THORNE).
2. **Cắt xen để người xem biết trước (dramatic irony)**: giữa màn sỉ nhục ở tiệc cưới, cắt sang vườn (86.6–149.1s) cho thấy "người làm vườn" là cha chú rể — người
   trong tiệc chưa biết. Ý đồ **[có thể]**: biến 1:30 sỉ nhục tiếp theo thành chờ đợi cú "vả mặt". Độ tin: có thể.
3. **Nhạc nền dày không một quãng lặng, dây kéo lên dưới chuỗi sỉ nhục** (đoạn 1: nhạc 100%, 0 quãng lặng, LUFS −10.3; violin 50–80s). Ý đồ **[có thể]**: giữ áp lực
   liên tục cho khán giả xem lướt. Độ tin: có thể.
4. **Lặng 1.5s đúng cắt, rồi shot dài 14.1s cửa sáng cháy + nhạc trồi lên −11 dB** khi nhân vật chính bỏ đi (79.1–80.6s → 84s). Ý đồ **[có thể]**: khoảnh khắc
   "thắng" được cho thở và phóng to. Độ tin: khá (đo khớp 0.1s) — cùng hình dạng với mẫu hình 5 (tắt rồi về ở cắt) và 7 (nhạc trồi ở shot mở không gian).
5. **Hậu quả ngay trong cùng tập, kết tập bằng cú ngã** (112.2–130.6s: bố cô dâu nghe tin bị đuổi việc, ngã sàn, insert hộp đỏ → 未完待续). Ý đồ **[có thể]**:
   trả "phần thưởng" cho người xem trước khi móc tập sau. Độ tin: có thể.

## Giới hạn / câu hỏi mở
- Chỉ đo ~5% thời lượng; phần giữa (bệnh viện, trung tâm thương mại, công ty) chưa đo.
- Mốc gốc đoạn 2 là ước tính (±10s).
- Không biết công cụ AI.

## Xoá dữ liệu
Đã xoá `v12_seg1.webm`, `v12_seg2.webm`, tờ quét, `v12_seg*_frames/`, các tờ ảnh `.jpg`, thư mục `v12_seg1_L0/`, `v12_seg2_L10/` và log. Chỉ giữ
`v12_seg{1,2}_result.json`, `v12_seg1_L0_numbers.json`, `v12_seg2_L10_numbers.json` (không lời chép).
