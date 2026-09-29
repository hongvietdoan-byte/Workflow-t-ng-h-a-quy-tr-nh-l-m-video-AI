# 15 — DramaBox: "My Dirty Secret With The Wrong Stepbrother" (kênh Brilliant Drama, quảng bá app DramaBox)

- **URL**: https://www.youtube.com/watch?v=fmvJdZkrB2k
- **Thể loại**: AI short drama 9:16 **tình cảm tuổi mới lớn / "anh kế"** (nữ chính thầm thương Derek, say rượu ngủ với "người lạ giống Derek", hôm sau mẹ báo tái
  hôn). **Tiếng Anh** + phụ đề Anh; logo DramaBox góc trên phải, dòng vàng "More episode in Comments / Due to Copyright" suốt video — mục 1b.3 trong `MAU_S0_12.md`
- **Khung hình**: **xác nhận 9:16** (file 360×640) — tồn đọng của `MAU_S0_12.md` đã đóng. Độ dài công bố 2:46:37.
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0);
  - (2) yêu cầu 38:00–40:30 — **lặp lại đoạn 1** (xem dưới), chỉ dùng để kiểm lặp;
  - (3) yêu cầu 2:38:00–2:40:30 — file 160.0s (bắt đầu sớm ~10s) — cảnh "sáng hôm sau" + gặp mẹ; mốc trong bảng là giây của file.
- **Tổng nội dung khác nhau đã đo**: ~340s / 10 000s (~3%)
- **Đã tải**: `v15_seg1/2/3.webm`, khúc quét 144p (yêu cầu 5:00–65:00, file quét chỉ 2210s → phủ 5:00–41:50) — **tất cả đã xoá**.

## Video gộp có lặp nội dung (như 10)
- Tờ quét: khung 9:00–10:30 (cổng biệt thự, váy jean xanh) trùng khung 21:30–23:00.
- Đo trực tiếp: whisper đoạn 2 cho **cùng chuỗi câu** với đoạn 1, lệch hằng số: câu giới thiệu Derek ở 36.4s (đoạn 1) ↔ 54.2s (file đoạn 2), "I'm in love" 61.9 ↔ 78.2,
  "He means me?" 69.9 ↔ 87.6 → lệch **17.7–17.8s** ổn định → nội dung ≈ 0:18–1:30 phát lại ở ≈ 38:08.
- Đoạn 3 (gần cuối video) lại là **đầu truyện** (sáng hôm sau đêm say) → [có thể] video gộp không theo thứ tự thời gian hoặc lặp nhiều vòng. "Cao trào" thật chưa tìm được.

## Phương pháp
Như 11 (`motion_cv2b.py`). `tools/audio_listen.py --lang en` đoạn 1 giây 0–90, đoạn 2 và 3 giây file 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | **100** | **1.79s** | 0.32–4.33s | **33.3** | tĩnh 57%, tịnh tiến 20%, zoom in 11%, roll 9%, thiếu dữ liệu 3% |
| Sáng hôm sau (đoạn 3, file 160s) | 76 | **1.85s** | 0.33–11.38s | 28.5 | tĩnh 74%, tịnh tiến 12%, roll 7%, zoom in 1%, thiếu dữ liệu 7% |

- Âm thanh: LUFS **−14.0** / **−13.9**, LRA **14.0** / **17.6 LU**; quãng lặng **57** / **68** (nhiều nhất trong mọi video đã đo).
- Nhịp cắt **nhanh nhất** trong 15 video (33 shot/phút); không shot nào > 4.4s trong 3 phút đầu.

### Nghe bằng số (audio_listen)
- **Nhạc 69% (đoạn 1) / 57% (đoạn 3)** — kiểu "thưa, bật tắt": giữa các câu, lớp giọng xuống −90…−100 dB và nhạc cũng tắt → 57–68 quãng lặng ngắn.
- **Đoạn 1**:
  - 0–4s (cảnh hôn — **cảnh tương lai**): nhạc −15 dB + **Explosion 0.81 ở 2s**; nhạc tắt 5–11s (lặng 4.9–11.7s), **tim đập 0.20 ở 10s**, Explosion / Bang 0.36 ở
    12s, cửa đóng 0.40 ở 14s ↔ cắt 12.7 / 15.3.
  - 14.3–57s: **giọng nội tâm** (cô gái không mở miệng) "crush… best friend… since I was 12"; nhạc rõ −19…−23 dB 24–34s; Whoosh 0.52 ở 22s.
  - Nhạc tắt 36–42s và 47–53s đúng các câu nội tâm then chốt; trống 0.26 ở 52s; nhạc về 53s.
