# Phương pháp Sân khấu 3D — đặt nhân vật, đạo cụ, máy quay bằng tọa độ và hình học (09/10)

> Tổng hợp từ người dùng 09/10. (1) Không vá lỗi từng chỗ; phải có cách làm đúng. (2) Sân khấu có lưới ô. (3) Mỗi cảnh có tâm lưới cố định; từ tâm đó kẻ đường đo tới từng vị trí, dùng hình học không gian. (4) Tâm đặt trên mặt sàn chung, nơi nhân vật đứng và đạo cụ được đặt.
> Thay cho cách G0 cũ: Director đoán phương vị máy, rồi Claude nhìn render để phán đúng sai.
> Nguyên tắc: **mọi thứ đo được thì đo bằng số. Model chỉ quyết ý đồ và chọn trong các phương án đã đạt luật.**

## 1. Ba vai, không chồng việc

| Vai | Làm gì | Không làm gì |
|---|---|---|
| **Director (Claude)** | Viết ý đồ của cảnh bằng ngôn ngữ ô lưới: đạo cụ ở ô nào, ai đứng ô nào theo từng nhịp, ai nhìn ai, cặp nhân vật tạo trục, mỗi góc máy cần thấy gì. Sau đó chọn trong các ứng viên **đã đạt luật**. | Không bịa tọa độ, độ, khoảng cách. Không phán bằng mắt những điều code đo được. |
| **Code (hình học + tia Blender, 0 USD)** | Đổi ô ra tọa độ. Đo sàn. Tính vị trí máy. Chiếu điểm vào khung. Kiểm vật cản và trục. Đo thành phần khung. Kiểm luật. | Không tự đổi ý đồ. Không âm thầm thay phương án khi không đạt, phải báo luật nào hỏng. |
| **Người dùng** | Duyệt tấm ghép ứng viên cuối. Sửa bằng câu ngắn ("dời giếng sang G8", "máy A lùi 1 m"). | — |

## 2. Hệ tọa độ sân khấu (mỗi cảnh một hệ, cố định)

**2.1 Gốc O.**
- Cảnh đã chốt một vị trí trên map thì đặt O **một lần** và lưu vào `stage.json`. Mọi shot của cảnh dùng chung O, không tính lại theo shot.
- Mặt phẳng ngang của O: tâm vùng diễn, tức chỗ đứng chính của cảnh (spot đã đăng ký).
- Cao độ của O: bắn tia thẳng từ trên xuống tại điểm đó; **chỗ tia chạm mặt sàn là z = 0** (sàn sân khấu).
- Hệ quả: mọi độ cao đều là độ cao thật tính từ sàn nơi nhân vật đứng (mắt Kelly 1,6 m; máy thấp 0,5 m).

**2.2 Trục.**
- x hướng Đông, y hướng Bắc, z hướng lên. Đơn vị: mét, ghi 2 số lẻ.
- Đổi từ tọa độ scene Blender: `p_sân_khấu = R(θ) · (p_scene − O)`.
  - θ là góc giữa trục scene và hướng Bắc của map.
  - Tỉ lệ `factor`/`LIFT_Z` giữa tọa độ model và scene dùng như trong `location_pack.reframe`.
- ⚠ Nguồn của hướng Bắc phải ghi rõ trong `stage.json` (hướng đăng ký của map hoặc trục model). Bước 0 xác nhận.

**2.3 Lưới ô (chỉ là tên gọi; vị trí thật là tọa độ liên tục).**
- Ô vuông cạnh c = 1 m. Vùng diễn gần có thể chia c = 0,5 m. Phủ N × N ô quanh O (mặc định N = 20).
- Cột: `i = ⌊x / c + N/2⌋` → chữ cái A, B, … (Tây → Đông).
- Hàng: `j = ⌊y / c + N/2⌋ + 1` → số 1, 2, … (Nam → Bắc).
- Với N = 20, c = 1: O nằm ở ô **K11**.
- Đổi ngược: tên ô ra tâm ô, rồi cộng độ lệch trong ô nếu Director ghi ("K11, lệch 0,3 m về Đông").

