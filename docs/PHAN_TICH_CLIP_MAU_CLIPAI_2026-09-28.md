# Phân tích clip mẫu làm bằng ClipAI + Update Log tháng 9 (2026-09-28)

> Nguồn: thư mục Drive người dùng gửi — `clip ref.mp4` (201 s, 1280×720 16:9, 30 fps, AAC) và `Copy of [EN] ClipAI User Guide.pdf`
> (Update Log 15–28/09/2026). Đo bằng ffmpeg + numpy trên máy, 0 USD. Không lưu hình / âm của clip vào repo (chỉ số đo + mốc giây).
> Ký hiệu: **[đo]** = số đo bằng máy · **[xem]** = Claude Code xem tờ ảnh 1 khung/giây + dải 10 khung/giây quanh điểm cắt ·
> **[suy luận]** = đoán cách làm, chưa có bằng chứng.

## 1. Clip mẫu là gì
MV kể chuyện (bài hát tiếng Trung, phụ đề = lời bài hát) về một người bị lừa vào "KK园区" (sòng bạc): đến nơi → được mời chơi → cầm
"con 9" → thua dần, bán máu đổi phỉnh → điệp khúc nhảy → thế giới siêu thực (người tí hon kẹt giữa chồng phỉnh / quân bài khổng lồ) →
vùng ra → đẩy cửa bước ra mưa: "这次，我真走" (lần này tôi đi thật) → tối dần. **2 nhân vật chính + nhóm "người trùm đầu"**, 1 bối
cảnh chính (sảnh sòng bạc tím–vàng) + 3 biến thể (sân khấu neon, mặt bàn phóng to, cửa ra mưa).

## 2. Số đo
| Chỉ số | Clip mẫu | #8 bản giao | Ghi chú |
|---|---|---|---|
| Số shot / độ dài | **62 shot / 201 s** [đo, ngưỡng cắt 0,25] | 33 / 83 s | cụm "cắt" 0,3 s ở 2:03–2:07, 2:28–2:34 là chuyển động nhảy nhanh / lóe sáng, không phải cắt |
| Độ dài shot trung vị / trung bình | **2,5 s / 3,25 s** [đo] | 3,0 s (bản cuối) | ≈ 1 shot mỗi câu hát; phim drama tham khảo S0: 1,86 s |
| Cắt trùng phách nhạc (±80 ms) | 17/61 = 28 % ≈ ngẫu nhiên (28 %) [đo, tempo ~103 BPM] | — | **cắt theo câu lời, không theo phách** |
| Âm lượng | **−14,6 LUFS**, LRA 5,9 LU, đỉnh thật **+0,7 dBFS** [đo] | — | nhạc liên tục; to dần về cuối (RMS −25 → −10 dB); chỉ 1 chỗ lặng có chủ ý ~0:10 (sau "欢迎来到KK园区"). Đỉnh > 0 dB = có vỡ nhẹ — **khâu âm của ta (limiter −1 dBTP) còn chặt hơn** |
| Khung hình trùng | 4.989/6.042 khung khác nhau = 0,83 ≈ 24/30 [đo] | — | nguồn 24 fps (Seedance) đẩy lên 30 fps bằng nhân khung, không nội suy |
| Phụ đề | 1 dòng, giữa đáy, chữ trắng nhỏ viền tối, suốt clip [xem] | 1–2 dòng | lời hát = lời kể truyện |

## 3. Vì sao clip này chỉn chu, liền mạch, dễ hiểu — nhận xét từng mặt

### 3.1 Thiết kế nhân vật **né điểm yếu của AI** [xem] — bài học lớn nhất
- **Nhân vật đám đông không có mặt**: áo liền quần trắng + mũ trùm đen có 2 mắt tròn. Không mặt → **không cần khớp môi, không trôi
  nhận diện, không bị bộ lọc "người thật"**, và AI vẽ lại 60 lần vẫn giống nhau. Cả clip dùng hình này cho nhân vật chính lẫn đám đông.
