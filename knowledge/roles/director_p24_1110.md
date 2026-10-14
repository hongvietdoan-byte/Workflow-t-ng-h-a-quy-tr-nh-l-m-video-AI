# Bổ sung Đạo diễn / Quay phim — bài học duyệt ảnh #24 (11/10)

Cách nghĩ rút từ lần người dùng soi 10 ảnh #24. Mỗi điều có LÝ DO và CĂN CỨ; khi hai điều va nhau, điều trên thắng. Đây không phải
luật cấm từ — là cách tính trước khi viết. Code kiểm lại các điều đo được (mức VÀNG, `core/shot_lessons.py`, `core/stage_facts.py`).

1. **Thấy gì do hình học quyết, không do ý muốn.** Máy thấp hơn miệng một vật (giếng, tường, bàn) thì KHÔNG thấy mặt trên / lòng của
   nó — chỉ thấy thành ngoài, mép trên nhìn ngang. Muốn thấy miệng giếng → máy phải cao hơn miệng và nhìn xuống. Vì: #24 shot 5 máy
   0,5 m trước giếng cao 0,9 m mà ảnh vẽ thấy miệng giếng — bị loại. Căn cứ: câu "Camera height …" code nối vào prompt ảnh (sự thật
   hình học của máy 3D). Mọi chỗ chữ của shot (image_prompt, blocking, action_peak) phải nói cùng một điều — câu phủ định ("never the
   opening") là được, câu tả lòng giếng là trái.
2. **Động tác di chuyển làm đổi chỗ đứng.** Nhịp có bò / trườn / đi / lùi / chạy (hoặc ref video có di chuyển) → điểm cuối = điểm đầu
   + quãng; ước quãng theo thân người (trườn ra khỏi giếng ≈ rướn một thân người: tâm người cách thành ≥ 1–1,5 m) hoặc theo ref. Ghi
   `den` (điểm cuối) cho nhịp đó; nhịp sau lấy `den`. Vì: #24 dàn cảnh để yêu nữ 0,25 m cách thành ở mọi nhịp sau khi trườn ra →
   shot 7 / 9 / 10 sai bố cục, lệch shot 8 đã duyệt. Căn cứ: hồ sơ tư thế (prompt 29 mục 2), video ref.
3. **Sửa chỗ một người → giữ bố cục các ảnh ĐÃ DUYỆT.** Người kia giữ nguyên vị trí, khoảng cách và bên trái/phải trong khung như ảnh
   đã duyệt; không giữ được thì nói rõ shot đã duyệt nào phải duyệt lại. Vì: ảnh đã duyệt là chuẩn người dùng đã chọn.
4. **Ref động tác / emote: liệt kê đủ nhịp + chi tiết nhỏ trước khi viết.** Một emote thường có nhiều nhịp (vd khóc: quỳ ôm mặt nấc →
   dang tay gào → gục rạp chống tay) và chi tiết nhỏ (nước mắt mảnh ánh xanh từ kẽ tay, vệt sẫm dưới mắt). Kịch bản / BYĐ phủ đủ hoặc
   ghi rõ lược nhịp nào, vì sao (`ref_luoc`). Vì: #24 shot 8 chỉ phủ nhịp 1 của ref khóc.
5. **Cỡ khung chứa biên độ động tác.** Dang tay / cả người không vừa CU / MCU → MS / WS cho nhịp đó. Ngược lại nhân vật quá nhỏ trong
   khung rộng (< ~25 % chiều cao khung) thì động tác từ ref truyền yếu và chi tiết mặt (nước mắt) không thấy → tách nhịp cần chi tiết
   sang cỡ chặt hơn hoặc thêm một shot cận. Căn cứ: bảng cỡ cảnh (tỉ lệ người trong khung) × tư thế (quỳ ≈ 0,7, ngồi ≈ 0,58 chiều cao).
6. **Hiệu ứng màn hình (nhiễu sóng, glitch toàn khung, sọc, mất tín hiệu) là hậu kỳ.** Không viết vào ảnh khởi đầu video — model video
   coi nhiễu là nội dung và giữ / lan cả clip. Ghi vào `post_fx` của shot để dựng bằng ffmpeg. Nhiễu là một phần thiết kế nhân vật
   (vd vệt glitch quanh cổ tay của bộ đồ) thì vẫn tả như trang phục.
   Lược đồ tùy chọn của shot: `"post_fx": {"loai": "glitch", "vi_tri": "cuoi", "thoi_luong_s": 0.5, "cuong_do": 0.8}`.
   `loai` chỉ nhận `nhieu_song` / `glitch` / `nhap_nhay`; `vi_tri` chỉ nhận `dau` / `cuoi` / `ca_shot`.
   `thoi_luong_s` là số hữu hạn > 0 và ≤ thời lượng clip (giây); `cuong_do` là số hữu hạn trong (0, 1].
   `ca_shot` áp toàn clip; `thoi_luong_s` vẫn bắt buộc và hợp lệ. Không cần hiệu ứng thì bỏ trường `post_fx`, không ghi object rỗng.
   Đây là hiệu ứng hậu kỳ có chủ ý, không đưa nó vào image_prompt hoặc motion prompt gửi model.


## Bổ sung từ duyệt ảnh thử #27 "Liệu bạn sẽ Booyah tập 1" (12/10)

7. **Vũ khí / đạo cụ đã gắn Kho cho dự án: gọi đúng TÊN trong mọi shot có nó.** Kelly cầm SKORP thì shot nào thấy súng cũng viết
   "SKORP" (kèm hình dáng ngắn), không viết chung "assault rifle / gun"; tường keo viết "bom keo / tường keo" kèm DẠNG. Vì: #27 shot
   1 / 19 / 21 viết chung → ảnh ra súng trường / AK; khâu chọn ảnh tham chiếu khớp theo tên nên không gửi ảnh Kho. Căn cứ: danh
   sách tài nguyên dự án gửi kèm. Code kiểm / chèn lại sau cờ `project_prop_lock`.
8. **Tường keo có 2 dạng, chọn một dạng và giữ cả cảnh.** (a) mặc định: tường keo màu TRẮNG trơn, không họa tiết / hình; (b) skin
   Gloowall OB55 theo ảnh Kho (người dùng 12/10). Shot sau của cùng cảnh giữ đúng dạng đã dùng. Vì: #27 shot 16 hổ phách, shot 19 băng
   xanh — hai thứ khác nhau cho cùng một bức tường.
9. **Chỗ núp / vật chắn chỉ dùng thứ CÓ trong model 3D của bối cảnh; cần thêm chỗ núp thì dùng tường keo.** Không tự vẽ thêm khối đá,
   thùng, xe… mà map không có. Bom keo là vật phẩm thật của trận đấu nên hợp lệ ở mọi chỗ. Vì: #27 shot 16 địch núp sau vật cản không
   có trong file 3D (người dùng 12/10). Căn cứ: sự thật sân khấu 3D (`stage_facts`), danh sách vật thể của chỗ đứng.
10. **Nhiều người bị hạ cùng lúc: tư thế nằm khác nhau theo cách ngã.** Úp mặt, nghiêng, co người, ngửa — không mặc định cả nhóm nằm
    ngửa dang tay. Vì: #27 shot 1 ba đồng đội nằm ngửa giống hệt nhau, người dùng yêu cầu có dáng úp gục.
11. **Được dùng mọi khu vực có trong model 3D quanh mốc** (vd bãi cỏ quanh Tháp Đồng Hồ), không chỉ quảng trường; chọn theo hành
    động của shot. Đây là gợi ý mở rộng chọn chỗ đứng (người dùng 12/10), không phải luật bắt buộc.
12. **Tỉ lệ súng so với người theo game, đo bằng chiều cao đầu.** Đo trên ảnh in-game Kelly cầm súng (người dùng 12/10, Kho
    #433/#434/#435/#436 có ảnh "kelly_cam_…_ty_le"): SKORP ≈ 3 đầu, M7 ≈ 3,3 đầu, RPK ≈ 3,7 đầu + chân chống, Hawk ≈ 4,6 đầu (người
    ≈ 7 đầu). Mọi súng chính đều cầm HAI tay, báng tì cánh tay/vai, nòng vượt qua hông bên kia — không bao giờ cỡ súng lục, không cầm
    một tay kể cả khi ăn mừng (tay kia giơ lên thì súng đeo / chống xuống, không thu nhỏ). Viết cỡ này vào câu tả shot có súng. Vì: #27
    ảnh thử SKORP bị vẽ như súng lục, cầm một tay. Căn cứ: ảnh tỉ lệ trong Kho (đo thô trên ảnh, sai số ~10 %).
    Súng KHÔNG cầm trên tay thì đeo chéo SAU LƯNG đúng cỡ thật (nòng chúc xuống, báng / ống ngắm nhô qua vai, tối đa 2 khẩu) —
    vd ăn mừng giơ tay: súng chính đeo sau lưng hoặc cầm hai tay hạ thấp, không biến thành súng lục. Viết "slung on her back" để
    gửi kèm ảnh Kho "ĐEO SÚNG SAU LƯNG".
13. **Góc nhìn thứ nhất (POV / FPV): hai tay KHÔNG cầm súng.** Free Fire không có góc nhìn thứ nhất khi cầm súng, nên ảnh POV có
    súng ở mép khung là hình game không có. POV chỉ thấy hai bàn tay + cẳng tay trong tay áo nhân vật, tay trống. Viết "empty hands",
    đừng viết "no gun / no weapon": chữ "gun" làm khóa súng tưởng shot có súng và gửi kèm ảnh súng. Vì: #27 shot 1–2 (người dùng
    12/10). Cả `performance` / `action` của shot POV cũng tay trống — không súng, báng, nòng, grip ("both hands empty, fingers
    flex"); code chặn ĐỎ. Vì: #27 shot 1–2 ảnh duyệt tay trống mà diễn xuất "hands tense around the rifle grip" (rà video 12/10).
14. **Vật bị nguyền / vật sự kiện vẽ ĐÚNG dạng trong ảnh Kho của nó**, kể cả vị trí so với vòng tròn đỏ. Quả bóng bãi biển LƠ LỬNG
    giữa vòng tròn đỏ, có cột sáng đỏ xuyên qua. Hộp nhạc ĐẶT trên sàn giữa vòng tròn đỏ. Mặt nạ trắng trong khung vuông trên tường giấy
    dán lục giác tối. Ô tô LƠ LỬNG trong cột sáng đỏ. Mỗi vật một mục Kho (#429 mặt nạ, #438 hộp nhạc, #439 quả bóng, #440 ô tô bay).
    Vì: #27 shot 6 tả "quả bóng nằm dưới sàn" (người dùng 12/10).
15. **Một vật thể cố định (cổng portal…) xuất hiện ở nhiều shot thì cùng MỘT chỗ.** Shot sau chạy tới / bước qua nó thì giữ đúng
    bối cảnh, giờ trong ngày và chỗ đứng của shot giới thiệu nó. Chỉ cảnh nhìn qua lòng cổng mới đổi thế giới. Vì: #27 hai cổng ở bãi
    cỏ phía bắc (shot 2), nhưng shot 3–4 lại vẽ cổng trên quảng trường đá ban đêm (người dùng 12/10).
16. **Gọi vật trong Kho bằng tên có trong tên / tên gọi khác của mục đó** (tiếng Anh đã thêm: "torii portal gate", "beach ball",
    "music box", "floating car", "cursed mask"). Khâu chọn ảnh tham chiếu chỉ khớp nguyên cụm tên. Tả bằng từ khác thì ảnh mẫu không được
    gửi kèm, và model tự vẽ một kiểu khác. Vì: #27 shot 2 cổng "không giống" vì ảnh Kho #426 không được gửi.
17. **Trời thế giới song song OB55 vẽ theo ảnh game, không phóng đại.** Trời đêm giông xám xanh. Trên tháp là một XOÁY MÂY GIÔNG TỐI
    (xám đen), chỉ có một đốm sáng cam đỏ mờ ở tâm. Ô tô / xe van / hòm lơ lửng quanh tháp, bên dưới có vệt sáng đỏ nhạt. Vệt gió
    trắng khắp trời. Cảnh vật tối, nhạt màu, chỉ điểm đỏ nhẹ. KHÔNG viết "red tornado / fiery core / red lightning / red sky", và cũng
    không viết dạng phủ định của chúng. Vì: #27 người dùng 12/10 "không thật sự có lốc xoáy đỏ rực". Căn cứ: Kho #428.
18. **Nhân vật đi TỚI / VÀO một vật (cổng, cửa…): ghi rõ máy đặt ở đâu so với nhân vật.** "Camera BEHIND her, seen from behind,
    walking AWAY from the camera into …" hoặc "camera in front, she walks TOWARD the camera". Chỉ viết "facing / walking into the gate"
    thì model hay đặt vật sau lưng nhân vật và cho nhân vật nhìn vào máy, nên trông như đang đi RA khỏi vật. Vì: #27 shot 11–12 (người
    dùng 12/10 "Kelly bị đi ngược hướng").
19. **Hướng đi và bố cục NHẤT QUÁN trong cùng cảnh, và giữa các cảnh quay lại cùng một chỗ** (người dùng 12/10, #27). Trước khi viết
    các shot của một chỗ, lập "sơ đồ chỗ" một lần: máy nhìn từ phía nào, vật cố định nằm bên nào của khung (cổng TRÁI = thực tại / cổng
    PHẢI = song song; tường keo bên trái, địch bên phải…), nhân vật đi theo hướng nào (trái → phải, hay đi xa máy vào chiều sâu). Mọi
    shot của chỗ đó viết theo đúng sơ đồ: cùng bên, cùng hướng, cùng phía máy. Ghi "frame-left / frame-right", "camera behind / in front",
    "walking away from / toward the camera" vào cả `image_prompt` lẫn `blocking`. Người / vật đã có trong shot trước (vd đồng đội nằm
    trên cỏ) mà máy vẫn nhìn về chỗ đó thì shot sau vẫn phải thấy. Đổi hướng hay vượt trục chỉ khi cố ý, có shot chuyển (cận, POV) và ghi
    lý do vào `why`. Vì: #27 shot 3 → 4 (đi vào cổng rồi lại đi ra phía máy), shot 11–12 ngược hướng. Căn cứ: luật trục 180°
    (`core/continuity.py`) và sơ đồ chỗ đứng 3D (`plate_spot`).
20. **Shot có nhân vật BẮN thì mục tiêu phải thấy được trong khung** (hoặc shot ngay trước / sau cho thấy rõ bắn vào ai): ghi tên địch
    vào `characters`, tả vị trí của địch (frame-right, mid-distance…) và trạng thái (bị thương, trúng đạn, khuỵu gối). Không viết
    "enemy implied off-frame". Người bị hạ ở shot trước, máy còn nhìn về chỗ đó, thì vẫn nằm đó. Vì: #27 shot 19–20 "bắn nhau nhưng
    không thấy bắn vào ai" (người dùng 12/10).
21. **Người nằm gục mặc váy / đồ ngắn:** chọn tư thế và góc máy kín đáo. Ưu tiên úp mặt, đầu hướng về máy, chân chĩa ra xa máy; không
    để chân hay váy chĩa về phía máy. Vì: #27 Kapella (người dùng 12/10, hai lần).
    Cập nhật 12/10 (sau 4 lần thử): với váy ngắn + tất đùi, nằm nghiêng / co gối / úp mặt vẫn lộ đùi khi máy ở gần. Cách CHẮC là cho người đó nằm NGAY SAU một người khác (xa máy hơn), chỉ thấy đầu, vai, tay, còn chân và váy bị thân người phía trước che kín.
22. **Vật mốc lớn (cổng, tháp, xe…) phải có kích thước thật trong Kho, và shot nối nhau giữ cùng độ cao máy.** Thiếu số đo thì model
    tự đoán: cùng một cổng lúc cao gấp 5 người, lúc bé như đồ chơi. Khâu "Kích thước vật mốc" báo VÀNG là phải đo / ước ngay (so với
    xe, cửa, người trong ảnh mẫu), ghi `assets.set_size`. Hai shot liền nhau cùng chỗ, cùng hướng (vd chạy tới cổng → bước qua cổng) dùng
    cùng độ cao máy (ngang vai sau lưng). Máy cao nhìn xuống làm vật ở xa bé lại, người gần to lên, sai tỉ lệ. Vì: #27 shot 3 cổng nhỏ,
    người to (người dùng 12/10); cổng #426 ≈ 9 m × 8 m.
23. **Vật mốc / đạo cụ phải giống ảnh mẫu 90–100% thì làm ẢNH MẪU SẠCH trước khi vẽ các shot.** Ảnh gốc là ảnh chụp game có bối cảnh
    (đêm, cây, vệt gió) thì model lẫn bối cảnh vào vật và tự đổi dáng. Gen MỘT ảnh cùng vật, cùng góc, nền xám trơn, tả từng bộ phận
    (`tools/asset_polish.py`), người dùng duyệt, đặt làm ảnh đầu của mục Kho. Không dán ghép vật vào ảnh: người dùng 12/10 cho rằng
    chất lượng thấp. Vì: #27 cổng torii vẽ sai 4 lần; ảnh mẫu sạch đạt ~90% ngay lần đầu.
24. **Vật phát sáng / trong mờ (cổng portal, hologram) ở cảnh BAN NGÀY: ảnh mẫu phải chụp ban ngày, vật mờ nhạt.** Ảnh mẫu đêm hay studio nền xám làm model vẽ cột đỏ đặc như đèn neon. Ảnh mẫu thứ hai "ban ngày, trong suốt khoảng một nửa, nhìn xuyên thấy trời / cây" (`tools/asset_polish.py`) đặt làm ảnh đầu; câu tả ghi rõ "CLEAR glass … faint … muted, nothing neon". Cảnh nhìn qua lòng cổng (thế giới khác) ghi "seen ONLY inside the gate opening" để trời không tràn ra ngoài. Vì: #27 người dùng 12/10 "cổng đậm và rõ quá".
