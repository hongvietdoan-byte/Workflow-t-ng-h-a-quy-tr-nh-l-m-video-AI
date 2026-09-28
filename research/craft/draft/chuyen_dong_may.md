# Chuyển động máy — đối chiếu thuật ngữ người dùng với nguồn (draft, 2026-09-29)

> Theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 3. Đây là **draft chờ duyệt**, chưa nhập vào `knowledge/video_motion_vocab.md` hay
> `knowledge/roles/dp.md`. Đọc ngày **2026-09-29** qua WebSearch/WebFetch (không dùng trình duyệt — agent khác đang dùng); phần lớn là
> **tóm tắt qua tìm kiếm**, không phải đọc trọn văn — độ tin ghi rõ theo từng dòng, hạ xuống **vừa** khi chỉ có trích dẫn/snippet.
> Nguồn đọc được (WebFetch) trọn trang: Runway "AI Camera Prompts", Kling "AI Camera Control Guide", Luma "Camera Concepts",
> Higgsfield "Camera Controls", StudioBinder "Camera Movements in Film". Không fetch được: ClipAI docs (403 — chặn tải tự động, như
> NGUON.md đã ghi cho clipai.ingarena.net), Runway Academy Gen-3 trang cũ (404, có thể đã đổi URL), trang chi tiết Volcengine Ark
> (yêu cầu đăng nhập console) — các phần này dùng lại vốn đã kiểm ở `knowledge/roles/dp.md` Q5 ([Q8][Q9][Q15][Q16] — Seedance/Kling
> official) làm căn cứ nội bộ, có đối chiếu thêm bằng tóm tắt bên thứ ba (độ tin thấp–vừa, ghi rõ).

## 1. Vì sao viết tài liệu này

Người dùng gửi hai danh sách để xác minh: (1) một bảng chú giải 10 thuật ngữ chuyển động máy cơ bản, (2) một ảnh "15 Camera Movements
for AI Video" (dạng infographic công cụ AI video, gần giống bộ preset Higgsfield). Mục đích: xác nhận chỗ đúng, chỗ cần chính xác hơn,
chỗ mơ hồ, đối chiếu với (a) nguồn nghề quay phim có tên tuổi/tổ chức nghề, (b) tài liệu chính thức các công cụ video AI — vì pipeline
này cuối cùng phải viết chuyển động thành **chữ trong prompt** cho model hiểu, không phải vận hành máy thật.

**Lưu ý đọc bảng dưới:** "camera move không có nghĩa cố định" — cùng một chuyển động phục vụ được nhiều ý đồ khác nhau tùy ngữ cảnh
(đúng nguyên tắc đã ghi ở `dp.md` Q5); bảng chỉ liệt kê **các khả năng thường gặp kèm điều kiện**, không phải bảng tra "chuyển động X =
ý nghĩa Y".

## 2. Bảng đối chiếu nhanh — thuật ngữ người dùng gửi → kết luận

| Thuật ngữ người dùng | Kết luận | Giải thích ngắn | Nguồn |
|---|---|---|---|
| **Static** | Đúng | Máy hoàn toàn không di chuyển — khớp mọi nguồn. | StudioBinder [S6]; Luma "static" [S4] |
| **Pan** | Đúng, nên nói rõ hơn | Máy **xoay tại chỗ** theo trục ngang (trục thẳng đứng đi qua chân máy) — không phải máy *di chuyển* trái/phải (đó là truck). "Rotate horizontally" của người dùng đúng nhưng nên thêm "camera stays in place" để tránh lẫn với truck. | StudioBinder, Runway [S1][S6]; Kling gọi trục này là "pan" tách riêng khỏi "horizontal" (dịch chuyển) [S3] |
| **Tilt** | Đúng | Máy xoay tại chỗ theo trục ngang (trục nằm ngang) — khớp mọi nguồn, không có gì cần sửa. | StudioBinder, Runway, Kling [S1][S3][S6] |
| **Zoom** | Đúng nhưng thiếu phần quan trọng nhất | "Change focal length" đúng, nhưng thiếu điểm khác biệt cốt lõi với dolly: zoom **không đổi vị trí máy** → không có parallax, phối cảnh không đổi, chỉ phóng to/thu nhỏ khung như cắt ảnh. Đây là chỗ hay bị nhầm với dolly nhất. | StudioBinder "no physical camera movement" [S6]; Runway [S1] |
| **Dolly / Push & Pull** | Đúng | "Whole camera body moves toward/away" đúng — đây là điểm phân biệt với zoom (có parallax thật, nền dịch chuyển theo chiều sâu). | StudioBinder, Runway, Kling (dolly forward/backward) [S1][S3][S6] |
| **Tracking / Truck** | **Cần chính xác hơn — hai khái niệm khác nhau, không nên gộp** | Đây là chỗ sai/mơ hồ rõ nhất trong bảng người dùng gửi. *Truck* = máy trượt **ngang** (trái/phải), vuông góc với hướng ống kính — dùng để hé lộ không gian hai bên. *Tracking* là **thuật ngữ ô** cho mọi chuyển động máy bám theo chủ thể, có thể là tiến/lùi, ngang, hoặc chéo — không chỉ "chạy dọc theo". Nói "tracking = truck" chỉ đúng trong trường hợp riêng khi bám chủ thể theo phương ngang. | Beverly Boy "tracking vs trucking" [S9]; Runway tách hai mục "Truck left/right" và không liệt "tracking" như một trục riêng — dùng "dolly/pan/tilt/truck/pedestal/orbit/arc/crane" làm bộ trục cơ bản [S1]; Boords/MasterClass coi tracking là umbrella term [S10] |
| **Arc** | Đúng nhưng cần phân biệt với Orbit | "Circle around the subject" — đúng về hình dạng đường đi, nhưng chính xác hơn: **arc là đường cong quanh chủ thể, không nhất thiết đi hết vòng tròn** (khác orbit — đi trọn 360°). Người dùng gộp "circle" vào định nghĩa arc là hơi rộng. | Runway: "Arc: camera travels a curved path around the subject **without completing a circle**"; "Orbit: camera circles the subject **completely**" [S1] |
| **Roll** | Đúng | "Rotate around the lens axis" đúng, khớp mọi nguồn (kể cả Kling, Luma dùng đúng tên "roll"). Nên phân biệt với **dutch angle** (xem mục riêng — dutch là *kết quả tĩnh* của một roll, không phải bản thân roll). | StudioBinder, Kling, Luma [S3][S4][S6] |
| **Pedestal** | Đúng | "Elevator — straight up/down" đúng: cả thân máy đi thẳng lên/xuống, **ống kính vẫn ngang bằng** không đổi góc (khác tilt). | StudioBinder, Luma (có mục riêng "pedestal" và "elevator" — hai khái niệm gần nhau) [S4][S6] |
| **Boom** | Đúng nhưng dễ lẫn với Pedestal/Crane | "Raise/lower with a wide crane arm" đúng — khác pedestal ở chỗ boom dùng **cần cẩu (arm)** nên đường đi có thể cong/vòng cung khi nâng, không chỉ thẳng đứng; boom/crane/jib thường được dùng thay nhau trong nguồn phổ thông, không có ranh giới cứng. | StudioBinder gộp Boom/Crane/Jib vào một nhóm [S6]; MasterClass, Videomaker tương tự [từ tìm kiếm chung] |

