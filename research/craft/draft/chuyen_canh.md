# Kho kỹ thuật — Chuyển động máy & Chuyển cảnh (draft S0.11, 2026-09-29)

> **Kiểm duyệt của phiên chính (2026-09-29) — BẢN NHÁP, CHƯA vào `knowledge/`:**
> - Nhiều mục ghi nguồn là **trang chủ** (theasc.com, rogerdeakins.com) hoặc "tóm tắt qua tìm kiếm", không phải bài cụ thể đã đọc trọn →
>   theo phương pháp mục 3, độ tin của các mục đó tạm hạ xuống **vừa** cho tới khi đọc bài gốc (có tên bài, người nói, đoạn liên quan).
> - Nguồn đọc được trọn / xác minh link: DGA — Dan Attias; ProVideo Coalition — Murch; Designing Sound — Randy Thom; VFX Voice; Team Deakins
>   (trang podcast). Một số trang chặn tải tự động (Frame.io, A Sound Effect, LBBOnline, No Film School, British Cinematographer) — cần mở
>   bằng trình duyệt ở lượt đọc kỹ.
> - Đã sửa: chuyển cảnh che máy có thể sinh trong 1 lần (clip mẫu 2:20,6) — không khẳng định "model không tự làm"; số 2,4 lần là mức chuyển
>   động so với #8; ví dụ *Locked* chưa xác minh.
> - Việc kế: lượt đọc kỹ nguồn gốc (thay trích dẫn chung bằng bài cụ thể) + ví dụ có mốc giây từ S0.12, mới đưa vào `knowledge/craft/`.


> Draft chờ duyệt. Lưu ý riêng đã chốt: **chuyển cảnh che (hidden cut) được thiết kế TRONG chuyển động** — vật/người đi ngang ống kính, máy
> lia theo vật, hoặc máy tiến vào vật cho đến khi che kín khung — không phải "chèn một cận cảnh vật ngẫu nhiên" ở điểm nối.

### Lia máy theo chủ thể (pan/tilt theo chuyển động)
- Cách làm: máy xoay ngang/dọc bám theo một chủ thể đang di chuyển, tốc độ lia khớp tốc độ chủ thể.
- Có thể phục vụ: ý đồ A — giữ chủ thể luôn trong khung để khán giả không rời mắt (theo dõi hành động) · ý đồ B — dùng chính vật/người đang
  di chuyển để che máy khi cần đổi bối cảnh — khi vật che gần hết khung, cắt sang cảnh mới, chủ thể "kéo" khán giả qua điểm nối mà không
  thấy cắt · ý đồ C — hé lộ không gian dần dần (chủ thể là cái cớ để máy khám phá bối cảnh xung quanh).
- Khi hợp / khi không: hợp khi có chuyển động thật để bám; không hợp khi chủ thể đứng yên — lia không chủ thể dễ thành "máy tự trôi" vô
  nghĩa.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12 (đối chiếu MV_NARRATIVE đã ghi "chuyển cảnh trong clip" ở `research/ff_styles`).
- Với video AI: mô tả rõ vận tốc tương đối máy–chủ thể ("camera pans to follow subject at walking pace") và, nếu muốn dùng làm chuyển cảnh
  che, mô tả rõ khoảnh khắc vật che gần hết khung hình trong cùng 1 shot rồi cắt sang shot sau bắt đầu từ trạng thái đã che — làm được theo 2 cách:
  trong một lần sinh (Seedance nhiều shot trong 1 clip — clip mẫu ClipAI 2:20,6–2:21 có đường máy nối liền hai không gian), hoặc 2 shot
  riêng (shot trước kết ở khung bị che, shot sau mở ra từ khung che) rồi nối ở khâu dựng.
- Nguồn: [chưa đọc bài gốc] American Cinematographer — bài về long take (chỉ thấy qua kết quả tìm kiếm), theasc.com, đọc 2026-09-29, cao; đối chiếu định nghĩa
  "cutting on action" — Wikipedia, đọc 2026-09-29, vừa.

### Máy tiến vào vật che khung (push-in to object / whip through)
- Cách làm: máy tiến (dolly-in/zoom-in) về phía một vật gần ống kính cho đến khi vật che kín khung hình, sau đó cắt sang shot khác cũng bắt
  đầu từ trạng thái bị che rồi lùi/mở ra.
- Có thể phục vụ: ý đồ A — chuyển cảnh liền mạch giữa hai không gian/thời điểm khác nhau mà không lộ điểm cắt (hidden cut kinh điển) · ý đồ
  B — tăng nhịp gấp gáp (dùng nhiều lần liên tiếp để dồn tốc độ, thường ở cao trào hành động hoặc MV) · điều kiện bắt buộc: vật che phải có
  mặt trong không gian cảnh một cách hợp lý (cột, người đi ngang, cửa) — không phải vật bất kỳ chèn vào chỉ để che.
- Khi hợp / khi không: hợp khi hai cảnh cần nối liền cảm giác thời gian trôi liên tục; không hợp nếu vật che xuất hiện phi lý (khán giả
  nhận ra đó là "thủ thuật" thay vì một phần tự nhiên của không gian).
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: [suy luận, chưa thử] khó sinh trọn trong 1 lần; cách chắc hơn là 2 shot riêng (shot A kết thúc = khung đen/che
  hoàn toàn bởi vật cụ thể, shot B bắt đầu = cùng trạng thái che rồi mở ra) rồi ghép ở khâu dựng, có thể thử 1 lần sinh nhiều shot trước (xem mục lia máy).
