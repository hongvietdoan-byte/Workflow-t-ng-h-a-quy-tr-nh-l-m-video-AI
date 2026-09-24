# Vai Dựng (Editor) — bộ nguyên tắc (bản nháp chờ người dùng duyệt, 2026-09-25)

> Kế hoạch 2026-09-25, H7. Dựng nhận **clip đã duyệt + giọng + chữ trên màn hình** và làm ra bản giao. Phần lớn việc là **code**
> (`core/delivery.py`, `final_cut.py`, `subtitles.py`, `audio_lib.py`, `voice.py`, `formats.py`, `ffmpeg_studio.py`); nguồn này là để
> code và (khi cần mắt) Claude biết **vì sao** và **đặt ở đâu**. Không đổi shot, không gen lại hình — lỗi hình trả về Quay phim.
> Vùng an toàn: `knowledge/editor/safe_zones.md`.

## Tầng 1 — Mục đích
Người xem hiểu và cảm được câu chuyện **trên điện thoại, trong app**: nghe rõ thoại, đọc kịp chữ, không bị giao diện app che, nhịp không hụt.

## Tầng 2 — Cách nghĩ
1. Dựng theo **timeline của Đạo diễn** (thứ tự shot, độ dài đã chuẩn hóa); clip gen dài hơn shot thì cắt lấy đoạn có hành động chính.
2. Đặt **giọng** lên timeline (không chồng tiếng), rồi **chữ** (phụ đề, thông báo game) theo giọng và theo khung.
3. Trộn âm (giọng > hiệu ứng > nhạc), rồi xuất theo nền tảng.
4. Tự rà trên khung hình thật (bảng khung) trước khi giao Đạo diễn duyệt.

## Tầng 3 — Nguyên tắc
### E1. Cắt
- Điểm cắt theo nhịp của Đạo diễn; clip dài hơn shot → lấy đoạn có hành động chính (thường đầu clip — Quay phim đã dặn "hành động xảy ra sớm").
- Một vị trí máy nhiều shot (H5): cắt clip dài thành các đoạn theo thứ tự shot, xen với shot vị trí khác.
### E2. Giọng
- Không chồng tiếng: câu sau bắt đầu sau câu trước (+ khoảng nghỉ 0,12–0,15 s); clip kéo dài theo độ dài giọng thật (`voice.fit_durations`).
- Có giọng lồng thì tắt tiếng gốc của clip (model không nói đúng tiếng Việt).
### E3. Chữ
- Vị trí theo `safe_zones.md` (luật cứng: trong hộp an toàn chung; phụ đề khung dọc cách đáy ≥ 36%, chữ trên cách đỉnh ≥ 15% — code mặc định).
- Không đè mặt/hành động: dùng vị trí nhân vật trong bảng shot; không đủ thông tin thì xem khung hình thật.
- Thông báo game ("Maxim đã bị hạ.") khác kiểu phụ đề; card cuối nền tối, chữ giữa khung.
- Hiển thị đủ lâu để đọc (~3 từ/giây, ≥ 1 s).
### E4. Âm thanh
- **Đỉnh âm ≤ −1 dBFS sau mã hóa** — mọi bước trộn kết thúc bằng bộ giới hạn −2 dBFS (`ffmpeg_studio.PEAK_LIMIT`; AAC vọt thêm ~0,8 dB).
  *Căn cứ:* chạy thử 2A — giọng lồng trên clip chạm 0,0 dBFS; sau khi thêm giới hạn đo được −1,3 dBFS.
- Thoại rõ nhất; nhạc hạ khi có thoại. Độ to tổng: nhiều nền tảng tự chuẩn hóa độ to — mục tiêu phổ biến ~ −14 LUFS cho mạng xã hội
  (*nguồn thứ ba, chưa có tài liệu chính thức — đo lại*).
### E5. Định dạng xuất
- Theo khung dự án (9:16 = 1080×1920). Bản đổi tỉ lệ: cắt lại khung giữ nhân vật, không bóp méo; chữ đặt lại theo vùng an toàn của tỉ lệ mới.

## Tầng 4 — Ưu tiên khi xung đột
Nghe rõ thoại > đọc được chữ (không bị che) > giữ nhịp Đạo diễn > đẹp. Không sửa được bằng dựng → trả lại vai phụ trách kèm lý do.

## Tầng 5 — Tự rà (trên bảng khung thật)
- Có chữ nào nằm trong dải bị giao diện app che? Có chữ nào đè mặt?
- Câu nào bị chồng tiếng, bị cắt cụt, hay hình đổi trước khi câu nói xong?
- Có điểm cắt nào làm mất hành động chính của shot?
