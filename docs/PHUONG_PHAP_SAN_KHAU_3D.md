# Phương pháp Sân khấu 3D — v2 (tối ưu, 09/10)

> Gộp mọi ý người dùng 09/10. (1) Không vá lỗi từng chỗ, phải có cách làm đúng. (2) Sân khấu có lưới ô. (3) Tâm lưới cố định theo cảnh; từ tâm kẻ đường đo, dùng hình học không gian. (4) Tâm nằm trên mặt sàn diễn. (5) Có "Góc nhìn camera". (6) Director quyết trong khung có gì, ai ở đâu; mỗi góc máy có mục đích; thứ đang được focus phải nằm trong khung.
> Đã thử thật trên #24 (Bước 0, 1–2, yêu nữ trong giếng, 0 USD): phần đo và hình học làm được (Phụ lục A).
> **v2 thay đổi lớn nhất:** máy không còn dò mù 72 hướng. Máy được **GIẢI** bằng hình học từ yêu cầu khung hình của Director. Dò thử chỉ còn là đường lùi khi lời giải bị vật che.

## 0. Nguyên tắc
1. **Ý đồ do Director, con số do code.** Director không bịa tọa độ, độ, mét. Code không tự đổi ý đồ.
2. **Đo được thì đo, tính được thì tính.** Không hỏi model những gì phép chiếu và tia trả lời được (vd góc cúi, có trong khung không, bị che không).
3. **Đúng ngay từ đầu vào.** Yêu cầu khung phải viết rõ trước, rồi máy mới được tính từ yêu cầu đó. Không render rồi mới đoán xem khung đúng hay sai.
4. **Không im lặng.** Không đạt thì nói rõ thứ gì hỏng, ở đâu, và gợi ý cách sửa. Người dùng quyết.
5. **Làm một lần, dùng lại.** Sân khấu (gốc, lưới, sàn) tính một lần cho mỗi chỗ đứng trên map. Mỗi góc máy render một lần, dùng chung cho mọi shot cùng góc.

## 1. Dòng chảy (5 khâu)

| # | Khâu | Ai | Ra | Chi phí |
|---|---|---|---|---|
| K1 | Sân khấu: gốc O, lưới, bản đồ sàn | code + tia Blender | `stage.json`, `grid.json`, `topgrid.png` | 0 USD, ≈ 20 s, mỗi chỗ đứng một lần (cache theo sha map + chỗ đứng) |
| K2 | Dàn cảnh + yêu cầu khung từng shot | **Director** (Claude), viết theo ô lưới | `blocking.json`, `shot_specs.json` | Claude ≈ vài cent mỗi cảnh, báo trước |
| K3 | Giải máy cho từng yêu cầu | code (hình học thuần) | C, hướng nhìn, ống kính, độ cao | 0 USD, mili giây |
| K4 | Kiểm bằng tia + "Góc nhìn camera" | code + Blender | số đo, hình phác, nền thật, hình nón | 0 USD, ≈ 1 s mỗi máy |
| K5 | Duyệt | người dùng (tấm ghép) | chốt / sửa bằng câu ngắn | 0 USD |

Không đạt ở K4 → quay về K3 dò quanh lời giải (mục 6.4). Vẫn không đạt → báo Director/người dùng sửa K2 (dời chỗ đứng, đổi cỡ, đổi vai). Không tự nới luật.

## 2. K1 — Hệ tọa độ sân khấu

**2.1 Gốc O.**
- Mỗi chỗ đứng (spot) đã chốt có một O, lưu một lần. Mọi shot của cảnh dùng chung O.
- Vị trí ngang của O = chỗ đứng chính. Bắn tia từ trên xuống; chỗ tia chạm mặt sàn là **z = 0**.
- Spot đăng ký lệch khỏi mặt sàn quá 0,05 m → báo, rồi sửa bằng `fix-spot`. #24 từng lệch 0,45 m.

**2.2 Trục.**
- x hướng Đông, y hướng Bắc (= +y của model, người dùng duyệt), z hướng lên. Đơn vị mét, ghi 2 số lẻ.
- `p_sân_khấu = R(θ)·(p_scene − O)`. Tỉ lệ model ↔ scene theo `factor`/`LIFT_Z`.

**2.3 Lưới — chỉ để gọi tên và để nhìn; vị trí thật là tọa độ liên tục.**
- **Lưới chính 1 m, có tên:**
  - cột = chữ cái từ Tây sang Đông: `i = ⌊x + N/2⌋`;
  - hàng = số từ Nam lên Bắc: `j = ⌊y + N/2⌋ + 1`;
  - N = 20, nên O ở góc Tây-Nam ô **K11**.
- **Lưới phụ 0,25 m:** không tên, kẻ mờ.
- **Bước bắt dính khi đặt tay, theo cỡ cảnh:** CU/MCU 0,05 m · MS 0,1 m · WS 0,25 m. Lý do: lệch 0,1 m ở khoảng cách 0,8 m ≈ 7° trong khung, ở 4 m chỉ ≈ 1,4°.
- **Ghi vị trí:** `(x, y, z)` kèm tên để đọc, vd "K11 +0,30 Đ +0,15 B".