**Nhận xét chung:** Bảng người dùng gửi **đúng phần lớn về cơ chế vật lý** (cái gì di chuyển). Hai chỗ cần sửa/làm rõ nhất: (1)
**tracking ≠ truck** — gộp chung là điểm sai đáng chú ý nhất; (2) **zoom vs dolly** thiếu phần "vì sao khác nhau" (parallax) — quan
trọng nhất khi viết prompt AI vì model hay lẫn hai lệnh này.

## 3. Chi tiết từng chuyển động (18 mục cơ bản + bản đồ 15 preset)

Mỗi mục: **Vật lý** (cái gì di chuyển) · **Trên khung hình** (phối cảnh/parallax đổi thế nào) · **Vài ý đồ có thể (kèm điều kiện —
không cố định)** · **Viết trong prompt AI thế nào** (tiếng Anh, theo cách tài liệu chính thức dùng) · **Giới hạn model đã biết**.

### Static (khoá máy / locked-off)
- **Vật lý:** không có bộ phận nào của máy di chuyển.
- **Trên khung hình:** khung hình cố định tuyệt đối; chỉ chủ thể/môi trường trong khung chuyển động.
- **Ý đồ có thể:** A — khách quan, để khán giả tự quan sát, không bị dẫn dắt (hợp cảnh cần cảm giác "thật", tài liệu) · B — tương phản
  với chuỗi cảnh có nhiều chuyển động trước đó, đánh dấu một khoảnh khắc "đứng lại" (im lặng, chờ đợi, sốc) · C — giữ nhận diện nhân vật
  ổn định cho AI (lý do kỹ thuật, không phải lý do kể chuyện) — xem "Giới hạn model".