**2.3b Hai cấp lưới (người dùng 09/10, theo mẫu Bàn đạo diễn có lưới mịn trên sàn).** Ô 1 m chỉ để GỌI TÊN. Vị trí thật luôn lưu tọa độ liên tục, chính xác 0,01 m.
- **Lưới chính 1 m, có tên** (K11): để Director và người dùng nói chuyện.
- **Lưới phụ 0,25 m, không tên, chỉ kẻ mờ:** để nhìn và để bắt dính khi đặt bằng tay. Chọn 0,25 m vì cỡ bàn chân ≈ 0,25–0,3 m và bề ngang thân người ≈ 0,45 m. Lệch dưới 0,25 m không đổi vị trí nhân vật so với đồ vật.
- **Bước bắt dính theo cỡ cảnh,** vì cùng một độ lệch thì máy càng gần càng thấy rõ:

  | Cỡ cảnh | Máy cách nhân vật | Bước bắt dính |
  |---|---|---|
  | CU / MCU | ≈ 0,8–1 m | 0,05 m |
  | MS / MLS | — | 0,1 m |
  | WS / EWS | — | 0,25 m |

  Lý do: 0,1 m ở cách 0,8 m là lệch ≈ 7° trong khung; ở cách 4 m chỉ còn ≈ 1,4°.
- **Đo sàn (mục 3):** trong vùng diễn (6 × 6 m quanh O và quanh từng đạo cụ) mỗi ô 1 m bắn lưới 4 × 4 tia (cách 0,25 m), để không lọt bậc, gờ, bồn cây hẹp hơn 1 m. Ngoài vùng diễn giữ 3 × 3.
- **Ghi vị trí:** tọa độ (x, y, z), kèm ô chính chỉ để đọc ("K11, +0,30 Đông, +0,15 Bắc"). Không đặt tên ô phụ, vì tên ô phụ kiểu "K11.3.2" dễ đọc nhầm.

**2.4 Đường đo từ O** (ghi cho mọi vật: mốc, đạo cụ, nhân vật, máy):
- khoảng cách ngang `d = √(x² + y²)`;
- phương vị la bàn `β = atan2(x, y)` (0° = Bắc, 90° = Đông);
- chênh cao `Δz = z`;
- ô chứa vật.

## 3. Bản đồ sàn (đo, không đoán)

Với mỗi ô, bắn k × k tia từ trên xuống (3 × 3; trong vùng diễn 4 × 4 = cách 0,25 m — mục 2.3b) và ghi:
- `floor_z`: trung vị cao độ các điểm trúng có pháp tuyến hướng lên (n_z ≥ 0,9) — tức mặt ngang;
- vật trúng: tên object và vật liệu, nhóm (tháp / nhà / tường / sàn / bậc / đạo cụ / khác);
- độ dốc lấy từ pháp tuyến;
- `top_z` của vật cao nhất trong ô.

Phân loại ô:
- **cùng mặt sàn**: |floor_z| ≤ 0,15 m (đứng và đặt đồ được);
- **bậc / tầng khác**: chênh lớn hơn 0,15 m;
- **vật chắn**: tường, nhà hoặc khối cao hơn 0,3 m chiếm ô.

Sàn quanh O dốc quá 2° thì báo: lúc này "mặt phẳng" chỉ còn là gần đúng.

Đầu ra:
- `grid.json`;
- `topgrid.png`: ảnh nhìn từ trên, kẻ lưới, ghi tên ô, tô màu theo nhóm và cao độ, đánh dấu O, hướng Bắc và các mốc.

## 4. Dựng sân khấu (blocking) trong 3D

**4.1 Đạo cụ.**
- Đặt bằng ô và hướng.
- Kích thước lấy từ kịch bản hoặc hồ sơ Kho, kèm nguồn. Thiếu thì hỏi, không tự đặt.
- Dựng **khối thay thế đúng cỡ** (giếng: trụ có đường kính và chiều cao thật) để render thấy được, tia đo trúng được.
- Đáy đạo cụ đặt tại `floor_z` của ô.
- Kiểm chân đế: mọi ô dưới đạo cụ phải cùng mặt sàn và không có vật chắn.

**4.2 Nhân vật.**
- Mỗi nhịp có: ô đứng, hướng mặt φ (độ la bàn), tư thế (đứng / quỳ / ngã).
- Chiều cao H lấy từ hồ sơ nhân vật.
- Dựng **người nộm** cao H tại `floor_z` của ô.
- Các điểm nhìn dùng tỉ lệ nhân trắc học thông dụng, Bước 0 kiểm bằng người nộm:
  - mắt `E = (x, y, floor_z + 0,93·H)`;
  - ngực `0,72·H`;
  - hông `0,53·H`.
- Ô đứng phải cùng mặt sàn. Khác tầng thì báo, trừ khi kịch bản ghi rõ "đứng trên bậc".

**4.3 Trục 180°.**
- Mỗi nhịp có một cặp (A, B): hai nhân vật nhìn nhau, hoặc nhân vật và vật đang nhìn (giếng).
- Vector trục `u = B − A` trên mặt ngang.
- Phía của máy C: `s = dấu( (u × (C − A))_z )`.
- Cảnh chọn một phía s₀ ở shot mở. Shot khác phía là vượt trục, chỉ được khi Director ghi lý do và là cú chuyển có chủ ý.

