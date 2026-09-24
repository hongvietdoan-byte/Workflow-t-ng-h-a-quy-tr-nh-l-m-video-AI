# Cảnh hành động phức tạp — khóa không gian và chia nhịp chuyển động

Nguồn: AI Film Direction & Prompt Workflow Kit 1.0.0 (motion-director, bản BETA, chắt lọc); bổ sung từ bản 2.0.0 (perception-physics) ngày 2026-09-24. Chỉ dùng cho cảnh hành động phức tạp; cảnh thường (tĩnh, đẩy chậm, một chủ thể) để model tự xử lý bằng câu tự nhiên.

## Khi nào áp dụng
Chỉ khi **cùng lúc**: từ 2 chủ thể trở lên **và** chuyển động thân người nhanh **và** quan hệ không gian đổi nhanh trong khung (đánh nhau, giáp lá cà, rượt đuổi, đối đầu thể chất). Một chủ thể, chậm, hoặc không gian ổn định thì **không** áp dụng, dù cảm xúc căng ("căng ≠ máy phức tạp"). Nếu thấy thực ra không phức tạp → giữ nguyên prompt thường.

## Bốn cách model hỏng ở cảnh phức tạp
1. **Trôi không gian:** không giữ được vị trí tương đối của hai cơ thể, vài nhịp sau trái phải đảo lộn, chi thể hoán đổi.
2. **Tranh chuyển động:** hai người đánh nhau + máy quay cùng chuyển động lớn → model nhòe.
3. **Mất thời điểm va chạm:** "máy bám theo trận đánh" quá mơ hồ; không rõ vung máy (whip pan) rơi đúng đòn nào.
4. **Che khuất khi áp sát:** ai che ai, máy bám vào điểm neo nào, câu tự nhiên nói không rõ.

## Cách làm
0. **Xác định loại chuyển động (archetype), rồi mới khóa trục:** trục nhất quán thay theo loại, các bước sau dùng chung.
| Loại | Trục không gian | Cần khóa gì |
|---|---|---|
| DUEL đối đầu 1–1 | đường nối hai chủ thể | máy ở một phía đường nối, trái/phải không đổi |
| MELEE hỗn chiến | hướng của chủ thể trọng tâm | khóa vị trí chủ thể trọng tâm trong khung, người khác định vị theo nó |
| CHASE rượt đuổi | vector di chuyển | hướng tiến giữ cùng một bên khung, không đảo chiều qua điểm cắt |
| VEHICLE phương tiện | vector di chuyển | như CHASE, máy gắn cùng tốc độ với xe, xe gần như đứng yên trong khung, thế giới "chảy" qua |
| FALL_STUNT rơi/đóng thế | trục trọng lực (dọc) | hướng lên xuống và cảm giác gia tốc nhất quán, không lúc nhanh lúc chậm |
| ENV_DESTRUCTION phá hủy | nguồn phá → vật chịu | chuỗi nhân quả, hướng mảnh vụn bắn ra nhất quán |
1. **Khóa không gian:** ghim từng chủ thể ở vị trí trong khung (trái/phải/giữa), hướng nhìn, tư thế; giữ nguyên xuyên suốt cảnh. Chỉ dựa vào bối cảnh/dàn dựng đã có, không tự bịa địa điểm.
2. **Chia 2–4 nhịp nhỏ (micro-beat)** cho một cảnh liên tục, ví dụ: chuẩn bị/quan sát → giao đấu → va chạm → thu/chuyển. **Mỗi nhịp chỉ một chuyển động chính.** Tổng thời lượng các nhịp = độ dài cảnh.
3. **Phân công chuyển động:** mỗi nhịp nói rõ **chủ thể động hay máy động**, bên kia thu lại. Chủ thể di chuyển nhanh → máy neo/bám nhẹ; chủ thể dừng/thu chiêu → máy mới đẩy vào. **Vung máy (whip pan) chỉ đặt vào nhịp va chạm**, không vung cả cảnh. Chỉ dùng các kiểu máy quen thuộc (tĩnh, dolly, tracking, handheld, arc, whip_pan, rack_focus...), không phát minh kiểu mới.
4. **Điểm neo (anchor)** mỗi nhịp: cho máy/bố cục một điểm ổn định để model bám (vd tay cầm dao của A, điểm tiếp xúc của hai người). Áp sát thì cỡ cảnh siết dần (trung → cận) và ghi rõ ai che ai.
5. **Viết thành lời:** thì hiện tại, câu khẳng định, dày. Dùng **hướng trên màn hình** (from frame left / toward camera / crosses to frame right) để mã hóa bản đồ không gian, vì đó là căn cứ duy nhất để model giữ địa lý. Hành động viết thành **chuỗi nhịp ngắn**, ví dụ: "A bước vào từ trái khung, lưỡi kiếm nâng lên; khi va chạm máy vung vài độ sang phải; cả hai khựng lại, máy giữ yên".
6. Cảnh liền mạch dài quá giới hạn 15 giây (thường ở CHASE/VEHICLE) → cắt thành đoạn, chỗ cắt giấu vào che khuất tự nhiên (mờ chuyển động, bóng tối, khói bụi), hai đầu nối cùng một vật.

