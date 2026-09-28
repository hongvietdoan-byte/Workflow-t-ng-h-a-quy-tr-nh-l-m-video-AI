# Phiếu nghiên cứu dựng phim — "(Lồng tiếng) Từ Hôn Năm Người Bạn Đời Định Mệnh" (ReelShort)

Nguồn: https://www.youtube.com/watch?v=bzsP_ArSIUA · dọc 9:16 (360×640) · dài công bố 2:54:32 (10472s).
**Đã đo đủ 5/5 đoạn** (mỗi đoạn 2–3 phút, rải theo yêu cầu phiên chính).
Dữ liệu thô: `bzsP_ArSIUA_mo_dau.json` (93 shot, 0:00–3:00), `bzsP_ArSIUA_thoai.json` (92 shot, 21:00–24:00), `bzsP_ArSIUA_hanh_dong.json` (71 shot, 40:00–42:00), `bzsP_ArSIUA_hoi_tuong.json` (75 shot, 70:00–72:00), `bzsP_ArSIUA_ket_tap.json` (66 shot, 172:00–174:00).
Cách đo: khác biệt histogram màu giữa khung liên tiếp trong trình duyệt (canvas 32×56, loại bỏ 28% dưới khung có phụ đề), phát ×1–×2 tốc độ; cắt dùng `core.reference_analysis.cuts_from_diffs(floor=30, factor=5, local_floor=35, local_factor=4)` cho cả 5 đoạn (đã nâng ngưỡng so với mặc định 18/4 từ đoạn 1, giữ nguyên từ đó để so sánh được). Nhãn bằng mắt qua các tờ ảnh ghép nhiều khung/sheet trong trình duyệt (canvas overlay, mỗi ô ghi rõ số shot + giây tuyệt đối của video). **Không đo brightness riêng cho 3 đoạn mới (hanh_dong, hoi_tuong, ket_tap)** do giới hạn lượt công cụ ở đợt 2 — chỉ có motion_in_shot (từ dữ liệu diff đã có sẵn, không tốn thêm lượt). Không đo được âm thanh (không tải video, Web Audio không gắn được vào iframe YouTube).

