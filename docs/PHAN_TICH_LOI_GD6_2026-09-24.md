# Phân tích lỗi đợt gen thật GĐ6 (2026-09-24) — lỗi nằm ở đâu, sửa thế nào

**Bối cảnh.** Kịch bản Kenta, 3 phương án (V0 mỗi cảnh một clip · V1 từng shot · V2 Kling multi-shot), 9:16, chế độ thử rẻ,
phong cách `ANIME_CGI`, chạy tự động qua Dashboard với Deepix + ClipAI + Claude CLI thật. Đã chi **$42,88 / $50** (video) + 53 ảnh,
nhưng phần lớn tiền đi vào **gen lại**: V2 gửi 19 lần Kling (245 giây) để có 21/26 shot, V0 gửi 8 lần cho 3 cảnh.
Người dùng yêu cầu: tìm lỗi nằm ở đâu thay vì gen lại liên tục không có chủ đích.

## 1. Cách phân tích

Lần ngược chuỗi đầu vào của từng clip bị QC loại, dừng ở **lớp đầu tiên đã sai**:

```
Ảnh tham chiếu (kho) → Character Bible (chữ + Lock) → prompt ảnh → ảnh khung đầu đã duyệt
                     → QC đồng bộ cả bộ ảnh (có thể sửa ảnh)       → motion prompt → model video → clip
```

Dữ liệu dùng: điểm QC từng tiêu chí (`qc_results`), lý do loại (`review_log`), prompt thật đã gửi (`motion_prompts`), ảnh nguồn của
clip (`jobs.source_job_id`), khung hình cắt từ clip, ảnh tham chiếu trong kho (`asset_images`).

## 2. Lỗi dồn vào đâu (số liệu)

| Cách gen | Model | Số clip có QC | Điểm QC TB | Sai nhân vật (identity < 0,7) | Sai hành động (motion_match < 0,7) |
|---|---|---|---|---|---|
| V1 từng shot | Seedance 2.0 Fast, clip 4s | 5 | **0,76** | **0/5** | 2/5 |
| V2 multi-shot, shot đầu nhóm | Kling | 4 | 0,64 | 2/4 | 2/4 |
| V2 multi-shot, shot sau trong nhóm | Kling | 12 | **0,60** | **6/12** | **10/12** |
| V0 clip dài 15s | Kling / Seedance | 4 | 0,65 | 1/4 | 4/4 |

→ Lệch nhân vật gần như chỉ xảy ra ở phần video **không có ảnh bám theo** (shot sau trong nhóm multi-shot, đoạn sau của clip dài).
Clip ngắn bám ảnh khung đầu (V1) giữ nhân vật tốt.

## 3. Nguyên nhân gốc (xếp theo mức ảnh hưởng)

### R1 — Character Bible mâu thuẫn với ảnh tham chiếu *(lớp: Character Bible — gốc của nhiều lỗi khác)*
- Ảnh tham chiếu Kelly (7 ảnh, thống nhất): **tóc bob đen ngắn có mái, vòng cổ, bộ thể thao vàng quần dài**, súng bắn tỉa.
- Character Bible của V1/V2: "dark hair in a **high ponytail**", Lock: "sporty jacket and **shorts** … **anime cel-shade look**".
- Maxim: Bible "short **dark** hair"; ảnh tham chiếu: **tóc bạc, mũ lưỡi trai ngược**, áo da + hoodie đỏ.
- V0 (Director chạy lại sau) mô tả Kelly đúng ("chin-length bob with bangs, choker") nhưng **Lock vẫn là bản cũ "ponytail"** (chép khi
  nhân bản) → một nhân vật có hai chỉ dẫn trái nhau.
- Vì sao: lần chạy Director đầu **không đọc được ảnh tham chiếu** (Dashboard chạy với thư mục làm việc sai → đường dẫn tương đối
  `data\assets\…` không tồn tại → Director viết mô tả từ chữ). Tôi đã nhận thấy và **đánh giá sai** là mô tả vẫn đúng.
