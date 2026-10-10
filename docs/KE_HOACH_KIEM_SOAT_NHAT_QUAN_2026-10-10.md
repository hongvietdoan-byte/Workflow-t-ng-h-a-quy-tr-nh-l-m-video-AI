# Kế hoạch: Quy trình kiểm soát chặt chẽ và nhất quán giữa khâu làm và khâu kiểm — BẢN HỢP NHẤT v2 (10/10/2026)

> Yêu cầu người dùng 10/10: "một plan chi tiết hoàn chỉnh để rà soát, kiểm tra tính chặt chẽ và nhất quán của các khâu. Lỗi đã sửa qua
> nhiều dự án mà vẫn chưa hoàn thiện — cần một quy trình thực sự hoàn chỉnh."
> Bản v2 viết lại toàn bộ sau: thẩm định độc lập 6,2/10 (`docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md`), nghiên cứu thị trường
> (`docs/NGHIEN_CUU_THI_TRUONG_KIEM_SOAT_VIDEO_AI_2026-10-10.md`) và các chốt của người dùng (mục A). Bản v1 (các lần vá 9b–12) ở commit
> `a9e19ea` — đã thay hoàn toàn, không dùng nữa. Nền: `docs/RA_SOAT_KHAU_VA_KIEM_TRA_2026-10-10.md`.
> **Trạng thái (10/10 tối): K0a ✅; K0b 🟡 (thẩm định lần 4: kế hoạch 7,9 / build 8,0 — CHƯA đạt cổng A21 ≥ 8,5). Đang đóng 6 lỗ hổng
> lần 4 (A18 chỉ VÀNG tới khi đo báo nhầm; "lưu gói gửi" vào K1a; sổ đo trung thực; công cụ đo ≥ 20 khung; 5 lỗi #24 chưa bắt thành dòng
> kế hoạch — mục 4b) rồi thẩm định lần 5. Lịch sử điểm: 6,2 → 7,1 → 7,6 → 7,9.**

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
| A14 | (sau thẩm định lần 2) **Hệ thống KHÔNG chèn bất kỳ chữ nào** vào prompt: hệ thống phân tích → đưa **khai báo** cho Đạo diễn → Đạo diễn viết lại → hệ thống kiểm lại đủ + đúng thông tin chưa → chưa thì đưa khai báo tiếp (**≤ 2 vòng như N2**, vẫn chưa đạt → giữ, hỏi người một dòng). Khóa nhận diện, hình học, số liệu được củng cố bằng khai báo BẮT BUỘC (Đạo diễn phải thể hiện, code kiểm) — mục 3.3b. |
| A15 | Dự án mới **chỉ dùng 2 bối cảnh có 3D: Tháp Đồng Hồ (Kho #263) và Cổng Trời (#265)** cho tới khi K1b đạt nghiệm thu cho bối cảnh đó — nhánh B (sân khấu từ ảnh) hoặc nhánh C (sân khấu khối tự dựng, A24). |
| A16 | **Chấp nhận chi phí kiểm** (~10–20 % chi gen) để đầu vào / đầu ra chất lượng, thay vì sửa và gen lại nhiều: chi phí kiểm chỉ ĐO và BÁO, không phải ngưỡng chặn. |
| A17 | Video có **2 lớp kiểm bằng code — TRƯỚC và SAU khi gen** — làm cùng đợt ảnh (K3); lớp Claude của video ở K4 (mục 3.4, 3.6, 8). |
| A18 | (thẩm định lần 3) Trong lúc lớp Claude của vòng viết còn học việc, **khai báo bắt buộc khóa nhận diện được CHẶN bằng code**: so tên món `must_keep` + màu lấy từ hồ sơ Kho với chữ Đạo diễn viết (thiếu / sai màu → ĐỎ, trả Đạo diễn) — không quay lại kiểu code chèn. **(thẩm định lần 4) ĐỎ chỉ bật SAU KHI đo báo nhầm đạt ngưỡng A25**: người dùng gán 1 chạm đúng / nhầm trên prompt #22 + #24 (n ≥ 30 trên ≥ 2 dự án, bảng `docs/NHAN_BAO_NHAM_A18_2026-10-10.md`), báo nhầm ≤ 10 % → ĐỎ; trước đó và khi chưa đạt → chỉ VÀNG (ghi + nhắc Đạo diễn, không chặn). Món đưa vào kiểm được **lọc theo BYĐ**: cỡ cảnh `co` (vd giày không kiểm ở MCU/CU), `thay` mặt / lưng (món phía trước không kiểm khi quay lưng), món không nằm trong khung → không kiểm; ca hồi quy chống báo nhầm (giày ở MCU, lưng) bắt buộc. |
| A19 | Đạo diễn **phải viết tên món must_keep + màu** trong prompt; KHÔNG tả lại dáng / mặt (ảnh tham chiếu giữ) — N11 viết lại theo đây. |
| A20 | Trang phục nhiều màu / họa tiết — chia 3 tầng: **chữ** = tên món + màu chủ đạo (1–2) + ≤ 1 dấu hiệu đặc trưng (code kiểm, chặn); **ảnh tham chiếu** giữ toàn bộ họa tiết; **QC sau gen** kiểm họa tiết (L2: code đo màu vùng + Claude khai từng dấu hiệu). Hồ sơ Kho thêm ô `khai_bao_chu` mỗi món: {mon + đồng nghĩa, mau_chinh[] + đồng nghĩa, dau_hieu (≤ 1) + cách viết tương đương, hoa_tiet[] (chỉ cho QC)}; món chưa có ô → VÀNG nhắc điền một lần (K0b tạo trường, K1a điền cho nhân vật dùng). |
| A21 | **Cổng điểm**: kế hoạch + phần đã build phải được agent thẩm định độc lập chấm **≥ 8,5/10** (cùng thang 8 tiêu chí) trước khi áp vào pipeline thật (K1a trở đi — đụng Đạo diễn, prompt, gen). K0a/K0b (0 USD, không đổi hành vi pipeline) được làm để tạo BẰNG CHỨNG chạy khô; chấm lại sau mỗi đợt; dưới 8,5 → sửa theo lỗ hổng rồi chấm lại. |
| A22 | **#24 là dự án thử** (ngoại lệ A1): bước 1 (ngay, 0 USD, KHÔNG đổi #24) — K0b dùng #24 làm dữ liệu chạy khô: dựng BYĐ 9 shot từ `shot_specs` V3 + kịch bản (lưu riêng), chạy các phép kiểm code (khóa nhận diện, hình học, vai ảnh tham chiếu, công cụ đo) trên prompt + ảnh thật, đo bắt được các lỗi người dùng từng bắt không; bước 2 (sau cổng A21 ≥ 8,5) — #24 là dự án thử đầu tiên K1a → K4, phần video còn lại đi qua 2 lớp code. |
| A23 | **Người dùng 10/10 — 2 quyết định thẩm định 4**: (1a) BỎ câu khai vị trí phần ba `in_frame` cho lớp Claude/QC (N5) — sự thật + câu prompt `in_frame` vẫn giữ, vị trí do code đo (chiếu 3D, bộ phát hiện K5); (2a) gộp mục Kho: nguồn NHÁP không chép `khai_bao_chu` sang đích ĐÃ DUYỆT (nháp không được thừa hưởng, A20). |
| A24 | **Người dùng 10/10 — Nhánh C sân khấu khối tự dựng** (`docs/PHUONG_PHAP_SAN_KHAU_3D.md` mục 12b): bối cảnh chưa có 3D → Director khai sơ đồ khối (enum + kích thước) → code dựng greybox Blender + kiểm số → người duyệt một lần → lưu Kho `location_pack` dạng `blockout`. Thuộc **K1b** (cùng nhánh B, sau K4); khối chỉ giữ bố cục + tỉ lệ + che khuất, render khối KHÔNG gửi làm ảnh vai "nền" (12b.3). Mở thêm bối cảnh cho A15 khi 12b.4 đạt. |
| A25 | **Người dùng 10/10 (thẩm định 5)**: (1) ngưỡng DUY NHẤT cho lớp code A18: báo nhầm **≤ 10 % trên n ≥ 30 mục gán nhãn, lấy từ ≥ 2 dự án (#22 + #24)**; đạt → ĐỎ, chưa đạt → VÀNG; (2) bộ phát hiện vật **hoãn sang K5** (thiếu trọng số) — K0b đóng không cần nó. |

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
| N11 | **Gọn theo model** | Mỗi model có ngân sách prompt (số từ, ý chính đặt đầu, một hành động / shot, chỉ câu khẳng định — "không được có" diễn lại thành mô tả dương) và trần số ảnh tham chiếu; ngoại hình (dáng, mặt) do ảnh tham chiếu giữ, chữ không tả lại; riêng tên món `must_keep` + màu PHẢI có trong chữ (A19). |

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
render + tham số), dùng chung ảnh và video → gói không đổi thì không kiểm lại. Vân tay băm trên **gói gửi đã lưu từ K1a** (3.9 "Lưu gói
gửi") — không tái dùng hàm băm cũ; mã cũ chỉ để tham khảo cách lưu (mục 12).
**So A/B (A7, cuối K2):** 3 shot phủ 3 kiểu (hình học, trang phục / nhận diện, hành động) × 2 bản (viết hợp tác vs cách hiện tại có chữ hệ
thống chèn), chất lượng thấp, trần cứng ≤ 1 USD, người dùng chấm bằng nút. 2/3 chỉ là định hướng; được chạy lần 2 trong trần nếu chưa rõ.

### 3.3b Chữ hệ thống → khai báo (A14)

Hiện `core/runner.py` `build_image_prompt` (~dòng 1811) tự ghép nhiều phần do code viết; `looks.clean_prompt` xóa chữ Đạo diễn;
`stage_facts.prompt_block` nối câu "…overrides any other words". Sau K2 (cờ `collab_prompt`), mọi phần chuyển thành KHAI BÁO cho Đạo diễn:

| Phần code đang ghép | Thành khai báo | Kiểm sau khi Đạo diễn viết |
|---|---|---|
| Khóa nhận diện + màu trang phục (Identity lock F1-C, sửa lỗi #22) | BẮT BUỘC: từng món `must_keep` + màu, dạng trang phục | **code kiểm (A18)**: so tên món + màu từ Kho với chữ (có bảng từ đồng nghĩa màu / món theo hồ sơ), món lọc theo BYĐ; thiếu / sai màu → VÀNG nhắc Đạo diễn tới khi đo báo nhầm đạt ngưỡng A25, sau đó ĐỎ trả Đạo diễn; lớp Claude khai thêm (học việc) cho cách diễn đạt khác |
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
  sản phẩm áp dụng; mỗi ô BYĐ có đủ 3 câu (dữ kiện / kiểm gói / mệnh đề QC — test bật ở K2 khi có câu).
  **Chống né:** `kiem_truoc`/`kiem_sau` chỉ nhận id có `vai: kiem` (không id người duyệt chung, không bộ SINH); `dot_hien_tai` trong sổ —
  khâu tốn tiền thiếu kiểm trước mà `dot` ≤ `dot_hien_tai` → đỏ (không khai "đợt sau" mãi); trạng thái phụ thuộc cờ đọc cờ thật
  (trường `co`), loại lỗi chỉ tính "có cách kiểm" khi cờ của nó đang bật; số liệu báo cáo lấy từ trang "Làm ↔ Kiểm", không chép tay.
- **Lưu gói gửi (K1a, thẩm định lần 4 lỗ hổng #2 — 0 USD, CHỈ ghi thêm, không đổi hành vi).** Hiện trạng: bảng `jobs`
  (`core/db.py:67` + cột thêm `core/db.py:794-801`) có `external_id` (mã job nhà cung cấp), `model`, `input_hash`, `quality_tier`,
  `sent_refs` (ảnh tham chiếu: `label`, `role`, tên tệp, `plate_key` — `core/runner.py:2222`, ghi ở `_stamp` `core/runner.py:2124` ảnh /
  `:1249` video) — **KHÔNG có prompt cuối đã gửi, không sha ảnh, không tham số** (độ phân giải, thời lượng, seed, negative, tỉ lệ khung);
  prompt hiện chỉ đọc lại được từ `scenes.data.image_prompt` / `motion_prompts` — là bản TRƯỚC khi code nối (`looks.clean_prompt`, khối
  khóa Kho, câu sân khấu) và bị ghi đè khi sửa. Việc: ở đúng chỗ gửi (`core/runner.py:363` `provider.submit(*args, **kwargs)`, cùng giao
  dịch với `external_id` dòng 386) ghi một cột mới `jobs.sent_package` (JSON) = {`prompt` cuối = `args` thật gửi đi, `negative`, `refs[]`:
  {vai, nhãn, đường dẫn, sha256}, `provider`, `model`, `params` (mọi kwargs không bắt đầu `_`), `external_id`, `at`, `v`: 1}; cùng cách cho
  `end_frames` (`sent_refs` → `sent_package`) và nhánh `submit_final_from_sample`. Lỗi khi tính sha / ghi gói → `_diag` VÀNG, KHÔNG chặn gửi
  (gói là sổ, không là cổng). **Nghiệm thu đo được:** (a) test: mỗi đường gửi (ảnh, video, khung cuối, nâng từ nháp) với provider giả →
  100 % job có `sent_package` khớp đúng `args`/kwargs đã gửi (so từng byte prompt); (b) test hành vi: cùng job, cờ tắt/bật → lời gọi
  `provider.submit` giống hệt; (c) dự án thử K1a: truy vấn `SELECT COUNT(*) FROM jobs WHERE created_at ≥ ngày bật AND type IN
  ('image_gen','video_gen') AND external_id IS NOT NULL AND sent_package IS NULL` = 0; (d) ≥ 1 ca hồi quy `tests/golden/` có trường `goi`
  dựng TỪ `sent_package` của job thật (không chép tay). Từ đây: vân tay (3.3), kiểm "prompt gửi thật" (A18 chạy trên gói đã gửi), ca hồi quy.
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

### 4b. Bài học chạy khô #24 (thẩm định lần 4 lỗ hổng #5) — lỗi CHƯA bắt → loại + đợt + nghiệm thu

Nguồn: `docs/BANG_CHUNG_K0B_P24_2026-10-10.md` mục 2 + bổ sung. Chạy khô K0b: 9 lỗi người dùng từng bắt → 2 bắt trước tiền bằng code, 2 chỉ
phòng ngừa, 5 chưa bắt. Tư thế ngã (job 635) thuộc L4 — số đo công cụ ở BANG_CHUNG mục "Đo công cụ K0b" (Pose). Còn lại 5 lỗi dưới đây.
**Loại mới R1** (đầu vào tham chiếu Kho — tiền tố R để không trùng mã khâu L1–L16 của sổ): sản phẩm áp dụng = ảnh mẫu + hồ sơ Kho, lớp
kiểm đặt ở khâu L5 (Hồ sơ / ảnh mẫu Kho) TRƯỚC tiền; thêm vào `devsys/error_types.json` + `knowledge/checks/R1.md` ở K1a (bảng thành 24 loại).

| # | Lỗi #24 | Loại | Lớp bắt (trước tiền → sau gen) | Đợt | Câu nghiệm thu (đo được) |
|---|---|---|---|---|---|
| 1 | Nguồn sáng / trăng luôn ở góc trái khung (job 623–631) dù máy quay nhiều hướng | **L12** (nguồn sáng: hướng + vị trí) | ② sự thật: hướng trăng cố định của bối cảnh (ô `nguon_sang` trong BYĐ nơi chốn) + hướng máy solver → "trăng ở phần ba trái / giữa / phải / ngoài khung" → dữ kiện Đạo diễn + câu kiểm gói; sau gen: code tìm vùng sáng nhất trên trời so phần ba dự kiến, Claude khai enum vị trí trăng | sự thật K2, đo K5 | ca hồi quy #24 (≥ 3 khung trăng sai phía) → lớp code sau gen bắt ≥ 3/3; 0 báo nhầm trên ≥ 3 khung đúng phía / không thấy trăng |
| 2 | Màu giếng không ăn khớp nền (trông dán vào) | **L10** (hòa hợp màu) | Kho: `mau_chinh` vật đo bằng code từ ảnh mẫu đã duyệt (dữ kiện, không chèn chữ); sau gen: thống kê màu vùng vật (hộp chiếu 3D) so `mau_chinh` + so tông nền quanh (ΔE, độ sáng) | dữ kiện K2, đo K5 | ngưỡng ΔE chốt trên ≥ 10 khung gán nhãn người (đúng / lệch); ca giếng #24 bắt; báo nhầm ≤ 10 % |
| 3 | Tháp theo "nền mẫu" (ảnh Kho toàn cảnh) thay vì render 3D — shot 2/3/8/9 | **L11** (nơi chốn, nền) | gói (lưu từ K1a): code kiểm ảnh vai "nền" phải là render plate đúng máy (`plate_key` khớp), ảnh toàn cảnh Kho không được đi kèm vai nền → ĐỎ; sau gen: so mốc tháp (hộp chiếu 3D) + chân trời. `plate_layout_qc` hiện MÙ (báo lệch 9/9) → KHÔNG tính "có cách kiểm" tới khi đo đúng ≥ 1 bối cảnh. Bối cảnh khối nhánh C (A24): vai "nền" KHÔNG là render khối (12b.3) → gói không có ảnh vai nền là ĐÚNG; kiểm `plate_key` chỉ áp bối cảnh có 3D thật, nhánh C kiểm "không có render khối trong vai nền" | gói K3 (lớp code ④), đo K5 | 4/4 shot nền mẫu #24 bắt ở gói; sau gen ≥ 3/4 bắt, ≤ 1/5 báo nhầm trên shot đúng render |
| 4 | Ảnh mẫu Kho bẩn (máu / tóc trên giếng `1.png`, job 623) lan vào mọi shot | **R1** (mới) | khâu L5, một lần khi ảnh mẫu được duyệt/dùng: Claude khai thứ thấy trên ảnh mẫu (enum: máu, tóc, chữ, người khác, nền rối, khác) → code so hồ sơ: thứ không có trong `must_keep` / mô tả → VÀNG, ảnh chưa được dùng làm tham chiếu tới khi người duyệt `sach`; gói chỉ nhận ảnh có `sach` | K1a | ảnh giếng `1.png` #24 bị gắn VÀNG; 100 % ảnh trong `sent_package` dự án thử K1a có `sach` đã duyệt |
| 5 | Mô tả Kho ↔ ảnh mẫu lệch ("đai đỏ" vs ảnh: đai gai đen + khóa tam giác đỏ, #418) → prompt viết sai màu | **R1** (mới) | khâu L5 khi điền `khai_bao_chu` (A20): Claude khai màu từng món trên ảnh mẫu (enum màu) → code so `mau_chinh` / mô tả Kho → lệch = ĐỎ cho hồ sơ (sửa Kho, không sửa prompt) | K1a | #418 "đai đỏ" bắt; 0 báo nhầm trên hồ sơ #23 Kelly (mô tả khớp ảnh); 100 % nhân vật dự án thử đã qua so trước khi gen |

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
| **K0a** Sổ khâu + định dạng — ✅ 10/10 (`df66a11`, `498fa12`; số sống xem trang devsys "Làm ↔ Kiểm" (`devsys/stages.summary_rows` + `only_building`, theo cờ thật); số tại 10/10 sau sửa thẩm định 3: 8 khâu tốn tiền thiếu kiểm trước, 11 khâu đọc chữ tự do, 17/23 loại lỗi không có cách kiểm nào đang chạy với cờ mặc định (6/23 nếu bật hết cờ) — trước đó ghi nhầm "9 khâu" và "6/23") | `devsys/stages.json` + test hợp đồng; thêm khâu code thiếu vào `decisions.json`; schema BYĐ tối thiểu + định dạng ca hồi quy; sửa `LLM_STAGE_TOKENS` khâu chấm (`core/cost.py:297` qc (6000, 900) → output đo ~5000 token, 10/10); gộp `tests/fixtures/stage_facts_golden.json` vào định dạng `tests/golden/` | 0 | test hợp đồng chạy, trang "Làm ↔ Kiểm" hiện đúng các khâu thiếu kiểm (đỏ) |
| **K0b** Bảng loại lỗi + kỹ năng + luật thế giới + bằng chứng chạy khô — ✅ 10/10 sau thẩm định 5 (chạy khô A18 thêm #22: 9 shot, BYĐ suy từ chữ 8/9 hợp lệ, sau lọc 26 món báo — #24 35; bảng gán nhãn 30 mục = 15 #22 + 15 #24 chờ người dùng; `knowledge/world_rules.json` 6 luật có nguồn; `segment` tên lồng nhau sửa + ca hồi quy; phát hiện vật hoãn K5 theo A25) — trước đó 🟡 (còn: ca chưa có lớp chạy; công cụ đo: Pose 32 khung gán nhãn / 27 đo được — KHÔNG phân biệt được ngã ngửa vs ngồi, chỉ dùng VÀNG "thân lệch ≥ 25°" (0/13 báo nhầm); YuNet 36 khung; phát hiện vật HOÃN sang K5 theo A25 (thiếu trọng số) — BANG_CHUNG mục 4, `tools/measure_tools_k0b.py`) (phần 1 `89c5f86`/`b472fda`, chạy lại CSDL thật `a95bfe7`: 31 có / 40 thiếu / 2 thiếu màu / 2 sai màu, 0 món bỏ im lặng; phần 2: `knowledge/checks/` 23 tệp + test hợp đồng, `core/world_rules.py` + `knowledge/world_rules.json` (chưa nối), ô `khai_bao_chu` trong `assets.profile` (không migration; identity_declare đọc ô, món thiếu ô → VÀNG; `color_conflicts`), TU_THE + `nga_ngua`/`nam` chỉ chạy khô (prompt 29 KHÔNG đổi tới khi solver đo thân nằm), ca hồi quy 16 (2 âm/chữ/dựng); rà kỹ bắt 4 lỗi → sửa `24ad1ca`) | `knowledge/checks/*.md` cho L1–L15, V1–V4, A1–A4; bảng luật thế giới có phạm vi; ô `khai_bao_chu` hồ sơ Kho (A20); ca hồi quy từ #8/#22/#24 (`ca_vang_tay`) gồm **≥ 2 ca âm/chữ/dựng** (thoại sai người nói; popup không giữ khung cuối) và **≥ 3 ca có BYĐ + gói**; **thử công cụ đo K5 trên khung thật #24 (0 USD, cục bộ)**: MediaPipe Pose (đã chạy được trên Py 3.14 — đo môi 29/09), YuNet (có), bộ phát hiện vật OpenCV DNN — đo đúng/sai trên ≥ 20 khung, ghi cái nào dùng được; **chạy khô kiểm khóa nhận diện A18 trên prompt thật #22/#24** (bao nhiêu prompt hiện tại sẽ đỏ) | 0 | mỗi loại có tệp kỹ năng + cách kết luận; ≥ 15 ca hồi quy (≥ 2 âm/chữ, ≥ 3 có BYĐ + gói); báo cáo công cụ đo + chạy khô có số |
| **K1a** BYĐ trên 2 bối cảnh có 3D (A15) | `core/shot_intent.py`; Đạo diễn điền BYĐ + `ngoai_le` (prompt 17/20/29, cờ `shot_intent`); dự án mới chỉ chọn được Tháp Đồng Hồ #263 / Cổng Trời #265; duyệt kiểu (c) có hình 3D trên Dashboard; **lưu gói gửi** `jobs.sent_package` (3.9: prompt cuối sau khi code nối + ảnh tham chiếu + vai + sha + model + tham số + mã job; chỉ ghi thêm, không đổi hành vi); lớp code trước tiền cho lỗi mục 4b đợt K1a (ảnh mẫu Kho bẩn, mô tả Kho ↔ ảnh mẫu) | Claude khi chạy Đạo diễn | một dự án mới thử có BYĐ đủ mọi shot, người dùng duyệt; **100 % job ảnh/video mới có `sent_package` (truy vấn = 0 job thiếu) + ≥ 1 ca hồi quy có `goi` dựng từ gói**; nghiệm thu 4b đợt K1a |
| **K1b** Sân khấu 3D cho bối cảnh chưa có 3D (A10, A24, sau K4) | Nhánh B mục 12 `docs/PHUONG_PHAP_SAN_KHAU_3D.md` (hiệu chỉnh, chiều sâu, ghép ảnh, P5; tải model chiều sâu ~100 MB — hỏi người dùng trước); Nhánh C mục 12b (sân khấu khối tự dựng từ khai báo Director, kiểm số, duyệt một lần, lưu `location_pack` `blockout`) — C làm trước (không cần ảnh tốt), B tinh chỉnh khi có ảnh | 0 (code); Claude khi Director khai sơ đồ | B: lệch chiếu ngược ≤ 3 % trên ≥ 3 bối cảnh; C: nghiệm thu 12b.4 → mở thêm bối cảnh cho dự án mới |
| **K2** Viết hợp tác (ảnh) | vòng 3.3 + dấu vân tay gói + ngân sách model + ảnh tham chiếu kiểu Elements; **so A/B ≤ 1 USD** (A7) | ≤ 1 USD (A/B) + Claude vòng viết | người dùng chấm A/B: bản hợp tác ≥ bản hiện tại ở ≥ 2/3 shot |
| **K3** Người duyệt gói ảnh + 2 lớp code video | ④ lớp code chặn, lớp Claude học việc; gen lại qua ③④ + N10; một dòng tiếng Việt; **video: lớp code TRƯỚC + SAU gen (3.4b, A17)** gồm phân loại chuyển động máy | Claude học việc (đo thật — báo giá trước) | lớp code bắt 100 % ca hồi quy thuộc nó; số đo Claude ghi đủ 1 dự án |
| **K4** Video ngang ảnh (lớp Claude) | ③ motion viết hợp tác; ④⑥ lớp Claude cho video: L1–L15 trên khung mẫu (số khung mẫu chốt ở K4 theo đo), tường thuật + chuyển động | như K3 | ca hồi quy video (#22, #24) bắt đúng; ④ video chặn khung đầu sai 100 % |
| **K5** QC sau gen + công cụ đo | DSG + đồ thị phụ thuộc; bộ phát hiện vật, Pose, embedding mặt, màu vùng (L10); Tổ QC C2/C3; N bản rẻ → chọn (tùy chọn) | QC ≈ 0,03–0,04 USD/khung (ước theo số mệnh đề) | số đo đạt mục 9 → đề xuất chặn |
| **K6** Âm thanh, phụ đề, dựng | ④ trước gen: thoại đúng người nói + giọng hồ sơ + độ dài ≤ shot; brief nhạc khớp đường cảm xúc + mốc nhịp; phụ đề chính tả + ≤ 2 dòng + vùng an toàn; danh sách cắt khớp thứ tự BYĐ + popup giữ khung cuối. ⑥ sau: so chữ TTS (d39), loudness, mốc nhịp, phụ đề so thoại + thời điểm, bản dựng so kịch bản; Claude khai SFX khớp hành động | nhỏ | ca hồi quy âm/chữ (≥ 2 từ K0b) bắt đúng 100 %; ④ chặn thoại sai người nói 100 % |
| **K7** Thay đổi theo BYĐ | `change_review` đọc khác biệt BYĐ | như hiện tại | không lớp nào còn đọc chữ tự do để kết luận |
| **K8** Vận hành | quy trình mục 10 vào `docs/CHUAN_XAY_DUNG.md` + CLAUDE.md; báo cáo số đo hàng tuần | 0 | — |

Phụ thuộc: K0a → K0b → K1a → K2 → K3 → K4; **K1b (thuần code) chạy song song từ sau K2** để mở thêm bối cảnh sớm; K5 sau K3 (song song K4 được); K6 sau K3; K7 sau K1a. Điểm dừng đo: cuối K2 (A/B), cuối K3
(số đo học việc), cuối K4 (video).

## 9. Chi phí (theo số đo sổ chi) và tiêu chí nghiệm thu

**Đơn giá ĐO THẬT** (`usage_events`, 10/10): Tổ QC chấm MỘT KHUNG (C1, ~12 mệnh đề) **0,018 USD/lần** (107 lần); QC cũ
0,028 USD/lần (87); Tổ rà soát tác động 0,016 USD/thay đổi (2); Đạo diễn cả kịch bản 0,194 USD/lần (32). Đơn vị ⑥ = MỘT KHUNG (không phải
cảnh). Vòng viết ③ / lớp Claude ④ chưa có khâu đo — ước bằng cỡ Tổ rà soát (một shot, bảng ý + đoạn chữ) ≈ 0,016–0,03 USD/lượt; ĐO thật
ở K2 (vòng viết) và K3 (④) rồi sửa bảng dưới.

**Chi phí vận hành thêm / dự án 9 shot:**

| Phần | Ảnh | Video | Âm/chữ/dựng |
|---|---|---|---|
| ③ vòng viết (9 shot × 1–2 lượt × 0,016–0,03) | 0,15–0,55 | 0,15–0,55 | ~0,1 |
| ④ lớp Claude (9 × 0,016–0,03) | 0,15–0,27 | 0,15–0,27 | — |
| ⑥ QC (9 khung × 0,018 × 1,5 cho ~20 mệnh đề; video 2 khung mẫu/clip) | ~0,25 | ~0,5 | ~0,1 |
| Cộng | ~0,55–1,1 | ~0,8–1,3 | ~0,2 |

Tổng ≈ 1,55–2,6 USD / dự án (đơn giá đo thật); so chi gen (ảnh ~0,05 × 9 × lần gen + video ~1–2 × 9) ≈ 10–20 USD → **≈ 10–20 %**. Người dùng chấp nhận
chi phí này (A16): chi phí kiểm chỉ ĐO và BÁO, không chặn; giảm bằng dấu vân tay (không kiểm lại gói không đổi), gom
mệnh đề, ReplayClient cho ca hồi quy.

**Tiêu chí nghiệm thu:**

| Chỉ số | Ngưỡng | Mẫu số |
|---|---|---|
| Độ phủ cấu trúc | 100 % ô BYĐ có đủ 3 câu; 100 % loại lỗi có cách kiểm thật cho từng sản phẩm áp dụng | số ô / số loại |
| Khâu tốn tiền có kiểm trước | 100 % | `stages.json` |
| Ca hồi quy | 100 % bắt đúng ở lớp được gán | số ca |
| Lọt | ≤ 1 lỗi / dự án trên 2 dự án mới liên tiếp; mỗi lỗi lọt xếp loại trong ngày | lỗi người dùng bắt sau |
| Báo nhầm lớp code A18 (khóa nhận diện) | ≤ 10 % trước khi ĐỎ, **n ≥ 30 mục trên ≥ 2 dự án (#22 + #24)** — A25 | bảng `docs/NHAN_BAO_NHAM_A18_2026-10-10.md` (người dùng gán đúng / nhầm) |
| Báo nhầm lớp Claude | ≤ 10 % trước khi chặn, **cỡ mẫu ≥ 50 mục trên ≥ 2 dự án** | số mục lớp đó báo (người dùng gán đúng/nhầm bằng nút 1 chạm) |
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
| Sân khấu 3D cho bối cảnh chưa có 3D (A10, A24) | A15: chỉ Tháp Đồng Hồ + Cổng Trời tới khi K1b (nhánh B hoặc C) đạt nghiệm thu cho bối cảnh đó |
| Kế hoạch dài, nhiều phiên | mỗi đợt một nhánh; `TODO.md` + kế hoạch này là nguồn trạng thái; điểm nghỉ theo skill vòng làm việc |

## 12. Tái dùng (không viết lại)

`shot_specs` + solver (`core/stage_solver.py`), `stage_facts.FACTS`, `qc_team` (enum, học việc, `ReplayClient`), `qc_rules`,
`trainee_log` (`core/trainee.py`), cách lưu dấu cổng (`core/storyboard_gate.py:103`, `core/autopilot.py:651-685` — CHỈ tham khảo;
dấu vân tay gói VIẾT MỚI ở K2 theo 3.3, không tái dùng),
`scene_storyboard.own_camera`, `palette_check` (`core/palette.py`), YuNet (`text_placement.face_boxes`), đo clip d42, `change_review`,
`before_run`, `script_cap` (trần cứng cho mọi công cụ chạy thật), `prompt_rewrite` (vòng sửa có lưu phiên bản).