## 5. Tính máy quay bằng hình học

**Đầu vào mỗi góc máy** (Director chỉ ghi ý đồ; code đổi ra số):
- điểm nhắm T: mắt, ngực hoặc tâm nhóm;
- hướng máy nhìn từ phía nào của nhân vật α (độ la bàn, nơi máy đứng);
- cỡ cảnh (EWS…ECU);
- độ cao định tính: thấp / ngang / cao / trên đầu;
- ống kính f.

**Các bước tính:**
1. **Khung cần chứa.** Chiều cao `h_f` của phần thân trong khung lấy theo bảng cỡ cảnh sẵn có (`plate_camera` FRAMING/HEADROOM).
   - FOV dọc `v = 2·atan(s_h / 2f)`, với s_h là chiều cao cảm biến theo tỉ lệ khung của dự án. FOV ngang `h` tính tương tự.
   - Khoảng cách xiên `D = (h_f / 2) / tan(v / 2)`.
2. **Độ cao máy so với sàn** h_c:
   - ngang: bằng mắt;
   - thấp: lấy từ 0,5·H, không sát đất;
   - cao: mắt + 0,5–1 m;
   - trên đầu: theo ý đồ.
   - Ghi cả cao so với z = 0 và cao so với sàn ngay dưới máy.
3. **Vị trí máy:**
   - `C_xy = T_xy + D_h·(sin α, cos α)`;
   - `C_z = floor_z(ô máy) + h_c`;
   - D_h chọn sao cho `√(D_h² + (T_z − C_z)²) = D`.
4. **Hướng nhìn.** `forward = (T − C)/|T − C|`. Góc cúi/ngửa thật: `pitch = atan2(T_z − C_z, D_h)`.
5. **Kiểm chỗ đứng của máy:**
   - ô máy phải đặt được: cùng mặt sàn, hoặc trên bậc có ghi rõ;
   - máy không nằm trong vật: tia lên và tia xuống từ C đều phải gặp mặt ngoài.

## 6. Kiểm bằng phép chiếu và tia (thay cho "Claude nhìn render")

Hệ máy: phải `r̂`, lên `û`, trước `f̂`. Với mỗi điểm P: `x_c = (P−C)·r̂`, `y_c = (P−C)·û`, `z_c = (P−C)·f̂`.
- **P có trong khung** khi `z_c > 0`, `|x_c/z_c| ≤ tan(h/2)` và `|y_c/z_c| ≤ tan(v/2)`.
- **Vị trí P trên ảnh:**
  - `u = 0,5 + x_c / (2·z_c·tan(h/2))`;
  - `w = 0,5 − y_c / (2·z_c·tan(v/2))`.
  - Áp cho chân/đỉnh tháp, mép giếng, đầu/chân từng nhân vật. Từ đó biết tháp ở đâu trong khung, nhân vật chiếm bao nhiêu phần trăm chiều cao khung, giếng cao ngang hông ai.
- **Bị che:** bắn tia C → P. Trúng vật khác ở khoảng cách nhỏ hơn |P − C| − 0,05 m thì P bị che bởi vật đó (ghi tên vật).
- **Thành phần khung:** bắn lưới khoảng 64 × 36 tia qua tâm các điểm ảnh. Mỗi tia ghi nhóm vật trúng (kể cả khối giếng, người nộm), không trúng gì thì là trời. Ra % tháp / nhà / tường / sàn / trời / giếng / từng nhân vật, kèm độ sâu gần nhất.
- **Đường chân trời:** `w_h = 0,5 + tan(pitch) / (2·tan(v/2))` (pitch âm khi cúi). Đây là số thật, không cần mắt.

## 7. Luật đạt / không đạt (kiểm bằng số)

Mỗi luật có lý do. Ngưỡng có dấu ⚙ đặt từ số đo Bước 0, không đặt cảm tính.