- Hậu quả: prompt ảnh, QC ảnh, QC đồng bộ và QC video đều nhận chỉ dẫn trái với ảnh → Kelly lúc đuôi ngựa lúc bob, Maxim lúc tóc đen
  lúc tóc bạc; QC loại ảnh đúng theo tham chiếu vì "sai Bible" và ngược lại.

### R2 — Xung đột phong cách *(lớp: thiết lập dự án)*
- Chọn `ANIME_CGI` + Lock "anime cel-shade look", trong khi ảnh tham chiếu và ảnh Deepix là **CGI bán tả thực**.
- Hậu quả: ảnh ra lẫn hai kiểu (QC đồng bộ V2 đòi vẽ lại S18, S22 "không cel-shading, không anime phẳng"); Kling vẽ shot S17 thành
  **anime 2D phẳng**; ảnh quá giống thật còn bị Seedance chặn "giống người thật".

### R3 — QC đồng bộ cả bộ ảnh không có "chuẩn" và tự sửa sai *(lớp: QC — lỗi trong pipeline)*
- Claude xem **một tấm ghép** mọi ảnh, so ảnh với "số đông" trong lô, không so với ảnh tham chiếu; không biết mỗi ảnh có những ai.
- Bằng chứng: V0 S02 ảnh gốc (job 58) **đúng Kenta**; QC đồng bộ nhận nhầm thành **"Maxim's sword-slash pose"**, loại ảnh, và câu
  sửa được đưa **nguyên văn** vào prompt gen lại → ảnh mới (job 86) vẽ **Maxim có búi tóc cầm katana**, hai Maxim trong khung → clip
  15s làm từ ảnh này sai từ khung đầu.
- Mỗi dự án nó chọn một "Kelly chuẩn" khác: V1 "đuôi ngựa nâu + bộ vàng", V2 "áo đen trắng + quần short", V0 "bob đen, không
  đuôi ngựa". V2 S09 câu sửa nhắc **Kelly dù shot chỉ có Kenta**.
- Đã gen lại 15 ảnh theo QC đồng bộ (V1 9, V2 5, V0 1).

### R4 — Nhóm multi-shot gom cả shot không có nhân vật trong ảnh đầu nhóm *(lớp: chia nhóm + prompt)*
- Kling multi-shot chỉ nhận **ảnh của shot đầu nhóm**. Nhóm S14–S17: ảnh đầu là cận Maxim; các shot sau là Kenta chạy, Kenta chém,
  cận Kelly → Kling không có hình Kenta/Kelly nào.
- Prompt từng shot chỉ gọi **tên** ("Kenta", "Kelly"), không tả ngoại hình (giới hạn 512 ký tự/shot) → Kling tự bịa: S15 một người
  choàng áo chung chung, S16 lính mặc giáp, S17 cô gái anime tóc nâu áo giáp (không phải Kelly).

### R5 — Clip dài nhiều nhịp *(lớp: cách chia cảnh v2)*
- V0: mỗi cảnh 15s với nhiều hành động + 3–4 người nói → motion_match thấp ở cả 4 clip (ví dụ Maxim đâm tường sai tư thế, kết thúc sai).
  Đây là giới hạn đã dự đoán của cách v2.

### R6 — Chính sách tự gen lại video không hội tụ *(lớp: QC video + tự động)*
- Ngưỡng 0,82 ở chế độ tự động; mỗi lần loại → gen lại (multi-shot: cả nhóm 15s). Nguyên nhân R1–R4 **không đổi** giữa các lần gen
  nên lần sau sai y như lần trước — tiền mất mà điểm không lên (V2 nhóm S35–S38: 0,55 → gen lại vẫn loại).
- Lỗi motion_match nhỏ (ví dụ "cúi thấp hơn một chút") cũng kích hoạt gen lại một clip trả tiền.

