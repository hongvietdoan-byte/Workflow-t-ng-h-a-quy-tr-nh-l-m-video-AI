# 13 — AI动漫频道: 《天命神算》 / "The Divine Fortune Teller" Ep01-30 (AI 漫剧 — tranh động, không phải người thật)

- **URL**: https://www.youtube.com/watch?v=I8pBeykLauA
- **Thể loại**: **AI 漫剧 / motion comic 16:9** kiểu anime, đô thị + "hệ thống" (系统): thanh niên sắp chết nhận "hệ thống bói toán", mỗi ngày xem tướng 3 khách.
  Lồng tiếng Trung, phụ đề Trung vàng — mục 1.6 trong `MAU_S0_12.md`
- **Độ dài công bố**: 57:23 · file tải 1280×720
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0);
  - (2) yêu cầu 12:30–15:00 (vụ bói thứ hai: bé gái con nhà giàu) — file 160.0s. Đối chiếu tờ quét (thẻ "有效算卦次数 2/3" ở ~14:00 ↔ shot 40 ở 113.9s) → file bắt
    đầu khoảng **12:06–12:20** gốc **[ước tính]**; mốc trong bảng là giây của file.
- **Tổng đã đo**: ~340s / 3443s (~10%)
- **Đã tải**: `v13_seg1.webm` (720p), `v13_seg2.webm`, khúc quét 144p (yêu cầu 3:00–57:00 nhưng file quét chỉ dài 817s → phủ 3:00–16:37) — **tất cả đã xoá**.

## Cách chọn đoạn
Tờ quét 1 khung/30s (3:00–16:37): phố + sạp bói (3:00), đồn cảnh sát (5:00–6:30), cổng trường + xe sang (11:00–16:00), bảng HUD "有效算卦次数: 2/3" (14:00). Không
thấy cảnh lặp. Chọn 12:30–15:00 = trọn một "ca bói" (tới HUD 2/3) + mở ca kế tiếp.

## Phương pháp
Như 11 (`motion_cv2b.py`). `tools/audio_listen.py --lang zh` đoạn 1 giây 0–90, đoạn 2 giây file 10–100.
Lưu ý: tranh tĩnh được làm "động" bằng phóng to / thu nhỏ khung → OpenCV đo ra zoom; đây là **chuyển động trong hậu kỳ trên ảnh tĩnh**, không phải máy quay.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 67 | **2.20s** | 0.63–11.3s | 22.3 | tĩnh 76%, **zoom in 13%, zoom out 6%**, tịnh tiến 4% |
| Ca bói bé gái (file 160s) | 54 | **2.06s** | 0.36–13.37s | 20.2 | tĩnh 65%, zoom in 9%, tịnh tiến 9%, zoom out 4%, roll 4%, thiếu dữ liệu 9% |

- Âm thanh: LUFS **−13.4** / **−11.2**, LRA **9.1** / **12.7 LU**; quãng lặng **0** / **0**.

### Nghe bằng số (audio_listen)
- **Nhạc 100% ở cả hai đoạn, mức gần như phẳng**: đoạn 1 −26…−29 dB gần suốt 90s (chỉ trồi −20 / −22 dB ở 60–62s), đoạn 2 −23…−33 dB (một lần "to lên" ở 71s).
  Tempo 117.5 BPM, giọng điệu độ khớp 0.33. Hầu như **không có nhãn tiếng động** (chỉ Meow 0.18 ở 68s, Ding 0.12 ở 52s đoạn 2).
- Giọng lồng tiếng dày: −11…−18 dB gần như liên tục; câu nối câu, không khoảng nghỉ.
- **Đoạn 1**: nhạc trồi 60–62s ngay trước lúc "hệ thống" lên tiếng (64.9s "有效算卦次数完成三分之一" → 74–90s giọng máy đọc nhiệm vụ).
- **Đoạn 2**: nhạc giữ −24…−26 dB suốt màn "đọc tướng" bé gái (38–78s); ở câu buộc tội người cha (69–78s) nhạc **không đổi** — cảm xúc chỉ nằm ở giọng và hình.

