# Rà Đ15 việc 3 — vùng an toàn lớp phủ (12/10/2026)

## Đánh giá lựa chọn phạm vi
- Tần suất: popup cuối #24 đã lấn tab; nhãn AI đặt ở góc trên mỗi bản bật nhãn; popup shot Đ17 đã có safe_box. Không có số đếm sản xuất vì không đọc dữ liệu thật.
- Lợi ích: giữ thông tin ngoài giao diện TikTok/Reels, cùng nguồn bảng subtitles/knowledge/editor/safe_zones.md. Thực tế file là knowledge/editor/safe_zones.md, không có thư mục subtitles/knowledge.
- Chi phí API bổ sung: 0 USD; xử lý PIL/ffmpeg cục bộ. Thêm kiểm bounds mỗi frame popup; chưa benchmark phim dài.
- Rủi ro: chữ/icon có thể nhỏ hơn khi quá lớn, dời lớp phủ có thể đè nội dung ảnh; không dò mặt mới, không cam kết chất lượng sản xuất. Cờ overlay_safe_zone OFF/OPT_IN_ONLY, verified False.

## Đối chiếu và cách làm
- core/end_popup.frames dựng icon/chữ rồi shade; kiểm RGBA nội dung riêng khỏi nền shade toàn khung. OFF giữ pixel của code main; ON fit content vào bảng subtitles.
- core/shot_popup.apply vốn đặt safe_box cho cả OFF: giữ nguyên; tránh thêm margin lần hai trong recursive frames.
- delivery.card_picture và ai_label_picture dùng cùng helper; endcard giữ màu nền toàn khung. Manual/autopilot/draft dùng delivery chung; crop export vẽ lại theo nền tảng dự án.
- Phụ đề/HUD dùng subtitles.to_ass sẵn với bảng nền tảng; không đổi margin kép trong bản này. Chưa đo pixel libass outline/HUD nhiều dòng; không coi đã nghiệm thu mọi loại chữ.
- Không thay widget/key; không cần ảnh UI1440/1280. PNG ở docs/images/d15 là frame RGBA thật PIL, không phải screenshot Dashboard.
- Không sửa runner/special files, TODO/PLAN, quyền hoặc dữ liệu thật; areas.version66 giữ.

## Bằng chứng
- ĐỎ: test_overlay_safe_zone_d15.py lỗi import helper chưa tồn tại.
- XANH lần đầu: nhóm5files safezone/end_popup_p24/shot_popup/ai_label/subtitles:89passed43,19s.
- Lần cuối cùng nhóm5file:91passed43,15s, gồm popup tất cả frame nằm trong box và hash không popup giữ nguyên khi bật cờ.
- QA riêng so module baseline gitshowHEAD: AI label/card và24frames popup (có shade) pixel giống hệt khi OFF. Assert hoàn tất trước lỗi console cp1252 in tiếng Việt; lỗi in không thay kết quả assert.
- FFmpeg ghép24 PNG ON vào fakevideo360x640/1s thành công; no API. PNG ON/OFF: docs/images/d15/safe_zone_on.png, safe_zone_off.png.

## Tự rà skill2b.5 / caller
Không nới assertion cũ; đường output do caller/tempdir truyền, không data thật; không thêmpaidcall; defaultOFF; safe_boxshotpopup legacygiữ. related_areas chạy PYTHONUTF8=1, step5 trực tiếp vàcallerdelivery/autopilot/compare/dashboardeditor; cả bộ/slow dành bước tích hợp, chưa chạy.

## Còn mở giao root + phiên rà
- Ba P2 của phiên rà độc lập đã sửa trong một vòng: export crop truyền notes/diag/manifest; khai areas.flags; ON vẽ đủ toàn bộ chữ trước fit.
- HUD outline/ngoại lệ margin sẵn chưa đo libass; không ghi finding hoặc sửa theo suy đoán. Không coi mọi loại chữ/HUD đã nghiệm thu.
- Chưa cả bộ Windows, chưa #24/#27, chưa bật sản xuất, không merge/push/live restart.

## Rà độc lập và vòng sửa gom
- Đọc skill 2b.5, CHUAN, CLAUDE 7 và related_areas: step5; caller autopilot/deliver/render, animatic _burn, compare/status, llm_io lưu cfg, draft shot_popup đã safe_box; không thêm lời gọi tốn tiền/quyền/widget.
- Ba P2: `_reframe` bỏ cảnh báo của ảnh vẽ lại; thiếu cờ trong step5; chữ dài/multiline bị clip trước fit. Năm ca regression ĐỎ → 11 xanh/1,16s, giữ assertion cũ.
- Regression nhiều dòng phát hiện wrap_text gộp newline của card: 1 đỏ/97 xanh → ON giữ newline; OFF giữ cách vẽ cũ.
- Root đọc diff phát hiện popup overshoot115% cũng clip trước fit. Regression headline345px →396px: ĐỎ thấy360px. ON canvas nội dung mở rộng trước đặt vào frame; OFF và safe_box shot-popup cũ giữ hành vi.
- Nhóm5file cuối safezone/end_popup_p24/shot_popup/ai_label/subtitles: **99 passed /24,12s**. Không cả bộ. Có thêm lượt test vì các lỗi thật mới phát hiện, không nới test.
- Sau toàn bộ fix, kiểm lại baseline gitshowHEAD: AI/card và24frame popup có shade **pixel bytes giống hệt OFF**. Dữ liệu/PNG kiểm trong tempdir, không API/data thật.
- ON nội dung quá dài được thu toàn bộ, có thể nhỏ khó đọc: cảnh báo VÀNG, không cắt bỏ/không chặn; chưa đo chất lượng sản xuất. Root cần đọc diff vòng sửa trước commit.
- Root đã đọc lại delivery/helper/end_popup/tests/areas sau vòng sửa: chốt 3P2 độc lập + lỗi overshoot root; 99test xanh, OFF baseline bytes giữ. Xem PNG ON/OFF; đây là raster PIL, không Dashboard. Popup shot giữ safe_box legacy, chưa xác minh chất lượng chữ/HUD hoặc mọi nội dung quá khổ của luồng legacy. Không gộp main.