### R7 — Lỗi tỉ lệ: người ↔ cảnh, người ↔ người, cỡ cảnh bị bỏ qua *(lớp: previz + prompt ảnh — người dùng phát hiện)*
Soi toàn bộ ảnh khung đầu đã duyệt (V1 26, V2 6, V0 3):
- **Cỡ cảnh không theo kế hoạch:** V1 S04/S07/S17 "MCU" ra toàn thân; S10 "ECU" ra cảnh rộng 3 người; S20 "CU" ra cảnh từ trên cao,
  người rất nhỏ; S26 "CU" ra toàn thân ngồi; V2 S22 "CU Kenta" ra **cảnh nhìn từ trên cao với Kenta tí hon trên bãi cỏ**.
- **Tỉ lệ giữa nhân vật trôi:** V1/V2 S18 Maxim (17 tuổi) chỉ cao ~50–60% Kenta, như trẻ con; V1 S24 ba người gần bằng nhau.
- **Tỉ lệ người ↔ cảnh trôi:** bức tường lúc cao quá đầu người ngồi, lúc ngang vai người đứng, lúc ngang đầu; ngôi nhà mái đỏ của ảnh
  nền nằm cùng một chỗ trong khung ở hầu hết shot, bất kể góc máy.
- QC ảnh **có thấy** (điểm "tỉ lệ" nhiều ảnh 0,5–0,7, "khớp bố cục" 0,45–0,6) nhưng tỉ lệ/bố cục không phải tiêu chí chặn → vẫn tự duyệt.

Nguyên nhân (lần ngược từng lớp):
1. **Layout (previz 2D) sai và được gửi làm ảnh tham chiếu số 1 cho Deepix.** Nền layout là ảnh tài nguyên "Cổng Trời" — một ảnh
   **chụp từ trên cao** (bản đồ), không có bức tường; nhân vật được dán như hình cắt ~20 px theo phối cảnh của ảnh nền đó, **không
   theo cỡ cảnh** (layout của shot MCU S04 là một Maxim tí hon ở xa). Module layout được thiết kế cho cảnh rộng dựng trên ảnh nền ngang
   tầm mắt; dùng cho shot cận thì nó chỉ dẫn sai — V2 S22 chép nguyên bố cục này. QC "khớp bố cục" lại so với chính layout sai.
2. **Ảnh của shot trước được gửi kèm làm tham chiếu "nối liền"** kể cả khi shot trước khác hẳn cỡ cảnh/góc máy → bố cục shot trước
   lấn sang shot sau.
3. **Prompt ảnh dùng ký hiệu kỹ thuật** ("Vertical MCU eye level", "MS", "CU") — không nói rõ khung cắt ở đâu; khung dọc 9:16 càng
   dễ ra toàn thân.
4. **Không có thang tỉ lệ nào**: Character Bible không có chiều cao/vóc dáng; prompt chỉ có tuổi ("17-year-old slightly stocky boy")
   → Deepix vẽ Maxim/Kelly như trẻ con cạnh Kenta 38 tuổi; chiều cao bức tường chỉ có chữ "shoulder-high" trong mô tả bối cảnh.
5. QC tỉ lệ/bố cục không chặn (xem trên).

### Lỗi phụ đã sửa trong lúc chạy (đều đã commit)
Seedance không nhận khung đầu + ảnh tham chiếu; Seedance chặn "giống người thật"/"bản quyền" → tự chuyển Kling; Kling multi-shot
giới hạn 512 ký tự/shot; chế độ tự động hỏi Claude 1.500+ lần khi hết hạn mức; giữ được clip QC đã loại thay vì gen lại.

## 4. Phương án sửa (theo lớp, rẻ → đắt)