- **Nhân vật nữ có "chữ ký" rõ**: tóc tím ngắn, kẹp tóc chữ A, váy nhung tím hở vai xẻ tà, bốt trắng — 4 dấu hiệu, nhìn silhouette là
  nhận ra; màu nhân vật **trùng bảng màu bối cảnh** (tím–vàng) nên không bao giờ lệch tông.
- Nhân vật nữ chỉ hát cận ở vài shot (0:55–0:57, 1:12–1:13, 2:16), còn lại là toàn / trung cảnh nhảy → rất ít chỗ phải khớp môi.
- So với #8: 3 nhân vật FF tả thực có mặt người, thoại nhiều, cận nhiều → đúng 3 điểm yếu (khớp môi 1.7, mặt lệch kiểu anime 1.3, bộ lọc
  người thật).

### 3.2 Một bối cảnh mạnh, dùng lại [xem]
- Sảnh sòng bạc: đèn chùm, cầu thang vòng, sàn đá bóng phản chiếu, bàn nỉ xanh, đèn tím. Xuất hiện ~70 % số shot từ nhiều góc → người
  xem hiểu không gian ngay, AI cũng dễ giữ nhất quán (một bộ ảnh tham chiếu).
- Biến thể có lý do kể chuyện: **sân khấu neon** = đoạn điệp khúc / nội tâm (1:47–1:55); **mặt bàn phóng to, người tí hon giữa phỉnh
  và quân bài khổng lồ** = ẩn dụ "bị cờ bạc giam" (2:21–2:59); **cửa mở ra mưa** = lối thoát (3:07–3:12). Mỗi lần đổi nơi = một ý mới.
- So với #8: tháp đồng hồ nhiều tầng (1.4) — bối cảnh thiếu một bộ tham chiếu chuẩn; S5 (render GLB) đúng hướng.

### 3.3 Âm thanh đi trước, hình theo sau [xem + đo]
- Bài hát hoàn chỉnh có sẵn; mỗi câu lời ≈ 1 shot, **hình minh họa đúng nghĩa câu lời**: "我有一个九" → giơ 1 ngón tay (0:10);
  "口袋比脸干净" → lộn túi quần rỗng (0:19–0:20); "有人递来一副牌" → tay đưa bộ bài (0:21); "打蚊子" → đập muỗi (1:30);
  "卖血换筹码" → máy đổi giọt máu lấy xu (1:38); "门外那场雨，还在等我" → cửa, mưa (3:07). **Lời và hình nói cùng một điều → dễ hiểu
  dù không có thoại.**
- Nhạc không bao giờ tắt; năng lượng tăng dần (RMS −25 dB ở đầu → −10 dB ở điệp khúc cuối) = đường cong cảm xúc của truyện.
- Đúng hướng S2 (timeline theo âm thanh) của ta; clip này là bằng chứng mạnh cho **khóa âm thanh trước, rồi mới chia shot**.

### 3.4 Chuyển động uyển chuyển **thật** — không phải "che lỗi" [xem kỹ 5 khung/giây + đo] (sửa sau góp ý người dùng 2026-09-28)
> Bản đầu ghi "dáng sai một chút vẫn thành vũ đạo" là **sai**: người dùng chỉ ra, soi lại 4 đoạn ở 5 khung/giây thì chuyển động sạch,
> không thấy lỗi tay chân / trượt chân / khựng trong các khung đã soi.
- **Chất lượng chuyển động cao, có trọng lượng:** 2:48,5–2:50,7 chuỗi breakdance sát sàn (chống tay → xoay hông → đá chân) liền mạch,
  trọng tâm đúng, tay chống đúng điểm tì; 1:17,9–1:19,5 váy nhung xoay có **vật lý vải** (bay ra, rủ xuống theo quán tính); 2:03–2:05
  nhảy toàn thân đổi thế liên tục.
- **Nhảy nhóm đồng bộ:** 1:00,5–1:02,7 nhân vật nữ + 5 người trùm đầu làm **cùng một chuỗi động tác cùng nhịp** — rất khó ra từ
  prompt chữ thuần → khả năng cao dùng **video tham chiếu chuyển động** (@Video1: vũ đạo người thật / video mẫu) để model chuyển
  động theo **[suy luận]**. Tài liệu ClipAI cho phép tối đa 10 video tham chiếu, vai "@Video1 tham chiếu chuyển động" (Game Video Production).