- **Đoạn 3 (giây file)**: chuông gió 0.33 (10s) mở cảnh sáng; tim đập 0.26–0.29 ở 40 / 46s dưới câu "you shouldn't have…"; nhạc tắt hẳn 60–70s (−83…−93 dB) dưới
  "It was a mistake"; **Ding 0.60 ở 78s + Whoosh / Explosion ở 80s + nhạc −24.6 dB** ↔ **insert hồi ức nụ hôn** (#34–35, 77.6–80.5s, tông hồng / xanh neon).

## Bảng shot — đoạn 1 (0:00–3:00, 100 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–12 | 0.0–18.3 | CU cô gái ↔ MS cặp đôi hôn nhau; insert hộp quà; CU sốc | ngang | tịnh tiến×4, zoom in×2, roll×1, tĩnh×4, thiếu dữ liệu×1 | **cảnh tương lai**; Explosion 2s; lặng 4.9–11.7; tim đập 10s |
| 13–24 | 18.3–38.2 | insert rượu sâm panh phun; WS tiệc neon; **thẻ tên** Haley Burns (#20), Derek Treves (#24) | ngang | roll×3, tịnh tiến×2, tĩnh×7 | "quay về trước": giọng nội tâm |
| 25–58 | 38.2–99.6 | CU nữ ↔ CU Derek ↔ MS bạn thân (**thẻ tên** Jessica #7 xuất hiện lại); insert hộp quà | ngang | tịnh tiến×6, zoom in×6, roll×3, tĩnh×19 | Derek "tôi đang yêu"; nội tâm "anh ấy nói mình à?"; nhạc tắt 36–42, 47–53 |
| 59–69 | 99.6–155.2 | **lặp lại khung của #2–12**: cặp đôi hôn, hộp quà, CU "and my best friend?" | ngang | tịnh tiến×4, zoom in×3, roll×2, tĩnh×2 | truyện đuổi kịp cảnh mở |
| 70–100 | 155.2–180.0 | nhà vệ sinh: CU hai cô gái (vàng / nâu) ↔ | ngang | roll×2, zoom in×1, tĩnh×26, thiếu dữ liệu×1 | đối chất bạn thân |

## Bảng shot — đoạn 3 (giây file; ≈ 2:37:50 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–12 | 0.0–31.8 | insert tay nắm cửa (11.4s, roll); CU cô gái tỉnh dậy; MS chàng trai quấn khăn | ngang | roll×2, tịnh tiến×1, tĩnh×9 | chuông gió; nội tâm "ngủ với người lạ giống Derek" |
| 13–33 | 31.8–77.6 | CU ↔ CU hai người trên giường; insert tay nhặt quần áo | ngang | tịnh tiến×3, tĩnh×17, thiếu dữ liệu×1 | tim đập 40 / 46s; nhạc tắt 60–70s dưới "It was a mistake" |
| 34–35 | 77.6–80.5 | **insert hồi ức nụ hôn** (tông neon) | ngang | tĩnh, tịnh tiến | **Ding + Whoosh + nhạc trồi** |
| 36–62 | 80.5–140.8 | CU ↔ CU; insert điện thoại (#55); WS hành lang | ngang | roll×3, tịnh tiến×4, zoom in×1, tĩnh×18, thiếu dữ liệu×1 | "we're not gonna see each other ever" |
| 63–76 | 140.8–160.0 | WS nhà có sân; MS cô gái ↔ mẹ | ngang | tĩnh×10, thiếu dữ liệu×3 | mẹ "we're getting married" |

## Kỹ thuật đáng học
1. **Mở bằng cảnh tương lai 0–18s (nụ hôn của crush và bạn thân) có tiếng nổ + tim đập, rồi truyện "đuổi kịp" và phát lại đúng các khung đó ở 99.6–155.2s.**
   Ý đồ **[có thể]**: móc bằng cú sốc, rồi khi cảnh quay lại người xem đã biết điều nhân vật chưa biết. Độ tin: khá — **giống 10** (mở bằng cảnh tương lai 0–14.2s).
2. **Giọng nội tâm (voice-over) trên CU phản ứng không mở miệng** (14.3–57s đoạn 1; đoạn 3 "who is he?"). Ý đồ **[có thể]**: cho người xem vào đầu nhân vật mà không
   cần diễn thoại; [suy luận] với AI: tránh bài toán khớp môi — giọng đặt lên CU câm.
3. **Thẻ tên + quan hệ** (Jessica — "Haley's best friend", Haley Burns, Derek Treves — "the birthday boy") trong 40s đầu. Độ tin: chắc — cùng cách với 10, 12.
4. **Nhạc bật / tắt theo câu → 57–68 quãng lặng ngắn / 3 phút**; nhạc tắt dưới câu nội tâm then chốt (36–42s, 47–53s) và dưới "It was a mistake" (60–70s). Ý đồ
   **[có thể]**: làm câu thoại "nổi" lên; nhịp nói – lặng – cắt rất nhanh. Độ tin: có thể.
5. **Insert hồi ức 1–2 shot có dấu âm (Ding + Whoosh + nhạc trồi)** chen giữa cảnh hiện tại (77.6–80.5s đoạn 3). Ý đồ **[có thể]**: nhắc người xem điều nhân vật
   vừa nhớ ra, không cần thẻ "flashback". Độ tin: có thể.

## Giới hạn / câu hỏi mở
- Video gộp lặp / không theo thứ tự: chưa tìm được đoạn cao trào thật; đoạn "38:00" là bản lặp của 0:18.
- Lớp "nhạc" lẫn hiệu ứng (Fart 0.93 ở 60s là nhãn sai của AST cho một tiếng động).
- Không biết công cụ AI.

## Xoá dữ liệu
Đã xoá `v15_seg1/2/3.webm`, tờ quét, `v15_seg*_frames/`, các tờ ảnh, thư mục `v15_seg*_L*/` và log. Chỉ giữ `v15_seg{1,2,3}_result.json` và
`v15_seg1_L0 / seg2_L10 / seg3_L10_numbers.json` (không lời chép).