## Tự kiểm
- Bỏ chữ, chỉ nhìn hướng trên màn hình: dựng lại được ai ở phía nào không? Không → khóa lại.
- Có nhịp nào bắt cả chủ thể và máy cùng chuyển động lớn? (sẽ nhòe) → chỉ để một bên động.
- Không tự ý đổi cỡ cảnh/góc/kiểu chuyển động đã chọn ở bước đạo diễn; chỉ phục vụ chúng bằng câu chữ.
- Ghi chú phần nào là **suy đoán** (vd dựng lại vị trí khi không có thông tin cảnh trước) để người duyệt biết chỗ cần xem lại.

## Khi chữ vẫn không đủ: dùng video tham chiếu chuyển động thay vì cố viết chi tiết hơn

Đã tự kiểm hết mục trên mà cảnh vẫn phức tạp tới mức không mã hóa được bằng chữ (vd một combo chiêu thức nhân vật nhiều pha, chuyển động đặc thù không có tên gọi quen thuộc) — **đừng cố viết dài hơn**, gợi ý người duyệt cảnh dùng **video tham chiếu chuyển động** thay thế/bổ sung cho phần mô tả hành động:
- Đây là tính năng thật của Clip AI (Kling `video_list`/`refer_type=feature`, Seedance `content[].role=reference_video`), đã lập trình sẵn trong Bước 3 của dashboard này (expander "🎥 Video tham chiếu chuyển động" dưới mỗi motion prompt) — không cần code thêm, chỉ cần người duyệt tải lên 1 clip.
- **Nguyên tắc tách vai trò, LUÔN giữ khi viết prompt cho cảnh có video tham chiếu:** ảnh khung đầu (và Character Bible) quyết định toàn bộ **diện mạo**; video tham chiếu chỉ quyết định **chuyển động/nhịp/lực** — **không được tả lại diện mạo nhân vật trong video đó** vào motion prompt (model có thể lẫn diện mạo nếu prompt mơ tả cả hai). Câu prompt nên viết kiểu: "nhân vật trong ảnh thực hiện đúng chuyển động/nhịp độ như trong video tham chiếu" thay vì diễn giải lại từng động tác bằng chữ.
- Ví dụ cụ thể của dự án: skill chủ động của nhân vật Free Fire (xem `knowledge/ff_character_skills_visual.md`) — dùng video gameplay/showcase thật của skill đó làm tham chiếu chuyển động, thay vì cố diễn tả VFX bằng chữ khi chưa xem video.
- Đây là gợi ý **thay thế cách viết chữ chi tiết hơn**, không phải bước bắt buộc thêm vào — cảnh đơn giản vẫn viết chữ như bình thường.

## Nguyên lý tri giác bổ sung (Kit 2.0.0 — perception-physics)
Quy tắc trục 180° không phải quy ước tùy ý mà là cách não dựng bản đồ không gian; ba nguyên lý hay bị bỏ sót:
- **Hướng nhìn bảo toàn:** hai người đối mặt/đối thoại thì hướng nhìn trên màn hình ngược nhau (A nhìn sang phải khung → B nhìn sang trái) và giữ nguyên qua các shot; ai đột nhiên nhìn sai phía = lỗi không gian.
- **Động lượng và trọng lượng:** người xem đánh giá thật/giả qua dấu hiệu phụ — vật nặng có quán tính (không dừng tức thì), vật bị đánh phản ứng theo khối lượng (nhẹ thì bay, nặng thì nứt), vải/tóc dài trễ sau thân người. Video AI "giả" chủ yếu vì vật chuyển động không có trọng lượng → viết rõ vào đoạn chất liệu.
- **Quán tính của mắt:** chuyển động nhanh có vệt mờ nhẹ; cú quét máy/dừng gấp được phép hơi "quá đà" kiểu cầm tay — chính xác tuyệt đối lại trông như CGI. Đây là chất cảm phụ, **không** phải chuyển động chính thứ hai.
Loại chuyển động mới chưa có trong bảng trên → tự suy ra bằng 3 câu hỏi: (1) người xem dựng bản đồ không gian bằng gì (đường nối, hướng nhìn, hướng di chuyển, trục trọng lực)? (2) dấu hiệu vật lý nào quyết định thật/giả? (3) chỗ nào bị che khuất (điểm cắt, chiều sâu)?