- **Nhiều chuyển động hơn #8 mà vẫn mượt [đo]:** độ đổi hình trung bình mỗi khung (khung xám 64×36, 24 khung/giây, gồm cả chuyển động
  máy): clip mẫu **1,39** / #8 **0,57** → clip mẫu **chuyển động gấp ~2,4 lần**. Lỗi "cứng" của #8 (1.5) trước hết là **nhân vật
  động quá ít** (đứng, cử chỉ nhỏ), không chỉ là giật.
- Mỗi shot **bắt đầu giữa chuyển động** (đã đang nhảy / đang bước), không khởi động từ tư thế đứng yên; máy đi theo nhịp động tác.
- **Chuyển cảnh được tạo ngay trong model**, không phải ở khâu dựng: 2:20.6–2:21 máy bay lên xuyên đèn chùm rồi hạ xuống mặt bàn phóng
  to (dải 10 khung/giây: liên tục, không có điểm cắt); 2:21 vệt mờ zoom; 3:14 hòa hình → mỗi lần sinh video có lẽ chứa **nhiều shot +
  chuyển cảnh** **[suy luận]**.
- Cắt chèn **cận vật** để nối (quân Át 1:16, tay đếm phỉnh 0:49, chân bước lên phỉnh 3:02).
- Vì sao làm được **[suy luận, xếp theo khả năng]**: (1) model mạnh về chuyển động (Seedance 2.x) + **video tham chiếu vũ đạo**;
  (2) **đầu vào không ép dáng**: ảnh tham chiếu nhân vật + chữ, không dùng ảnh storyboard dáng đứng làm khung đầu — đúng điều Director
  Workspace khuyên (mục 4: nhân vật hình học để Seedance "tự do tạo chuyển động mượt thay vì bắt chước cứng"); (3) **chọn lọc**: sinh
  nhiều bản, giữ bản đẹp (không biết số lần sinh lại).
- So với #8: khung đầu = ảnh storyboard dáng cứng → Seedance giữ dáng cứng; không có video tham chiếu chuyển động; hành động khó (chạy,
  ngã, bắn) không có tham chiếu.

### 3.5 Kể chuyện rõ nhờ **mô-típ lặp và kết có trả lời** [xem]
- Một nhân vật, một mục tiêu ("thắng đủ tiền rồi đi"), lặp mô-típ **con số 9 → cửa → mưa**; mở ở cổng sắt trong mưa đêm (0:00),
  kết ở cửa mở ra mưa sáng (3:07) = vòng tròn khép lại.
- Ẩn dụ hình ảnh thay thoại: người tí hon giữa phỉnh khổng lồ = bị cờ bạc nuốt; bảng xếp hạng, hóa đơn dài = nợ.
- So với #8: truyện cụt, hồi tưởng không dấu hiệu (1.9) — thiếu mô-típ và thiếu shot "trả lời".

### 3.6 Quay phim [xem]
- Cỡ cảnh xoay vòng toàn → trung → cận vật → toàn; góc thấp cho cảnh "bị áp đảo" (2:31–2:47), góc cao nhìn xuống bàn (0:30–0:32)
  cho "bị vây"; shot sau lưng (3:07–3:12) cho quyết định rời đi. Mỗi góc có lý do.
- Ánh sáng thống nhất tím–vàng + phản chiếu sàn cả clip; đêm mưa ở đầu, trời sáng sau mưa ở cửa ra = đổi ánh sáng theo truyện.

### 3.7 Điểm chưa tốt (để không thần thánh hóa)
- Đỉnh âm +0,7 dBFS (có thể vỡ trên loa điện thoại).
- Mặt nhân vật nữ trôi nhẹ giữa các shot cận (0:56 so với 1:12: mắt / môi hơi khác) [xem]. Chuyển động: không thấy lỗi trong các khung đã soi.
- Clip 16:9, dạng MV — **không phải drama thoại dọc 9:16** như dự án của ta: né được khớp môi vì là MV. Bài học chuyển sang drama chỉ
  dùng được một phần (xem mục 5).