## Bảng shot — đoạn 1 (0:00–3:00, 67 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–4 | 0.0–6.8 | WS phố, sạp bói; MS cặp đôi | ngang | tĩnh×4 | "thầy bói, xem giùm chúng tôi cưới được không" |
| 5–11 | 6.8–26.2 | **ECU** mắt thầy bói nhắm / mở; **mặt cô gái phủ hình mạch xanh** (#6–7); ECU mũi có vết đen (#10) | ngang | zoom in×2, zoom out×2, tĩnh×3 | đọc tướng: "tài bạch cung" u tối |
| 12–17 | 26.2–44.8 | MS bạn trai nổi giận; **ECU mắt có dấu X đỏ** (#15) | ngang | tịnh tiến×1, tĩnh×5 | "ấn đường đen — điềm quan tai" |
| 18–29 | 44.8–67.5 | insert laptop; **insert giấy nợ "500 vạn"** (#24); WS đám đông; cảnh sát đến (#29) | ngang | tịnh tiến×1, zoom in×1, zoom out×1, tĩnh×9 | lộ lừa đảo; nhạc trồi 60–62s |
| 30–37 | 67.5–85.4 | tối; thẻ **"三天前"** + phim chụp não (#31); giấy chẩn đoán; **HUD "生命倒计时"** (#36); mắt phát sáng xanh (#37) | ngang | **zoom in×5**, tịnh tiến×1, tĩnh×2 | hồi tưởng + "hệ thống" gắn vào; giọng máy |
| 38–57 | 85.4–147.8 | khách mới: MS người xăm trổ; insert tiền; insert ảnh con trên điện thoại | ngang | zoom out×1, tĩnh×19 | ca bói thứ hai |
| 58–67 | 147.8–180.0 | WS cụ già (#58 11.3s); **ECU mắt** (#60), trán (#64), vết đen (#66) | ngang | zoom in×1, tĩnh×9 | ca bói thứ ba bắt đầu |

## Bảng shot — đoạn 2 (giây file; ≈ 12:10 + t)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–5 | 0.0–26.9 | WS cổng trường, xe sang, đám đông; #5 13.4s tay đặt lên đầu bé | ngang | tĩnh×5 | "Madame Curie trọng sinh" — thần đồng |
| 6–15 | 26.9–50.2 | CU bé gái ↔ MS người cha; ECU tay sờ đầu (xem **cốt tướng**) | ngang | zoom in×2, zoom out×2, tịnh tiến×1, tĩnh×5 | bé đọc thuộc lòng; "停" |
| 16–33 | 50.2–97.5 | CU bé; **insert hai tay đan chặt** (#20–21); CU cha nổi giận; bé ôm đầu khóc (#29–31) | ngang | roll×2, zoom in×1, tịnh tiến×2, tĩnh×13 | "tôi không thấy tình yêu trong mắt con — chỉ thấy sợ" |
| 34–40 | 97.5–116.0 | MS cha ôm con; WS đám đông; **HUD "有效算卦次数: 2/3"** (#40) | ngang | zoom in×1, tịnh tiến×1, tĩnh×3, thiếu dữ liệu×2 | kết ca bói |
| 41–54 | 116.0–160.0 | WS xe đen; MS bà cụ áo tím + **vòng hào quang HUD** (#43); **bàn tay phủ khung đỏ** (#51); ECU | ngang | zoom in×1, tịnh tiến×1, tĩnh×9, thiếu dữ liệu×3 | khách thứ ba |

## Kỹ thuật đáng học
1. **"Vẽ ra điều vô hình" bằng lớp đồ hoạ trên ECU** (mạch xanh phủ mặt 8.0–14.5s, vết đen trên mũi 21.4s, dấu X đỏ trên mắt ~34s; hào quang và khung đỏ ở đoạn
   2 #43, #51). Ý đồ **[có thể]**: người xem "thấy" cái thầy bói thấy, biến lời phán thành bằng chứng hình. Độ tin: chắc về quan sát, có thể về ý đồ.
2. **Một "ca" = một đơn vị truyện ~1.5–2 phút, khép bằng HUD đếm "1/3 → 2/3"** (≈67s đoạn 1; 113.9s đoạn 2). Ý đồ **[có thể]**: nhịp "mỗi ca một cú lật" cho xem
   lướt, và bộ đếm hứa hẹn ca tiếp theo. Độ tin: có thể — chức năng giống thẻ "未完待续" của 11, 12.
3. **Cấu trúc lặp trong mỗi ca**: toàn cảnh đám đông → ECU chẩn đoán → insert bằng chứng (giấy nợ 500 vạn #24; hai tay đan chặt #20–21) → phản ứng đám đông /
   cảnh sát → HUD. Độ tin: có thể (thấy 2 ca đầy đủ).
4. **Chuyển động bằng phóng to / thu nhỏ trên tranh tĩnh** (zoom 19% đoạn 1, tịnh tiến chỉ 4%): cú zoom dồn vào chỗ "hệ thống" (5 zoom in trong 67.5–85.4s). Ý đồ
   **[có thể]**: nhấn khoảnh khắc siêu nhiên bằng chuyển động rẻ nhất có thể. [suy luận] với pipeline: ảnh tĩnh + zoom hậu kỳ là phương án tiết kiệm cho shot
   "đọc / nhìn".
5. **Nhạc nền phẳng, không lặng, gần như không tiếng động** (100% nhạc, 0 quãng lặng, mức ±3 dB suốt 90s). Ý đồ **[đoán]**: sản xuất số lượng lớn — nhạc chỉ là lớp
   lót; kịch tính mang bằng lời lồng tiếng. Là **đối cực** của 12 (nhạc dây kéo lên theo sỉ nhục) và 14 (tiếng động làm dấu câu).

## Giới hạn / câu hỏi mở
- Tờ quét chỉ phủ tới 16:37 (file quét cắt ngắn) — nửa sau chưa xem.
- Chuyển động đo trên tranh — nhãn "zoom" không nói gì về máy quay; "roll" có thể là rung khung hậu kỳ.
- Không biết công cụ AI tạo tranh / lồng tiếng (chỉ thấy tag #AI漫剧).

## Xoá dữ liệu
Đã xoá `v13_seg1.webm`, `v13_seg2.webm`, `v13_seg*_frames/`, các tờ ảnh, thư mục `v13_seg1_L0/`, `v13_seg2_L10/` và log. Chỉ giữ `v13_seg{1,2}_result.json`,
`v13_seg1_L0_numbers.json`, `v13_seg2_L10_numbers.json` (không lời chép).