| # | Sửa | Chặn nguyên nhân | Tốn credit? |
|---|---|---|---|
| F1 | **Kiểm Bible ↔ ảnh tham chiếu** trước khi gen ảnh: Claude so mô tả + Lock với ảnh tham chiếu từng nhân vật (1 lần/nhân vật), báo và chặn khi lệch; Director **bắt buộc thấy ảnh** (báo lỗi nếu ảnh tham chiếu không đọc được thay vì im lặng viết từ chữ); nhân bản/chạy lại Director thì viết lại Lock cùng mô tả | R1 | Không (chỉ Claude) |
| F2 | **Phong cách lấy từ ảnh tham chiếu**: kiểm xung đột `style_profile`/Lock với ảnh tham chiếu; với nhân vật Free Fire gợi ý `REAL_CGI_VFX`/CGI bán tả thực | R2 | Không |
| F3 | **QC đồng bộ có chuẩn**: đưa ảnh tham chiếu + danh sách nhân vật của từng ảnh vào QC; câu sửa không được nhắc nhân vật không có trong shot, không đổi tên nhân vật; mặc định **chỉ báo**, người duyệt mới gen lại | R3 | Không |
| F4 | **Chia nhóm multi-shot theo nhân vật**: shot có nhân vật không xuất hiện trong ảnh đầu nhóm → mở nhóm mới (có ảnh riêng); mỗi prompt shot thêm **thẻ ngoại hình ngắn** lấy từ Lock (≤ 512 ký tự) | R4 | Không |
| F5 | **Chẩn đoán trước khi gen lại** (`core/diagnose.py`): khi QC loại, xác định lớp sai theo chuỗi ở mục 1 (ảnh khung đầu đã sai? nhân vật không có trong ảnh? Bible lệch tham chiếu? prompt quá nhiều nhịp cho thời lượng?) → đề xuất sửa đúng lớp; chỉ tự gen lại khi lỗi là **ngẫu nhiên của model** (đầu vào đúng), tối đa 1 lần; motion_match nhỏ chỉ báo | R6 | Giảm |
| F6 | V2/v2: cảnh dài nhiều nhịp → gợi ý chia shot (đã là hướng v3) | R5 | — |
| F7 | **Layout chỉ dùng khi hợp:** chỉ gửi layout cho shot rộng (WS/EWS) có ảnh nền **cùng góc máy** (bỏ ảnh nền chụp từ trên cao cho shot ngang tầm mắt — phân tích ảnh nền đã có trường góc máy); shot MS/MCU/CU/ECU dùng **khung người mẫu theo cỡ cảnh** (người lấp khung đúng chuẩn: MCU = từ giữa ngực trở lên…) thay cho ảnh nền + hình cắt tí hon | R7.1 | Không |
| F8 | **Nối ảnh shot trước chỉ khi cùng cỡ cảnh + góc máy** và liền mạch | R7.2 | Không |
| F9 | **Prompt ảnh nói rõ khung cắt** thay cho ký hiệu (MCU → "medium close-up, framed from mid-chest up, face in the upper third"), có dòng "không vẽ toàn thân" cho shot cận | R7.3 | Không |
| F10 | **Thang tỉ lệ trong Character Bible:** chiều cao (cm) + vóc dáng từng nhân vật (Kelly/Maxim 17 tuổi = người lớn trẻ, không phải trẻ con), mốc bối cảnh (tường cao ~1,2 m = ngang ngực Kelly); đưa vào mọi prompt ảnh có ≥ 2 người hoặc có mốc; kiểm với ảnh tham chiếu (F1) | R7.4 | Không |
| F11 | **Tỉ lệ + bố cục thành tiêu chí chặn** (mức sàn ~0,6) và đi qua chẩn đoán F5 (sửa đúng lớp, không gen lại mù) | R7.5 | Giảm |

## 5. Đề xuất bước tiếp theo
1. Làm F1 → F11 (không tốn credit), có test — ưu tiên F1 (Bible ↔ tham chiếu), F3 (QC đồng bộ có chuẩn), F7–F10 (layout + khung cắt + thang tỉ lệ), F5 (chẩn đoán trước khi gen lại).
2. Kiểm lại **chỉ phần chữ/ảnh**: chạy Director lại (thấy ảnh), kiểm Bible ↔ tham chiếu, gen lại ảnh khung đầu của **một cảnh**
   (ví dụ cảnh 2 — cảnh lỗi nhiều nhất) cho V1/V2 → xem ảnh trước khi gen video.
3. Chỉ khi ảnh đúng mới gen video cảnh đó (~$3–5), so với bản cũ. Phần còn $7,1 của trần $50 đủ cho bước này; làm lại cả phim cần
   bạn duyệt thêm ngân sách.