**2.4 Bản đồ sàn.** Mỗi ô bắn 3 × 3 tia; vùng diễn 6 × 6 m quanh O và quanh đạo cụ bắn 4 × 4 (đo #24: lưới 3 × 3 bỏ lọt mép tường ở J8).
- **Mỗi ô ghi:** `floor_z` (trung vị các điểm có pháp tuyến hướng lên, n_z ≥ 0,9), `top_z`, độ dốc, nhóm.
- **Nhóm:** phân theo **từng điểm tia trúng**, dựa trên cao độ so với sàn và pháp tuyến. Không phân theo tên object, vì ở #24 quảng trường, tường và bậc là cùng một mesh. Tên chỉ dùng cho vật riêng: tháp, nhà, cây.
- **Loại ô:**
  - cùng mặt sàn: |floor_z| ≤ 0,15 m;
  - bậc / tầng khác: lệch lớn hơn;
  - vật chắn: cao hơn 0,3 m;
  - có mái che.
- Map có tầng rỗng bên dưới (#24: −6,18 m), nên tia đo dưới đạo cụ phải đo **trước khi** dựng khối thay thế.

## 3. K2 — Director viết dàn cảnh và yêu cầu khung (đầu vào chính)

**3.1 Dàn cảnh (`blocking.json`)** — một lần cho mỗi cảnh liên tục:
- **Đạo cụ:** ô, hướng, kích thước kèm nguồn (kịch bản / Kho). Thiếu số thì hỏi người dùng, không tự đặt. Dạng đặc biệt (giếng rỗng) có cờ riêng.
- **Nhân vật theo từng nhịp:**
  - ô đứng, hướng mặt φ, tư thế (đứng / quỳ / ngã / trong giếng);
  - chiều cao H lấy từ hồ sơ;
  - người nộm cao H đặt tại `floor_z` của ô (trường hợp "trong giếng": chân ở `WELL_H − 0,72·H`).
- **Cặp trục của từng nhịp** (A, B) và phía máy s₀, chọn ở shot mở.

**3.2 Yêu cầu khung từng shot (`shot_specs.json`)** — đây là thứ quyết định máy:
```json
{"shot": 3,
 "muc_dich": "thấy Kelly nhìn vào giếng và thứ trong giếng cùng lúc",
 "co": "MS", "do_cao": "cao", "goc": "cúi",
 "thanh_phan": [
   {"vat": "yeunu", "vai": "chinh", "vung": "1/3 phải, 1/3 giữa", "thay": "mat", "co_pct": [15, 35]},
   {"vat": "gieng", "vai": "chinh", "vung": "giữa dưới"},
   {"vat": "kelly", "vai": "phu", "vung": "1/3 trái", "thay": "lung|nghieng"},
   {"vat": "thap", "vai": "khong_duoc_co"}],
 "nen": "cùng gia đình shot mở"}
```
- **vai:**
  - `chinh` = bắt buộc trong khung, phần thấy ≥ ngưỡng, đúng vùng ± dung sai;
  - `phu` = nên có, dùng để xếp hạng;
  - `khong_duoc_co` = có thì hỏng.
- **vung:** một trong 9 ô của lưới một phần ba, hoặc ghép 2 ô.
- **thay:** mặt / lưng / nghiêng.
- **co_pct:** khoảng % chiều cao khung.
- **Cỡ cảnh (`co`) là cỡ của cả khung**, đo theo thứ `chinh` đầu tiên; không phải cỡ của một nhân vật bất kỳ. Đo #24: một "toàn cảnh" tính theo cỡ Kelly ra Kelly 52 % khung.
- Director phải ghi lý do ở `muc_dich`. Code kiểm tính tự nhất quán trước khi giải: hai thứ `chinh` cùng một vùng mà xa nhau trên sàn → báo mâu thuẫn ngay.
- **Chốt khi làm V1 (09/10):**
  - Cách ghi vùng: `"ngang-dọc"`, vd `"phai-giua"`, `"giua+phai-duoi"` (ghép ô), `"trai"` (chỉ ngang), `"duoi"` (chỉ dọc); nhận cả chữ có dấu.
  - **Vị trí của NGƯỜI trong vùng = MẮT** (0,93·H), theo quy tắc một phần ba. Lý do đo được: cỡ MCU thân chiếm 85 % khung nên tâm thân không thể nằm ở 1/3 trên (lệch 0,26 khung). Đạo cụ / mốc = tâm phần thấy.
  - Không ghi vùng dọc: mắt người đặt trên đường 1/3 trên; đạo cụ giữa khung.
  - Nhịp: `blocking.beats` ghi đè từng vật theo nhịp (`hidden`, `at`, `H` tư thế, `in`); shot ghi `"nhip"`. Ngồi / quỳ = người nộm thấp hơn (`tu_the`).

## 4. Tính cho từng vật

- **Điểm của nhân vật:**
  - mắt `0,93·H`, ngực `0,72·H`, hông `0,53·H`, đỉnh đầu `H`, chân `0`;
  - mỗi nhân vật có điểm đầu và điểm chân để đo cỡ, cộng khoảng 27 điểm phủ thân để đo % bị che.
- **Điểm của đạo cụ:** tâm miệng, mép trên và đáy.
- **Hướng thấy:** mặt nếu `|φ − hướng_tới_máy| ≤ 60°`, lưng nếu ≥ 120°, còn lại là nghiêng.

## 5. Khung hình (dùng chung cho K3 và K4)

- **FOV:**
  - `v = 2·atan(s_h / 2f)`, s_h là chiều cao cảm biến theo tỉ lệ khung của dự án (9:16 hoặc 16:9);
  - `h` tính tương tự cho chiều ngang.
- **Chiếu điểm P:**
  - hệ máy (r̂, û, f̂): `x_c = (P−C)·r̂`, `y_c = (P−C)·û`, `z_c = (P−C)·f̂`;
  - `u = 0,5 + x_c / (2·z_c·tan(h/2))`, `w = 0,5 − y_c / (2·z_c·tan(v/2))`;
  - P có trong khung khi `z_c > 0`, `0 ≤ u ≤ 1`, `0 ≤ w ≤ 1`.
- **Chân trời:** `w_h = 0,5 + tan(pitch) / (2·tan(v/2))`.
- **Cỡ trong khung:** `|w_đầu − w_chân|` (hoặc phần thân trong khung với các cỡ cận).

## 6. K3 — Giải máy từ yêu cầu (thay cho dò mù)

Gọi A = thứ `chinh` thứ nhất, B = thứ `chinh` hoặc mốc thứ hai (nếu có).

**6.1 Khoảng cách từ cỡ.** Cỡ đích s (phần khung) và chiều cao thật của phần cần thấy h_A cho:

`D_A = h_A / (2·s·tan(v/2))`

Đây là khoảng cách từ máy tới A. Ống kính f mặc định theo cỡ; muốn nén hay giãn hậu cảnh thì đổi f, D_A tính lại.

**6.2 Phương vị từ vùng đích của 2 thứ — định lý góc nội tiếp.**
- Góc ngang dưới đó máy thấy A và B: `γ = atan((u_B − 0,5)·2·tan(h/2)) − atan((u_A − 0,5)·2·tan(h/2))`.
- Các điểm nhìn đoạn AB (trên mặt sàn, dài L) dưới cùng một góc γ nằm trên **một cung tròn**:
  - bán kính `R = L / (2·sin γ)`;
  - tâm nằm trên đường trung trực của AB, cách trung điểm `L / (2·tan γ)`.
- Chọn **cung ở phía s₀ của trục**. Luật 180° vì thế chọn luôn lời giải, không cần kiểm sau.
- Giao cung với đường tròn tâm A bán kính `D_A` (chiếu ngang) cho **tối đa 2 điểm C**. Chọn điểm thỏa yêu cầu "thấy" (mặt / lưng) và không đứng trong ô vật chắn.
- **Chỉ có một thứ `chinh`:** B = mốc nền nếu yêu cầu có (thấy tháp ở vùng X), hoặc phương vị lấy từ yêu cầu "thấy mặt" (máy đặt ở `φ ± 30°` theo hướng mặt). Không có ràng buộc nào thì báo "thiếu ý đồ hướng", không tự chọn.

- **Đã kiểm bằng số (09/10, Python thuần).** Đầu vào #24: Kelly ở (0; 0), yêu nữ ở (−0,28; 1,58), đích Kelly u = 0,33, yêu nữ u = 0,67, D_A = 2,4 m. Kết quả:
  - 2 nghiệm đúng: C = (1,72; −1,68) và (−0,12; 2,40), chiếu lại ra đúng u = 0,330 / 0,670.
  - Cung đối xứng cho ra góc ngược dấu, nên tự bị loại.
  - Nghiệm (−0,12; 2,40) đứng sau lưng yêu nữ, bị loại theo yêu cầu "thấy mặt" (mục 4) và luật P1.

**6.3 Độ cao và cúi.**
- Có vùng dọc đích của A: `pitch = ε_A − atan((0,5 − w_A)·2·tan(v/2))`, trong đó `ε_A = atan2(A_z − C_z, khoảng cách ngang)` là góc ngẩng từ máy tới A. Với độ cao máy theo lớp, giải ra pitch; hoặc cho pitch, giải ra `C_z`.
- Không có vùng dọc thì theo lớp độ cao:
  - ngang = bằng mắt;
  - thấp = từ 0,5·H, không sát đất;
  - cao = mắt + 0,5–1 m.
- **Tinh chỉnh:** pitch khác 0 làm u lệch chút ít. Lặp 2–3 lần: chiếu lại A, B, chỉnh α và D cho đến khi lệch vùng ≤ 0,02 khung.

**6.4 Đường lùi khi lời giải bị che hoặc đứng chỗ cấm.** Dò quanh lời giải: α ± 5° / 10° / 15°, D ± 10–20 %, độ cao ± 0,3 m. Khoảng 30 điểm, không phải 72 điểm mù. Giữ phương án lệch vùng ít nhất mà vẫn đạt. Hết đường lùi thì báo kiểu "giếng bị Kelly che ở mọi hướng 150–210° → đề xuất dời Kelly sang J11 hoặc đổi cỡ MCU".

**6.4b Chốt khi làm V1 (09/10, `core/stage_solver.py`).**
- **Cỡ là một khoảng** (`co_pct`, hoặc bảng cỡ ± 15 %). Ở khoảng cách đích không có điểm nào thấy AB dưới góc γ → thử các khoảng cách khác trong khoảng cỡ, gần đích trước, rồi ghi chú. #24 shot 9: 2,31 m không có, 1,97 m có.
- **γ ≈ 0** (hai thứ cùng cột, vd giếng sau lưng yêu nữ): máy nằm trên đường B→A kéo dài.
- B có cả vùng dọc → thả độ cao máy trong lớp ± 0,3 m (đủ ẩn). Hệ dư phương trình thì vị trí A được ưu tiên (trọng số 4), B và cỡ chịu lệch.
- Luật S1 với thứ chính đầu tiên chỉ tính **phần thân mà cỡ cần thấy** (MCU: 35 % trên), không đòi thấy cả người.
- Không đạt ở mọi phương án → `advice`: luật nào hỏng ở cả N phương án, kèm câu gợi ý sửa. Đây là đầu vào K5.

**6.5 Hai giai đoạn kiểm.**
- (a) Python thuần: chiếu các điểm, ra vùng / cỡ / trong khung, loại phương án sai ngay (mili giây).
- (b) Blender chỉ chạy cho phương án còn lại: đo che khuất, thành phần khung, vật cản.

## 7. K4 — Luật kiểm (bằng số) + Góc nhìn camera

**7.1 Luật vật lý** (mọi shot):
| Mã | Luật | Kiểm |
|---|---|---|
| P1 | Máy đứng chỗ hợp lệ | ô máy đặt được; tia lên / xuống gặp mặt ngoài (máy không nằm trong vật). Đo #24: shot 4 cũ có máy nằm trong khối giếng |
| P2 | Không vật cản sát ống kính | vật gần nhất trước thứ `chinh` ≥ 0,3 m và chiếm ≤ 10 % khung |
| P3 | Cúi / ngửa đúng ý đồ | pitch thật: ngang \|p\| ≤ 12°, cúi ≤ −20°, ngửa ≥ 8°. Đo #24: shot 3 khai "ngang" nhưng thật là −35° |
| P4 | Tỉ lệ đạo cụ / người | đo trên khối thay thế (giếng ÷ hông = 1,00 ở #24) |

**7.2 Luật yêu cầu** (sinh từ `shot_specs`):
| Mã | Luật | Kiểm |
|---|---|---|
| S1 | Thứ `chinh` có trong khung và thấy rõ | phần thấy ≥ ngưỡng (người 60 %, đạo cụ 50 %; trường hợp "trong giếng" tính trên phần trên miệng giếng) |
| S2 | Đúng vùng | tâm thứ đó nằm trong vùng đích ± 0,08 khung |
| S3 | Đúng cỡ | cỡ trong khoảng `co_pct` |
| S4 | Đúng hướng thấy | mặt / lưng / nghiêng theo mục 4 |
| S5 | Không có thứ `khong_duoc_co` | phần thấy = 0 % |
| S6 | Khung không bị một thứ ngoài yêu cầu nuốt hết | một nhóm ngoài danh sách (sàn / tường / trời) > 70 % → hỏng. Đo #24: máy cao đặt tay 3,4 m cho sàn 84,5 % |

**7.3 Luật liên tục** (giữa các shot trong cảnh):
| Mã | Luật | Kiểm |
|---|---|---|
| C1 | Trục 180° | đã khóa ở 6.2; chỉ kiểm lại khi người dùng chỉnh tay |
| C2 | Gia đình nền | nhóm nền lớn nhất trùng shot mở, trừ khi `nen` ghi góc ngược có chủ ý |
| C3 | Dùng lại góc máy | hai shot có cùng C, hướng nhìn, ống kính (lệch ≤ 0,05 m, 1°) dùng chung một render |

**Ngưỡng:**
- Các số trên lấy từ đo #24 và từ phim thật.
- Hiệu chỉnh tiếp từ phản hồi người dùng: mỗi lần duyệt tấm ghép, ghi "đạt / chê + lý do" vào `stage_feedback.jsonl`.
- Ngưỡng chỉ đổi khi có ≥ 3 phản hồi cùng chiều. Không đổi theo một ca lẻ.

**7.4 Góc nhìn camera.** Mỗi máy có 3 hình:
1. **Hình phác clay**, khoảng 0,2–0,4 s:
   - người nộm và đạo cụ có nhãn;
   - lưới một phần ba, chân trời, vạch chừa đầu, vùng thanh trên 15 %;
   - **vẽ vùng đích của từng thứ `chinh`** để thấy ngay khung lệch bao nhiêu.
2. **Nền thật**, khoảng 3–4 s: có vật liệu, giờ, thời tiết, khối thay thế.
3. **Hình nón trên lưới:** hình nón nhìn, đường trục, phía s₀.

**Nhãn:**
- trong khung → chấm đặc;
- bị che → chấm rỗng kèm "(bị che bởi …)", **chỉ vẽ cho thứ `chinh` và `phu`**;
- ngoài khung → mũi tên ở mép;
- sau máy → không vẽ.

Sau khi vẽ ảnh: so "nền thật" với ảnh kết quả bằng `plate_layout_qc`, đánh cờ nền lệch.

## 8. K5 — Người duyệt
- **Tấm ghép cho cả cảnh, mỗi shot gồm:** mục đích, hình phác có vùng đích, nền thật, các luật đạt.
- **Sửa bằng câu ngắn,** Director đổi thành sửa `blocking` hoặc `shot_specs`, rồi chạy lại K3–K4 (0 USD). Ví dụ:
  - "Kelly lùi 1 m";
  - "yêu nữ sang 1/3 trái";
  - "bỏ tháp".
- Chỉ sau khi duyệt mới vẽ ảnh, và báo giá trước.

## 9. Dữ liệu và code
| Thứ | Nơi |
|---|---|
| Hình học thuần (ô ↔ tọa độ, chiếu điểm, vùng đích, luật P/S) | `core/stage_grid.py` |
| Giải máy K3 (góc nội tiếp, tinh chỉnh, đường lùi, gợi ý sửa) | `core/stage_solver.py` |
| Chạy v2: `py tools/stage_grid.py v2 --blocking … --specs … --out … --stage-from <thư mục K1> [--solve-only]` | `tools/stage_grid.py` |
| Blender: đo sàn, dựng khối, đo bằng tia, clay, nền thật | `tools/stage_grid.py` |
| Dữ liệu cảnh | `data/projects/<pid>/stage/`: `stage.json`, `grid.json`, `blocking.json`, `shot_specs.json`, `setups.json`, `stage_feedback.jsonl`, ảnh |
| Cache sân khấu | theo (sha map, place, spot): tính lại khi map đổi |

## 10. Thứ tự làm (từ trạng thái hiện tại)
| # | Việc | Chi phí |
|---|---|---|
| V1 ✅ | Bộ giải máy K3 (mục 6) + luật S1–S6 thay L5/L6/L8; nhãn chỉ cho `chinh`/`phu`; vẽ vùng đích lên clay | 0 USD |
| V2 ✅ | Thử V1 trên #24 bằng `shot_specs` viết tay cho 9 shot (lấy từ góp ý của người dùng). So với 72 điểm dò mù: số đạt, độ lệch vùng, thời gian — kết quả ở Phụ lục A | 0 USD |
| V3 | Director viết `blocking` + `shot_specs` (prompt dạng cách nghĩ có lý do), thay phần "Claude duyệt render" của G0 | Claude ≈ vài cent mỗi cảnh, báo trước |
| V4 | #24: tấm ghép → người duyệt → báo giá vẽ lại shot 1–9 | báo giá |
| V5 | Nối vào luồng (sau cờ), đo `level_9_4` và các chỗ đứng khác, Bàn đạo diễn 3D (G3) | 0 USD |
| V6 | Nhánh B (mục 12): bối cảnh chỉ có 1–3 ảnh — hiệu chỉnh ảnh, tách lớp chiều sâu (model cục bộ, tải trọng số ≈ 100 MB một lần — HỎI trước), khối thay thế theo kích thước suy, chiếu ngược kiểm lệch, luật P5 vùng máy; thử trên 1 bối cảnh Kho chỉ có ảnh | 0 USD (+ vẽ thêm góc: báo giá) |
| V7 | Đọc lại hai chiều R1–R2 (mục 13) cho cả hai nhánh; đo lại V3 #24 xem tăng từ 7/9 | Claude ≈ vài chục cent, báo giá |

## 11. Quy trình CHUẨN (rút từ V1–V3 trên #24, áp cho mọi kịch bản)

**11.1 So sánh V2 (người viết tay) với V3 (Director viết, 09/10).**

| | V2 — tay (Claude Code + người dùng) | V3 — Director (`claude-sonnet-5`, prompt 29) |
|---|---|---|
| Lượt 1 | 6/9 đạt (sau 3 lần sửa mâu thuẫn do bộ giải báo trước Blender) | 4/9 đạt |
| Lượt cuối | 9/9 — cần 4 quyết định của người dùng (tháp, shot 4, shot 5–7 theo emote, shot 3 qua vai) | 7/9 sau 1 lượt tự sửa theo số đo (lượt 2) |
| Lỗi hay gặp (cả hai) | vùng dọc không khả thi theo độ cao máy; khoảng cỡ quá hẹp; luật tự bịa (tháp); người chồng lên đạo cụ | như bên trái + 3 thứ chính một shot; đòi "thấy nghiêng" trái với chỗ máy bị ép tới |
| Làm tốt | — | theo đúng lời người dùng (POV + lùi + rung, qua vai `thay_min`, sau lưng-chéo, không ràng buộc tháp); tự ghi `can_hoi` khi thiếu số |
| Máy so với bản tay (shot cùng đạt) | — | lệch 0,5–2,8 m, 4–53°: nhiều lời giải đúng — khác nhau là phong cách, không phải sai |
| Chi phí / thời gian | 0 USD Claude, nhiều giờ người | ≈ 0,53 USD (2 lượt, 1 lần hỏi lại vì sai mẫu), ≈ 10 phút (Claude ≈ 3 phút/lời gọi + Blender ≈ 1 phút/lượt) |

Kết luận: Director viết được dàn cảnh + yêu cầu khung dùng được khi có (a) prompt cách nghĩ có lý do, (b) code kiểm chặt câu trả lời,
(c) vòng sửa bằng SỐ ĐO thật. Phần còn lại sau 2 lượt là chỗ cần người quyết (thẩm mỹ / chấp nhận che), không phải lỗi máy.

**11.2 Quy trình chuẩn — 7 bước** (mỗi bước: ai làm, tốn gì, khi nào dừng):

| # | Bước | Ai | Chi phí | Dừng / chuyển |
|---|---|---|---|---|
| B0 | **Sân khấu** (K1): đo sàn, mốc, ô cấm; đạo cụ có kích thước từ Kho (thiếu → HỎI người dùng, không tự đặt) | code + Blender | 0 USD, ≈ 20 s, một lần mỗi chỗ đứng (cache) | thiếu số đạo cụ → hỏi |
| B1 | **Đề bài**: kịch bản từng shot (ghi chú khung cũ = chỉ để hiểu ý), chiều cao hồ sơ, vật cố định, ô sàn cấm, lời người dùng, tham chiếu | code | 0 USD | — |
| B2 | **Director viết** `blocking` (nhịp) + `shot_specs` theo prompt 29 | Claude | ≈ 0,15–0,3 USD / cảnh 9 shot, BÁO GIÁ trước | — |
| B3 | **Kiểm câu trả lời** (`stage_director.validate_answer`): đủ shot, vật cố định không bị dời, người không chồng đạo cụ, vùng không mâu thuẫn, chuyển động hợp lệ | code | 0 USD | sai → hỏi lại 1 lần (kèm lý do) |
| B4 | **Giải máy** (K3, ms) + **đo Blender** (K4, ≈ 40 s / 9 shot, cả khung cuối khi máy chuyển động) | code | 0 USD | shot hỏng → B5 |
| B5 | **Vòng sửa tự động**: gửi Director đúng số đo / lời khuyên của shot hỏng; shot đạt giữ nguyên | Claude | như B2 | ≤ 2 lượt Claude (CHUAN_XAY_DUNG) |
| B6 | **Người duyệt tấm ghép** (hình phác + vùng đích + khung cuối + luật): shot còn hỏng hiện 2–3 LỰA CHỌN cụ thể (vd qua vai: lệch máy / chấp nhận che / đổi góc) | người dùng | 0 USD | quyết định → ghi vào spec (`thay_min`, `pov`, `may`…) + `stage_feedback.jsonl` |
| B7 | **Khóa**: `setups.json` = camera của nền 3D; `pov` / `may` / `rung` → câu chuyển động của prompt video; rồi mới vẽ ảnh (báo giá) | code | ảnh: theo bảng giá | — |

**11.3 Nguyên tắc cố định** (đã vào prompt 29 + code kiểm):
1. Không biến góp ý / ghi chú cũ thành luật cứng; thứ không ai yêu cầu → không ghi (tháp #24).
2. Người = vị trí MẮT trên lưới một phần ba; đạo cụ = tâm phần thấy.
3. Tối đa 2 thứ chính / shot; cỡ là một khoảng rộng; người bò / nằm → khoảng rất rộng.
4. Vùng phải khả thi với độ cao máy (máy ngang tầm mắt → đạo cụ thấp ở giữa khung) và với khoảng cách giữa các thứ chính.
5. `thay` phải khớp phía máy bị ép tới; không chắc → bỏ.
6. Máy thấp hơn miệng vật chắn không nhìn vào trong được → người trong vật đứng mép gần, hoặc máy cao hơn.
7. Qua vai → `thay_min` cho vật bị vai che; ngưỡng CHUNG chỉ đổi khi ≥ 3 phản hồi cùng chiều.
8. Cảm xúc của nhân vật → `pov` + `may` (lùi khi sợ, tiến khi bị hút vào), rung ghi cho prompt chuyển động.
9. Có tham chiếu (emote) → bám góc máy của tham chiếu.
10. Lỗi đo phát hiện khi chạy thật sửa tận gốc trong code (đo sàn trước khi dựng khối, khe cổ người nộm, mốc rộng, điểm mặt).

**11.4 Tối ưu tiếp (chưa làm):** (a) đưa lời khuyên giai đoạn (a) — miễn phí, mili giây — cho Director NGAY trong lượt 1 bằng công cụ
(tool use) thay vì chờ hết lượt; (b) thử `effort: low` để giảm token suy nghĩ (lượt 1 ra 18k token); (c) nối vào luồng sau cờ (V5): camera
từ `setups.json` thay `plate_camera.camera_for`, câu chuyển động từ `pov`/`may`.

## 12. Nhánh B — bối cảnh KHÔNG có mô hình 3D, chỉ có 1–3 ảnh (người dùng 09/10; Kho: 87/90 bối cảnh thuộc nhánh này)

Ý người dùng: (1) phân tích ảnh, tách lớp theo chiều sâu; (2) vẫn xếp vào sân khấu 3D; (3) vật không có kích thước → suy từ tỉ lệ với
vật quen (ô tô to hơn người, súng vừa tay người, bóng cỡ đầu người…); (4) xếp lớp không lệch nhiều so với thực tế, thiếu góc thì vẽ thêm;
(5) các bước khác như quy trình, Director ↔ code trao đổi HAI CHIỀU, tự kiểm lẫn nhau (mục 13). Cách làm:

**12.1 Hiệu chỉnh ảnh trước (vì mọi thứ sau đều dựa vào máy ảnh của tấm chụp).** Mỗi ảnh ra: tiêu cự (EXIF, không có thì từ điểm tụ của
các đường thẳng song song), đường chân trời (→ máy ngẩng/cúi), độ cao máy (từ một vật đứng trên sàn biết chiều cao: người, cửa, bậc).
Ảnh không có đường thẳng nào và không có vật biết cỡ → ghi "độ tin thấp", người duyệt thấy.

**12.2 Tách lớp theo chiều sâu.** Model ước lượng chiều sâu chạy CỤC BỘ (Depth Anything V2 / bản "metric"; 0 USD/lần, tải trọng số một lần)
cho bản đồ sâu tương đối → nhân hệ số để khớp vật biết cỡ (12.4) → mét. Rồi tách thành lớp:
- **Sàn** = mặt phẳng khớp các điểm sàn (pháp tuyến hướng lên) → z = 0 của sân khấu, đứng được hay không theo vùng sàn thấy trong ảnh.
- **Vật giữa** (người đứng sau / trước được, che được): mỗi vật một khối thay thế (hộp / trụ) đúng kích thước 12.4 tại chỗ chân nó chạm sàn,
  mặt trước dán ảnh tách nền của vật → có che khuất thật, có chỗ đặt nhân vật.
- **Nền xa** (nhà, núi, trời): tấm ảnh (card) ở khoảng cách trung vị của lớp, hoặc vòm trời.
- Đường giáp ranh giữa lớp: tách theo bước nhảy chiều sâu, không theo tên vật.

**12.3 Xếp lên CÙNG một sân khấu (1–3 ảnh).** Ảnh 1 định gốc O và trục. Ảnh 2–3: khớp điểm đặc trưng (OpenCV) + vật chung → vị trí máy của
ảnh đó trên sân khấu. **Kiểm không lệch thực tế** = chiếu ngược từng lớp vào từng ảnh gốc, đo lệch (% khung): ≤ 3 % đạt, lớn hơn → báo vật
nào lệch ở ảnh nào (không im lặng). Vật thấy ở 2 ảnh cho 2 ước lượng vị trí → trung bình có trọng số, lệch > 15 % → hỏi Director / người.

**12.4 Kích thước vật không có số.** Thứ tự nguồn: (1) Kho (`height_m`) → (2) đo trong ảnh so với vật biết cỡ CÙNG lớp sâu (tỉ lệ pixel ×
khoảng cách) → (3) Director suy theo vật quen, ghi KHOẢNG + lý do ("ô tô con cao 1,4–1,6 m, dài 4–4,8 m"; "súng trường dài 0,9–1,1 m, vừa
hai tay người"; "bóng đường kính ≈ 0,22 m ≈ cỡ đầu người"). Code so (2) với (3): khớp ±20 % → dùng; lệch → đọc lại cho Director (mục 13),
vẫn lệch → hiện cho người dùng chọn. Số suy luôn gắn nhãn "ước lượng" trong dàn cảnh và tấm ghép; người dùng sửa một lần → ghi về Kho.

**12.5 Vùng máy được phép (luật mới P5).** Sân khấu từ ảnh chỉ đúng gần góc chụp (thị sai nhỏ): máy lệch phương vị > ≈ 25° so với ảnh gần
nhất, hoặc nhìn sang phía không ảnh nào thấy → lộ mặt sau tấm ảnh / chỗ trống. Bộ giải coi đó là ràng buộc như ô cấm: ưu tiên lời giải trong
vùng phủ; nếu ý đồ bắt buộc ra ngoài → **vẽ thêm** góc đó (model ảnh, có ảnh gốc làm tham chiếu, BÁO GIÁ ≈ 0,05 USD/ảnh) → tách lớp ảnh vẽ
thêm như 12.2 → kiểm chiếu ngược khớp phần trùng với ảnh gốc trước khi dùng.

**12.6 Các bước còn lại như mục 11** (B1–B7); B0 thay bằng 12.1–12.5; tấm ghép B6 thêm: ảnh gốc + chiếu ngược các lớp + vùng máy được phép.

## 13. Trao đổi HAI CHIỀU Director ↔ code (áp cho cả hai nhánh — người dùng 09/10)

Mỗi chỗ một vai đưa thông tin cho vai kia, vai nhận phải **đọc lại bằng lời của mình** để vai đưa xác nhận — như đọc lại lệnh trong buồng
lái. Lý do: V3 #24 cho thấy Director có ý đúng nhưng viết số làm ra hình khác ý (thấy nghiêng ↔ máy ở trước mặt); còn code tính đúng số
nhưng không biết ý có được giữ không. Ba điểm đọc lại, mỗi điểm ≤ 2 vòng:

| Điểm | Code đọc lại cho Director | Director trả lời | Code làm gì |
|---|---|---|---|
| R1 dàn cảnh | mỗi nhịp: "Kelly cách giếng 1,05 m phía Nam, quay mặt 350° (về giếng); yêu nữ trong lòng giếng, đầu nhô 0,48 m" + ảnh nhìn từ trên | từng dòng: `dung` / `sai` + sửa (khóa có sẵn, không văn xuôi) | sửa → dựng lại → đọc lại phần đổi |
| R2 góc máy | mỗi shot: "máy ô L9 cao 0,6 m nhìn 326°; trong khung: Kelly trái thấy lưng 93 %, giếng giữa 100 %; khung cuối …" + hình phác | quan sát theo danh mục (enum) trên hình phác: thứ chính đúng chỗ? hướng thấy? cảm giác khớp `muc_dich`? | **code áp luật** từ quan sát (bài học Tổ QC: model thấy đúng nhưng suy sai) → shot nào lệch ý → quay lại B2/B5 |
| R3 sau khi vẽ ảnh | `plate_layout_qc` so ảnh vẽ với render nền: vật lệch chỗ / thiếu | xác nhận lỗi có làm hỏng ý đồ không | vẽ lại có đổi đầu vào (≤ 3) |

Chiều ngược lại cũng bắt buộc: code thiếu số / gặp mâu thuẫn → HỎI Director bằng câu cụ thể (đã có: `advice`, `can_hoi`), không tự chọn.
Chi phí: R1 + R2 thêm ≈ 1–2 lời gọi Claude ngắn mỗi vòng (có hình phác) — báo giá trước như B2.

---

## Phụ lục A — Số đo thật #24 (09/10, 0 USD)
- **Bước 0** (`40f9c69`):
  - O nằm trên CLK_OUT_Base002, sàn dốc 0,02°;
  - lưới 400 ô: 378 cùng mặt sàn, 22 tầng khác, 48 vật chắn, 15 có mái che;
  - hình học khớp render (nhãn, chân trời, tháp 16,04 m phía Bắc);
  - clay 0,2–0,4 s, nền thật 3–4 s, một lượt Blender ≈ 22 s.
- **Bước 1–2** (`02ebf0a`):
  - spot `plaza_front` đã nâng 9,38 → 9,83 (có bản sao CSDL trước khi sửa);
  - 9 shot cũ: đỉnh đầu Kelly lọt ra ngoài khung 8/9 shot, máy shot 4 nằm trong giếng, shot 3 cúi −35°, vật cản bằng 0;
  - dò 72 điểm mù: R1 10 đạt, R2 2 đạt, R3 7 đạt.
- **Yêu nữ trong giếng** (`4aa946d`):
  - R2 (qua vai, cúi) thấy yêu nữ 30–33 %, đúng ý đồ;
  - R1 (toàn cảnh mở) "đạt luật chung" mà yêu nữ chỉ thấy 4–19 %, bị Kelly che. Đây là lý do có v2: Director ghi thứ `chinh`, máy được giải từ yêu cầu.
- **Người dùng quyết 09/10:**
  - sửa spot `plaza_front`; Bắc = +y của model;
  - giếng cao 0,9 m, đường kính 1,5 m; yêu nữ cao 1,7 m;
  - nhãn ngoài khung vẽ thành mũi tên ở mép;
  - luật theo yêu cầu của Director.
- **V1 + V2 (09/10 tối, 0 USD)** — `core/stage_solver.py`, `tools/stage_grid.py v2`, đầu vào viết tay ở `tools/experiments/stage_v2_p24/`, kết quả `data/projects/24/stage_v2/` (ngoài git):
  - K3 giải 9 shot trong 0,1–0,6 s; K4 Blender đo 250 phương án (≈ 28 / shot) trong ≈ 32–40 s. Dò mù cũ: 216 điểm cho 3 yêu cầu, ≈ 29 s đo.
  - Vòng K5 lần 1 (bộ giải tự báo, chưa chạy Blender): 3 yêu cầu viết tay mâu thuẫn hình học — shot 1 giếng "1/3 dưới" khi máy ngang tầm mắt; shot 2 MS quá chặt để Kelly trái + giếng phải; shot 9 Kelly–yêu nữ chỉ cách 0,85 m. Sửa yêu cầu (ghi `_sua_k5` trong file).
  - Kết quả: **7/9 shot có máy đạt đủ P1–P4 + S1–S6** (1, 2, 4, 5, 6, 8, 9). Hỏng thật, cần sửa dàn cảnh (người dùng / Director quyết): shot 3 qua vai — Kelly che giếng còn thấy 33 %; shot 7 — yêu nữ đứng che giếng còn 13 %. Shot 5 đạt sát ngưỡng (yêu nữ thấy 60,7 %, thành giếng che phần dưới).
  - Lỗi đo bắt được khi chạy thật → sửa tận gốc: (1) đo sàn cho mọi vật TRƯỚC khi dựng khối (yêu nữ cách người nộm Kelly 5 cm bị đặt xuống tầng −6,18 m → thấy 0 %), có cảnh báo khi người nộm không đứng trên mặt sàn; (2) điểm phủ người thêm điểm mặt/mũi (mũi Kelly "không được có" lọt góc shot 7 mà 27 điểm thân không bắt).
  - Lần sửa thứ 3 (cùng tối): mốc phủ điểm ra cả bề ngang (tháp rộng 9,35 m lọt MÉP khung mà trục ngoài khung → luật "không được có tháp" qua oan). Đo lại: **6/9 đạt** — shot 1 nay hỏng thật (tháp thấy 17,8 % < 25 %, bị tường quảng trường che).
  - Người dùng hỏi 09/10: shot 4 nhìn sau lưng Kelly ngã ngửa? + emote = yêu nữ chui lên, bò ra, ĐỨNG TRƯỚC giếng (giữ dàn cảnh, shot 7 sửa bằng góc máy). Thử `shot_specs_alt_4_7.json` → `data/projects/24/stage_v2_alt/`: **42 (sau lưng-chéo, máy 0,63 m) và 43 (máy thấp 0,6 m) đạt**; 41/44 (máy cao nhìn qua đầu Kelly) hỏng: thấy tháp, cúi chưa tới −20°; shot 7: **73 đạt** (giếng là thứ PHỤ sau lưng yêu nữ), 71/72 hỏng. Luật mâu thuẫn "cùng vùng" sửa: chỉ khi cùng cả hàng dọc.
  - Thêm (09/10 khuya, người dùng chốt): `"pov": "<vật>"` = máy ở mắt người đó, người đó bỏ khỏi khung, chỉ giải hướng nhìn; `"may": {"kieu": "lui"|"tien", "m": …, "rung": …}` = máy dời song song theo hướng nhìn, luật chấm cả KHUNG CUỐI (bỏ cỡ + vùng; rung chỉ là ghi chú cho prompt chuyển động). Người trong giếng ghi được chỗ (`at` + `in`: bám mép gần). Người nộm: thân lên tới tâm đầu (khe cổ làm người nộm bò 0,6 m mất 46 % điểm). **#24 sau các quyết định: 9/9 đạt** — shot 3 qua vai: người dùng chấp nhận vai che một phần giếng → `"thay_min"` = ngưỡng S1 riêng của một thành phần trong một shot (ngưỡng chung không đổi; phản hồi ghi `stage_feedback.jsonl`).
- **Chưa tái hiện được:** lỗi "tường cao che" của shot 4 và 5. Có thể ảnh người dùng chê được vẽ từ camera cũ, khác camera hiện tại.

## Phụ lục B — Vì sao bỏ cách G0 cũ
G0 cũ để Director đoán phương vị máy khi không thấy sân khấu: giếng và nhân vật không có trong 3D. Sau đó Claude nhìn render để phán những điều code đã biết bằng số; máy nghiêng −6° bị khai là "cúi". Chạy thật tốn ≈ 0,37 USD và lộ ra 4 lỗi cùng một gốc. Phần còn dùng được: sơ đồ cảnh, góc máy dùng lại, luật trục / gia đình nền (cờ `director_camera_plan` vẫn TẮT).