## Sửa nhãn sai (đợt soát của phiên chính)
Phiên chính soát 10 nhãn ngẫu nhiên của đợt 1: 7 đúng, 1 gần đúng, 2 sai rõ (mo_dau #91, thoai #45).

**Nguyên nhân**: KHÔNG phải do quảng cáo chen vào làm lệch thứ tự khung (giả thuyết ban đầu của phiên chính) — đã kiểm tra lại bằng cách seek trực tiếp tới từng giây tuyệt đối và so khớp phụ đề, quảng cáo chỉ ảnh hưởng tới quá trình dựng tờ ảnh (đã phát hiện và chụp lại ngay lúc đó) chứ không ảnh hưởng tới thời điểm gắn nhãn sau này. Nguyên nhân thật là **lỗi chép tay khi viết nhãn**: nhãn được viết vào script Python từ trí nhớ/ghi chú sau khi xem xong toàn bộ 8 tờ ảnh của một đoạn, thay vì đối chiếu lại từng ô — với các cụm shot liên tiếp có bố cục giống nhau (nhiều CU gần giống nhau của cùng nhân vật, nói các câu khác nhau), nội dung bị gán nhầm sang shot lân cận (lệch 1–2 vị trí trong bảng lưới, đặc biệt ở hàng cuối một tờ ảnh không đủ số ô).

**Đã sửa 13 nhãn** (kiểm tra lại bằng cách seek trực tiếp `video.currentTime` tới giây tuyệt đối của từng shot ± 5 shot lân cận và so khớp phụ đề thật):
- `bzsP_ArSIUA_mo_dau.json`: shot #34 (GRAPHIC→CU, người thật bị lóa trắng chứ không phải đồ họa), #90, #91, #92, #93 (nội dung bị lệch 1 vị trí ở cụm 5 shot cuối đoạn — #91 thực ra là CU thoại tiếp, #92 mới là WS toàn cảnh 5 cô dâu).
- `bzsP_ArSIUA_thoai.json`: shot #37, #38, #41, #42, #43, #44, #45, #46 (toàn bộ cụm 37–46 có subject mô tả sai/lẫn nội dung; #45 đặc biệt — nhãn cũ ghi "hiệp sĩ cưỡi ngựa lửa" hoàn toàn không khớp, thực tế là 2 người (phụ nữ đội vương miện + thanh niên tóc trắng) nói "Còn Seth thì khác").

Sau khi sửa, mỗi shot lệch đều đã xác nhận lại bằng phụ đề thật tại đúng giây tuyệt đối (không chỉ đoán theo bố cục hình).

## Số đo gộp (5 đoạn, 397 shot, 720s)
- Độ dài shot: median **1.86s**, p10 0.83s, p25 1.17s, p75 2.14s, p90 2.88s — nhất quán rất nhanh qua mọi loại đoạn (mở đầu, thoại, hành động, hồi tưởng, cuối tập).
- Cỡ cảnh: CU 52%, MCU 27%, WS 10%, MS 5%, ECU 4%, EWS/GRAPHIC ~1.5%.
- Góc máy: eye 81%, low 12%, high 7%. Máy: static 98%, push_in 1.5%, track 0.8%.
- Vai trò: dialogue 45%, reaction 24%, setup 23%, insert 5%, action 2%, ending/hook/transition ~2% gộp.
- text_on_screen 99%, vfx 3%.
- Độ dài theo vai trò: dialogue median 1.93s, setup 1.96s, reaction 1.63s, insert 1.33s, ending 0.92s, action 0.43s, transition 0.37s (khung flash rất ngắn).

## A. Cấu trúc truyện
- Móc 3s đầu (mo_dau): cắt thẳng vào EWS lâu đài rồi ngay lập tức vào đối thoại CU — không có logo/tên kênh chặn đầu.
- Giới thiệu nhân vật: chuỗi CU liên tiếp (mo_dau #64–73: mỗi shot 1 "cô dâu"), có bảng tên chữ hiện trên khung — xem mục riêng "Bảng tên nhân vật" bên dưới.
- Các đoạn giữa (thoai, hanh_dong, hoi_tuong, ket_tap) đều vào thẳng giữa mâu thuẫn/thoại đang diễn ra, không thiết lập bối cảnh mới ở đầu đoạn — phù hợp bản chất video dài liên tục, không phải mỗi đoạn là 1 tập riêng.
- Cú ngoặt: mo_dau kết ở cao trào "cưới cả 5 cô" (cliffhanger thật). **ket_tap KHÔNG có cú ngoặt riêng** — xem phát hiện quan trọng bên dưới.

## B. Thoại & lồng tiếng
- Gần như mỗi câu/lượt nói = 1 shot CU/MCU riêng của người đang nói; hiếm khi giữ 2 người trong 1 khung khi nói (chỉ vài WS/MS thiết lập).
- Khi nhiều nhân vật ngắt lời nhau liên tục, shot rút xuống 0.3–0.7s (thoai #57, #77; hanh_dong #48–50; ket_tap #59–60).
- Người nói gần như luôn xuất hiện trong khung; cắt sang người nghe ở các shot "reaction" xen giữa — tỉ lệ reaction cao nhất ở ket_tap (41% shot) vì đây là cảnh nhiều người phản ứng trước một lễ công bố gây tranh cãi.
- Phụ đề dạng TikTok-safe-zone, đặt gần đáy khung, đôi khi kèm SFX ngoặc vuông (vd "[khịt mũi]").

## C. Quay phim
- Phân bố cỡ cảnh theo loại đoạn (xem mục riêng bên dưới) — nhìn chung nghiêng mạnh CU/MCU (~79%).
- Góc chủ yếu ngang mắt; hất lên (low) dùng cho nhân vật quyền lực/đe dọa hoặc VFX mắt sáng.
- Qua vai (ots) **không xuất hiện trong cả 397 shot đã nhãn** — xác nhận qua cả 5 đoạn, không dùng để dựng thoại.
- Máy gần như tĩnh tuyệt đối (98%); push_in dùng đúng lúc cho khoảnh khắc lặng/xúc động (thoai #63, #81; mo_dau #90–93 lúc cao trào).

## D. Diễn xuất & chuyển động
- Cử chỉ khi nói tối giản (đầu/mắt), ít hành động lớn trong khung.
- Bạo lực/xung đột thể hiện qua HẬU QUẢ (máu, vết thương, vật thể ECU) chứ không quay cảnh va chạm trực tiếp — xác nhận rõ ở hanh_dong và hoi_tuong (nhiều insert ECU tay/dao/vết máu).
- Vai trò "action" luôn rất ngắn (median 0.43s) và hiếm (2%) — không phải trọng tâm dựng phim của kiểu video này.

## E. Dựng
- Độ dài shot theo vai trò: dialogue/setup dài nhất (~1.9–2.0s), reaction/insert trung bình (1.3–1.6s), ending/action/transition ngắn nhất (<1s).
- Cắt theo nhịp câu thoại nhiều hơn cắt theo hành động.
- Chưa thấy J-cut/L-cut rõ ràng qua quan sát hình (không đo được âm thanh để xác nhận).

## F. Chuyển cảnh & hồi tưởng — xem mục "Dấu hiệu hồi tưởng" bên dưới.

## G. Âm thanh
- **Không đo được** ở cả 5 đoạn — không tải video (đúng ràng buộc 0 USD), Web Audio API không gắn được vào `<video>` của iframe YouTube (CORS).

## H. Chữ trên màn hình
- Banner CTA cố định "Các tập tiếp theo trong phần bình luận" xuất hiện dưới phụ đề ở gần như mọi shot có thoại (99%) — lớp UI nền tảng (kênh chèn), tách riêng khỏi text mang nghĩa biên tập.
- Phụ đề: nền đen mờ, chữ trắng, đặt trong vùng an toàn TikTok (không che mặt).
- Xem mục riêng "Bảng tên nhân vật" bên dưới.

## I. Màu & ánh sáng
- Độ sáng đo được ở 2 đoạn đầu dao động rộng (39–250/255); nhiều cảnh tối (<60) xen cảnh sáng (>110) khi trang phục sáng màu hoặc có VFX phát sáng.
- Hồi tưởng dùng grayscale toàn bộ hoặc gần-toàn bộ (xem mục "Dấu hiệu hồi tưởng").
- 3 đoạn sau không đo brightness số nhưng quan sát bằng mắt: hanh_dong và hoi_tuong đều có phần cảnh đêm (quang trường, sảnh lâu đài) tối, tương phản cao; ket_tap sáng đều hơn (lễ trong nhà, nhiều ánh nến/đèn).

## J. Bối cảnh
- mo_dau: lâu đài/thánh đường/phòng họp hội đồng.
- thoai: sảnh lâu đài đối chất → hồi tưởng grayscale không gian trong nhà.
- hanh_dong: hồi tưởng đen-trắng (phòng riêng, hậu quả bạo lực) → phòng dưỡng thương màu → quảng trường đêm (đám đông) → sân lâu đài ban ngày (nhóm cô dâu).
- hoi_tuong: hồi tưởng đen-trắng (phòng riêng, tương tự hanh_dong) → quảng trường đêm, lễ công bố (đám đông áo choàng lông thú).
- ket_tap: sảnh lâu đài lớn buổi tối, lễ kế vị — cùng loại bối cảnh với phần màu của hoi_tuong/hanh_dong (quang trường/sảnh về đêm), khớp với phát hiện nội dung lặp lại bên dưới.
- **Tổng kết**: video tái sử dụng một số ít loại bối cảnh lõi (phòng riêng, sảnh lớn, quảng trường, sân ngoài trời) xuyên suốt nhiều đoạn — hợp lý với hạn chế chi phí dựng CGI.

## Dấu hiệu hồi tưởng (tổng hợp 5 đoạn)
Xác nhận **2 kỹ thuật khác nhau**, dùng không nhất quán giữa các đoạn:
1. **Grayscale toàn bộ + dissolve vào + flash trắng ra** (thoai, hoi_tuong, hanh_dong): cả cảnh hồi tưởng chuyển hẳn sang đen-trắng, kéo dài nhiều chục giây đến cả phút; ra khỏi hồi tưởng bằng 1 khung gần-trắng rất ngắn (0.37–1.73s, đo được brightness ~250/255 ở mo_dau #34).
2. **Không đổi tông màu, chỉ dissolve** (mo_dau #13): hồi tưởng ngắn hơn, vẫn giữ màu, chỉ đánh dấu bằng dissolve vào và 1 khung gần-trắng flash ra (mo_dau #34) — đây chính là nhãn đã sửa (trước ghi nhầm "GRAPHIC").
- Cả hoi_tuong và hanh_dong đều mở đầu ĐÃ ở giữa hồi tưởng đen-trắng (không bắt được điểm dissolve vào vì đoạn 2 phút không đủ dài để chứa cả đầu-cuối hồi tưởng) — cho thấy các đoạn hồi tưởng đen-trắng trong phim có thể kéo dài hơn 2 phút.
- Nội dung hồi tưởng ở hanh_dong và hoi_tuong trùng chủ đề (người bị thương/ép lấy máu, hộp trang sức đỏ) dù lấy mẫu ở 2 mốc thời gian cách nhau 30 phút — có thể là cùng một hồi tưởng dài được nhắc lại, hoặc 2 hồi tưởng khác nhau nhưng cùng mô-típ hình ảnh.

## Bảng tên nhân vật
- **Có dùng**, nhưng không nhất quán — không phải mọi nhân vật/mọi lần xuất hiện đều có tên.
- Vị trí: chữ nhỏ hiện trực tiếp trên khung hình (góc dưới-trái vùng ảnh), không phải card/overlay riêng biệt.
- Thời điểm: chỉ xuất hiện ở LẦN GIỚI THIỆU ĐẦU TIÊN của nhân vật trong đoạn mo_dau (Marcus #2, Caine #4, DARA #71, ROSE #73) — sau đó không lặp lại tên dù nhân vật xuất hiện lại nhiều lần trong cùng đoạn hoặc ở đoạn khác.
- Thời lượng: tên hiện suốt shot đó (~1–3s), biến mất khi cắt sang shot kế.
- 4 đoạn còn lại (thoai, hanh_dong, hoi_tuong, ket_tap) **không quan sát thấy bảng tên nào** — kể cả khi nhân vật mới xuất hiện lần đầu trong đoạn đó (có thể vì họ đã được giới thiệu tên ở đoạn khác trước đó trong phim).

## Phân bố cỡ cảnh theo loại đoạn
| Đoạn | Shot | CU | MCU | WS | MS | ECU | Khác |
|---|---|---|---|---|---|---|---|
| mo_dau (hook) | 93 | 66% | 13% | 14% | 2% | 2% | 3% (GRAPHIC/EWS) |
| thoai (đối thoại) | 92 | 49% | 34% | 5% | 12% | 0% | 0% |
| hanh_dong | 71 | 41% | 37% | 4% | 6% | 8% | 4% (EWS) |
| hoi_tuong | 75 | 53% | 23% | 16% | 0% | 8% | 0% |
| ket_tap | 66 | 50% | 30% | 8% | 8% | 3% | 2% (GRAPHIC) |
- mo_dau dùng CU nhiều nhất tuyệt đối (hook cần cận mặt liên tục) và cũng dùng WS nhiều nhì (thiết lập bối cảnh mới liên tục vì đang giới thiệu thế giới).
- thoai gần như không dùng WS/ECU — tập trung tuyệt đối vào khuôn mặt (CU+MCU = 83%).
- hanh_dong có ECU cao nhất (8%, insert chi tiết máu/vật thể) — khớp nhận định "bạo lực qua hậu quả" ở mục D.
- ket_tap nghiêng reaction/CU hơn dialogue — hợp với việc nó là cảnh nhiều người phản ứng trước 1 tuyên bố.

## Phát hiện quan trọng: nội dung lặp lại gần cuối video
Khi tìm đoạn "ket_tap" trong khoảng 2:40:00–2:54:00 theo yêu cầu, phát hiện shot #66 (giây tuyệt đối 10439.75, ~2:53:59) có **thoại giống hệt** một shot đã đo ở đoạn "thoai" (giây tuyệt đối 1348.53, ~22:28): cùng câu "Này Khay, anh có quyền lực, địa vị và sự tôn trọng." Đã xác nhận bằng cách xem trực tiếp cả 2 vị trí, không phải trùng hợp ngẫu nhiên về câu thoại — bố cục nhân vật cũng giống. Nghi vấn: **bản video 2:54:32 này lặp lại nội dung tập đầu** (có thể do kênh ghép nhiều lần phát lại, hoặc video gốc là danh sách phát nhiều tập nhưng phần cuối bị lặp do lỗi dựng của kênh upload). Do đó đoạn "ket_tap" đo được ở đây **không phải cao trào/kết thúc thật của toàn bộ nội dung** mà chỉ là một lần lặp lại — số liệu dựng phim (cỡ cảnh, độ dài shot...) vẫn hợp lệ để thống kê phong cách, nhưng không nên dùng đoạn này để phân tích "cách kết 1 tập" của kênh.

## 10 cặp (đoạn, số shot, giây) ngẫu nhiên MỚI để soát — từ 3 đoạn mới thêm
| # | Đoạn | Shot | Giây (đoạn) | Giây tuyệt đối | Nhãn chính |
|---|------|------|-------------|-----------------|------------|
| 1 | hanh_dong | #14 | 29.23–31.0s | 2429.2–2431.0 | ECU, insert, "bàn tay dính máu" (đen-trắng) |
| 2 | hanh_dong | #46 | 81.07–82.13s | 2481.1–2482.1 | EWS, setup, quảng trường làng đêm |
| 3 | hanh_dong | #63 | 102.0–102.6s | 2502.0–2502.6 | ECU, insert, chi tiết khó xác định (0.6s) |
| 4 | hoi_tuong | #1 | 0.0–1.23s | 4200.0–4201.2 | CU, setup, thanh niên minh trần (đen-trắng) |
| 5 | hoi_tuong | #40 | 68.23–69.47s | 4268.2–4269.5 | ECU, insert, hộp trang sức đỏ (đen-trắng) |
| 6 | hoi_tuong | #57 | 95.8–96.17s | 4295.8–4296.2 | GRAPHIC, transition, khung lóe trắng (0.37s) |
| 7 | hoi_tuong | #67 | 107.33–108.33s | 4307.3–4308.3 | MCU, dialogue, "công bố Luna tương lai của mình" |
| 8 | ket_tap | #6 | 7.9–9.17s | 10327.9–10329.2 | CU, reaction, mắt sáng xanh (VFX) |
| 9 | ket_tap | #27 | 51.8–52.17s | 10371.8–10372.2 | GRAPHIC, transition, khung lóe trắng (0.37s, chưa xác nhận lại bằng mắt) |
| 10 | ket_tap | #66 | 119.5–120.0s | 10439.5–10440.0 | MCU, dialogue, trùng nội dung với đoạn thoai (xem phát hiện quan trọng) |