## 4. Update Log tháng 9 — điều mới đọc được từ PDF (bổ sung `docs/CAP_NHAT_CLIPAI_2026-09-28.md`)
| Ngày | Tính năng | Chi tiết mới | Ảnh hưởng |
|---|---|---|---|
| 28/09 | **Sample Mode (Seedance)** | nút "Generate Sample" **chỉ 480p**, ví dụ dùng **Seedance 2.5**; trên bản mẫu có "Generate 1080p Final" (**chỉ 1080p**), giữ bố cục + chuyển động bản mẫu; bản mẫu có hạn (~7 ngày, ảnh chụp ghi "Expires in 6d 23h"); xem lại lịch sử bản mẫu từ bản cuối | S4.11: đúng quy trình "thử rẻ → duyệt → bản đẹp" ta cần; **vẫn chưa rõ có trong API** — cần thử 1 lần gọi |
| 28/09 | **Eleven Music v2.5** | Audio → Text to Music; **prompt chỉ tiếng Anh, ≤ 4.100 ký tự**; chọn độ dài (30 s mặc định), công tắc Instrumental; ví dụ giá hiển thị **7,5 ¢** cho 30 s | S1.15: prompt nhạc của ta (`music_timing.brief`, ≤ 1.990 ký tự) đã là tiếng Anh; nới trần ký tự nếu dùng v2.5 |
| 28/09 | Prompt Assistant cho Seed Audio | viết đúng định dạng mốc giờ `[1.0s:2.5s]` trước câu thoại | S2.6: mẫu prompt Seed Audio dùng đúng định dạng này |
| 21/09 | **Advanced Edit** (Transform) | sửa video có sẵn: chụp khung + vẽ / ghi chú từng chỗ cần sửa, "Smart understanding" gộp thành 1 prompt; "Edit @Video1 …"; tham chiếu tối đa 30 ảnh / 10 video / 10 âm thanh | **sửa clip lỗi thay vì sinh lại** (mặt lệch, tay hỏng) → giảm chi phí làm lại; việc mới S4.12 |
| 17/09 | **Seed Audio 1.0** | 1 ảnh tham chiếu **hoặc** ≤ 3 clip âm (≤ 30 s, 10 MB mỗi clip); ~**15 ¢/phút**; MP3, 44,1 kHz; chỉnh tốc độ / độ to / cao độ | S2.6 rẻ: track 30 s ≈ 0,08 USD |
| 16/09 | Blender plugin (macOS, v0.3.4) | đưa shot white-model / ảnh chụp / video từ Blender vào ClipAI làm tham chiếu; có mục "Use with Codex / Claude Code" | S5.6 (máy ta là Windows — bản macOS; cần kiểm bản Windows) |
| 15/09 | **Director Workspace**: phông xanh + nhân vật hình học | chỉnh màu nền / ánh sáng để tách nền; nhân vật **Geometric (trụ + cầu)** hoặc **Humanoid** có tư thế; **khuyên dùng Geometric**: "nhân vật đơn giản cho Seedance tự do tạo chuyển động mượt, tự nhiên thay vì bắt chước cứng tay chân thô của ảnh / video tham chiếu"; thêm khối hộp / cầu / trụ để dàn cảnh | **Giải thích trực tiếp lỗi 1.5 (khựng)**: ta đưa ảnh storyboard dáng cứng làm khung đầu → Seedance bám dáng cứng. Dàn cảnh bằng khối đơn giản (vị trí, hướng máy) thay vì ảnh dáng chi tiết |

