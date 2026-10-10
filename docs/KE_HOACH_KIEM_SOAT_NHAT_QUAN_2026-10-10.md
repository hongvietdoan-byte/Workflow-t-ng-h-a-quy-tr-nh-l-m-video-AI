# Kế hoạch: Quy trình kiểm soát chặt chẽ và nhất quán giữa khâu làm và khâu kiểm — BẢN HỢP NHẤT v2 (10/10/2026)

> Yêu cầu người dùng 10/10: "một plan chi tiết hoàn chỉnh để rà soát, kiểm tra tính chặt chẽ và nhất quán của các khâu. Lỗi đã sửa qua
> nhiều dự án mà vẫn chưa hoàn thiện — cần một quy trình thực sự hoàn chỉnh."
> Bản v2 viết lại toàn bộ sau: thẩm định độc lập 6,2/10 (`docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md`), nghiên cứu thị trường
> (`docs/NGHIEN_CUU_THI_TRUONG_KIEM_SOAT_VIDEO_AI_2026-10-10.md`) và các chốt của người dùng (mục A). Bản v1 (các lần vá 9b–12) ở commit
> `a9e19ea` — đã thay hoàn toàn, không dùng nữa. Nền: `docs/RA_SOAT_KHAU_VA_KIEM_TRA_2026-10-10.md`.
> **Trạng thái (10/10): thẩm định lần 2 = 7,1/10 "sửa nhỏ rồi build K0a" → đã sửa 3 điểm CAO (3.3b, 3.3 khai/so + học việc, K1a/K1b) + A14–A17; build K0a.**

## A. Các chốt của người dùng (10/10) — nguồn duy nhất cho phạm vi

