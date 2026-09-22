# Dịch skill → hình ảnh: 67 nhân vật Free Fire

Nguồn cơ chế: mô tả kỹ năng chính thức đồng bộ từ ff.garena.com (bảng `assets`, kind=`character`, xem Kho chủ thể trong dashboard). File này **không lặp lại** tiểu sử/lore — chỉ dịch **cơ chế gameplay** (thứ ảnh tĩnh không thể hiện được) thành **mô tả nhìn thấy được**: hành động kích hoạt, hiệu ứng hình ảnh (màu/ánh sáng/hạt), vật lý/chất liệu — đúng khung của `t2v_prompt_structure.md` (đoạn 5 "chủ thể + hành động", đoạn 6 "chất liệu/vật lý") và `seedance_prompting.md` (một sự kiện liên tục, không mô tả lại ngoại hình đã có trong ảnh).

**Cách dùng:** khi viết prompt ảnh (Director) hoặc motion prompt (Bước 3) cho một cảnh có nhân vật đang dùng kỹ năng, copy phần *"Hình ảnh"* của nhân vật đó vào đoạn hành động/chất liệu, giữ nguyên ngoại hình đã chốt trong Character Bible. Đây là suy luận hợp lý từ cơ chế game (không phải ảnh chụp màn hình thật), nên coi là **gợi ý mặc định** — sửa lại nếu người duyệt có ảnh/video tham chiếu chính xác hơn.

**Chính xác hơn nữa (khuyến khích cho skill quan trọng):** thay vì chỉ copy chữ "Hình ảnh" ở dưới, tải luôn video gameplay/showcase thật của skill đó vào ô "🎥 Video tham chiếu chuyển động" ở Bước 3 — model sẽ theo đúng chuyển động thật thay vì suy luận từ mô tả cơ chế. Xem `knowledge/motion_complex_shots.md` mục "Khi chữ vẫn không đủ" để biết cách viết prompt đúng khi có video tham chiếu (không tả lại diện mạo nhân vật trong video đó).

Không xếp: **A PATROA** (khe kỹ năng trống, không có hiệu ứng riêng), **ANDREW thuc tinh** (id 62, chưa có dữ liệu đồng bộ), **Kenta ở OB55** (id 377, placeholder "thông tin update").

## Chủ động vs Bị động — nguồn xác thực, không suy luận

Ban đầu bản nháp đầu tiên của file này suy luận Chủ động/Bị động từ cách hành văn của mô tả kỹ năng (vd thấy chữ "bắn", "ném", "kích hoạt" thì đoán là chủ động) — **cách này sai với 5 nhân vật** (Antonio, Joseph, Kapella, Rin, Rafael: hành văn đọc như chủ động nhưng thực chất là hiệu ứng tự động/bị động). Đã sửa lại bằng cách gọi thẳng API của `wiki.ff.garena.vn` (`POST /api/app/char?lang=vi`, field `isActive`) — đây là dữ liệu game client thật, không phải suy luận.

**24 nhân vật có kỹ năng CHỦ ĐỘNG** (xác nhận `isActive:true`, 22/9/2026): A124, Alok, Chrono, Clu, Dimitri, Homer, Ignis, Iris, K, Kassie, Kenta, Koda, Morse, Nero, Orion, Oscar, Ray, Ryden, Santino, Skyler, Steffie, Tatsuya, Wukong (Ngộ Không), Xayne.

Tất cả 43 nhân vật còn lại (có kỹ năng) là **Bị động** — bao gồm cả những cái dễ đọc nhầm thành chủ động: **Antonio, Joseph, Kapella, Rin, Rafael, Kelly, Jai** (đã sửa lại phần "Hình ảnh" bên dưới cho đúng — bỏ chữ "kích hoạt", chuyển sang mô tả hiệu ứng tự động/thường trực).

## ⚠ Phân biệt "sửa kỹ năng gốc vĩnh viễn" vs "Skill Boost theo sự kiện có thời hạn"

Free Fire có 2 loại thay đổi kỹ năng dễ nhầm lẫn nhau, cả hai đều xuất hiện trong patch note gắn tag `#OBxx`:
1. **Rework vĩnh viễn** (đổi kỹ năng gốc, áp dụng mãi mãi cho tới lần đổi tiếp theo) — ví dụ Kenta ở OB55: đổi hẳn từ "Khiên Thịnh Nộ" sang "Đột Kích Lốc Xoáy", không phải sự kiện.
2. **Skill Boost theo sự kiện** (chỉ có hiệu lực trong thời gian sự kiện của đúng bản OB đó, hết sự kiện thì kỹ năng trở lại bản gốc) — ví dụ Chrono/Homer/Kassie/Oscar/Skyler/Wukong/Alok/Koda ở OB54: đã hết hạn, không còn áp dụng từ OB55 (22/9/2026, thời điểm viết file này).

**Trước khi ghi nhận bất kỳ thay đổi kỹ năng nào tìm được qua patch note/video, phải xác minh nó thuộc loại nào** — nếu không chắc, coi là sự kiện tạm thời và không đưa vào mô tả "Hình ảnh" gốc, chỉ ghi chú riêng kèm ngày hết hạn.