| # | Luật | Cách kiểm | Lý do |
|---|---|---|---|
| L1 | Máy đứng chỗ hợp lệ | mục 5 bước 5 | Máy trong tường hoặc ở tầng khác thì ra nền sai (shot 5 #24) |
| L2 | Nhân vật chính thấy rõ | ≥ ⚙80 % tia nhắm vào người nộm trúng chính nó | Bị che thì model vẽ sai chỗ |
| L3 | Đúng cỡ cảnh | % chiều cao khung của nhân vật trong ±⚙15 % so với bảng cỡ | Cỡ lệch thì ảnh lệch ý đồ |
| L4 | Không vượt trục | `s = s₀`, trừ khi có lý do | Khán giả mất phương hướng |
| L5 | Mốc đúng ý đồ | thấy mốc: tháp ≥ ⚙X % khung; không thấy mốc: 0 % | Ý đồ "thấy tháp / bỏ tháp" (shot 1, shot 3 #24) |
| L6 | Cùng gia đình nền với shot mở | nhóm nền chiếm nhiều nhất trùng shot mở, hoặc góc ngược có ghi chủ ý | Cảnh liên tục, người xem không thấy phía chưa giới thiệu |
| L7 | Cúi / ngửa đúng ý đồ | `pitch` thật: ngang \|pitch\| ≤ ⚙12°, cúi ≤ −⚙20°, ngửa ≥ ⚙8° | Lấy số thật, không lấy mắt model (máy −6° từng bị khai là "cúi") |
| L8 | Khung không chỉ là một thứ | không nhóm nào > ⚙70 % khung, trừ khi ý đồ yêu cầu; shot cúi phải có đạo cụ hoặc nhân vật trong khung | Cúi nhìn sàn trống thì nền vô dụng (shot 2–3 #24) |
| L9 | Không vật cản sát ống kính | vật gần nhất trước nhân vật ≥ ⚙0,3 m và không chiếm > ⚙10 % khung | Tường hoặc cột chắn trước ống kính |
| L10 | Tỉ lệ đạo cụ / nhân vật | chiều cao giếng so với hông, ngực nhân vật lấy từ số thật của khối thay thế | Shot 7 #24 lệch tỉ lệ |

## 8. Ứng viên và chọn

1. Mỗi góc máy Director yêu cầu: code thử α theo bước 15° (24 hướng), 3 độ cao theo lớp góc, ống kính theo cỡ.
2. Mỗi ứng viên chạy mục 5–7, ghi bảng số và render ảnh nhỏ (Blender, 0 USD).
3. Bỏ ứng viên hỏng luật, ghi luật hỏng.
4. Với ứng viên đạt, xếp hạng theo thứ tự ưu tiên của ý đồ Director (vd thấy giếng > thấy tháp > ánh sáng).
5. Director chọn trong tối đa 3 ứng viên đạt đầu bảng, ghi lý do.
6. **Không có ứng viên nào đạt:** báo rõ luật hỏng theo từng hướng và gợi ý dời ô máy hoặc ô nhân vật. Người dùng quyết. Không tự lùi về cách cũ một cách im lặng.
7. Các shot cùng góc máy (cùng C, cùng hướng, cùng ống kính) dùng chung một render nền. Shot khác độ cao là góc máy khác.

## 9. Dữ liệu lưu (mỗi dự án / cảnh)

| File | Nội dung |
|---|---|
| `stage.json` | O (scene + model), θ Bắc + nguồn, c, N, floor tại O, độ dốc |
| `grid.json` | mỗi ô: floor_z, top_z, nhóm, dốc |
| `blocking.json` | đạo cụ (ô, tọa độ, cỡ, nguồn cỡ), nhân vật theo nhịp (ô, φ, tư thế, H), cặp trục, s₀ |
| `setups.json` | mỗi góc máy: ý đồ, C, T, f, pitch, ô máy, các số kiểm L1–L10, ứng viên bị loại kèm lý do |
| Ảnh | `topgrid.png` (lưới + O + mốc + đạo cụ + nhân vật + máy + đường trục), tấm ghép ứng viên |

## 10. Những gì chưa biết — phải đo ở Bước 0, không giả định

- **Hướng Bắc** của map #24 và nguồn của nó.
- **Phân nhóm vật thể:** tên object/vật liệu trong map có phân được tháp / nhà / tường / sàn / bậc không. Không thì phải dùng cách khác (kích thước, chiều cao đỉnh).
- **Các ngưỡng ⚙** ở mục 7: đo trên render #24 và trên các shot người dùng đã chê hoặc khen.
- **Cỡ thật của giếng:** lấy từ kịch bản hoặc ảnh Kho 1127, ghi nguồn.
- **Tỉ lệ điểm nhìn trên người nộm** (mắt, ngực, hông) so với hồ sơ nhân vật.

## 11. Thứ tự làm

| Bước | Việc | Chi phí |
|---|---|---|
| 0 | Đo: lưới, sàn, nhóm vật thể, O, khối giếng, người nộm, 2 góc thử | 0 USD |
| 1 | `core/stage_grid.py` (hình học thuần, có test) + `tools/stage_grid.py` (Blender) | 0 USD |
| 2 | Đo khung bằng tia, luật L1–L10, ứng viên | 0 USD |
| 3 | Director viết ý đồ theo ô và chọn ứng viên; gỡ "Claude duyệt render" của G0 | Claude ≈ vài cent mỗi cảnh, báo trước |
| 4 | #24: tấm ghép cho người dùng duyệt, rồi mới vẽ ảnh | báo giá |