| # | Chốt |
|---|---|
| A1 | Áp cho **dự án mới**. Dự án cũ chỉ dùng làm ca kiểm hồi quy (nhập Bảng ý đồ bằng tay, đánh dấu `ca_vang_tay`). |
| A2 | Người dùng sửa shot bằng **Bảng ý đồ (BYĐ)**, không sửa prompt; **không có chữ nào không được kiểm**. |
| A3 | Ngưỡng nghiệm thu (mục 9) **tạm giữ**. |
| A4 | Thứ tự đợt giữ (ảnh trước, video sau) **và mức kiểm ảnh, video, âm thanh / phụ đề / dựng chặt NHƯ NHAU**. |
| A5 | **Không phụ thuộc lỗi đã xảy ra**: độ phủ đến từ cấu trúc (mục 4), ca vàng chỉ là kiểm hồi quy. |
| A6 | **Lẽ thường không phải luật tuyệt đối** (vd bóng + ô tô lơ lửng do hiệu ứng game) → chuẩn so theo tầng (mục 5). |
| A7 | Chi **≤ 1 USD** (trần cứng) cho so A/B chất lượng prompt trước K3. |
| A8 | Câu hỏi "cố ý hay lỗi" ≤ 5 / dự án, gom theo vật; **Đạo diễn đọc kịch bản khai trước** vật/người nào cố ý trái lẽ thường ở cảnh nào. |
| A9 | Duyệt BYĐ kiểu **(c)**: mặc định chỉ hiện ô đáng ngờ, mỗi shot kèm hình render 3D nhỏ; có nút "xem tóm tắt tất cả". |
| A10 | **Bắt buộc dựng sân khấu 3D cho mọi dự án mới**, kể cả bối cảnh không có model 3D (dựng từ ảnh ref / ảnh bố cục — mục 12 `docs/PHUONG_PHAP_SAN_KHAU_3D.md`). |
| A11 | **Âm thanh, phụ đề, dựng nằm trong khâu kiểm soát** ngay từ đầu. |
| A12 | **Prompt do Đạo diễn và hệ thống HỢP TÁC viết**: hệ thống không tự chèn / sửa chữ của Đạo diễn (tránh vô tình ngược ý); hệ thống kiểm và trả lỗi cụ thể, Đạo diễn sửa, lặp tới khi đạt (mục 3.3). |
| A13 | Người dùng **không phải đọc prompt**: mọi quyết định qua một dòng tiếng Việt + nút. |
| A14 | (sau thẩm định lần 2) **Hệ thống KHÔNG chèn bất kỳ chữ nào** vào prompt: hệ thống phân tích → đưa **khai báo** cho Đạo diễn → Đạo diễn viết lại → hệ thống kiểm lại đủ + đúng thông tin chưa → chưa thì đưa khai báo tiếp. Khóa nhận diện, hình học, số liệu được củng cố bằng khai báo BẮT BUỘC (Đạo diễn phải thể hiện, code kiểm) — mục 3.3b. |
| A15 | Dự án mới **chỉ dùng 2 bối cảnh có 3D: Tháp Đồng Hồ (Kho #263) và Cổng Trời (#265)** cho tới khi dựng sân khấu từ ảnh (K1b) xong. |
| A16 | **Chấp nhận chi phí kiểm** (~10–20 % chi gen) để đầu vào / đầu ra chất lượng, thay vì sửa và gen lại nhiều: chi phí kiểm chỉ ĐO và BÁO, không phải ngưỡng chặn. |
| A17 | Video có **2 lớp kiểm bằng code — TRƯỚC và SAU khi gen** — làm cùng đợt ảnh (K3); lớp Claude của video ở K4 (mục 3.4, 3.6, 8). |

## 0. Vì sao sửa nhiều lần vẫn lặp lại

| Dự án / ngày | Lỗi người dùng bắt | Cách đã sửa | Vì sao kiểu lỗi quay lại |
|---|---|---|---|
| #8 (27/09–01/10) | trái/phải chi tiết nhân vật, chiều mũ | luật trong prompt QC → "model khai enum" cho riêng mũ | chỉ áp 2 loại; trái/phải VLM vốn kém (~56 %, nghiên cứu) |
| #22 KLD (07/10) | nền sai map 3D, trang phục lệch mẫu, khẩu trang mất | sửa prompt từng shot bằng tay (8/9 viết tay) — ảnh đẹp | công thức không vào hệ thống; hệ thống không có vòng nhìn–sửa như người |
| #24 (09/10) | tháp "nền mẫu", tường cao không có thật, máu/tóc trên giếng | vá máy → sân khấu 3D; ảnh mẫu Kho sạch | ảnh mẫu + ảnh neo cũ kéo nền; không ai đối chiếu gói |
| #24 (10/10) | nghiêng máy mất, trăng luôn góc trái, thấy lòng giếng (máy thấp hơn miệng), giếng thành khối, tư thế ngã sai, màu giếng không ăn khớp | `stage_facts` | prompt Director chữ tự do trái hình học; QC có render vẫn chấm 'ok' |

**Ba gốc chung** (có bằng chứng code, thẩm định xác nhận):
1. **Không có một bản ý đồ có cấu trúc** — mỗi lớp tự hiểu lại chữ tự do bằng mẫu từ riêng (`core/qc_spec.py:20-25`,
   `core/prompt_formula.py`, `core/stage_facts.contradictions`).
2. **Kiểm không nhìn đúng thứ trả tiền** — không lớp nào xem cả gói gửi model (prompt + ảnh tham chiếu + vai) trước khi gửi; QC đứng sau
   gen và đang TẮT → người dùng là cổng duy nhất.
3. **Bài học không thành hợp đồng** — mỗi lỗi thành một luật lẻ, không có sổ "khâu nào phải có kiểm nào".

**Bài học từ thị trường** (nghiên cứu): người viết tay "chuẩn hơn" vì (a) có vòng nhìn–sửa và chọn bản tốt nhất (~25 % clip dùng được);
(b) prompt ngắn đúng ngữ pháp model; (c) prompt dài nhồi nhiều ý thì model gắn đúng thuộc tính/không gian chỉ ~50 %; (d) viết lại tự do
thêm chi tiết sai; (e) ảnh tham chiếu ít mà có vai rõ. Không công cụ thương mại nào công bố kiểm gói tự động — đó là phần ta thêm, phải
chứng minh bằng số đo.

## 1. Nguyên tắc (bất biến — mọi đợt phải giữ; test hợp đồng kiểm các điểm có thể kiểm)

| # | Nguyên tắc | Nghĩa cụ thể |
|---|---|---|
| N1 | **Một nguồn ý đồ** | Mỗi shot một BYĐ có cấu trúc. Mọi lớp kiểm đọc BYĐ (và gói thật), không đọc lại chữ tự do bằng mẫu từ để KẾT LUẬN. |
| N2 | **Viết hợp tác, hệ thống không chèn chữ (A14)** | Đạo diễn viết TOÀN BỘ prompt (ngắn, đúng ngữ pháp model). Hệ thống KHÔNG sửa / chèn chữ nào — mọi phần code từng ghép thành khai báo (3.3b); hệ thống đưa trước dữ kiện (sự thật hình học, vai ảnh, ngân sách model), kiểm bản viết, trả lỗi cụ thể; Đạo diễn sửa; lặp ≤ 2 vòng rồi hỏi người. |
| N3 | **Kiểm trước tiền** | Mọi khâu tốn tiền (ảnh, video, TTS, nhạc, Claude lớn) có lớp kiểm TRƯỚC khi gửi, nhìn ĐÚNG gói sẽ gửi. |
| N4 | **Model khai, code kết luận** | Lớp Claude chỉ khai điều THẤY (enum / danh sách mở có giới hạn), không khai "đúng/sai", "vô lý hay không". Code so với điều mong đợi (mục 5) và quyết. |
| N5 | **Không giao VLM việc nó kém** | Trái/phải, đếm, vị trí, tỉ lệ, góc máy: code / bộ phát hiện / hình học 3D quyết. VLM chỉ khai có/không. Đo không được → VÀNG, không đoán. |
| N6 | **Đối xứng làm ↔ kiểm** | Mỗi khâu làm có dòng trong Sổ khâu (`devsys/stages.json`): kiểm trước, kiểm sau, đọc từ, trạng thái. Khâu tốn tiền thiếu kiểm trước → test đỏ. |
| N7 | **Độ phủ theo cấu trúc** | Mỗi ô BYĐ và mỗi loại lỗi (mục 4) có sẵn: câu dữ kiện cho Đạo diễn, câu hỏi kiểm gói, mệnh đề kiểm kết quả. Ca vàng chỉ để kiểm hồi quy. |
| N8 | **Đo rồi mới chặn** | Lớp chắc chắn (hình học, đếm bằng bộ phát hiện, hợp lệ BYĐ) chặn ngay. Lớp Claude chạy học việc → đạt ngưỡng (mục 9) mới chặn. Mọi chặn có nút Bỏ qua + lý do. |
| N9 | **Người dùng không đọc prompt** | Một dòng tiếng Việt / shot / lần gen lại; quyết bằng nút. |
| N10 | **Gen lại phải đổi đúng đầu vào** | Chẩn đoán gốc (chữ / ảnh tham chiếu / render / model) → đổi đúng thứ đó; ≤ 2 lần tự động rồi hỏi người. |
| N11 | **Gọn theo model** | Mỗi model có ngân sách prompt (số từ, ý chính đặt đầu, một hành động / shot, chỉ câu khẳng định — "không được có" diễn lại thành mô tả dương) và trần số ảnh tham chiếu; ngoại hình do ảnh tham chiếu giữ, chữ không tả lại. |

## 2. Kiến trúc

```
Kịch bản ─▶ Đạo diễn ─▶ ① BYĐ (có cấu trúc + ô ngoại lệ có chủ đích)  ◀── người dùng duyệt kiểu (c) có hình 3D
                               │
             ② SỰ THẬT SUY RA (code, bắt buộc mọi shot — sân khấu 3D A10): hình học · hồ sơ Kho · liên tục · luật thế giới
                               │
             ③ VIẾT HỢP TÁC: Đạo diễn viết prompt ⇄ hệ thống kiểm (≤ 2 vòng) · chọn ảnh tham chiếu kiểu Elements · dấu vân tay gói
                               │
             ④ NGƯỜI DUYỆT GÓI: lớp code (chặn) + lớp Claude khai (học việc → chặn)            ── trước tiền
                               │ đạt
             ⑤ GEN (tốn tiền) — tùy chọn N bản rẻ → chọn → nâng (cần người dùng duyệt chi)
                               │
             ⑥ QC SAU GEN: mệnh đề kiểu DSG từ BYĐ, code đo + Claude khai, code kết luận
                               │ lệch
             ⑦ GEN LẠI: chẩn đoán gốc → đổi đúng đầu vào → quay ③④
                               │
             ⑧ SỔ KHÂU + SỔ ĐIỂM QUYẾT ĐỊNH + BỘ CA HỒI QUY + SỐ ĐO (bắt đúng / báo nhầm / lọt theo loại)
```

Cùng khung ①–⑧ áp cho **ảnh, video, âm thanh (TTS, nhạc, SFX), phụ đề, dựng** (A4, A11) — mục 6.

## 3. Thành phần

### 3.1 ① Bảng ý đồ shot (BYĐ)

Mở rộng `shot_specs` sân khấu 3D V3 đã có (`prompts/29_director_stage_specs.md:55-67`, `core/stage_solver.py:90-114`; `beats` có
`tu_the`). Mô-đun mới `core/shot_intent.py` (schema + kiểm hợp lệ).

| Nhóm | Trường (enum khi có thể) |
|---|---|
| Truyện | `nhip`, `muc_dich`, `cam_xuc` |
| Ai trong khung | `thanh_phan[]`: `vat` (mã Kho), `vai` chính/phụ/không_duoc_co, `vung` 3×3, `thay` mặt/lưng/nghiêng, `dang` (dạng trang phục Kho) |
| Hành động | mỗi người: `bat_dau` / `dinh` / `ket_thuc` = tư thế (enum) + bộ phận chạm đất + hướng nhìn (mã vật) |
| Vật | `vat[]`: mã Kho + phần phải thấy / không được thấy (mặc định do ② tính, Đạo diễn chỉ ghi khi ý đồ khác) |
| Máy | `co`, `do_cao`, `goc`, `chuyen_dong` (enum); `stage_camera` do solver giải |
| Nơi chốn | mã Kho + spot, thời gian, thời tiết, ánh sáng |
| Ngoại lệ có chủ đích | `ngoai_le[]`: vật/người, điều trái lẽ thường, lý do (kỹ năng / hiệu ứng game / phong cách), cách hiển thị, phạm vi (các shot) — Đạo diễn khai từ kịch bản (A8) |
| Âm / chữ | thoại (đã có), nhạc theo nhịp, SFX, popup, phụ đề |

Không có trường chữ tự do "không kiểm": mọi ý muốn thêm phải nằm trong ô hoặc trong prompt Đạo diễn viết — mà prompt thì được kiểm (3.3).
Kiểm hợp lệ (code, chặn): enum đúng; mã Kho có thật; người có trong kịch bản cảnh đó; dạng trang phục có trong Kho; ý BYĐ không trái
sự thật ② trừ khi có `ngoai_le` tương ứng.

### 3.2 ② Sự thật suy ra (code, 0 USD)

| Nguồn | Hiện có | Phải xây (đợt) |
|---|---|---|
| Hình học sân khấu 3D | `core/stage_facts.py` (FACTS: top_visible, stand_in, in_frame, pitch_horizon, ref_viewpoint), `core/stage_grid.py`, `core/stage_solver.py` | người (mặt/lưng/vùng) từ dàn cảnh; vật không phải khối trụ; sân khấu từ ảnh ref (A10, V6 — K1) |
| Hồ sơ Kho | `must_keep`, dạng, `height_m` | `goc_anh_mau` (góc chụp ảnh mẫu), bộ ảnh chuẩn trước/3-4/nghiêng (K1) |
| Liên tục | trạng thái cuối shot trước | sinh điều kiện đầu shot sau (K1) |
| Luật thế giới (T2, mục 5) | hồ sơ kỹ năng `data/skills`, `knowledge/ff_gameplay_visual.md` | bảng luật dự án có phạm vi + hạn dùng + nút gỡ (K0b) |

### 3.3 ③ Viết hợp tác (A12)

Vòng cho mỗi shot (ảnh và video):
1. Hệ thống đưa Đạo diễn **gói dữ kiện**: BYĐ của shot; sự thật ② dạng câu ngắn (vd "máy cao 0,60 m < miệng giếng 0,90 m: chỉ thấy thành
   ngoài"); vai + ảnh tham chiếu đã chọn (kiểu Elements: nhân vật/vật gọi bằng tên, ngoại hình do ảnh giữ); ngân sách model (N11);
   ngoại lệ đã khai.
2. Đạo diễn viết prompt (ngắn, câu khẳng định, ý chính đầu).
3. Hệ thống kiểm bản viết — KHÔNG sửa, KHÔNG chèn chữ (A14):
   - code: ngân sách từ / số ý / câu phủ định; tên nhân vật/vật có trong BYĐ; khai báo bắt buộc (3.3b) có mặt; regex chỉ GỢI Ý (VÀNG);
   - Claude **chỉ khai** (kiểu DSG, N4): tách prompt thành ý nguyên tử, mỗi ý = (trường BYĐ, giá trị enum, trích ≤ 12 từ) hoặc (ý ngoài
     BYĐ, trích). Claude KHÔNG khai "đúng / trái".
4. **Code so** từng ý khai với ô BYĐ + ② + Kho + luật thế giới → có / thiếu / trái → trả Đạo diễn danh sách lỗi cụ thể ("ô 'giếng: chỉ
   thành ngoài' — prompt có ý 'giếng: thấy lòng' ← 'its dark mouth facing us'"). Ý ngoài BYĐ được giữ nếu không trái nguồn nào.
   **Học việc (N8):** khi lớp Claude của vòng này chưa đạt ngưỡng mục 9, chỉ lỗi của lớp CODE được trả tự động cho Đạo diễn; lỗi suy từ
   khai của Claude ghi `trainee_log` + so với người dùng, chưa tác động.
5. Đạo diễn sửa → kiểm lại. ≤ 2 vòng. Vẫn đỏ → giữ, hỏi người một dòng + nút (sửa BYĐ / chấp nhận / bỏ shot).
Kết quả: prompt cuối = chữ của Đạo diễn, đã kiểm đủ; mọi ý có nguồn. **Dấu vân tay gói: VIẾT MỚI ở K2** (thẩm định lần 2: vân tay hiện có
ở `storyboard_gate` chỉ là id ảnh duyệt, ở `autopilot` là trường cổng plates) — băm (prompt cuối + id/sha ảnh tham chiếu + vai + model +
render + tham số), dùng chung ảnh và video → gói không đổi thì không kiểm lại.
**So A/B (A7, cuối K2):** 3 shot phủ 3 kiểu (hình học, trang phục / nhận diện, hành động) × 2 bản (viết hợp tác vs cách hiện tại có chữ hệ
thống chèn), chất lượng thấp, trần cứng ≤ 1 USD, người dùng chấm bằng nút. 2/3 chỉ là định hướng; được chạy lần 2 trong trần nếu chưa rõ.

### 3.3b Chữ hệ thống → khai báo (A14)

Hiện `core/runner.py` `build_image_prompt` (~dòng 1811) tự ghép nhiều phần do code viết; `looks.clean_prompt` xóa chữ Đạo diễn;
`stage_facts.prompt_block` nối câu "…overrides any other words". Sau K2 (cờ `collab_prompt`), mọi phần chuyển thành KHAI BÁO cho Đạo diễn:

| Phần code đang ghép | Thành khai báo | Kiểm sau khi Đạo diễn viết |
|---|---|---|
| Khóa nhận diện + màu trang phục (Identity lock F1-C, sửa lỗi #22) | BẮT BUỘC: từng món `must_keep` + màu, dạng trang phục | code: mỗi món có ý tương ứng (khai Claude + so); thiếu → lỗi trả Đạo diễn |
| Câu sự thật hình học (`stage_facts.prompt_block`) | BẮT BUỘC: phần thấy của vật, khối thay thế = vật thật, chân trời, góc ảnh mẫu | code so ý khai với ② |
| Ghi chú góc nhìn (view_notes), thấy mặt / lưng | BẮT BUỘC theo BYĐ `thay` | code so |
| Phong cách dự án (style), câu chốt chất lượng | KHUYẾN NGHỊ: Đạo diễn viết theo ngân sách model | code: có ý phong cách; không trái phong cách dự án |
| Gỡ chữ tả thực (`looks.clean_prompt`) | KHAI BÁO "tránh chữ X" thay vì xóa | code: chữ X còn → lỗi trả Đạo diễn |
| Giới hạn máu / gore | KHAI BÁO theo luật dự án | code + Claude khai |

Khai báo bắt buộc chưa thể hiện sau 2 vòng → giữ, hỏi người một dòng. Cờ tắt → hành vi cũ y hệt (test so trước/sau).

### 3.4 ④ Người duyệt gói (trước tiền)

**Lớp code — chặn ngay:** BYĐ hợp lệ; prompt đã qua 3.3; ảnh tham chiếu đúng vai (mỗi người trong khung một bộ đúng dạng; không ảnh
người không có trong khung; ảnh vật có nhãn "chỉ hình dáng/chất liệu" khi góc máy khác `goc_anh_mau`; render nền có; ảnh neo chỉ cùng
máy — `scene_storyboard.own_camera`); trần số ảnh theo model; video: khung đầu = ảnh đã duyệt hiện hành của chính shot, motion đủ
đầu–đỉnh–cuối, thời lượng hợp model; âm thanh: thoại đúng người nói/giọng, độ dài khớp shot; gen lại: N10.
**Lớp Claude — học việc rồi chặn:** nhìn ảnh tham chiếu thu nhỏ có nhãn vai + prompt cuối + BYĐ; khai mỗi ảnh có kéo trái ý nào không
(enum) — vì ảnh tham chiếu xung đột là nguồn lỗi #24 mà code không thấy được nội dung ảnh.

### 3.4b Video: 2 lớp kiểm bằng code, trước và sau gen (A17 — làm ở K3)

| Lớp | Kiểm (code, 0 USD) | Mức |
|---|---|---|
| TRƯỚC gen | khung đầu = ảnh ĐÃ DUYỆT hiện hành của chính shot (mã job + sha tệp; ảnh đã bị thay / bỏ duyệt → chặn) · khung cuối (nếu dùng) khớp `ket_thuc` BYĐ và đã duyệt · thời lượng hợp model + khớp độ dài thoại / nhịp · ảnh / video tham chiếu theo luật từng model (Kling video ref ≥ 3 s, rộng 700–4553 px, SAR 1:1; Seedance mỗi tài sản một vai; trần số ảnh) · motion có đủ đầu–đỉnh–cuối + chuyển động máy enum · dấu vân tay gói khác lần trước khi gen lại (N10) | chặn |
| SAU gen | trôi hình / giật / viền lạ / môi (`core/clip_measure.py`, có) · **khung 0 của clip khớp ảnh khung đầu** (so ảnh, ngưỡng đo) · khung cuối khớp khung cuối duyệt (nếu có) · thời lượng thật · có tiếng / không tiếng đúng ý · **chuyển động máy so `chuyen_dong`** (luồng quang `motion_series` có sẵn → phân loại đứng / đẩy / kéo / lia — XÂY ở K3) · đầu–cuối trạng thái người (YuNet thấy mặt / lưng ở khung đầu, cuối) | lệch chắc → gen lại theo N10; không chắc → VÀNG |

Lớp Claude của video (khai L1–L15 trên khung mẫu, tường thuật + chuyển động) ở K4.

### 3.5 ⑤ Gen — N bản rẻ (tùy chọn, tốn tiền)
Mở rộng tuyến E1 (09/10) từ video sang ảnh khung đầu: 2–4 bản chất lượng thấp → ⑥ chấm theo ý → code/người chọn → nâng. Bật theo dự án,
người dùng duyệt chi trước (ước tính in rõ).

### 3.6 ⑥ QC sau gen (DSG)
- Mệnh đề sinh từ BYĐ + ② + ngoại lệ (thay `qc_spec` đọc chữ bằng mẫu từ), **nguyên tử + đồ thị phụ thuộc** (ý cha "có Kelly trong
  khung" sai → bỏ ý con), mỗi mệnh đề gắn loại (mục 4) để thống kê.
- Code đo phần N5: YuNet (đã có), bộ phát hiện vật / Pose / embedding mặt / thống kê màu vùng (phải xây — K5), chân trời giải tích.
- Claude khai (cơ chế `qc_team` enum + `qc_rules`; Tổ QC hiện chỉ có C1 — C2/C3 xây ở K5) + câu hỏi mở có giới hạn "liệt kê ≤ 5 thứ thấy
  mà BYĐ không nói" (mục 4, L15).
- Video: VLM chỉ chấm tường thuật + chuyển động; trôi hình / giật / viền / môi bằng đo clip (d42 đã có); không chặn tự động theo "chất
  lượng hình" (nghiên cứu: VLM r 0,345 vs người 0,705).
- Chạy lại ca hồi quy lớp Claude 0 USD bằng `qc_team.ReplayClient` khi prompt kiểm không đổi.

### 3.7 ⑦ Gen lại
Chẩn đoán gốc (code, từ ⑥ / ghi chú người dùng tách ý): BYĐ sai → người sửa ô; prompt sai → vòng 3.3 với lỗi cụ thể; ảnh tham chiếu
kéo → đổi ảnh / nhãn vai; render → sửa máy / khối; model lờ ý đúng → câu nhấn mạnh khác hoặc đổi model. Kiểm "đã xử lý ý / chưa / một
phần" + không thoái lui (ý đã đạt ở bản trước còn trong gói). Người dùng thấy: "Gen lại lần 2 · sửa 'tư thế ngã': ✅ · giữ 8/8 ý ✅ ·
đổi: chữ tư thế + bỏ ảnh neo cũ".

### 3.8 Thay đổi giữa chừng
`change_review` (bật 10/10, đo 0,013–0,019 USD/thay đổi) đọc khác biệt BYĐ (bảng WATCH chuyển sang trường BYĐ); gói shot bị ảnh hưởng mất
dấu vân tay → ③④ lại.

### 3.9 ⑧ Sổ và số đo
- `devsys/stages.json` (MỚI): khâu L1–L16 + A1–A4 (mục 6) → `kiem_truoc[]`, `kiem_sau[]` (id trong `devsys/decisions.json`), `doc_tu`
  (BYĐ / gói / kết quả), `trang_thai`, `ton_tien`. Không nhồi cột vào 84 điểm quyết định. Thêm vào `decisions.json` các khâu code
  đang thiếu (prompt_formula, stage_facts, before_run, giải máy, render nền, end_popup, vòng viết hợp tác, người duyệt gói).
- Test hợp đồng (`tests/test_devsys_stages.py`): khâu `ton_tien` thiếu `kiem_truoc` đang chạy/học việc → đỏ; lớp kiểm `doc_tu: chu_tu_do`
  để kết luận → đỏ; mỗi loại lỗi mục 4 có ≥ 1 cách kiểm CÓ THẬT (không tính "học việc" khi chưa có cách đo — thẩm định #7) cho từng loại
  sản phẩm áp dụng; mỗi ô BYĐ có đủ 3 câu (dữ kiện / kiểm gói / mệnh đề QC).
- Bộ ca hồi quy `tests/golden/` (định dạng chốt ở K0a): ca = BYĐ (tay cho dự án cũ, `ca_vang_tay`) + máy + Kho + gói + (ảnh kết quả) +
  lỗi + lớp phải bắt.
- Trang devsys "Làm ↔ Kiểm": bảng mục 7 sinh từ sổ, đỏ khi khâu thiếu kiểm; số đo theo loại.

## 4. Độ phủ theo cấu trúc (A5)

Ba nguồn, không dựa lỗi cũ:
1. **Ô BYĐ tự sinh phép kiểm** (N7): ý đồ mới của dự án mới → phép kiểm mới tự có.
2. **Bảng loại lỗi** — mỗi loại có cách kiểm cho từng sản phẩm áp dụng:

| # | Loại | Code đo (hiện có / xây ở đợt) | Claude khai | Ảnh | Video | Âm/Chữ |
|---|---|---|---|---|---|---|
| L1 | Danh tính | đếm mặt YuNet (có) · embedding mặt (K5) | người X: có / không / không chắc | ✓ | ✓ khung mẫu | — |
| L2 | Trang phục / dạng | `palette_check` (có, TẮT) · màu vùng thân (K5) | từng món must_keep: có / khác / không thấy | ✓ | ✓ | — |
| L3 | Số người, người lạ | YuNet (có) · bộ phát hiện (K5) | người không có trong BYĐ: có / không | ✓ | ✓ | — |
| L4 | Tư thế, hành động | Pose (K5) | tư thế enum | ✓ | ✓ đầu–đỉnh–cuối | — |
| L5 | Hướng nhìn, mặt/lưng | YuNet (có) | mặt / lưng / nghiêng | ✓ | ✓ | — |
| L6 | Vị trí trong khung | bộ phát hiện + vùng 3×3 (K5) · chiếu 3D (có) | (không giao VLM — N5) | ✓ | ✓ | — |
| L7 | Vật: có/không, phần thấy, hình dáng | `stage_facts` (có) | phần thấy · hình dáng (khối / thật) | ✓ | ✓ | — |
| L8 | Tỉ lệ, cỡ cảnh | đo mặt/khung (có) · chiếu 3D (có) | cỡ | ✓ | ✓ | — |
| L9 | Máy: góc, nghiêng, chân trời | giải tích (có) | chân trời ở ba phần nào | ✓ | ✓ + chuyển động máy | — |
| L10 | Hòa hợp ánh sáng / màu | thống kê màu-độ sáng vùng vật vs nền quanh, so render (K5) | vật nào trông dán vào / khác tông | ✓ | ✓ | — |
| L11 | Nơi chốn, nền | so render nét / chân trời (có, sửa 10/10) | thứ trong nền không có trong render | ✓ | ✓ | — |
| L12 | Thời gian, thời tiết, ánh sáng | độ sáng, nhiệt màu (K5) | ngày/đêm · sương · nguồn sáng | ✓ | ✓ | — |
| L13 | Liên tục shot kề | so trạng thái cuối/đầu (K1) | đồ / chỗ / tư thế giữ không | ✓ | ✓ | ✓ thoại |
| L14 | Lỗi tạo hình | — | tay, mặt méo, chữ lạ: có/không + chỗ | ✓ | ✓ | — |
| L15 | Thứ lạ ngoài BYĐ | — | danh sách mở ≤ 5 → code so "không được có" + vàng thứ lạ | ✓ | ✓ | — |
| V1–V4 | Trôi hình, giật, môi (có, `clip_measure`); chuyển động máy so BYĐ (XÂY K3) | đo clip d42 | chuyển động khớp `bat_dau→dinh→ket_thuc` / máy | — | ✓ | — |
| A1 | Thoại: đúng câu, đúng người, đúng giọng | so chữ TTS d39 (có), độ dài | — | — | — | ✓ |
| A2 | Nhạc / SFX theo nhịp, cường độ | loudness (có), mốc nhịp | SFX khớp hành động: có/không | — | — | ✓ |
| A3 | Phụ đề: chính tả, khớp thoại, thời điểm, vùng an toàn | so chữ, so mốc thời gian (K6) | — | — | — | ✓ |
| A4 | Dựng: thứ tự, nhịp, chuyển cảnh, popup giữ khung cuối | so kịch bản / BYĐ (K6) | rough_cut (học việc) | — | ✓ | ✓ |

3. **Phát hiện cái chưa biết:** L15 + mọi lỗi người dùng bắt mà lọt được xếp vào một loại; không xếp được → thêm loại mới. Số đo "lọt
   theo loại" chỉ loại kiểm yếu.

**Bộ kỹ năng kiểm** `knowledge/checks/<loai>.md` (K0b): mỗi loại một tệp gom từ nghề — giám sát kịch bản / liên tục (L4, L5, L13),
quay phim (L6, L8, L9), ghép hình VFX: hướng + nhiệt màu nguồn sáng, mức đen, bóng tiếp xúc, phối cảnh, độ nét, nhiễu (L7, L10), thiết kế
bối cảnh / map FF (L11, L12), lỗi ảnh / video AI (L14, V1–V4), Character Lock (L1–L3), âm thanh / phụ đề / dựng (A1–A4). Mỗi mục =
câu hỏi khai được + cách code kết luận. Hạng mục "lẽ thường" (vật lý, tỉ lệ, góc nhìn…) chỉ là GỢI Ý để model nhìn kỹ, không phải luật.

## 5. Chuẩn so theo tầng (A6, A8)

| Tầng | Nguồn | Ví dụ |
|---|---|---|
| T1 Ý đồ shot | BYĐ + `ngoai_le` Đạo diễn khai từ kịch bản | "bóng + ô tô lơ lửng do hiệu ứng kỹ năng Z: quầng sáng xanh" |
| T2 Luật thế giới | hồ sơ kỹ năng FF, tư liệu gameplay, phong cách, luật dự án do người dùng trả lời | xe FF không bay; kỹ năng đúng màu/hình |
| T3 Lẽ thường | mặc định đời thực | vật không tự lơ lửng |

Code tìm điều mong đợi T1 → T2 → T3 cho từng điều Claude khai thấy:
- T1 có ngoại lệ → **đảo chiều kiểm**: hiệu ứng có đúng như tả (quầng sáng, vật nào lơ lửng, độ cao) không.
- T2 có luật → kiểm theo luật.
- Chỉ T3 mà lệch, T1/T2 im lặng → **không tự kết luận**: VÀNG + câu hỏi "cố ý hay lỗi?" (≤ 5 / dự án, gom theo vật — A8). "Cố ý" → luật
  T2 **có phạm vi** (vật + ngữ cảnh/kỹ năng + dự án), có hạn dùng, có nút gỡ; không áp ngầm cho vật khác (bài học "không khái quát từ
  một mẫu"). "Lỗi" → đỏ + gen lại.
- Trước tiền: ý trong BYĐ / prompt trái T3 mà `ngoai_le` trống → Đạo diễn phải khai lý do + cách hiện trong vòng 3.3.

## 6. Cùng một mức chặt cho mọi sản phẩm (A4, A11)

| Sản phẩm | ① ý đồ | ② sự thật | ③ viết hợp tác | ④ duyệt gói | ⑥ QC | ⑦ gen lại |
|---|---|---|---|---|---|---|
| Ảnh khung đầu / neo / khung cuối | BYĐ | 3D + Kho | prompt ảnh | code + Claude | L1–L15 | N10 |
| Video | BYĐ hành động + máy | 3D + khung đầu duyệt | motion prompt | code (khung đầu, motion, ref video theo luật model) + Claude | L1–L15 trên khung mẫu + V1–V4 | N10 |
| TTS / thoại | thoại BYĐ | hồ sơ giọng | văn bản đọc | người nói, giọng, độ dài | A1 | đổi câu / giọng |
| Nhạc / SFX | nhịp, cảm xúc | đường cảm xúc cả truyện | brief | độ dài, mốc nhịp | A2 | đổi brief |
| Phụ đề | thoại | — | bản dịch | chính tả, độ dài dòng | A3 | sửa chữ |
| Dựng / popup | thứ tự, nhịp | thời lượng | danh sách cắt | khớp kịch bản | A4 | đổi cắt |

## 7. Ma trận Làm ↔ Kiểm mục tiêu

| Khâu làm | Kiểm trước (đọc) | Kiểm sau | Trạng thái mục tiêu |
|---|---|---|---|
| L1 kịch bản | dựng được, IP | người | như cũ |
| L3 Đạo diễn → BYĐ | hợp lệ + mâu thuẫn ② (BYĐ) | người duyệt kiểu (c) | code chặn |
| L5 Kho / ảnh mẫu | `must_keep`, `goc_anh_mau`, bộ ảnh chuẩn | người duyệt Kho | code chặn khi dùng |
| L6 sân khấu 3D (mọi dự án mới) | luật P/S/C solver | ② | có |
| L7–L9 gói + gen ảnh | ③ + ④ | ⑥ + người | code chặn; Claude học việc → chặn |
| L10 gen lại | ③ + ④ + N10 + không thoái lui | ⑥ | như L9 |
| L11–L13 motion, gói + gen video | ③ + ④ video | ⑥ video + d42 + người | như ảnh |
| L14 TTS / nhạc / SFX / phụ đề | ④ âm/chữ | A1–A3 + người | như ảnh |
| L15 dựng, popup | ④ dựng | A4 + người | như ảnh |
| L16 thay đổi | Tổ rà soát (khác biệt BYĐ) | — | có |

## 8. Lộ trình

Mỗi đợt: cờ riêng (TẮT mặc định), test đỏ → xanh, rà KỸ khi đụng tiền / chặn job / dữ liệu, cả bộ test trước gộp, quy ước 7.

| Đợt | Việc | Tốn tiền | Xong khi |
|---|---|---|---|
| **K0a** Sổ khâu + định dạng | `devsys/stages.json` + test hợp đồng; thêm khâu code thiếu vào `decisions.json`; schema BYĐ tối thiểu + định dạng ca hồi quy; sửa `LLM_STAGE_TOKENS` khâu chấm (`core/cost.py:297` qc (6000, 900) → output đo ~5000 token, 10/10); gộp `tests/fixtures/stage_facts_golden.json` vào định dạng `tests/golden/` | 0 | test hợp đồng chạy, trang "Làm ↔ Kiểm" hiện đúng các khâu thiếu kiểm (đỏ) |
| **K0b** Bảng loại lỗi + kỹ năng + luật thế giới | `knowledge/checks/*.md` cho L1–L15, V1–V4, A1–A4; bảng luật thế giới có phạm vi; ca hồi quy từ #8/#22/#24 (`ca_vang_tay`) | 0 | mỗi loại có tệp kỹ năng + cách kết luận; ≥ 15 ca hồi quy định dạng đúng |
| **K1a** BYĐ trên 2 bối cảnh có 3D (A15) | `core/shot_intent.py`; Đạo diễn điền BYĐ + `ngoai_le` (prompt 17/20/29, cờ `shot_intent`); dự án mới chỉ chọn được Tháp Đồng Hồ #263 / Cổng Trời #265; duyệt kiểu (c) có hình 3D trên Dashboard | Claude khi chạy Đạo diễn | một dự án mới thử có BYĐ đủ mọi shot, người dùng duyệt |
| **K1b** Sân khấu 3D từ ảnh (A10, sau K4) | Nhánh B mục 12 `docs/PHUONG_PHAP_SAN_KHAU_3D.md` (hiệu chỉnh, chiều sâu, ghép ảnh, P5; tải model chiều sâu ~100 MB — hỏi người dùng trước) | 0 (code) | lệch chiếu ngược ≤ 3 % trên ≥ 3 bối cảnh → mở thêm bối cảnh cho dự án mới |
| **K2** Viết hợp tác (ảnh) | vòng 3.3 + dấu vân tay gói + ngân sách model + ảnh tham chiếu kiểu Elements; **so A/B ≤ 1 USD** (A7) | ≤ 1 USD (A/B) + Claude vòng viết | người dùng chấm A/B: bản hợp tác ≥ bản hiện tại ở ≥ 2/3 shot |
| **K3** Người duyệt gói ảnh + 2 lớp code video | ④ lớp code chặn, lớp Claude học việc; gen lại qua ③④ + N10; một dòng tiếng Việt; **video: lớp code TRƯỚC + SAU gen (3.4b, A17)** gồm phân loại chuyển động máy | Claude học việc (đo thật — báo giá trước) | lớp code bắt 100 % ca hồi quy thuộc nó; số đo Claude ghi đủ 1 dự án |
| **K4** Video ngang ảnh (lớp Claude) | ③ motion viết hợp tác; ④⑥ lớp Claude cho video: L1–L15 trên khung mẫu (số khung mẫu chốt ở K4 theo đo), tường thuật + chuyển động | như K3 | ca hồi quy video (#22, #24) bắt đúng; ④ video chặn khung đầu sai 100 % |
| **K5** QC sau gen + công cụ đo | DSG + đồ thị phụ thuộc; bộ phát hiện vật, Pose, embedding mặt, màu vùng (L10); Tổ QC C2/C3; N bản rẻ → chọn (tùy chọn) | QC ≈ 0,03–0,04 USD/khung (ước theo số mệnh đề) | số đo đạt mục 9 → đề xuất chặn |
| **K6** Âm thanh, phụ đề, dựng | ③④⑥ cho A1–A4 | nhỏ | ca hồi quy âm/chữ bắt đúng |
| **K7** Thay đổi theo BYĐ | `change_review` đọc khác biệt BYĐ | như hiện tại | không lớp nào còn đọc chữ tự do để kết luận |
| **K8** Vận hành | quy trình mục 10 vào `docs/CHUAN_XAY_DUNG.md` + CLAUDE.md; báo cáo số đo hàng tuần | 0 | — |

Phụ thuộc: K0a → K0b → K1a → K2 → K3 → K4 → K1b; K5 sau K3 (song song K4 được); K6 sau K3; K7 sau K1a. Điểm dừng đo: cuối K2 (A/B), cuối K3
(số đo học việc), cuối K4 (video).

## 9. Chi phí (ước, đo lại ở K3) và tiêu chí nghiệm thu

**Chi phí vận hành thêm / dự án 9 shot** (giá đo: Tổ QC C1 ≈ 0,019 USD cho ~12 mệnh đề; Tổ rà soát 0,013–0,019 USD / thay đổi):

| Phần | Ảnh | Video | Âm/chữ/dựng |
|---|---|---|---|
| ③ vòng viết (≤ 2 vòng × ~0,02) | ~0,2–0,4 | ~0,2–0,4 | ~0,1 |
| ④ lớp Claude | ~0,2–0,3 | ~0,2–0,3 | — |
| ⑥ QC (~20 mệnh đề × 9) | ~0,3–0,4 | ~0,3–0,5 (khung mẫu) | ~0,1 |
| Cộng | ~0,7–1,1 | ~0,7–1,2 | ~0,2 |

Tổng ≈ 1,6–2,5 USD / dự án; so chi gen (ảnh ~0,05 × 9 × lần gen + video ~1–2 × 9) ≈ 10–20 USD → **≈ 10–20 %**. Người dùng chấp nhận
chi phí này (A16): chi phí kiểm chỉ ĐO và BÁO, không chặn; giảm bằng dấu vân tay (không kiểm lại gói không đổi), gom
mệnh đề, ReplayClient cho ca hồi quy.

**Tiêu chí nghiệm thu:**

| Chỉ số | Ngưỡng | Mẫu số |
|---|---|---|
| Độ phủ cấu trúc | 100 % ô BYĐ có đủ 3 câu; 100 % loại lỗi có cách kiểm thật cho từng sản phẩm áp dụng | số ô / số loại |
| Khâu tốn tiền có kiểm trước | 100 % | `stages.json` |
| Ca hồi quy | 100 % bắt đúng ở lớp được gán | số ca |
| Lọt | ≤ 1 lỗi / dự án trên 2 dự án mới liên tiếp; mỗi lỗi lọt xếp loại trong ngày | lỗi người dùng bắt sau |
| Báo nhầm lớp Claude | ≤ 10 % trước khi chặn | số mục lớp đó báo |
| Câu hỏi người dùng | ≤ 5 "cố ý hay lỗi" / dự án; ≤ 1 câu hỏi chặn / shot; tổng thao tác / dự án (duyệt BYĐ + câu cố ý + câu chặn + A/B + chọn bản) đo và báo | đếm |
| "Ô đáng ngờ" (A9) | = ô BYĐ có VÀNG, mâu thuẫn ②, có `ngoai_le`, hoặc suy từ chữ chưa duyệt — chỉ những ô này hiện mặc định | định nghĩa |
| Vòng viết hợp tác hội tụ | ≥ 90 % shot đạt trong ≤ 2 vòng | số shot |
| Chất lượng prompt | A/B: bản hợp tác ≥ bản hiện tại ở ≥ 2/3 shot | người dùng chấm |
| Chi phí kiểm | đo và báo (A16 — không chặn) | sổ chi |
| Người dùng không đọc prompt | 100 % quyết định qua một dòng + nút | rà giao diện |

## 10. Quy trình khi gặp lỗi mới

1. Ghi ca hồi quy (BYĐ, gói, ảnh, lỗi đúng) — 0 USD.
2. Xếp vào loại mục 4 (không xếp được → loại mới) và xác định khâu làm sinh lỗi + lớp kiểm lẽ ra phải bắt (theo sổ khâu).
3. Lớp kiểm chưa có cho loại → thêm (đủ: dữ kiện cho Đạo diễn / câu kiểm gói / mệnh đề QC / cách code kết luận); có mà lọt → sửa lớp đó.
4. Sửa nguồn (BYĐ / ② / ③ / ảnh tham chiếu), KHÔNG vá prompt của riêng ca đó.
5. Test: ca mới đỏ trên code cũ, xanh sau sửa; cả bộ test; quy ước 7.
6. Ghi số đo (lọt +1 theo loại) + bài học `.claude-memory`.

## 11. Rủi ro và cách giảm

| Rủi ro | Giảm |
|---|---|
| Vòng viết hợp tác tốn lượt / chậm | ≤ 2 vòng; dấu vân tay; dữ kiện đưa TRƯỚC để Đạo diễn viết đúng lần đầu |
| Prompt hợp tác kém prompt hiện tại | A/B ≤ 1 USD cuối K2, không qua K3 nếu thua |
| BYĐ cứng nhắc | ý thêm của Đạo diễn trong prompt được giữ nếu không trái nguồn; enum mở rộng theo loại lỗi |
| Công cụ đo (Pose, phát hiện, embedding) chưa có | cột "xây ở đợt" mục 4; khi chưa có → VÀNG (N5), test hợp đồng không tính là phủ |
| Chặn nhầm làm kẹt autopilot | chỉ lớp chắc chắn chặn ngay; Claude học việc; nút Bỏ qua + lý do |
| Luật "cố ý" lan rộng | phạm vi + hạn dùng + nút gỡ |
| Sân khấu 3D từ ảnh ref chưa có (A10) | A15: chỉ Tháp Đồng Hồ + Cổng Trời tới khi K1b đạt nghiệm thu |
| Kế hoạch dài, nhiều phiên | mỗi đợt một nhánh; `TODO.md` + kế hoạch này là nguồn trạng thái; điểm nghỉ theo skill vòng làm việc |

## 12. Tái dùng (không viết lại)

`shot_specs` + solver (`core/stage_solver.py`), `stage_facts.FACTS`, `qc_team` (enum, học việc, `ReplayClient`), `qc_rules`,
`trainee_log` (`core/trainee.py`), dấu vân tay (`core/storyboard_gate.py:103`, `core/autopilot.py:651-685`),
`scene_storyboard.own_camera`, `palette_check` (`core/palette.py`), YuNet (`text_placement.face_boxes`), đo clip d42, `change_review`,
`before_run`, `script_cap` (trần cứng cho mọi công cụ chạy thật), `prompt_rewrite` (vòng sửa có lưu phiên bản).
