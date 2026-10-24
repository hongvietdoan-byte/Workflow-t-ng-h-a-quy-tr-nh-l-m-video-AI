# Việc người dùng CHỈ dùng Dashboard thì không tự xử lý được (gặp khi làm #34 "Mèo nhảy tập 2", 23–24/10/2026)

Người dùng 24/10: "Lưu lại những vấn đề mà khi người dùng nếu chỉ thao tác trên dashboard sẽ không xử lý được".
Mỗi mục: **gặp gì → phiên Claude Code đã làm thay bằng cách nào → cần gì để Dashboard tự làm được**. "Đã kiểm" = có bằng chứng chạy thật
trong phiên; "chưa kiểm" = phiên làm ngoài Dashboard nhưng chưa dò hết Dashboard có lối khác hay không.

## A. Chặn hẳn (không có nút nào gỡ được)

1. **Tổ rà soát lỗi đăng nhập → cổng gen bị giữ mà Dashboard ghi "không có mục lệch" (đã kiểm).**
   Sổ `change_events` của #34 có 13 lần `failed` (OAuth Claude Code hết hạn). Dashboard (Bước 2 · 🔎 Rà soát tác động) ghi "không có mục
   lệch"; 📥 Việc cần bạn không có mục nào của #34; vậy mà `pregen_check` và job gen đều bị `change_review.blocking()` giữ. Mục ĐỎ
   "rà soát lỗi" chỉ được tạo khi có ai gọi `blocking()` có ghi (G35 `_hold_failed`), nên nút ↻ Rà lại / Bỏ qua không hiện.
   Phiên làm thay: gọi `change_review.blocking` → `rerun_failed(892)` → `review_scene_now` (đúng hàm của nút).
   Cần: màn Rà soát / 📥 hiện "N lần rà lỗi chưa rà lại" kèm nút ↻ Rà lại (+ giá) và Bỏ qua, kể cả khi chưa có mục đỏ.
2. **Claude Code (`claude -p`) hết hạn đăng nhập (đã kiểm).** Pipeline gọi bản npm `C:\Users\hongviet.doan\AppData\Roaming\npm\claude.CMD`
   (2.1.278, cấu hình `C:\Users\hongviet.doan\.claude`) với môi trường đã bỏ dấu phiên cha; `claude auth status` → `"loggedIn": false`
   ngay cả sau khi người dùng báo "đã đăng nhập" (tệp `.credentials.json` vẫn 23/10 23:03) — đăng nhập ở app desktop / chỗ khác không có
   tác dụng cho pipeline. Dashboard chỉ nói "mở `claude` để đăng nhập lại", không nói đăng nhập Ở ĐÂU, không có nút kiểm.
   Cần: ô trạng thái "Claude Code của pipeline: đã / chưa đăng nhập" (chạy `claude auth status` với `ClaudeCliClient.clean_env()`), ghi
   rõ đường dẫn lệnh + thư mục cấu hình, nút "Kiểm lại".
3. **Tổ làm phim ở Bàn đạo diễn 3D cần câu trả lời JSON của phiên Claude Code (đã kiểm).** N3 📝 Đề bài viết `crew/de_bai_<vai>.md`;
   N4 📥 Nạp câu trả lời vai đọc JSON (dán vào ô hoặc `crew/tra_loi_<vai>.json`). Không có nút "cho Claude trả lời" — người chỉ dùng
   Dashboard phải tự mở một phiên Claude Code, đưa đề bài, chép JSON về. #34: phiên viết 3 lượt Đạo diễn + 6 lượt Quay phim / duyệt.
   Cần: nút "Giao vai cho Claude" (claude_cli theo dự án, qua sổ chi + ước tính trước) đọc đề bài → ghi tra_loi → tự nạp.
4. **Nhân vật thiếu chiều cao `height_m` trong hồ sơ Kho → Bàn đạo diễn chặn (đã kiểm chặn; lối sửa trên Dashboard chưa kiểm).**
   Phiên làm thay bằng script: tạo bản Kho riêng #456/#457 (`assets.set_profile(..., approved=True)`), nối lại nhân vật, gỡ 452/454 khỏi dự án —
   để không sửa Kho đang dùng ở #33. Cần: từ chỗ báo thiếu ở Bàn đạo diễn, ô nhập chiều cao → ghi hồ sơ (hỏi "sửa Kho chung hay tạo bản
   riêng cho dự án này").

## B. Làm được nửa chừng / dễ sai nếu chỉ nhìn Dashboard

