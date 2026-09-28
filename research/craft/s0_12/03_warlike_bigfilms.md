# 03 — WARLIKE (BIGFILMS)

- **URL**: https://www.youtube.com/watch?v=SLStk36wLZc
- **Thể loại**: phim hành động ngắn, live-action — nữ diễn viên/đạo diễn võ thuật Aurélia Agel (theo `MAU_S0_12.md`)
- **Độ dài**: 4:00 (240.9s) · khung 1280×720 (16:9)
- **Đoạn đã đo**: **TOÀN BỘ phim (240.9s, ≤4 phút nên tải và đo hết, không cần chia đoạn)**
- **Đã tải**: `v03_full_SLStk36wLZc.webm` (19.3 MB) — **đã xoá cùng frame/sheet sau khi viết xong file này**.

## Phương pháp
Giống video 01/02 (v2 — tải bằng yt-dlp, đo cắt bằng ffmpeg `scene>0.28`, tờ ảnh 30 shot/tờ đọc trực tiếp, âm thanh `ebur128`+`silencedetect`+RMS). 67 shot trên toàn phim, 3 tờ ảnh.

## Tóm tắt truyện (đọc từ tờ ảnh, không có phụ đề/thoại rõ để trích)
Mở đầu tối, chữ "WARLIKE" (#1-2) → nhóm đặc vụ/lính đánh thuê đột nhập một căn hộ sang trọng nhiều cửa sổ lớn (#3-13, có màn hình giám sát/hack), phát hiện một con tin bị trói trên sàn (#13) → nữ chính (tóc buộc đuôi ngựa) xuất hiện (#14) và **chiến đấu tay đôi + súng với nhiều đối thủ liên tiếp** xuyên suốt căn hộ (#15-60, ~140s) — đấm đá, vật lộn, dùng súng cận chiến, một số shot qua ống ngắm súng trường (#45, #52) → nữ chính bị thương (máu trên mặt, #63) → cảnh trên mái nhà/tháp có bóng người cầm súng bắn tỉa (#61) → kết bằng nữ chính dựa tường, thở dốc, đầy máu (#62-64) → toàn cảnh nhiều người nằm trên sàn (kết cục trận đánh, #65) → credit cuối (#66-67: "Story/Screenwriter — Fight choreographer: Jérôme Gaspard", logo Actual Cinema, BIGFILMS).

## Số đo
| Chỉ số | Toàn phim | Đoạn chiến đấu (22–183s, 161s) | Đoạn mở đầu+kết (còn lại, ~80s) |
|---|---|---|---|
| Số shot | 67 | 55 | 12 |
| Độ dài trung vị | 2.0s | **1.84s** | **4.72s** |
| Min–Max | 0.44–21.9s | — | — |

- **Nhịp cắt trong đoạn chiến đấu (~33 shot/phút, median 1.84s) gần bằng nhịp cắt của video 01 (AI short drama, ~30-36 shot/phút)** — dù hai thể loại hoàn toàn khác nhau (hành động live-action vs drama thoại AI), khi vào đoạn "nhiều thông tin/nhiều chuyển động" cả hai đều hội tụ về nhịp cắt nhanh tương tự. **Độ tin: có thể** — đây là quan sát chéo giữa 2/3 video đã xem, đáng ghi vào `TONG_HOP.md`.
- **Đoạn mở đầu + kết chậm hơn hẳn (median 4.72s, gấp 2.5× đoạn đánh nhau)** — khớp nguyên tắc dựng phim cổ điển "nhịp cắt phản ánh mức độ hành động", đã thấy tương tự ở video 02 (đoạn cao trào cắt nhanh, đoạn tĩnh lặng cắt cực chậm).
- Shot dài nhất (#55, 21.9s, 143.5–165.4s) — cảnh chiến đấu kéo dài không cắt, có thể là một pha võ thuật dài quay 1 lần (long take) giữa cao trào.

### Âm thanh
- LUFS tích hợp **−14.4 LUFS**, LRA **10.1 LU**, đỉnh thật **1.8 dBFS** (vượt 0dBFS — dấu hiệu tương tự video 02 đoạn cao trào, có thể là đặc điểm chung của các đoạn nhạc/hiệu ứng hành động cường độ cao, không riêng 1 phim — **độ tin: có thể**, 2/3 video đã thấy).
- **Chỉ 1 quãng lặng duy nhất trong cả phim** (ở giây 237.8–240.8, đúng đoạn credit cuối) — nhạc/hiệu ứng chạy liên tục từ đầu đến cuối, không tắt lúc nào — khác hẳn video 01 (46+33 quãng lặng ngắn) và giống hướng của video 02 (rất ít quãng lặng). **Độ tin: có thể → xu hướng** — phim tự sự có hình ảnh/hành động chủ đạo (video 02, 03) giữ âm thanh liên tục; phim thoại nhiều (video 01) mới có nhạc ngắt theo câu — đây là quan sát chéo 3/3 video, đủ điều kiện ghi vào `TONG_HOP.md` như một mẫu hình bước đầu.

## Kỹ thuật đáng học
1. **Nhịp cắt hội tụ ở đoạn "nhiều chuyển động"** (~1.8-2.0s dù thể loại khác hẳn video 01) nhưng **nhịp cắt phân kỳ mạnh ở đoạn "ít chuyển động"** (video 03 mở đầu/kết 4.7s vs video 01 gần như không đổi suốt phim ~1.5-2.0s) — gợi ý: phim hành động/tự sự đổi nhịp theo kịch tính, còn AI short drama thoại-liên-tục giữ nhịp gần như hằng số bất kể nội dung. Độ tin: có thể, cần thêm mẫu.
2. **Âm thanh liên tục không ngắt trong toàn bộ đoạn có hình ảnh chính** (chỉ ngắt ở credit) — kỹ thuật chung của phim hành động/tự sự hình ảnh chủ đạo, khác kiểu ngắt/bật theo câu thoại của drama đối thoại nhiều.
3. **Long take giữa cao trào** (shot #55, 21.9s không cắt) xen giữa các shot rất ngắn — kỹ thuật đối lập nhịp: dùng 1 shot dài để "thở" giữa chuỗi cắt nhanh, tạo điểm nhấn cho một pha võ thuật đặc biệt liền mạch. Độ tin: có thể.
4. **Đỉnh âm vượt 0dBFS (1.8 dBFS)** — cùng hiện tượng với video 02 đoạn cao trào (3.4 dBFS) — 2/3 video có hiện tượng "vỡ đỉnh nhẹ" ở đoạn cường độ cao, đáng nghi là đặc điểm chung của khâu master âm thanh hành động/cao trào (không giới hạn true-peak đủ chặt), chứ không phải lỗi riêng 1 phim.

## Nhạc nền
**Không nghe được bằng tai.** Số đo cho thấy âm thanh (nhạc + SFX) chạy gần như liên tục toàn phim (chỉ 1 khoảng lặng, ở đoạn credit) với cường độ cao và LRA vừa phải (10.1 LU) — phù hợp với nhạc action-score điển hình (căng thẳng liên tục, không có khoảng nghỉ để không làm mất đà trận đánh) — **suy đoán từ số đo, cần người dùng nghe để xác nhận** có beat/nhịp nhạc trùng với các cú đánh không (thường thấy ở phim hành động chuyên nghiệp).

## Giới hạn / câu hỏi mở
- Đã đo toàn bộ phim (khác 2 video trước chỉ đo đoạn) nên không có giới hạn "chưa xem hết" — nhưng chỉ xem qua **ảnh mid-frame tĩnh**, không xác nhận được chi tiết chuyển động máy (dolly/handheld/tĩnh) từng shot bằng phương pháp này.
- Không đọc được tên nhân vật/thoại (phim gần như không có phụ đề đọc được qua ảnh tĩnh, khác 2 video AI drama có phụ đề burn-in rõ).
- Chưa xác nhận danh tính diễn viên nữ chính có đúng là Aurélia Agel (đạo diễn/diễn viên võ thuật) như ghi trong `MAU_S0_12.md` — chỉ đối chiếu bằng mắt qua ảnh, chưa tra cứu riêng.

## Xoá dữ liệu
Đã xoá `v03_full_SLStk36wLZc.webm`, thư mục `v03_full_frames/`, và `v03_full_sheet_*.jpg` khỏi `scratchpad/s012` sau khi viết xong file này — chỉ giữ JSON số đo nội bộ.
