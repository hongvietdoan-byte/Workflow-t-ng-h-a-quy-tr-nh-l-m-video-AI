# Sổ tay kiểm tra của agent QC (có phiên bản — docs/AGENT_QC_THIET_KE_2026-09-27.md)

Mỗi mục = một loại lỗi ĐÃ ĐƯỢC NGƯỜI XÁC NHẬN ở một dự án thật: dấu hiệu, CÁCH SOI (thao tác cụ thể), mức, sửa gốc. Agent đọc sổ tay mỗi
lần chạy và PHẢI làm đủ các thao tác soi của các mục áp dụng được; lỗi mới được người xác nhận → thêm mục. Loại lỗi ≥ 3 ca và đo được →
chuyển thành bộ đo code (lớp 0).

## A. Nhân vật
### A1. Chi tiết bất đối xứng bị lật gương theo hướng máy — `chặn` (#8: 4 khung)
- Dấu hiệu: trang bị / hình xăm / huy hiệu / vết thương của một bên (vd. găng giáp + huy hiệu vai TRÁI của Kenta) hiện ở bên sai khi nhân
  vật quay lưng hoặc quay nghiêng.
- Cách soi: từ hồ sơ nhân vật lấy các chi tiết có chữ LEFT/RIGHT; ghép DẢI cùng vùng (vai, tay) của mọi khung có nhân vật đó, TÁCH khung
  quay trước và quay sau. **Xét theo BÊN THÂN NGƯỜI, không theo mép khung** (trái/phải dưới đây là theo NGƯỜI XEM ẢNH, so với đường
  giữa thân nhân vật): quay mặt vào máy → tay trái của nhân vật nằm ở nửa ảnh bên PHẢI của đường giữa thân; quay lưng → nằm ở nửa ảnh
  bên TRÁI của đường giữa thân — dù người đứng ở nửa nào của khung. Quay nghiêng / 3/4 / qua vai: nhân vật nhìn về phía trái-khung thì
  bên TRÁI thân (của nhân vật) quay về phía máy, nhìn về phải-khung thì bên PHẢI thân quay về phía máy (#8 28/09: nhãn lượt 1 chặn oan S1·2, S1·3 vì xét "tay ở mép phải khung", thật ra Kenta đứng nửa phải, quay lưng, tay mang
  găng nằm phía trái thân = tay trái = ĐÚNG). Trước khi kết luận: xác định (1) quay trước hay sau (thấy mặt / thấy gáy), (2) ranh giới
  thân người, (3) cánh tay nằm phía nào của thân.