5. **N5 "Dựng tấm ghép" từng lấy lần đo đầu (`full_measure`) thay vì lần đo đã sửa / đã chọn (đã kiểm 24/10 sáng).** EP nhìn máy cũ
   trong khi chốt ghi máy mới; phiên phải ghép tay ảnh m3. (Đã báo phiên chính; lần chạy 11:26 tấm ghép có dòng "lần đo: 1←m1" — có thể
   đã sửa, chưa kiểm lại ca có nhiều lần đo.)
6. **Luật kiểm vai `core/change_audit.py` dò nhân vật theo TÊN trên toàn Kho, không theo Kho nhân vật đang nối `characters.ref_asset_id`
   (đã kiểm).** #34: "RỐI TÍM" khớp nhầm Kho #454 của #33 ("thiếu must_keep"), "RỐI ĐỎ" báo "không có trong Kho" dù đã nối #456/#457.
   Bấm ✓ Đã sửa thì lần rà sau lại mọc lại. Người dùng không phân biệt được cảnh báo thật với cảnh báo sai.
7. **Bộ giải máy chọn phía máy mà người dùng không điều khiển được bằng chữ (đã kiểm).** Dời người (Đạo diễn) đổi hẳn phía máy (biệt thự
   chính diện ↔ lệch trái); sửa máy giữ cùng phía; `thay_min` của thứ phụ không ép. Muốn "biệt thự chính diện + RỐI ĐỎ trọn" phải thử dời
   chỗ 3 lần. Cần: ô chọn phía / hướng nền trên Bàn đạo diễn hoặc cho thứ phụ ép được (`thay_min` thành ràng buộc).
8. **Đổi chỗ đứng 3D / góc máy / thời tiết / sửa image_prompt + motion cho khớp nền mới (chưa kiểm hết).** Phiên sửa thẳng CSDL
   (`scenes.data`: plate_spot, angle, weather, location, image_prompt; `motion_prompts`). Chỗ đứng giữa `duong_truoc_cong` và
   `san_truoc` không có trong Kho 265; góc "hơi cao" (`slightly_high`) nằm sau cờ `whitebox_height_dummy` đang TẮT.
9. **Dựng dự án từ video TikTok (chưa kiểm hết).** Tải yt-dlp, cắt video ref chuyển động (720×1280, 30 fps), phân tích nhịp (librosa),
   tạo dự án + nhân vật chép từ #33 bằng `tools/experiments/ob55_meo_nhay_tap2_create.py`. Hậu kỳ tách phông xanh mèo
   (`chromakey + despill`) + chữ 2 dòng: ngoài Dashboard.
10. **Đăng nhập Dashboard mất khi mở URL mới (đã kiểm).** Mở `?pid=34&step=1` trong tab mới / sau khi đổi URL → về màn nhập e-mail
    (phiên nằm ở tham số `s=`). Phiền khi gửi link thẳng tới một bước.
11. **"Ảnh: deepix" trên Bước 2 trong khi model ảnh dự án = `gpt-image-2.5-sunburst` (chưa kiểm).** Dễ tưởng chọn sai model.

12. **Ghép video phụ có tách phông xanh (2 con mèo thật đè dưới khung) — không có chức năng (đã kiểm 24/10 16:00).** Bước 5 chỉ có
    phụ đề / card cuối / popup icon PNG / kích thước; không có lớp video phủ + chromakey. Bản đủ mèo phải ghép ngoài bằng ffmpeg
    (`hau_ky/hau_ky.sh`). Cần: "khung phụ" nhận video + vị trí/cỡ + cắt + tách màu nền, đồng bộ theo nhạc.
13. **Chữ đè suốt video (2 dòng tiêu đề trên đầu, 2 màu) — không có (đã kiểm).** Phụ đề chỉ sinh từ lời thoại (`delivery.subtitle_cues`,
    bảng `num_rows="fixed"`) → dự án không thoại thì không thêm được dòng; card chữ chỉ ghép cuối video. Cần: phụ đề/tiêu đề tự gõ với
    thời điểm, vị trí, màu từng dòng.
14. **Dùng tiếng gốc video tham chiếu làm nhạc — làm được nhưng vòng.** Phải tự tách âm (ffmpeg) ra `data/projects/<id>/nhac_rieng/`
    rồi mới chọn được; âm lượng mặc định 0.6 phải kéo lên 1.0. (Đã làm cho #34: dựng + xuất bản trên Dashboard → `output/FINAL_VIDEO.mp4`,
    "Kiểm bản dựng: đạt", không mèo/không chữ.)

## C. Đã gửi phiên chính (hộp thư)
- Mục 5 (20261024-094619-phien-con-meo-nhay-tap2).
- Mục 1, 2, 3, 6, 7 gửi cùng commit tài liệu này.