- **Viết trong prompt AI:** tài liệu Runway khuyên nói **khẳng định** ("locked camera", "static shot") thay vì phủ định ("no
  movement") vì model hiểu câu khẳng định tốt hơn; nếu bị cắt cảnh ngoài ý muốn thì thêm "continuous, seamless shot" [S1] — khớp với
  điều `dp.md` Q5 đã ghi từ trước.
- **Giới hạn model:** dữ liệu chạy thật của dự án (FF, CSDL 2026-09-25): `static` là lựa chọn an toàn nhất cho shot cần nhận diện nhân
  vật chính xác (19/nhiều clip duyệt) — nhưng ngay cả clip tĩnh cũng có thể tự chèn cảnh lạ ở đầu/cuối (ghi ở `dp.md` Q5, không phải
  nguồn ngoài — nêu lại để đối chiếu).
- **Nguồn:** StudioBinder [S6] · Runway [S1] · Luma "static" concept [S4].

### Pan (trái/phải)
- **Vật lý:** máy xoay quanh trục thẳng đứng tại một điểm cố định (chân máy/tripod không di chuyển).
- **Trên khung hình:** quét ngang cảnh, không đổi khoảng cách tới chủ thể → không có parallax kiểu dolly, hơi "phẳng" hơn truck.
- **Ý đồ có thể:** A — nối hai điểm quan tâm trong cùng không gian (ai đang nói → ai đang nghe) · B — hé lộ dần không gian rộng theo
  chiều ngang (thiết lập bối cảnh) · C — theo dõi chủ thể di chuyển ngang qua khung ở khoảng cách không đổi.
- **Viết trong prompt AI:** "pan left/right" — cả Kling và Seedance dùng đúng từ này làm nhãn riêng [S3]; nên kèm tốc độ ("slow pan
  right") và biên độ góc nếu cần kiểm soát chặt (Seedance 1.5 dùng công thức điểm đầu → chuyển động → biên độ → điểm cuối, đã ghi ở
  `dp.md` Q5).
- **Giới hạn model:** pan nhanh (whip pan) dễ gây biến dạng khung/nhân vật hơn pan chậm — xem mục Whip pan riêng.
- **Nguồn:** StudioBinder, Runway, Kling [S1][S3][S6].

### Tilt (lên/xuống)
- **Vật lý:** máy xoay quanh trục ngang tại một điểm cố định.
- **Trên khung hình:** quét dọc cảnh (thấp → cao hoặc ngược lại), không đổi khoảng cách.
- **Ý đồ có thể:** A — hé lộ theo chiều cao (từ chân lên đầu nhân vật, hoặc từ nhân vật lên một công trình để nhấn quy mô) · B — dẫn mắt
  theo hành động dọc (ai đó ngã, ai đó nhìn lên trời) · C — mở đầu/kết một cảnh bằng cách tách khỏi một chi tiết rồi lộ toàn cảnh.
- **Viết trong prompt AI:** "tilt up/down"; Seedance liệt "tilt up" trong bộ từ vựng đã kiểm [S3] và `dp.md` Q5 (`[Q8][Q9]`).
- **Giới hạn model:** tilt kết hợp với nhân vật đứng gần khung hẹp (dọc 9:16) dễ làm mất phần đầu/chân khỏi khung nếu biên độ lớn — nên
  test biên độ nhỏ trước.
- **Nguồn:** StudioBinder, Runway, Kling [S1][S3][S6].

### Zoom
- **Vật lý:** đổi tiêu cự ống kính; **máy không di chuyển** — khác biệt cốt lõi so với dolly.
- **Trên khung hình:** phóng to/thu nhỏ toàn khung như cắt ảnh, **không có parallax** — các lớp cảnh (tiền/hậu cảnh) giữ nguyên tỉ lệ
  tương đối với nhau, khác hẳn dolly (lớp gần dịch chuyển nhanh hơn lớp xa).
- **Ý đồ có thể:** A — nhấn nhanh một chi tiết (cảnh giật gân, hài) — thường "rẻ"/kém tinh tế hơn dolly nên ít dùng trong phim nghiêm
  túc · B — crash zoom cho hiệu ứng sốc/giật/cường điệu (hành động, hài, MV) · C — zoom rất chậm gần như không nhận ra, dùng thay dolly
  khi không gian không cho phép di chuyển máy thật.
- **Viết trong prompt AI:** "zoom in/out"; Runway resource khuyến cáo phân biệt rõ với "push in" trong lời prompt vì hai lệnh cho kết
  quả thị giác khác nhau dù nghe giống nhau [S1][S6].
- **Giới hạn model:** vì model video AI không "biết" khái niệm ống kính vật lý, nó suy luận zoom từ ví dụ huấn luyện — dễ lẫn với dolly
  nếu prompt không nói rõ "no perspective shift" hay "camera stays in place, lens zooms"; nên mô tả **hiệu ứng nhìn thấy được** (nền có
  đổi phối cảnh hay không) thay vì chỉ ghi từ "zoom" (nguyên tắc đã có ở `dp.md` Q2 cho ống kính, áp dụng tương tự ở đây).
- **Nguồn:** StudioBinder [S6] · Runway [S1] · Kling liệt "zoom" là 1 trong 6 trục cơ bản [S3].

### Dolly / Push in / Pull out
- **Vật lý:** toàn bộ thân máy di chuyển tiến/lùi theo trục ống kính (trên track, xe đẩy, hoặc tay).
- **Trên khung hình:** có **parallax thật** — lớp cảnh gần dịch chuyển nhanh hơn lớp xa, phối cảnh đổi liên tục; đây là điểm khác zoom.
- **Ý đồ có thể:** A — đẩy vào chậm (push-in) thường kéo người xem lại gần cảm xúc nhân vật, hoặc đánh dấu khoảnh khắc nhận ra điều gì
  đó (đã ghi ở `dp.md` Q5, dẫn ASC [Q20]) · B — lùi ra (pull-out) thường tiết lộ thêm không gian/thông tin, hoặc tạo cảm giác buông/bỏ
  lại · C — cả hai **không cố định nghĩa** — đẩy vào cũng có thể tạo cảm giác đe dọa/xâm lấn tùy tốc độ và chủ thể.
- **Viết trong prompt AI:** Kling dùng "dolly forward/backward" [S3]; Seedance dùng "slow push-in / pull out" là cụm đã kiểm trong tài
  liệu chính thức [S3][S8][S9] theo `dp.md` Q5. Nên luôn kèm tốc độ.
- **Giới hạn model:** dữ liệu chạy thật FF: push_in cùng lúc nhân vật bước tới từng gây lỗi "nhân vật đi tại chỗ" (job 206, ghi ở
  `dp.md` Q5) — vì model phải giải hai chuyển động cùng lúc (máy + chân) → nên tách: hoặc máy đẩy + nhân vật đứng yên, hoặc máy tĩnh +
  nhân vật đi.
- **Nguồn:** StudioBinder, Runway, Kling [S1][S3][S6]; `dp.md` Q5 (dữ liệu nội bộ, không phải nguồn ngoài).

### Truck (trucking)
- **Vật lý:** toàn bộ thân máy trượt **ngang** (trái/phải), vuông góc với hướng ống kính.
- **Trên khung hình:** có parallax ngang — nền trôi ngang qua khung theo lớp chiều sâu; khác pan (pan không đổi vị trí máy nên không có
  parallax kiểu này).
- **Ý đồ có thể:** A — hé lộ không gian/bối cảnh hai bên khi chủ thể đứng yên hoặc đi ngang · B — theo một hàng người/vật đang di
  chuyển ngang (diễu hành, xe cộ) · C — tạo cảm giác "lướt qua" một chuỗi khung cảnh (dùng trong montage).
- **Viết trong prompt AI:** "truck left/right" — Runway và Luma đều dùng đúng từ "truck" làm nhãn riêng [S1][S4]; nên phân biệt rõ với
  "track" trong prompt tiếng Anh vì hai từ dễ gõ nhầm nhau.
- **Giới hạn model:** hiện MOVES của pipeline (`core/reference_analysis.py`) **không có** `truck` như giá trị riêng — xem mục 4.
- **Nguồn:** Runway [S1] · Luma [S4] · StudioBinder [S6] · Beverly Boy (tracking vs trucking) [S9].

### Tracking / Follow (thuật ngữ ô)
- **Vật lý:** **không phải một chuyển động vật lý duy nhất** — là tên gọi chung cho mọi kiểu máy bám theo chủ thể đang di chuyển (có
  thể thực hiện bằng dolly, truck, steadicam, gimbal, hoặc kết hợp).
- **Trên khung hình:** chủ thể giữ vị trí tương đối ổn định trong khung trong khi nền trôi qua.
- **Ý đồ có thể:** A — giữ khán giả "đi cùng" nhân vật, tăng cảm giác nhập vai/thân mật · B — duy trì cỡ cảnh ổn định khi chủ thể di
  chuyển (thực dụng, không cần hàm ý cảm xúc) · C — track dài liên tục (long take) để giữ căng thẳng không bị cắt.
- **Viết trong prompt AI:** "track", "follow", "smooth lateral tracking" — Seedance dùng "follow", "smooth lateral tracking" trong bộ
  từ vựng đã kiểm [S3] theo `dp.md` Q5.
- **Giới hạn model:** dữ liệu FF: `track` là chuyển động dùng nhiều thứ nhì (8 clip duyệt) nhưng từng gây lỗi "áo choàng đổi màu nhấp
  nháy" ở MS (job 197, `dp.md` Q5) — nhân vật di chuyển + máy cũng di chuyển là tổ hợp khó cho model giữ nhất quán trang phục/màu sắc.
- **Nguồn:** Beverly Boy [S9] · Boords/MasterClass (umbrella term) [S10] · Seedance vocab qua `dp.md` Q5.

### Arc
- **Vật lý:** máy di chuyển theo đường **cong** quanh chủ thể, **không đi hết một vòng tròn**.
- **Trên khung hình:** góc nhìn chủ thể đổi dần, nền phía sau chủ thể thay đổi liên tục trong khi chủ thể giữ vị trí gần trung tâm.
- **Ý đồ có thể:** A — hé lộ thêm một phía của chủ thể/bối cảnh mà góc tĩnh không thấy được · B — tạo nhịp động nhẹ cho cảnh đối thoại
  đứng yên (thay đổi góc nhìn mà không cắt cảnh) · C — nhấn một khoảnh khắc quan trọng bằng chuyển động bao quanh nhẹ.
- **Viết trong prompt AI:** "camera arcs around [subject]" — nên ghi rõ biên độ góc ("arcs 30° clockwise") vì "arc" một mình dễ bị model
  hiểu thành orbit trọn vòng.
- **Giới hạn model:** `dp.md` Q5 ghi arc "không có giá trị `camera_move` riêng" trong pipeline hiện tại — gần nhất map vào `orbit`,
  ghi chuyển động thật trong `why` để Motion viết đúng chữ.
- **Nguồn:** Runway (định nghĩa arc vs orbit) [S1] · StudioBinder [S6].

### Orbit
- **Vật lý:** máy di chuyển theo đường tròn **trọn vòng** quanh chủ thể (hoặc gần trọn).
- **Trên khung hình:** chủ thể luôn ở trung tâm trong khi toàn bộ nền quay quanh nó — hiệu ứng mạnh hơn arc nhiều.
- **Ý đồ có thể:** A — khoe/giới thiệu chủ thể (giới thiệu nhân vật, sản phẩm, công trình — "hero shot") · B — nhấn một khoảnh khắc cao
  trào bằng chuyển động bao trọn, thường kết hợp slow-motion (bullet-time-adjacent) · C — mất phương hướng có chủ đích (hoảng loạn, say).
- **Viết trong prompt AI:** "orbit around [subject]", hoặc preset "360 Orbit"/"AerialOrbit" ở các tool AI — Higgsfield có cả "Arc
  Left/Right" và "360 Orbit" như hai preset riêng, khớp đúng phân biệt arc/orbit ở trên [S5]; Luma có concept "Orbit left/right" riêng
  [S4].
- **Giới hạn model:** orbit trọn vòng là chuyển động phức tạp nhất cho model video AI hiện nay (đổi góc nhìn 360° buộc model "bịa" ra
  phần chưa từng thấy của chủ thể/bối cảnh) — rủi ro biến dạng cao nhất trong nhóm 18 mục này; nên test đoạn ngắn/biên độ nhỏ trước.
- **Nguồn:** Runway [S1] · Higgsfield [S5] · Luma [S4].

### Roll (xoay trục ống kính)
- **Vật lý:** máy xoay quanh trục của chính ống kính (như nghiêng đầu sang một bên).
- **Trên khung hình:** đường chân trời nghiêng dần hoặc đột ngột; toàn khung xoay, không phải nội dung trong khung xoay.
- **Ý đồ có thể:** A — chuyển tiếp/transition kiểu xoay giữa hai cảnh · B — cường điệu mất phương hướng/choáng váng khi roll nhanh · C —
  hiệu ứng "che máy" cho chuyển cảnh liền mạch (roll tới góc bị che rồi cắt).
- **Viết trong prompt AI:** "camera roll", "camera rolls clockwise/counter-clockwise" — Kling liệt "roll" là 1 trong 6 trục cơ bản
  [S3]; Luma có concept "Roll left/right" riêng [S4].
- **Giới hạn model:** dễ nhầm với **dutch angle** trong mô tả bằng lời — xem mục kế; roll là *chuyển động*, dutch là *trạng thái tĩnh*
  đã nghiêng sẵn từ đầu khung.
- **Nguồn:** Kling [S3] · Luma [S4] · StudioBinder [S6].

### Dutch angle / Canted angle (đối chiếu với Roll, không phải chuyển động)
- **Vật lý:** khung hình được nghiêng **cố định** ngay từ đầu (không phải quá trình xoay) — có thể đạt được bằng cách roll máy rồi giữ
  nguyên, khác với "roll" là quá trình đang xoay.
- **Trên khung hình:** đường chân trời nghiêng suốt cảnh (tĩnh hoặc trong lúc di chuyển khác).
- **Ý đồ có thể:** A — bất ổn, mất cân bằng, hỗn loạn (thường dùng cho phản diện, cảnh bạo lực — đã ghi ở `dp.md` Q1) · B — góc nhìn
  chủ quan của nhân vật đang chóng mặt/say/bị thương.
- **Viết trong prompt AI:** "dutch angle", "canted frame, camera tilted 15° to the left" — cần ghi rõ số độ nếu muốn kiểm soát mức
  nghiêng; đây là **góc máy** (một thuộc tính của khung hình), không phải `camera_move`.
- **Giới hạn model:** ít dữ liệu chạy thật của dự án cho mục này — cần thêm ví dụ ở S0.12.
- **Nguồn:** StudioBinder/nguồn giáo dục chung [tìm kiếm]; đối chiếu khái niệm với `dp.md` Q1 (góc máy).

### Pedestal
- **Vật lý:** toàn bộ thân máy đi thẳng lên/xuống, **ống kính giữ nguyên góc ngang** (khác tilt — tilt chỉ xoay ống kính, không đổi độ
  cao thân máy).
- **Trên khung hình:** khung hình dịch chuyển lên/xuống như "thang máy", các lớp cảnh giữ song song với nhau (không có hiệu ứng nghiêng
  góc như tilt).
- **Ý đồ có thể:** A — điều chỉnh độ cao khung hình mượt trong khi vẫn giữ góc nhìn ngang (kỹ thuật, ít hàm ý cảm xúc riêng) · B — dùng
  chậm để thay đổi tầm mắt khán giả từ ngang bằng chủ thể sang nhìn xuống/lên nhẹ mà không "lật" góc như tilt.
- **Viết trong prompt AI:** "pedestal up/down" — Luma dùng đúng tên "pedestal" (và một concept gần là "elevator") [S4]; StudioBinder
  cũng dùng "pedestal shot" riêng [S6].
- **Giới hạn model:** không có giá trị `camera_move` riêng trong pipeline hiện tại — xem mục 4.
- **Nguồn:** Luma [S4] · StudioBinder [S6].

### Boom / Crane / Jib
- **Vật lý:** máy gắn trên cần cẩu (crane/jib), nâng/hạ theo đường có thể **cong** (khác pedestal — pedestal đi thẳng đứng); nhiều
  nguồn phổ thông dùng ba từ boom/crane/jib gần như thay nhau, không có ranh giới thuật ngữ cứng.
- **Trên khung hình:** đổi độ cao khung hình kèm khả năng đổi cả góc nhìn (vì cần cẩu xoay được), thường dùng để mở ra không gian rộng.
- **Ý đồ có thể:** A — mở đầu/kết thiết lập không gian hùng vĩ (trailer, cảnh sử thi — đã ghi ở `video_motion_vocab.md` mục thể loại
  "Hùng vĩ/trailer game") · B — chuyển cảnh mượt từ không gian rộng xuống cận cảnh nhân vật (hoặc ngược lại) trong một cú máy liên tục.
- **Viết trong prompt AI:** "the camera cranes up/down"; ví dụ đã ghi trong `dp.md` Q5 nhóm G-MV5: "camera cranes up through the
  chandelier, then descends to…" cho chuyển cảnh sinh trong 1 lần gọi model.
- **Giới hạn model:** phức tạp (đổi cả độ cao lẫn góc) → theo nguyên tắc "một chuyển động chính mỗi shot" (Seedance 2.0, `dp.md` Q5),
  nên tách crane thành chuyển động chính, không cộng thêm pan/tilt cùng lúc trừ khi test riêng trước.
- **Nguồn:** StudioBinder [S6] · Luma (crane up/down) [S4] · `dp.md` Q5 (ví dụ nội bộ).

### Dolly zoom (Vertigo effect)
- **Vật lý:** dolly và zoom diễn ra **đồng thời, ngược hướng** — máy tiến/lùi trong khi ống kính zoom ra/vào theo chiều ngược lại, giữ
  kích thước chủ thể không đổi trên khung.
- **Trên khung hình:** kích thước chủ thể không đổi nhưng **nền phía sau đổi kích thước liên tục** (phồng ra hoặc nén lại) — đây là
  hiệu ứng méo phối cảnh đặc trưng, không có ở bất kỳ chuyển động nào khác trong danh sách này.
- **Ý đồ có thể:** A — khoảnh khắc "chợt nhận ra/sốc" (đã ghi ở `dp.md` Q5, dẫn ASC [Q20]) · B — cảm giác chóng mặt/mất phương hướng
  (nguồn gốc: hiệu ứng "Vertigo" của Hitchcock).
- **Viết trong prompt AI:** "dolly zoom", "vertigo effect" — Seedance liệt "dolly zoom" trong bộ từ vựng đã kiểm [S3][S8][S9] theo
  `dp.md` Q5; Higgsfield có preset riêng "Dolly Zoom In/Out" [S5]; Luma có concept "dolly_zoom" [S4].
- **Giới hạn model:** đây là chuyển động khó nhất để mô tả chỉ bằng chữ vì nó đòi hỏi model hiểu quan hệ nghịch giữa hai tham số cùng
  lúc — nên coi là thử nghiệm rủi ro cao, không dùng cho shot cần độ tin cậy.
- **Nguồn:** Wikipedia "Dolly zoom" (định nghĩa cơ chế — nguồn hỗ trợ) [S8] · Seedance/Kling qua `dp.md` Q5 · Higgsfield [S5] · Luma [S4].

### Whip pan (Swish pan)
- **Vật lý:** pan cực nhanh, đủ nhanh để hình bị nhòe/mờ chuyển động.
- **Trên khung hình:** một vệt nhòe ngang nối hai khung hình, gần như một kiểu chuyển cảnh trong-shot.
- **Ý đồ có thể:** A — chuyển tiếp năng lượng cao giữa hai điểm nhìn (hành động, hài) · B — dùng thay cho cắt cảnh cứng để giữ cảm giác
  liên tục, che một điểm nối dựng.
- **Viết trong prompt AI:** "whip pan" — Runway ghi rõ "very fast pan that smears the frame into motion blur" [S1]; Higgsfield có
  preset riêng "Whip Pan" [S5].
- **Giới hạn model:** chuyển động rất nhanh dễ gây lỗi hình (nhấp nháy, biến dạng) — nhóm rủi ro cao tương tự orbit/dolly zoom, nên
  test ngắn trước.
- **Nguồn:** Runway [S1] · Higgsfield [S5].

### Handheld
- **Vật lý:** máy cầm tay, không ổn định hoàn toàn — rung nhẹ tự nhiên theo nhịp thở/bước chân người quay.
- **Trên khung hình:** rung nhẹ ngẫu nhiên, khung không hoàn toàn cố định ngay cả khi "đứng yên".
- **Ý đồ có thể:** A — cảm giác đời thực/tài liệu, chủ quan (đã ghi ở `video_motion_vocab.md` cho thể loại hành động) · B — tăng căng
  thẳng/hỗn loạn trong cảnh hành động.
- **Viết trong prompt AI:** "handheld camera, subtle natural shake" — Runway: "subtle natural shake, slightly imperfect framing" [S1].
- **Giới hạn model:** dữ liệu FF: `handheld` từng gây lỗi nặng nhất trong nhóm đã đo (MS job 198 — nhận diện nhân vật rơi xuống 0,20,
  ghi ở `dp.md` Q5) — rung ngẫu nhiên làm model khó giữ nhận diện khuôn mặt ổn định giữa các khung hình.
- **Nguồn:** Runway [S1] · `dp.md` Q5 (dữ liệu nội bộ).

### Steadicam / Gimbal
- **Vật lý:** máy cầm tay nhưng có bộ ổn định cơ/điện tử — chuyển động mượt theo người quay đi lại, không rung như handheld.
- **Trên khung hình:** mượt như dolly nhưng linh hoạt hơn (đi qua địa hình, cầu thang, cửa hẹp mà dolly không tới được).
- **Ý đồ có thể:** A — theo nhân vật đi/nói liên tục mà vẫn giữ cảm giác điện ảnh mượt (khác hẳn cảm giác "thô" của handheld) — đã ghi ở
  `dp.md` Q5 · B — long take phức tạp qua nhiều không gian.
- **Viết trong prompt AI:** "steadicam", "smooth gimbal, steady motion" — Runway: "stabilized handheld, smooth while walking" [S1];
  Kling liệt "stabilizer" trong bộ từ vựng đã kiểm [S3] theo `dp.md` Q5.
- **Giới hạn model:** cần phân biệt rõ với handheld trong prompt (từ "smooth"/"stabilized" quan trọng) — nếu không model có thể áp
  rung như handheld.
- **Nguồn:** Runway [S1] · Kling qua `dp.md` Q5.

### Aerial / Drone
- **Vật lý:** máy gắn trên thiết bị bay (flycam/drone), di chuyển tự do trong không gian 3 chiều, không bị giới hạn bởi mặt đất/ray.
- **Trên khung hình:** góc nhìn cao, có thể kết hợp tiến/lùi/orbit/pull-away trong cùng một cú máy.
- **Ý đồ có thể:** A — thiết lập bối cảnh quy mô lớn (địa hình, thành phố, công trình) · B — pull-away kết ở cuối cảnh/phim để "thoát"
  khỏi câu chuyện, tạo khoảng cách cảm xúc.
- **Viết trong prompt AI:** "aerial drone shot", "the camera pulls away and rises" — Higgsfield có preset "FPV Drone" và "Aerial
  Pullback" [S5]; Luma có concept "aerial", "aerial drone" riêng [S4].
- **Giới hạn model:** không có giá trị `camera_move` riêng trong pipeline hiện tại — xem mục 4; cảnh có nền 3D dựng sẵn (tháp FF) cần
  kiểm máy ảo (`plate_camera`) có hỗ trợ góc/độ cao kiểu drone hay không trước khi hứa hẹn với Đạo diễn.
- **Nguồn:** Higgsfield [S5] · Luma [S4].

## 4. Bản đồ 15 preset trong ảnh người dùng gửi → chuyển động cơ bản ở mục 3

| Preset trong ảnh | Chuyển động cơ bản tương ứng | Ghi chú |
|---|---|---|
| AerialOrbit | Aerial + Orbit (kết hợp) | Higgsfield không có đúng tên "AerialOrbit" nhưng có "360 Orbit" + các preset gắn nhãn "Aerial…" riêng — khớp về khái niệm, tên preset trong ảnh khả năng do bên tổng hợp/infographic đặt lại, không phải tên gốc |
| ArcShot | Arc | Higgsfield: "Arc Left/Right" [S5] |
| DronePullAway | Aerial + Pull out | Higgsfield: "Aerial Pullback" [S5] |
| TruckLeft | Truck | Runway, Luma đều có "Truck left/right" [S1][S4] |
| CameraRoll | Roll | Kling, Luma đều có "Roll" [S3][S4] |
| PanRight | Pan | mọi nguồn |
| CraneDown | Boom/Crane | Higgsfield: "Crane Down" [S5]; Luma: "Crane up/down" [S4] |
| DollyZoom | Dolly zoom | mọi nguồn AI đều có preset riêng |
| TiltUp | Tilt | mọi nguồn |
| DollyIn | Dolly / Push in | mọi nguồn |
| OverheadRotation | Orbit (biến thể góc từ trên) | Higgsfield có "Overhead" và "360 Orbit" riêng — "OverheadRotation" nhiều khả năng là kết hợp hai preset đó |
| DollyOut | Dolly / Pull out | mọi nguồn |
| PedestalUp | Pedestal | Luma: "Pedestal up/down" [S4]; StudioBinder [S6] |
| LowAngleArc | Arc + góc thấp (không phải chuyển động riêng) | "low angle" là **góc máy** (thuộc tính tĩnh, xem `dp.md` Q1), không phải chuyển động — preset này là arc thực hiện từ vị trí thấp |
| LateralReveal | Truck (hoặc tracking ngang) dùng để hé lộ | không phải tên chuẩn ở bất kỳ nguồn nào đã kiểm — mô tả chức năng ("hé lộ theo chiều ngang") gần nhất với truck |

**Kết luận về ảnh 15 preset:** phần lớn (11/15) khớp trực tiếp hoặc là tổ hợp rõ ràng của các chuyển động cơ bản đã kiểm ở mục 3, cho
thấy ảnh **nhiều khả năng bắt nguồn từ bộ preset kiểu Higgsfield** (đặt tên PascalCase — "AerialOrbit", "TruckLeft" — khác cách
Higgsfield chính thức viết "Aerial Orbit", "Truck Left" có khoảng trắng, nên đây là bản tổng hợp/dịch lại của bên thứ ba, không phải
ảnh chụp trực tiếp từ trang chính thức). 4 preset còn lại (OverheadRotation, LowAngleArc, LateralReveal, AerialOrbit) là **tổ hợp** của
hai khái niệm cơ bản chứ không phải chuyển động mới — không cần thêm giá trị `camera_move` riêng cho chúng, chỉ cần mô tả bằng chữ
trong `why`/motion prompt (đúng nguyên tắc đã có ở `dp.md` Q5 cho arc/dolly zoom/steadicam).

## 5. Đề xuất đối chiếu với từ vựng pipeline (`core/reference_analysis.py` MOVES) — CHỈ ĐỀ XUẤT, CHƯA SỬA CODE

`MOVES = ("static", "push_in", "pull_out", "pan", "tilt", "track", "orbit", "handheld", "crane", "whip", "zoom")` — 11 giá trị.

| Chuyển động đã xác minh ở mục 3 | Có trong MOVES? | Đề xuất |
|---|---|---|
| Truck | **Không** | Thêm `truck` riêng (hiện không có, và `dp.md` Q5 cũng chưa nhắc cách map — khác arc/dolly-zoom là đã có hướng dẫn map tạm) |
| Pedestal | **Không** | Thêm `pedestal` riêng — hiện dễ bị nhầm gộp vào `crane` (crane đổi cả góc, pedestal không) |
| Roll | **Không** | Thêm `roll` riêng — khác `whip` (whip là pan nhanh, roll là xoay trục ống kính, hai chuyển động khác hẳn nhau) |
| Arc vs Orbit | Chỉ có `orbit` | `dp.md` Q5 đã có hướng dẫn tạm: arc → map vào `orbit`, ghi chuyển động thật ở `why`. Đề xuất: nếu dữ liệu chạy thật sau này cho thấy arc (không trọn vòng) và orbit (trọn vòng) có tỉ lệ lỗi khác nhau rõ rệt (orbit rủi ro cao hơn theo mục 3), tách hai giá trị riêng để so sánh được bằng SQL như câu lệnh mẫu ở `dp.md` Q5 |
| Dolly zoom | Không có giá trị riêng | `dp.md` Q5 đã có hướng dẫn map vào `push_in`/`pull_out` + ghi ở `why`. Đủ dùng — không đề xuất thêm giá trị riêng vì đây là chuyển động rủi ro cao, hiếm dùng, tách riêng có thể không đáng công |
| Crane up/down | Có `crane` (gộp chung) | Đủ dùng cho hiện tại; nếu cần phân biệt hướng thì thêm chi tiết ở `why`, không cần tách `crane_up`/`crane_down` thành hai giá trị enum |
| Aerial/Drone | **Không** | Đây là loại chuyển động khác hẳn nhóm còn lại (không neo vào mặt đất) — nếu pipeline định làm cảnh có góc flycam/drone (đã có ví dụ dùng Blender cho tháp 3D), nên cân nhắc thêm `aerial` riêng thay vì gò vào `crane`, vì `plate_camera`/máy ảo có thể cần tham số khác (độ cao tự do, không bị giới hạn bởi rig) |
| Dutch angle | Không áp dụng | Đây là **góc máy** (`angle`), không phải `camera_move` — không đề xuất gì ở MOVES, chỉ ghi chú để tránh nhầm khi có người đề xuất thêm "dutch" vào MOVES sau này |
| Steadicam/Gimbal | Không có giá trị riêng | `dp.md` Q5 đã map vào `track`. Đủ dùng — track đã bao hàm khái niệm "bám theo mượt". |

**Tóm lại:** 4 khoảng trống rõ nhất nếu muốn mở rộng `MOVES`: **truck, pedestal, roll, aerial**. Ba mục còn lại (arc/orbit tách, dolly
zoom riêng, crane_up/down tách) là "có thể cân nhắc" chứ không cấp thiết — dữ liệu chạy thật hiện có (theo `dp.md` Q5) chưa đủ lớn để
biết tách ra có ích hay chỉ làm phức tạp thêm. Đề xuất này **không tự sửa `core/reference_analysis.py`** — chờ người quyết.

## 6. Thuật ngữ làm việc tiếng Việt (đối chiếu nhanh)

| Tiếng Anh | Tiếng Việt hay dùng trong nghề | Ghi chú |
|---|---|---|
| Pan | lia máy (ngang) | "lia máy theo chủ thể" = pan bám theo hành động |
| Tilt | quay/lia máy dọc | ít khi tách riêng khỏi "lia máy" trong tiếng Việt thông dụng — dễ mơ hồ hơn tiếng Anh |
| Dolly in / push in | đẩy máy | |
| Dolly out / pull out | kéo máy (lùi) | |
| Zoom | zoom (mượn nguyên) | tiếng Việt không có từ riêng tách bạch với "đẩy máy" — dễ gây đúng lỗi nhầm lẫn ở mục 3 hơn cả tiếng Anh |
| Dutch angle | góc nghiêng / quay nghiêng | |
| Truck / Tracking | máy lướt ngang / máy bám theo | tiếng Việt cũng không tách rõ hai khái niệm này — cùng vấn đề mơ hồ như bảng người dùng gửi |

**Nguồn:** dhtn.ttxvn.org.vn — Trung tâm điều hành tác nghiệp, Thông tấn xã Việt Nam, "Động tác máy trong truyền hình" [S12] — đơn vị
đào tạo nghiệp vụ, không phải phỏng vấn một chuyên gia cụ thể nên chỉ dùng làm tham khảo thuật ngữ, không dùng làm căn cứ kỹ thuật.

## 7. Việc còn để ngỏ / cần đọc thêm

- **ClipAI docs (clipai.ingarena.net/docs/)** — WebFetch bị chặn (403) trong đợt này, giống ghi chú cũ ở NGUON.md. Cần một agent có
  trình duyệt mở lại phần "camera movement" của tài liệu ClipAI chính thức để đối chiếu trực tiếp (hiện dựa vào `dp.md` Q5 đã kiểm
  trước, không fetch lại được lần này).
- **Volcengine Ark / Seedance official docs** — trang chi tiết (`docs.volcengine.com`) yêu cầu đăng nhập console hoặc trả về 404 khi
  fetch trực tiếp; chỉ lấy được qua tóm tắt tìm kiếm và trang blog `seed.bytedance.com` (không đi sâu vào bảng từ vựng camera). Từ vựng
  Seedance dùng trong tài liệu này lấy lại từ `dp.md` Q5 (đã kiểm ở phiên trước, không phải nguồn mới đợt này).
- **Runway Academy Gen-3 trang cũ** — 404, có thể đã đổi cấu trúc URL; đã bù bằng trang "AI Camera Prompts" (runway.com/resources) fetch
  được trọn vẹn.
- Chưa có ví dụ mốc giây thật (từ video mẫu) cho từng chuyển động — nên bổ sung ở đợt xem mẫu S0.12 (theo đúng thói quen các file khác
  trong `research/craft/draft/`).