- Sửa gốc: `view_notes` trong hồ sơ chuẩn (câu cho từng hướng nhìn). **Liệt kê MỌI chi tiết một bên**, không chỉ trang bị lớn
  (#8 lượt 2: sau khi có câu cho găng Kenta / mũ Maxim — đúng 4/4 và 5/5 — tab đỏ tay áo trái của Maxim chưa có câu nên vẫn lật 2/5 khung).
- Câu sửa trái/phải đã thua **2 lần ở cùng một bố cục** (#8 S6·2: qua vai từ sau, tay gần giữa khung luôn mang găng) → không lặp câu:
  **đổi bố cục** để chi tiết bất đối xứng ra khỏi khung (qua vai chặt chỉ đầu + khăn), hoặc đổi hướng máy.
- Soi cả khung quay MẶT vào máy — huy hiệu vai dễ lật riêng dù găng đúng bên (#8 S6·5: găng đúng, sao ở vai phải; lượt 1 chỉ chấm nhỏ).
### A2. Phụ kiện đổi chiều khi quay sau lưng — `chặn` (#8: 5 khung — mũ MAXIM)
- Dấu hiệu: mũ đội ngược (khóa cài ở trán) thành đội xuôi (khóa cài ở gáy) ở các khung quay sau.
- Cách soi: dải vùng đầu qua mọi khung có nhân vật; khung quay sau phải thấy lưỡi trai che gáy.
- Sửa gốc: `view_notes.from_behind`.
### A3. Sai người / sai trang phục / sai màu so với ảnh chuẩn — `chặn`
- Cách soi: đặt mặt + thân từng người cạnh ảnh chuẩn; đối chiếu từng nét "bắt buộc giữ" của Lock.
### A4. Găng / băng / phụ kiện nhỏ đổi loại giữa các khung — `nhỏ` (#8: găng hở ngón thay găng kín)
- Cách soi: dải bàn tay qua các khung.

## B. Diễn xuất và hướng
### B1. Hướng nhìn sai so với blocking — `chặn` (#8: 2 khung)
- Dấu hiệu: bảng shot nói "nhìn sang trái về X", mắt nhìn sang phải.
- Cách soi: CẮT SÁT hai mắt (phóng to ≥ 3×), xác định hướng đồng tử; đối chiếu blocking + vị trí người kia ở khung trước.
- Sửa gốc: câu "gaze follows the blocking" + hướng cụ thể trong câu sửa.
### B2. Hướng chạy / hướng di chuyển đảo qua các cú cắt — `nhỏ` (#8 cảnh 2)
- Cách soi: xếp các khung liền nhau của cảnh, đánh dấu hướng di chuyển trên màn hình.
### B3. Hành động không khớp mô tả shot — `chặn` nếu mất nghĩa câu chuyện

## C. Liền mạch
### C1. Hai khung khác shot gần như trùng hình — `chặn` nếu cả hai đều dùng (#8: S1·2 / S1·3)
- Cách soi: đặt các khung liền nhau cạnh nhau; cùng bố cục + cùng tư thế = trùng.
### C2. Vết thương / đạo cụ lệch vị trí giữa các khung liền — `nhỏ` (#8: vết đạn hông ↔ ngực)
### C3. Hồi tưởng không khác hiện tại — `chặn` (#8 S5·3)
- Cách soi: so ánh sáng / màu với khung hiện tại cùng nơi; hồi tưởng phải khác ít nhất 2 tầng (màu + bối cảnh hoặc hạt / mờ); soi cả
  các khung HIỆN TẠI có vô tình cùng tông với hồi tưởng không.
- Sửa gốc: `scene_establish.FLASHBACK` (màu có hiệu quả — lượt 2 đạt; bối cảnh vẫn là quảng trường hiện tại → nhỏ).
### C4. Ánh sáng / giờ nhảy trong cùng một cảnh sau khi vẽ lại — `chặn` (#8 lượt 2: S4·2 thành hoàng hôn giữa trưa)
- Cách soi: dải toàn khung của cảnh cạnh ảnh toàn cảnh; so màu trời, hướng nắng, độ dài bóng.
- Sửa gốc: câu sửa khi vẽ lại luôn kèm câu khóa ánh sáng của cảnh; ứng viên bộ đo code (sắc độ trung bình vùng trời).
- #8 lượt 3: câu "no sunset" rõ ràng vẫn thua — vẽ lại S4·2 hai lần đều hoàng hôn (vùng trời B−R = −29, các khung khác +110…+128).
  Ảnh cha KHÔNG nằm trong tham chiếu (đã kiểm `sent_refs`); cùng một `storyboard_id` + `frame_index` được dùng lại cho mọi lượt vẽ lại
  → nghi phiên storyboard phía nhà cung cấp nhớ các lượt trước. Hướng đổi đầu vào: vẽ lại lỗi ánh sáng trong phiên storyboard MỚI
  (neo khung 1 làm tham chiếu), không lặp câu. Ứng viên lớp 0: vùng trời lệch B−R > 60 so với khung neo cùng cảnh → chặn.
## F. Quy trình
### F1. Sau mỗi lượt vẽ lại, soi lại các khung ĐÃ DUYỆT cùng dải chi tiết bị sửa (#8 lượt 2: đặt cạnh khung đã sửa mới lộ S6·2 mang găng
  ở tay phải — lượt 1 chỉ chấm nhỏ). Luật đã rõ ở một khung là thước đo cho các khung còn lại.

## D. Kỹ thuật hình
### D1. Khung trống / đen / một màu — `chặn` (lớp 0 bắt bằng code)
### D2. Cỡ cảnh sai — lệch ≥ 2 bậc `chặn`, 1 bậc `nhỏ` (lớp 0 đo bằng chiều cao mặt; không áp cho khung chèn cố ý không có mặt)
### D3. Ghép lộ: mảng chữ nhật dán, đường nối thẳng, nhân vật lơ lửng / cụt mép, ánh sáng người ≠ nền — `chặn` (#8 cách ghép phông xanh)
- Cách soi: cắt sát mép người–nền và chân–sàn; tìm cạnh thẳng dài bất thường và mảng khác màu nền.
### D4. Người thừa / người thiếu so với bảng shot — `chặn` (bộ đếm mặt dễ nhầm tay thành mặt → luôn xác minh bằng mắt)

## G. Bối cảnh sai bản đồ thật
### G1. Kiến trúc tự "xây thêm": nhiều tầng tường chắn / bậc thang chồng lên nhau, tháp đứng trên một khối thành cao — `chặn` nếu rõ
  (#8 người dùng 28/09: nền Tháp Đồng Hồ bị xây nhiều lớp cao tầng, không đúng map)
- Sự thật (Kho, ảnh chụp trên cao + bản đồ): tháp đứng NGAY trên quảng trường đá rộng, phẳng; quảng trường tối đa 2 mặt thấp nối bằng vài
  bậc ngắn, tường chắn chỉ cao ngang ngực–đầu người; quanh là nhà 1–2 tầng mái đỏ, cỏ, dừa, biển. KHÔNG có chuỗi bậc thang lên cao, không
  thành lũy.
- Cách soi: gọi `reference("establishing")` rồi xem nền từng khung: đếm số tầng tường / bậc sau lưng nhân vật, so chiều cao tường với
  người (1,7 m), tháp đứng trên quảng trường hay trên đỉnh khối bậc. Ghép dải vùng nền quanh chân tháp qua các khung.
- Nguyên nhân đã biết: ảnh toàn cảnh (nhìn cao) ĐÚNG; khung ngang tầm mắt tự đoán phần sau → nghi ảnh tham chiếu render 3D chụp sát chân
  tháp (bậc lớn, tường cao) + prompt thiếu câu tả bố cục thật. Sửa gốc: câu bố cục trong mô tả địa điểm Kho (vào mọi prompt ảnh); câu sửa
  khi vẽ lại: "flat open stone plaza, the tower stands directly on it, only low retaining walls, no stacked terraces".
- Thử A/B 28/09 (S4·1, S4·3; `docs/qc_agent_2026-09-27/relabel/tower_ab.jpg`): thêm câu bố cục (giữ render) → nền phẳng hẳn, chỉ còn tường thấp;
  bỏ thêm render sát chân tháp → phẳng nhất nhưng tháp bị vẽ thêm MẶT ĐỒNG HỒ (sai dáng tháp game). Nguyên nhân chính = thiếu câu bố
  cục. Soi thêm: dáng tháp (không mặt đồng hồ, chóp nhọn, cửa sổ vòm) so với ảnh chuẩn Kho.

## E. Bảng shot tự mâu thuẫn — không vẽ lại, để người sửa (#8: xin MLS nhưng đòi thấy toàn thân; góc qua vai mà chỉ 1 người)