**Trạng thái xác minh bằng video thật** (xem trực tiếp gameplay/showcase thay vì suy luận từ text):
- ✅ Đã xác minh qua video chính thức (skill gốc, còn hiệu lực): **KENTA** (rework vĩnh viễn OB55 — đổi hẳn sang "Đột Kích Lốc Xoáy"), **OSCAR** (dáng lướt gốc, video quay sau OB55).
- ✅ Đã đối chiếu UI trong game xác nhận tag Chủ động: **CHRONO**.
- 📌 Có ghi chú lịch sử Skill Boost OB54 đã hết hạn (không ảnh hưởng mô tả gốc): CHRONO, HOMER, KASSIE, OSCAR, SKYLER, WUKONG, ALOK, KODA.
- ⏳ Chưa xác minh bằng video (mô tả vẫn là suy luận hợp lý từ cơ chế + màu icon, ưu tiên xác minh trước khi dùng cho cảnh quan trọng): A124, Alok, Clu, Dimitri, Homer, Ignis, Iris, K, Kassie, Koda, Morse, Nero, Orion, Ray, Ryden, Santino, Skyler, Steffie, Tatsuya, Wukong, Xayne. Cách làm tiếp: tìm video mới nhất trên kênh chính thức [Garena Free Fire VN](https://www.youtube.com/@GarenaFreeFireVN) (6.16M sub), tìm kèm CẢ tên nhân vật + tên skill (vd "A124 Sức Nóng Chiến Trường") thay vì chỉ tên nhân vật — tỉ lệ ra đúng clip giới thiệu/showcase skill cao hơn nhiều so với chỉ tên riêng (dễ ra video linh tinh/không liên quan skill).
- ✅ **Đối chiếu chéo `isActive` bằng nguồn thứ 2** (2026-09-22): người dùng chia sẻ Google Sheet nội bộ ("Data for Viet Mabu", tab `char_Skill`, cột `isActive` — dữ liệu có vẻ khai thác trực tiếp từ game client, độc lập với API `wiki.ff.garena.vn` đã dùng trước đó) — cả 21 nhân vật trong danh sách "chưa xác minh" trên đều cho `isActive: TRUE` trong sheet này, khớp 100% với kết quả API. Tăng độ tin cậy của việc phân loại Chủ động/Bị động, nhưng **không thay thế** việc xác minh hình ảnh/cơ chế chuyển động bằng video — sheet chỉ có cờ đúng/sai và icon tĩnh (cột `skillImg`, ảnh CDN chính thức), không có mô tả VFX chi tiết hơn ff.garena.com.
- ⚠ **Bài học khi thử xác minh qua video (2026-09-22, thử với A124)**: trình duyệt của Claude chỉ chụp được khung hình tĩnh theo thời gian thực, không tua/seek chính xác được trong video Shorts — xác minh 1 nhân vật tốn ~15+ thao tác mà vẫn có thể lỡ đúng khoảnh khắc kích hoạt kỹ năng. Video 7 năm trước của A124 cũng cho thấy: cùng tên skill "Sức Nóng Chiến Trường" nhưng mô tả cơ chế CŨ (chuyển EP thành máu) khác hẳn cơ chế hiện tại trong kho (EMP vô hiệu hóa kỹ năng) — xác nhận nhân vật có thể bị rework nhưng GIỮ NGUYÊN tên skill, nên **video cũ tìm được chưa chắc phản ánh đúng cơ chế hiện tại**, phải ưu tiên video có ngày gần nhất/nhắc đúng OB hiện hành. Cách hiệu quả hơn đã dùng cho Kenta trước đó: người dùng tự xem video rồi báo lại mô tả cho Claude ghi vào file, thay vì Claude tự mò qua trình duyệt.

**Lưu ý khi tiếp tục xác minh:** không phải nhân vật nào cũng được chỉnh sửa/cập nhật ở OB55 — thực tế trong đợt kiểm tra này chỉ có **Kenta** là rework thật sự ở OB55 (tìm qua search "rework"/"OB55" trên kênh chính thức không ra thêm nhân vật nào khác). Với 21 nhân vật còn lại trong danh sách "chưa xác minh", **không mặc định là họ cũng vừa bị đổi** — cứ tìm video mới nhất có sẵn của nhân vật đó để xem đúng hình dạng/cách vận hành VFX là đủ; nếu video cũ nhất tìm được vẫn khớp với mô tả cơ chế hiện tại trong kho (không có dấu hiệu "rework"/"OB" nào mới hơn), thì coi như hình ảnh đã ổn định, không cần cố tìm video "mới hơn OB55" bằng mọi giá.

---

## A124 — Sức Nóng Chiến Trường [CHỦ ĐỘNG — xác nhận `isActive:true` qua API wiki.ff.garena.vn]
Cơ chế: phóng sóng điện từ vô hiệu hóa kỹ năng đối phương.
Hình ảnh: A124 giơ thẳng một tay, khớp nối cơ khí phát sáng xanh lam dọc cánh tay, một vòng sóng điện từ dạng lưới hình cầu bung ra từ lòng bàn tay, không khí nhiễu như sóng nhiệt, ăng-ten sau lưng đối phương trúng sóng chớp tắt rồi tắt hẳn.

## ALOK — Giai Điệu Sinh Mệnh [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: hồi HP theo thời gian + tăng tốc chạy, tạo vùng hiệu ứng lan cho đồng đội.
Hình ảnh: Alok giậm nhẹ xuống sàn giữ nhịp DJ, một vòng tròn ánh sáng vàng-xanh lá pulse theo bass lan ra từ chân, các nốt nhạc phát sáng bay lơ lửng quanh vòng tròn, ai bước vào vùng sáng thì viền cơ thể ánh lên nhẹ và bước chân nhanh hơn thấy rõ.
**Đã HẾT HẠN — sự kiện OB54:** từng có Skill Boost tạm thời chỉ tăng số liệu (bán kính vùng, %tốc độ, HP/s), không đổi hình ảnh; đã hết cùng sự kiện OB54, không còn liên quan từ OB55.

## ALVARO — Bom Phân Hạch
Cơ chế: tăng sát thương/tầm nổ, lựu đạn tách thành nhiều mảnh sau khi nổ.
Hình ảnh: lựu đạn nổ tạo một quầng lửa cam trung tâm, ngay sau đó tách thành 3-4 mảnh nhỏ hơn văng ra các hướng như pháo hoa vỡ, mỗi mảnh để lại vệt khói cong, bụi và mảnh vụn bắn tung theo trọng lực thật.

## ANDREW — Siêu Áo Giáp
Cơ chế: passive giảm sát thương giáp, mạnh hơn khi có đồng minh gần.
Hình ảnh: khi đồng đội tiến lại gần, lớp giáp của Andrew hiện các đường mạch năng lượng xanh dương mờ dọc bề mặt giáp, sáng rõ dần theo số đồng minh xung quanh; đạn bắn trúng giáp nảy ra kèm tia lửa nhỏ thay vì xuyên qua.

## ANTONIO — Khí Chất Đại Ca [BỊ ĐỘNG — xác nhận `isActive:false` qua API wiki.ff.garena.vn]
Cơ chế: tự động nhận Lá Chắn, tự hồi lại theo thời gian — không có nút kích hoạt riêng.
Hình ảnh: một lớp màng khiên tím-xám dạng lục giác luôn âm ỉ bao quanh thân Antonio kể cả lúc đứng yên, bề mặt khiên gợn sóng rất nhẹ theo nhịp thở; sau khi khiên vỡ vì trúng đòn, các mảnh lục giác tự động từ từ bay ngược trở về ghép liền dần theo thời gian mà không cần thao tác gì.

## CAROLINE — Dẻo Dai
Cơ chế: tăng tốc chạy khi cầm Shotgun.
Hình ảnh: khi rút shotgun lên ngang hông, Caroline bật người lao nhanh về phía trước, tà váy/áo khoác tung theo gió do tốc độ, vệt mờ chuyển động (motion blur) kéo dài phía sau hai chân.

## CHRONO — Hào Quang Hộ Mệnh [CHỦ ĐỘNG — xác nhận qua UI trong game, video chính thức @GarenaFreeFireVN]
Cơ chế: trường lực không thể xuyên phá + tăng tốc di chuyển bên trong. Khiên đứng yên một chỗ tại vị trí kích hoạt (không di chuyển theo người dùng).
Hình ảnh: Chrono giơ hai tay ra trước, một mái vòm trong suốt màu xanh cyan bung ra từ người và đứng cố định tại chỗ, đạn bắn tới bị chặn lại ở bề mặt vòm tạo gợn sóng năng lượng lan tỏa như mặt nước bị ném đá, đồng đội bên trong di chuyển với vệt tốc độ nhẹ quanh chân.
**Đã HẾT HẠN — sự kiện OB54 (đã qua, giờ là OB55, 22/9/2026):** OB54 từng có "Skill Boost" tạm thời cho chọn 1 trong 2 nhánh — "Di động" (khiên bám theo người dùng) hoặc "Xem Chặn Sát Thương" (khiên đứng yên, chặn sát thương nhiều hơn) — nhưng đây là nội dung sự kiện có thời hạn, đã hết. Kỹ năng hiện tại đã trở lại đúng mô tả gốc ở trên (khiên đứng yên).
Nguồn: [video showcase Chrono OB54 (đã hết hạn, chỉ dùng để đối chiếu UI/tag Chủ động), kênh chính thức Garena Free Fire VN](https://www.youtube.com/watch?v=kJbwf2aaCco) — màn hình chọn kỹ năng trong game hiển thị tag "[CHỦ ĐỘNG]" ngay cạnh tên Chrono, xác nhận trực tiếp từ UI thật.

## CLU — Truy Vết [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: xác định vị trí kẻ địch (trừ người đang ngồi/nằm).
Hình ảnh: mắt Clu ánh lên một lớp overlay quét radar mỏng màu cam, các đốm sáng nhỏ hiện lên xuyên qua địa hình đánh dấu vị trí địch đang đứng/di chuyển, đốm sáng mờ dần rồi biến mất nếu địch nằm xuống.

## D BEE — Đạn Xuyên Âm
Cơ chế: tăng tốc di chuyển + độ chính xác khi vừa bắn vừa di chuyển.
Hình ảnh: mỗi phát súng bắn ra kèm một vòng sóng âm mỏng màu tím-hồng lan quanh nòng súng, D Bee vẫn giữ bước chạy nhịp nhàng như đang nhảy, súng gần như không rung khi di chuyển.

## DASHA — Quẩy Lên
Cơ chế: sau khi hạ gục địch, tăng tốc bắn + tốc độ di chuyển.
Hình ảnh: ngay khoảnh khắc địch gục, một vòng năng lượng hồng neon bùng lên quanh Dasha như tiếng bass dội, cô bật người lùi/xoay nhanh hơn, nòng súng khói nhẹ do nhịp bắn dồn dập tăng tốc.

## DIMITRI — Nhịp Điệu Hồi Sinh [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: tạo vùng hồi máu, cho phép tự cứu khi bị hạ gục trong vùng.
Hình ảnh: Dimitri đặt tay xuống một thiết bị âm thanh nhỏ, một vòng tròn ánh sáng xanh lá ngọc lan ra trên mặt đất theo nhịp sóng âm đồng tâm, đồng đội gục trong vùng có các hạt sáng nhỏ bay vào cơ thể như đang hồi phục.

## FORD — Ý Chí Sắt Đá
Cơ chế: hồi máu khi nhận sát thương.
Hình ảnh: mỗi lần trúng đạn, vết thương lóe lên một quầng sáng đỏ cam nhạt rồi mờ dần nhanh như đang tự lành, biểu cảm Ford chỉ gằn người chịu đòn chứ không ngã, hơi thở nặng nhưng vững.

## HAYATO — Xuyên Giáp (Bushido)
Cơ chế: máu càng thấp, xuyên giáp càng cao + giảm sát thương từ phía trước.
Hình ảnh: khi HP giảm, lưỡi kiếm của Hayato bắt đầu ánh đỏ dọc theo cạnh sắc, khí thế người dâng cao thấy qua tư thế gồng vai thấp xuống thủ thế; đòn chém xuyên giáp để lại một vệt cắt đỏ rực ngắn trên không khí theo hướng vung kiếm.

## HOMER — Bom Tầm Xa [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: thả drone tự tìm địch, bay đến và phát nổ.
Hình ảnh: một drone nhỏ hình cầu tách khỏi thắt lưng Homer, đèn báo đỏ nhấp nháy, bay là là mặt đất dò đường rồi tăng tốc thẳng về phía mục tiêu, phát nổ tạo quầng lửa cam nhỏ gọn và mảnh vỡ kim loại văng ra.
**Đã HẾT HẠN — sự kiện OB54 (24/6/2026), không còn áp dụng từ OB55 trở đi:** OB54 từng có "Skill Boost" tạm thời cho Homer (chọn 1 trong 2: quét khu vực hiện hình địch, hoặc drone bay lượn nhanh hơn 15%) nhưng đây là nội dung sự kiện có thời hạn, đã hết khi OB54 kết thúc — kỹ năng hiện tại (OB55, 22/9/2026) đã trở lại đúng mô tả gốc ở trên. Ghi chú lại chỉ để tránh nhầm khi xem video/tài liệu cũ còn nhắc tới Skill Boost này.
Nguồn: [OB54 Patch Notes, ff.garena.com](https://ff.garena.com/en/article/1673/).

## IGNIS — Ảo Ảnh Lửa [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: triệu hồi màn lửa di chuyển về phía trước, sát thương thiêu đốt + phá Bom Keo, tích lũy lần dùng.
Hình ảnh: Ignis vung tay, một bức tường lửa cam-đỏ cao ngang người cuộn trào tiến thẳng về phía trước như sóng nhiệt, gloo wall chạm lửa chảy mềm rồi cháy đen, nhiệt làm không khí phía trước gợn sóng.

## IRIS — Xuyên Tường [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: bắn xuyên Bom Keo, gây sát thương + đánh dấu địch sau tường.
Hình ảnh: viên đạn Iris bắn ra để lại vệt sáng tím ngắn, xuyên thẳng qua bề mặt gloo wall làm lớp keo nứt một lỗ tròn nhỏ phát sáng viền tím, phía sau tường một biểu tượng đánh dấu hiện lên trên người địch trúng đạn.

## J BIEBS — Hỗ Trợ Câm Lặng
Cơ chế: người dùng và đồng minh chặn một phần sát thương bằng EP.
Hình ảnh: khi trúng đạn, một lớp sóng âm mờ màu xanh dương nhạt gợn lên quanh điểm va chạm như tấm khiên âm thanh hấp thụ một phần lực, đồng thời thanh EP phía trên đầu giảm nhẹ thay vì máu.

## JOSEPH — Điên Cuồng (API wiki.ff.garena.vn ghi tên khác: "Chiếc Thìa Bạc", cùng mô tả — chỉ khác bản dịch tên) [BỊ ĐỘNG — xác nhận `isActive:false`]
Cơ chế: tự động miễn nhiễm hiệu ứng khống chế + tăng tốc di chuyển ngay khi trúng hiệu ứng đó, không cần bấm nút.
Hình ảnh: ngay khoảnh khắc một hiệu ứng khống chế (làm chậm/choáng/trói) chạm vào Joseph, nó vỡ tan ngay lập tức như chạm phải một lớp hào quang cam nhạt vô hình bao quanh anh, bước chạy ngay sau đó dồn dập hẳn lên với vệt tốc độ rõ — toàn bộ diễn ra như một phản xạ tự động, không có động tác chuẩn bị.

## JOTA — Đột Kích
Cơ chế: hồi HP nhỏ khi bắn trúng, hồi lớn khi hạ gục.
Hình ảnh: mỗi phát đạn trúng địch bắn ngược một tia sáng đỏ nhạt về phía Jota, chạm ngực anh thì lan thành quầng sáng mờ quanh người trong tích tắc; lúc hạ gục địch, quầng sáng bùng mạnh hơn hẳn rồi tắt.

## Jai — Lên Đạn
Cơ chế: tự động nạp đạn sau khi hạ gục địch hoặc dùng kỹ năng chủ động.
Hình ảnh: ngay khi địch gục, băng đạn của Jai tự trượt ra và một băng mới lách cách gài vào không cần chạm tay, khói nòng súng bốc lên ngắn rồi súng đã sẵn sàng bắn tiếp.

## K — Bậc Thầy [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: tăng EP tối đa, tăng tốc hồi/chuyển hóa EP cho bản thân và đồng minh trong tầm.
Hình ảnh: K đứng tấn thế võ jiu-jitsu, một vòng khí tím nhạt xoáy quanh hai bàn tay theo nhịp thở, đồng đội trong tầm có thanh EP phía trên đầu nhấp nháy sáng nhanh hơn bình thường.

## KAIROS — Phá Giáp
Cơ chế: tự hồi EP khi chưa đầy; đầy EP thì gây thêm sát thương lên Lá Chắn/Giáp.
Hình ảnh: mắt và các đường nứt trên da Kairos rực đỏ-đen dần theo EP tích tụ, khi đầy năng lượng nắm đấm bùng lên một quầng lửa tối màu, cú đấm/đạn chạm khiên địch làm khiên nứt vỡ mạnh hơn bình thường kèm tia lửa đen đỏ.

## KAPELLA — Khúc Cao Trào [BỊ ĐỘNG — xác nhận `isActive:false`; không phải kỹ năng kích hoạt riêng, là luật tự động áp lên phát bắn thường]
Cơ chế: bất kỳ phát súng lục nào của Kapella bắn trúng đồng đội tự động hồi máu thay vì gây sát thương (không cần kích hoạt riêng), hồi nhiều hơn nếu dùng Súng Lục Điện.
Hình ảnh: Kapella chĩa súng lục vào đồng đội và bắn như một phát súng bình thường, nhưng viên đạn phát sáng vàng ấm bay chậm hơn đạn thường như nốt nhạc, chạm người đồng đội thì vỡ thành các hạt sáng nhỏ hòa vào người thay vì để lại vết thương.

## KASSIE — Liên Kết Hồi Phục [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: tạo liên kết hồi máu từ từ với một đồng đội; tái kích hoạt hồi ngay lượng lớn.
Hình ảnh: một sợi dây năng lượng tím-hồng mảnh, lấp lánh như tia điện, nối liền giữa Kassie và đồng đội được chọn, dây rung nhẹ theo nhịp hồi máu; khi tái kích hoạt, dây sáng bùng lên một nhịp mạnh rồi mờ trở lại bình thường.
**Đã HẾT HẠN — sự kiện OB54 (24/6/2026), không còn áp dụng từ OB55 trở đi:** OB54 từng có "Skill Boost" tạm thời cho Kassie (chọn 1 trong 2: hồi thêm HP cho bản thân, hoặc hiệu ứng "Kassie thu nhỏ" đứng sau hai người) nhưng là nội dung sự kiện có thời hạn, đã hết — kỹ năng hiện tại (OB55) đã trở lại đúng mô tả gốc ở trên.
Nguồn: [OB54 Patch Notes, ff.garena.com](https://ff.garena.com/en/article/1673/).

## KELLY — Phát Bắn Tối Thượng / Phát Bắn Gia Tốc (thức tỉnh) [BỊ ĐỘNG — xác nhận `isActive:false`; tự kích hoạt sau khi chạy đủ lâu, không có nút bấm riêng]
Cơ chế: chạy nước rút 4 giây để kích hoạt, phát bắn đầu tiên sau đó gây thêm sát thương.
Hình ảnh: Kelly bứt tốc chạy nước rút, tóc và vệt mờ tốc độ kéo dài phía sau như vận động viên điền kinh; khi dừng lại nâng súng bắn phát đầu, đầu nòng lóe một tia sáng trắng ngắn mạnh hơn phát bắn thường.

## KENTA — ⚠ ĐÃ ĐỔI KỸ NĂNG Ở OB55 (7 ngày trước tính đến 22/9/2026): "Đột Kích Lốc Xoáy" thay cho "Khiên Thịnh Nộ" [CHỦ ĐỘNG — xác nhận `isActive:true` + video chính thức]
**Mô tả cũ trong kho (`Khiên Thịnh Nộ`) đã lỗi thời — đây là bản vá kỹ năng gốc, áp dụng từ OB55 trở đi, không phải sự kiện tạm thời của riêng bản OB đó.** Cơ chế mới: vung kiếm giải phóng một cơn lốc xoáy bay về phía trước, gây sát thương xuyên qua cả Bom Keo.
Hình ảnh (đã xem trực tiếp video showcase): Kenta rút kiếm vung một nhát dứt khoát, một cơn lốc xoáy trắng-xanh dương cuộn tròn dày đặc hạt bụi/mảnh vụn bắn ra ngay trước mũi kiếm và lăn thẳng về phía trước theo mặt đất; khi lốc xuyên trúng Bom Keo, để lại một vệt chém đỏ dài cắt ngang bề mặt tường như vừa bị lưỡi kiếm khổng lồ chém qua, tường không vỡ vụn mà mang vết cắt rõ nét.
Nguồn: [Kenta Rework OB55 - Swordsman's Wrath Skill, kênh chính thức Garena Free Fire VN](https://www.youtube.com/watch?v=BjsCv0MRRrs) — đã xem trực tiếp khung hình 0:16–0:20, không suy luận.

## KLA — Muay Thái
Cơ chế: tăng sát thương nắm đấm.
Hình ảnh: trước mỗi cú đấm/gối, cổ tay và ống chân Kla quấn băng bốc khói nhẹ ma sát, cú va chạm tạo một vòng sóng xung kích tròn mỏng lan ra từ điểm tiếp xúc, đối phương giật bật lùi rõ rệt hơn bình thường.

## KODA — Mắt Thần [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: phát hiện địch qua tường + tăng tốc di chuyển; phát hiện địch khi nhảy dù.
Hình ảnh: mắt Koda ánh lên một lớp quét màu xanh lá nhạt, các bóng địch phía sau vật cản hiện dạng viền sáng mờ xuyên qua tường như tia X, bước chạy có vệt tốc độ nhẹ theo sau gót chân.
**Đã HẾT HẠN — sự kiện OB54:** từng có Skill Boost tạm thời gắn thêm "dấu ấn" (imprint) tích lũy tới 3 lần khi phát hiện địch; đã hết cùng sự kiện OB54, không còn liên quan từ OB55.

## LAURA — Siêu Xạ Thủ
Cơ chế: tăng độ chính xác khi ngắm qua ống ngắm.
Hình ảnh: khi Laura ghé mắt vào ống ngắm, hình ảnh qua kính hoàn toàn tĩnh không rung dù cơ thể vẫn thở nhẹ, một dấu chấm đỏ nhỏ hội tụ ổn định ngay lập tức lên mục tiêu thay vì lắc lư ban đầu.

## LEON — Ghi Điểm Phút Chót
Cơ chế: hồi máu sau khi rời khỏi giao tranh.
Hình ảnh: khi Leon lùi ra xa khỏi tầm bắn, đôi chân sinh học cơ khí của anh phát sáng cam nhạt dọc khớp nối, các vết thương trên người mờ dần với một lớp ánh sáng cam mỏng lan qua như đèn hồi phục.

## LILA — Đạn Băng Giá
Cơ chế: làm chậm địch trúng đạn súng trường/súng trường tầm xa; nhận thêm Bom Keo.
Hình ảnh: viên đạn bay ra để lại vệt hơi lạnh trắng xanh ngắn, chạm vào địch thì đóng một lớp băng mỏng nứt rạn quanh chân khiến bước chạy của địch khựng lại rõ rệt, hơi lạnh bốc lên từ điểm trúng đạn.

## LUNA — Chiến Hay Chạy
Cơ chế: tăng tốc độ bắn; bắn trúng địch thì chuyển hóa tốc độ bắn thành tốc độ di chuyển.
Hình ảnh: nòng súng Luna rung nhịp nhanh dần theo tốc bắn tăng, ngay khi đạn trúng địch một luồng năng lượng đỏ cam ngắn chạy ngược từ nòng súng về chân cô, bước chân bất ngờ nhanh hẳn lên như được đẩy tới.

## LUQUETA — Hat Trick
Cơ chế: tăng Lá Chắn tối đa vĩnh viễn mỗi lần hạ gục.
Hình ảnh: ngay khi địch gục, một quả bóng năng lượng vàng-xanh lá nhỏ (như quả bóng đá thu nhỏ) bay từ hướng địch về ngực Luqueta và tan vào lớp khiên, khiên quanh người dày/sáng rõ hơn một nấc sau mỗi lần.

## MARO — Ưng Tiễn
Cơ chế: tăng sát thương theo khoảng cách và với địch bị đánh dấu.
Hình ảnh: khi ngắm bắn xa, một vệt lông vũ mờ ảo hình chim ưng lướt theo quỹ đạo viên đạn; địch trúng đạn ở khoảng cách xa bị đánh dấu bằng một biểu tượng móng vuốt mảnh phát sáng phía trên đầu.

## MAXIM — Ham Ăn
Cơ chế: dùng cứu thương nhanh hơn.
Hình ảnh: động tác băng bó/tiêm thuốc của Maxim dứt khoát và nhanh gọn hơn hẳn, tay đưa vật phẩm cứu thương vào cơ thể với chuyển động rút gọn, một quầng sáng trắng nhạt chớp nhanh quanh vết thương báo hiệu hồi máu tức thì.

## MIGUEL — Kẻ Cuồng Sát
Cơ chế: nhận EP khi hạ gục địch.
Hình ảnh: khi địch gục, một tia năng lượng vàng nhạt bắn từ hướng địch bay thẳng vào ngực Miguel, thanh EP phía trên đầu anh nhảy vọt lên kèm một nhịp sáng ngắn.

## MISHA — Bùng Nổ
Cơ chế: khi lái xe, giảm khả năng bị bắn trúng + nhận hiệu ứng.
Hình ảnh: khi Misha cầm lái, chiếc xe rung nhẹ theo nhịp tăng tốc, một luồng khí động lực mờ bao quanh thân xe như đang lướt nhanh hơn thực tế, đạn bắn tới sượt qua thân xe với vệt tóe lửa thay vì trúng thẳng.

## MOCO — Mắt Công Nghệ
Cơ chế: đánh dấu địch bị bắn trúng, thời gian đánh dấu dài hơn nếu địch di chuyển (thức tỉnh).
Hình ảnh: viên đạn của Moco chạm địch để lại một icon quét radar nhỏ màu cam trên đầu mục tiêu, icon xoay tròn chậm theo hướng địch di chuyển và mờ dần rồi biến mất khi hết hiệu lực.

## MORSE — Tàng Hình [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: kích hoạt tàng hình, khó bị phát hiện nhưng không thể bắn.
Hình ảnh: cơ thể Morse mờ dần thành trong suốt như hơi nước tan, chỉ còn viền ánh sáng rất nhạt lay động theo bước chân; lúc rút súng định bắn, hiệu ứng tàng hình vỡ ra như kính rạn và cơ thể hiện rõ trở lại ngay.

## NAIRI — Keo Bất Tử
Cơ chế: Bom Keo hồi độ bền + hồi máu cho đồng đội gần trong thời gian ngắn.
Hình ảnh: gloo wall Nairi đặt xuống phát một quầng sáng xanh dương nhạt lan tỏa quanh chân tường, các vết nứt trên tường tự liền lại có thể thấy rõ, đồng đội đứng gần có các hạt sáng nhỏ bay vào người.

## NERO — Khóa Keo [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: ném Gấu Bông gây sát thương, tạo vùng cấm dùng Bom Keo.
Hình ảnh: một con gấu bông đồ chơi bay ra theo vòng cung, phát nổ thành một quầng khói tím đen mỏng phủ xuống mặt đất; bất kỳ gloo wall nào cố dựng trong vùng khói tan rã ngay khi vừa hiện hình.

## NIKITA — Chuyên Gia Vũ Khí
Cơ chế: tăng tốc thay đạn + giảm khả năng hồi máu của địch bị bắn trúng.
Hình ảnh: động tác thay băng đạn của Nikita gọn và nhanh bất thường, gần như một nhịp liên tục không giật cục; viên đạn trúng địch để lại một vệt đỏ sẫm mỏng quanh vết thương báo hiệu hồi máu bị chặn.

## NOTORA — Phước Lành Đường Đua
Cơ chế: hồi máu cho bản thân và đồng đội khi ở trong xe.
Hình ảnh: khi Notora cầm lái, một quầng sáng cam ấm tỏa nhẹ từ vô-lăng/tay lái lan ra khắp khoang xe, hành khách trong xe có ánh sáng mỏng thoáng qua người theo nhịp hồi máu.

## OLIVIA — Hồi Phục
Cơ chế: tăng lượng hồi máu và lan tỏa hiệu ứng hồi máu.
Hình ảnh: bàn tay Olivia chạm nhẹ lên vết thương phát ra một quầng sáng vàng ấm mềm mại lan rộng hơn bình thường, quầng sáng đó tràn thêm sang đồng đội đứng sát cạnh như sóng lan trên mặt nước.

## ORION — Bất Tử [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: miễn nhiễm sát thương + hút máu địch khi kích hoạt.
Hình ảnh: cơ thể Orion bọc trong một lớp giáp đỏ sẫm phát sáng rực khi kích hoạt, đạn bắn tới nảy bật ra không để lại dấu vết; mỗi cú đấm trúng địch kéo theo một vệt máu-năng lượng đỏ mỏng bay ngược về phía Orion.

## OSCAR — Tiến Công [CHỦ ĐỘNG — xác nhận `isActive:true` + video showcase chính thức đối chiếu, xem "Kenta vs Tatsuya vs Oscar" bên dưới]
Cơ chế: lướt về phía trước, phá Bom Keo trên đường đi, gây sát thương/đẩy lùi khi va chạm.
Hình ảnh: Oscar khom người lao thẳng về phía trước với vệt mờ tốc độ tím-đen kéo dài sau lưng như bóng đêm, gloo wall chắn đường vỡ vụn ngay khi anh xuyên qua, địch va chạm bị hất văng ngược theo hướng lao tới.
**Đã HẾT HẠN — sự kiện OB54 (24/6/2026), không còn áp dụng từ OB55 trở đi:** OB54 từng có "Skill Boost" tạm thời cho Oscar (chọn 1 trong 2: triệu hồi "bóng ma" tăng tầm lướt, hoặc lướt dài 8s nhưng chậm hơn) nhưng là nội dung sự kiện có thời hạn, đã hết — kỹ năng hiện tại (OB55) đã trở lại đúng mô tả gốc ở trên.
Nguồn: [OB54 Patch Notes, ff.garena.com](https://ff.garena.com/en/article/1673/); dáng lướt gốc đã đối chiếu qua video ["How does the reworked Kenta compare to Tatsuya and Oscar?"](https://www.youtube.com/watch?v=lSBSVfUVJkE), kênh chính thức Garena Free Fire VN — video này quay sau OB55 nên là dáng lướt hiện hành, đáng tin cậy.

## OTHO — Vén Màn Bí Ẩn
Cơ chế: sau khi hạ gục/bị hạ gục, đánh dấu + làm chậm địch quanh người bị hạ.
Hình ảnh: ngay khoảnh khắc một người gục xuống, một vòng sóng xám nhạt lan tỏa từ vị trí đó ra xung quanh, địch trong vòng sóng bị gắn icon đánh dấu nhỏ trên đầu và bước chân chậm lại thấy rõ.

## PALOMA — Bậc Thầy Vũ Khí
Cơ chế: tăng độ chính xác sau khi phá Bom Keo.
Hình ảnh: ngay khi gloo wall trước mặt Paloma vỡ tan, súng trên tay cô ổn định lại tức thì, tâm ngắm thu hẹp nhanh về một điểm duy nhất thay vì dao động như trước.

## RAFAEL — Câm Lặng [BỊ ĐỘNG — xác nhận `isActive:false`; hiệu ứng vũ khí thường trực, không cần kích hoạt]
Cơ chế: súng ngắm/súng trường tầm xa của Rafael luôn có sẵn hiệu ứng giảm thanh; địch bị hạ gục mất máu nhanh hơn.
Hình ảnh: đầu nòng súng Rafael đã gắn sẵn một lớp giảm thanh phát sáng mờ suốt trận, phát bắn ra gần như không có tia lửa đầu nòng và không tiếng nổ lớn; địch trúng đạn chí mạng có một vệt đỏ sẫm lan nhanh bất thường quanh vết thương.

## RIN — Bão Kunai [BỊ ĐỘNG — xác nhận `isActive:false`; hiệu ứng tự động khi bắn trúng, không phải nút bấm riêng]
Cơ chế: khi Rin bắn trúng địch hoặc Bom Keo, tự động triệu hồi thêm kunai bay tới cùng mục tiêu đó, gây thêm sát thương lớn lên Bom Keo — không cần kích hoạt.
Hình ảnh: ngay khoảnh khắc đạn của Rin chạm mục tiêu, từ sau lưng cô một loạt kunai bạc lấp lánh tự tách ra bay xoáy theo cùng quỹ đạo tới đúng điểm va chạm đó như một cơn lốc kim loại đi kèm, kunai cắm vào gloo wall làm bề mặt tường nứt toác nhanh.

## RYDEN — Cạm Bẫy Nhện Độc [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: thả nhện gây nổ làm chậm địch bị phát hiện, tích trữ nhiều lần dùng.
Hình ảnh: Ryden thả một con nhện cơ khí nhỏ có mắt đỏ nhấp nháy bò nhanh trên mặt đất về hướng mục tiêu, khi tới gần nó phát nổ thành một quầng khí tím phun ra khiến chân địch trong vùng dính chất nhờn làm chậm bước.

## Ray — Phán Quyết [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: liên kết với địch phía trước, hạ gục ngay nếu địch còn ít HP; thành công thì hồi HP + reset hồi chiêu.
Hình ảnh: một sợi chỉ ánh sáng trắng-bạc mảnh phóng ra từ tay Ray nối thẳng tới địch phía trước, nếu chạm trúng khi địch yếu, sợi chỉ siết chặt lại trong chớp mắt kéo địch gục xuống; đồng thời một quầng sáng ấm ngắn bao quanh Ray báo hiệu hồi máu.

## SANTINO — Dịch Chuyển Nhân Dạng [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: tạo hình nhân tự di chuyển, có thể đổi vị trí với nó; địch phá hình nhân sẽ bị đánh dấu.
Hình ảnh: một bản sao mờ ảo lấp lánh như vải lụa của Santino tách ra và tự bước đi độc lập; khi kích hoạt đổi chỗ, cả hai thân hình xoẹt qua nhau như tráo bài rồi hoán đổi vị trí tức thì, hình nhân vỡ ra thành các mảnh vải ánh sáng nếu bị phá.

## SHANI — Giáp Vĩnh Cửu
Cơ chế: khi dùng kỹ năng chủ động, cấp lá chắn cho bản thân và đồng đội gần.
Hình ảnh: Shani gõ nhanh vào một thiết bị phế liệu đeo trên tay, các mảnh kim loại vụn quanh đó bay lên tự lắp ráp thành lớp khiên mỏng bọc quanh cô và đồng đội gần, bề mặt khiên có vân hàn thô ráp thay vì trơn bóng công nghệ cao.

## SHIROU — Ăn Miếng Trả Miếng
Cơ chế: đánh dấu đối phương gây sát thương lên người dùng.
Hình ảnh: ngay khi Shirou trúng đạn, kẻ vừa bắn anh hiện lên một icon dấu chân/mũi tên đỏ mảnh phía trên đầu, đánh dấu đó theo dõi hướng di chuyển của kẻ địch đó.

## SKYLER — Hủy Diệt Băng Thành [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: bắn luồng sóng năng lượng gây sát thương lớn lên Bom Keo.
Hình ảnh: Skyler giơ tay theo động tác vũ đạo, một luồng sóng âm hình quạt màu tím-hồng lan ra từ lòng bàn tay như đang biểu diễn, luồng sóng chạm gloo wall làm bề mặt tường rung nứt rồi vỡ vụn theo từng lớp.
**Đã HẾT HẠN — sự kiện OB54 (24/6/2026), không còn áp dụng từ OB55 trở đi:** OB54 từng có "Skill Boost" tạm thời cho Skyler (chọn 1 trong 2: vùng năng lượng tự khóa địch gần nhất, hoặc tự động quét/bắn mọi Bom Keo trong 75m) nhưng là nội dung sự kiện có thời hạn, đã hết — kỹ năng hiện tại (OB55) đã trở lại đúng mô tả gốc ở trên.
Nguồn: [OB54 Patch Notes, ff.garena.com](https://ff.garena.com/en/article/1673/).

## SONIA — Khiên Hồi Sinh
Cơ chế: sau khi nhận sát thương chí mạng, nhận lá chắn công nghệ; hạ gục khi khiên hết hiệu lực.
Hình ảnh: ngay lúc sắp gục, một lớp khiên nano dạng lưới tinh thể xanh dương bao trọn cơ thể Sonia bật lên tức thì như đóng băng thời gian trong khoảnh khắc, lớp khiên rạn dần theo thời gian còn lại rồi vỡ tan hoàn toàn khi hết hiệu lực.

## STEFFIE — Không Gian Sắc Màu [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: tạo khu vực chặn ném lựu đạn các loại; đồng minh trong khu vực nhận hiệu ứng phòng thủ.
Hình ảnh: Steffie xịt một vòng tròn graffiti neon nhiều màu lên mặt đất, viền vòng tròn phát sáng rực rỡ như sơn ướt dưới đèn UV; lựu đạn bay vào vùng bị chặn lại nảy bật ra ngoài như chạm vào một mặt kính vô hình.

## SUZY — Thợ Săn Tiền Thưởng
Cơ chế: hạ gục địch bị đánh dấu (bất kỳ ai trong đội) nhận thêm tiền thưởng.
Hình ảnh: khi Suzy đánh dấu mục tiêu, một biểu tượng đồng tiền vàng nhỏ hiện lên trên đầu địch đó; lúc mục tiêu gục, biểu tượng vỡ ra thành các đồng xu ánh sáng bay về phía người vừa hạ gục.

## TATSUYA — Tốc Hành Tức Thời [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: lướt nhanh về phía trước, hồi chiêu ngay nếu hạ gục địch.
Hình ảnh: Tatsuya bật người lao vọt về phía trước với vệt mờ tốc độ kéo dài, giày ma sát để lại vệt khói mờ trên mặt đất; nếu cú lướt hạ gục địch, một tia sáng ngắn lóe quanh người báo hiệu kỹ năng đã sẵn sàng lại ngay.

## THIVA — Giai Điệu Sinh Tồn
Cơ chế: cứu đồng đội bị gục nhanh hơn + hồi máu cho họ sau khi cứu.
Hình ảnh: động tác đỡ đồng đội gục của Thiva nhanh và dứt khoát hơn bình thường, khi kéo đồng đội dậy một nốt nhạc ánh sáng nhỏ tỏa ra lan khắp người họ như luồng sinh khí trở lại.

## WOLFRAHH — Livestream
Cơ chế: tăng sát thương bắn vào đầu địch, giảm sát thương nhận vào đầu bản thân.
Hình ảnh: khi ngắm bắn vào đầu, khung ngắm của Wolfrahh có một vòng nhấn mạnh đỏ nhẹ quanh điểm ngắm như đèn stream; mũ/mặt của anh có một lớp giáp mờ gần như trong suốt hấp thụ bớt lực khi bị bắn vào đầu.

## WUKONG — Ảo Ảnh [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: biến hình thành bụi cây; hồi chiêu ngay khi hạ gục đối phương.
Hình ảnh: cơ thể cơ khí-hữu cơ của Wukong tan biến thành các mảnh lá và cành cây xoáy quanh người trước khi định hình lại thành một bụi cây tĩnh, chỉ còn ánh mắt le lói ẩn trong tán lá; lúc hạ gục địch trong lúc ẩn nấp, bụi cây rung nhẹ và một tia sáng ngắn báo hồi chiêu.
**Đã HẾT HẠN — sự kiện OB54 (24/6/2026), không còn áp dụng từ OB55 trở đi:** OB54 từng có "Skill Boost" tạm thời cho Wukong (chọn 1 trong 2: để lại Wukong giả tự di chuyển, hoặc tạo thêm 2 bụi cây giả) nhưng là nội dung sự kiện có thời hạn, đã hết — kỹ năng hiện tại (OB55) đã trở lại đúng mô tả gốc ở trên.
Nguồn: [OB54 Patch Notes, ff.garena.com](https://ff.garena.com/en/article/1673/).

## XAYNE — Cuồng Bạo [CHỦ ĐỘNG — xác nhận `isActive:true`]
Cơ chế: nhận Lá Chắn tạm thời; hạ gục trong thời gian hiệu lực hồi lại Lá Chắn.
Hình ảnh: một lớp khiên năng lượng cam-vàng dạng tia sét mỏng bao quanh cơ thể Xayne khi kích hoạt, rung lên theo mỗi nhịp thở gấp gáp của cô; mỗi lần hạ gục địch trong lúc khiên còn hiệu lực, khiên lóe sáng bùng lên dày hơn một nhịp.

---

## Ghi chú khi áp dụng vào prompt
- Không lặp lại mô tả ngoại hình/trang phục đã chốt trong Character Bible — chỉ thêm phần "Hình ảnh" ở trên vào đoạn hành động/chất liệu.
- Theo nguyên tắc "một sự kiện liên tục" của `seedance_prompting.md`: nếu cảnh 4–5 giây, chỉ chọn **một khoảnh khắc** trong mô tả trên (vd lúc kích hoạt, hoặc lúc hiệu ứng chạm mục tiêu) — không nhồi cả chuỗi kích hoạt → duy trì → kết thúc vào một prompt ngắn.
- Màu/ánh sáng liệt kê ở đây là suy luận có căn cứ từ tên kỹ năng và hiệu ứng UI trong game (icon, aura), dùng làm mặc định nhất quán giữa các cảnh của cùng một nhân vật; nếu dự án có ảnh/video gameplay tham chiếu của kỹ năng đó, ưu tiên tham chiếu thật hơn mô tả ở đây.
- Nhân vật có bản Thức Tỉnh (awaken) chỉ liệt kê hiệu ứng của kỹ năng chính đang hoạt động trong game hiện tại, không tách riêng hai bộ hình ảnh.