- Nguồn: Wikipedia "Cutting on action" (định nghĩa kỹ thuật), đọc 2026-09-29, vừa; suy luận cách áp dụng cho AI video là của dự án (ghi rõ
  đây là suy luận, chưa có nguồn chuyên gia nói riêng về AI).

### Long take / cú máy dài không cắt
- Cách làm: một shot kéo dài, máy có thể di chuyển qua nhiều không gian, không cắt.
- Có thể phục vụ: ý đồ A — giữ khán giả trong "thời gian thực" của cảnh, tăng căng thẳng liên tục (không cho nghỉ bằng cách cắt) · ý đồ B —
  phô diễn không gian dàn dựng phức tạp (một cảnh nhiều tầng lớp hành động) · ý đồ C — gắn khán giả vào góc nhìn chủ quan gần như liên tục
  của một nhân vật xuyên nhiều khu vực.
- Khi hợp / khi không: hợp khi cảnh có đủ nội dung hành động/kịch tính để "nuôi" toàn bộ thời lượng không cắt; không hợp khi nội dung mỏng —
  long take vô nghĩa sẽ lộ ra là phô kỹ thuật.
- Ví dụ: [chưa xác minh] tìm kiếm nhắc cú máy dài ~3 phút trong xe SUV của phim *Locked* (DP Michael Dallatorre, American Cinematographer) —
  chưa đọc bài gốc, chưa rõ chi tiết; không dùng làm căn cứ cho tới khi đọc.
- Với video AI: giới hạn lớn nhất hiện tại — hầu hết model video AI sinh clip ngắn (vài giây đến ~30s ở Seedance 2.5); "long take" thực tế
  cho pipeline phải ghép nhiều lần sinh có tính liên tục (giữ nhân vật/bối cảnh nhất quán) + dựng nối bằng chính kỹ thuật che khung ở trên,
  không phải sinh 1 lần dài.
- Nguồn: American Cinematographer, theasc.com, đọc 2026-09-29, cao (tóm tắt thứ cấp, chưa đọc trọn bài gốc).

### Video tham chiếu động tác khó (motion reference)
- Cách làm: quay/dùng video tham chiếu một chuyển động phức tạp (vũ đạo, võ thuật, chuyển động vải) để làm khuôn cho AI hoặc diễn viên thật
  học theo.
- Có thể phục vụ: ý đồ A — khi động tác đòi hỏi kỹ thuật cơ thể khó (breakdance, đội hình nhảy nhóm đồng bộ) mà chỉ đạo bằng lời không đủ
  chính xác — reference là công cụ bổ sung cho chỉ đạo, KHÔNG thay thế việc đạo diễn giải thích tình huống/động cơ · ý đồ B — giữ nhất quán
  một chuyển động đặc trưng lặp lại nhiều lần (một điệu bộ nhận diện nhân vật) qua nhiều cảnh/nhiều lần sinh AI.
- Khi hợp / khi không: hợp khi động tác vượt khả năng diễn đạt bằng mô tả lời (kỹ thuật cơ thể cao) — **không phải mặc định cho mọi diễn
  xuất tốt**; diễn xuất thường (biểu cảm, tương tác) nên đến từ chỉ đạo diễn xuất (xem `chi_dao_dien_xuat.md`), không cần video mẫu.
- Ví dụ: đã ghi trong `knowledge/ff_styles/MV_NARRATIVE.md` + `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md` (S0.9, người dùng chọn lọc) — breakdance, chuyển động vải váy, nhảy nhóm đồng bộ;
  mức chuyển động trung bình của clip gấp ~2,4 lần #8 (đo). Việc họ có dùng video tham chiếu vũ đạo hay không là [suy luận], chưa có bằng chứng.
- Với video AI: ClipAI cho phép tối đa 10 video tham chiếu (@Video) trong chế độ Reference/Transform (Update Log 09/2026); dùng khi
  đã xác định rõ động tác khó, không dùng tràn lan.
- Nguồn: dự án tự phân tích clip mẫu ClipAI (đã có trong `knowledge/ff_styles/MV_NARRATIVE.md` + `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md`), đọc lại 2026-09-29, cao (quan sát trực tiếp
  của người dùng + dự án).

### Chuyển cảnh cắt cứng đúng nhịp (hard cut on rhythm)
- Cách làm: cắt trực tiếp không hiệu ứng, điểm cắt canh đúng một mốc nhịp bên ngoài (phách nhạc, nhịp bước chân, nhịp thở).
- Có thể phục vụ: ý đồ A — tạo cảm giác đồng bộ, "đóng đinh" khoảnh khắc (thường ở MV, cao trào hành động) · ý đồ B — nếu cố ý cắt LỆCH nhịp
  một chút, tạo cảm giác khó chịu/bất ổn có chủ đích (không phải lỗi) — vẫn là "theo nhịp" nhưng nhịp bị phá vỡ có lý do kịch bản.
- Khi hợp / khi không: hợp khi có nhịp ngoài rõ ràng để bám (nhạc, hành động lặp lại đều); MV không bắt buộc "1 câu = 1 shot" hay luôn cắt
  theo phách — nhiều editor MV trộn cắt theo câu hát rồi mới nhấn phách ở đoạn cao trào, để tránh cảm giác đoán trước được.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: nhịp cắt là việc của khâu dựng (ghép các clip đã sinh), không phải việc của model sinh video — cần lên kế hoạch độ dài mỗi
  shot theo nhịp nhạc TRƯỚC khi gọi model, để mỗi clip sinh ra đúng độ dài cần khi ghép.
- Nguồn: LBBOnline — biên tập MV, lbbonline.com, đọc 2026-09-29, vừa.