## 5. Bài học → việc đề xuất cho dashboard (chờ người dùng duyệt; theo quyết định 2026-09-28: là **gợi ý / phong cách tham khảo**, không thành luật bắt buộc)
| Mã | Bài học | Việc | Loại |
|---|---|---|---|
| **G-MV1** | Nhân vật né điểm yếu AI (không mặt / chữ ký rõ / màu trùng bối cảnh) | Director được gợi ý: đám đông / nhân vật phụ dùng hình dễ giữ (mặt che, đồ đồng phục); nhân vật chính có ≥ 3 dấu hiệu nhận diện ghi trong hồ sơ; **đếm số shot cần khớp môi** và báo chi phí | 💻 gợi ý phong cách mới `MV_NARRATIVE` (trộn được với `DRAMA_DOC`) |
| **G-MV2** | Một bối cảnh chính + biến thể có lý do | Director gợi ý "1 nơi chính / ≤ 2 biến thể" cho video ≤ 60 s; mỗi lần đổi nơi ghi lý do kể chuyện | 💻 gợi ý |
| **G-MV3** | Âm thanh trước; 1 shot ≈ 1 câu (lời / thoại); hình minh họa đúng nghĩa câu | đưa vào S2: shot chia theo câu của track âm thanh đã khóa; kiểm "câu này hình nói gì" ở agent người xem (S3.2) | 💻 S2 / S3.2 |
| **G-MV4** | Mỗi shot 1 hành động rõ, bắt đầu giữa chuyển động; nhân vật động nhiều hơn (#8 chỉ bằng ~40 % clip mẫu) | linter bảng shot gợi ý (💡) khi 1 shot có > 1 hành động hoặc shot thoại nhân vật đứng yên; prompt chuyển động mô tả động tác đang diễn ra từ khung đầu | 💻 S3.5 / S4.4 |
| **G-MV8** | **Video tham chiếu chuyển động** cho nhảy / hành động khó (chạy, ngã, đánh) | kho video tham chiếu động tác (quay tay / render Blender / clip mẫu có quyền dùng) gắn @Video vào prompt Seedance; A/B có / không tham chiếu trên shot chạy của #8 | 💻 + 💵 (trong trần S4.6) |
| **G-MV5** | Chuyển cảnh sinh trong model, nhiều shot / 1 lần sinh | S3.4 + S4.8: gom shot liền của cùng đoạn vào 1 lần sinh Seedance, mô tả chuyển cảnh trong prompt ("camera cranes up through the chandelier, then descends to…") | 💻 S3.4 / S4.8 |
| **G-MV6** | Đầu vào dáng đơn giản cho chuyển động mượt (Director Workspace khuyên) | khung đầu / tham chiếu tư thế: dùng ảnh dàn cảnh **đơn giản** (vị trí, hướng, cỡ cảnh) thay ảnh storyboard dáng cứng cho shot chuyển động; A/B trong S4.6 | 💻 + 💵 (trong trần S4) |
| **G-MV7** | Mô-típ lặp + kết trả lời mở đầu | Director gợi ý: 1 mô-típ hình lặp ≥ 3 lần; shot kết "trả lời" shot mở | 💻 gợi ý |
| **S4.12** | Advanced Edit: sửa thay vì sinh lại | thử sửa 1 clip #8 lỗi mặt (cận Kelly) bằng Transform + Advanced Edit (web; kiểm có API không) | 🔍 + 💵 ~0,5 USD |

**Áp ngay cho lần chạy kiểm K (hài 20–30 s, Kelly · Maxim · Kenta):** 1 bối cảnh; mỗi shot 1 hành động đơn giản; thoại khóa trước bằng
âm thanh (Seed Audio / TTS); shot khó (ngã, chạy) đứng riêng hoặc thay bằng phản ứng / hậu quả; số shot cần khớp môi đếm trước và tính
tiền trước.

## 6. Giới hạn của phân tích này
- Không biết prompt, model, số lần sinh lại, chi phí thật của clip mẫu → mọi điều về "cách làm" là **[suy luận]** từ hình.
- Nhãn [xem] dựa trên 1 khung/giây + 6 dải 10 khung/giây quanh điểm cắt, không xem từng khung cả clip.
- Tempo ước bằng tự tương quan phổ (không có librosa) — đủ để kết luận "cắt không bám phách", không đủ để đo nhịp chính xác.
