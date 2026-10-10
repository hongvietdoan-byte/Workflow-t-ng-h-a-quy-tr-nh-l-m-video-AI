# Kế hoạch: Quy trình kiểm soát chặt chẽ và nhất quán giữa khâu làm và khâu kiểm (10/10/2026)

> Người dùng 10/10: "Tôi cần một plan chi tiết hoàn chỉnh để rà soát, kiểm tra tính chặt chẽ và nhất quán của các khâu. Lỗi đã sửa qua
> nhiều dự án mà vẫn chưa hoàn thiện — cần một quy trình thực sự hoàn chỉnh." Nền: `docs/RA_SOAT_KHAU_VA_KIEM_TRA_2026-10-10.md`
> (16 khâu làm, 20 vai kiểm, 6 khâu chưa ai kiểm). Kế hoạch này CHƯA được duyệt — mục 9 là các điểm người dùng cần chốt.

## 0. Vì sao sửa nhiều lần vẫn lặp lại

| Dự án / ngày | Lỗi người dùng bắt | Cách đã sửa | Vì sao kiểu lỗi vẫn quay lại |
|---|---|---|---|
| #8 (27/09–01/10) | trái/phải chi tiết nhân vật, chiều mũ | thêm luật vào prompt QC → rồi "model khai enum" cho riêng mũ | chỉ áp cho 2 loại; không thành cơ chế |
| #22 KLD (07/10) | nền không đúng map 3D, trang phục lệch mẫu, khẩu trang mất | sửa prompt từng shot bằng tay (8/9 prompt viết tay) | công thức không vào hệ thống (bài học 09/10) |
| #24 (09/10) | tháp giữa "nền mẫu", tường cao không có thật, máu/tóc trên giếng | vá máy 3D → làm lại bằng sân khấu 3D; ảnh mẫu Kho sạch | ảnh mẫu Kho + ảnh neo cũ kéo nền; không ai đối chiếu |
| #24 (10/10) | nghiêng máy mất (2, 6, 9), trăng luôn góc trái | câu "nền chỉ từ render", ảnh neo riêng | QC bố cục mù với ảnh đêm |
| #24 (10/10) | thấy lòng giếng khi máy thấp hơn miệng giếng (4), giếng thành khối (8), tư thế ngã sai (4) | `stage_facts` (một nguồn sự thật hình học) | prompt Director chữ tự do trái hình học; QC cả có render vẫn chấm 'ok' |

**Ba gốc chung** (không phải từng lỗi):

1. **Không có một bản ý đồ có cấu trúc.** Đạo diễn viết chữ tự do. Prompt gửi model, ảnh tham chiếu, QC và Tổ rà soát mỗi nơi tự hiểu lại
   chữ đó bằng cách riêng → mỗi nơi một "niềm tin", không ai so chúng với nhau.
2. **Kiểm không đứng đúng chỗ.** Thứ thật sự trả tiền là *gói gửi model* (prompt cuối + ảnh tham chiếu + vai), nhưng không lớp nào nhìn cả
   gói trước khi gửi; lớp mạnh nhất (QC) đứng sau khi đã trả tiền và đang TẮT → người dùng là cổng duy nhất.
3. **Bài học không thành hợp đồng.** Lỗi người dùng bắt được sửa thành một luật lẻ ở một chỗ; không có danh sách "khâu làm nào phải có
   khâu kiểm nào", không có bộ ca kiểm lại tự động → loại lỗi mới hoặc khâu khác lại lọt.

## 1. Nguyên tắc của quy trình (bất biến — mọi thay đổi sau này phải giữ)

| # | Nguyên tắc | Nghĩa cụ thể |
|---|---|---|
| N1 | **Một nguồn ý đồ** | Mỗi shot có MỘT Bảng ý đồ shot (BYĐ) có cấu trúc. Mọi thứ gửi model và mọi lớp kiểm đều ĐỌC BYĐ, không đọc lại chữ tự do. |
| N2 | **Sinh, không chép tay** | Prompt ảnh / motion và danh sách ảnh tham chiếu được code SINH từ BYĐ + sự thật suy ra (hình học 3D, hồ sơ Kho). Chữ tự do chỉ là phần trang trí không kiểm được, ghi rõ như vậy. |
| N3 | **Kiểm trước tiền** | Mọi khâu tốn tiền (ảnh, video, TTS, nhạc, Claude lớn) có một lớp kiểm TRƯỚC khi gửi, nhìn ĐÚNG gói sẽ gửi. |
| N4 | **Model khai, code kết luận** | Lớp Claude chỉ trả lời câu hỏi chọn sẵn (có / không / trái / không chắc) về điều nó THẤY; code so với BYĐ và quyết. Không hỏi "có ổn không". |
| N5 | **Đối xứng làm ↔ kiểm** | Mỗi khâu làm có dòng trong Sổ Làm ↔ Kiểm: kiểm trước, kiểm sau, nguồn đọc, trạng thái. Test đỏ khi khâu tốn tiền thiếu kiểm trước. |
| N6 | **Lỗi người bắt = ca vàng** | Mỗi lỗi người dùng bắt mà máy lọt → một ca trong Bộ ca vàng + chỉ ra lớp kiểm nào lẽ ra phải bắt → sửa LỚP đó (hoặc thêm loại kiểm), không vá prompt của ca đó. |
| N7 | **Đo rồi mới chặn** | Lớp kiểm mới chạy "học việc" (ghi, không tác động) → đo trên bộ ca vàng + dự án thật → đạt ngưỡng mới cho chặn (quyết định 08/10). Lớp code chắc chắn (hình học, đếm) được chặn ngay. |
| N8 | **Người dùng không đọc prompt** | Người dùng thấy MỘT dòng tiếng Việt cho mỗi shot / mỗi lần gen lại: đạt gì, lệch gì, sửa ở đâu. Không bắt người dùng so chữ. |
| N9 | **Gen lại phải đổi đúng đầu vào** | Lần gen lại phải đổi thứ gây lỗi (chữ, ảnh tham chiếu, vai ảnh, render, máy) — kiểm bằng code; ≤ 2 lần tự động rồi hỏi người. |

## 2. Kiến trúc mục tiêu

```
Kịch bản ─▶ Đạo diễn ─▶ ① BẢNG Ý ĐỒ SHOT (BYĐ, có cấu trúc)  ◀── người dùng sửa ở đây (không sửa prompt)
                               │
             ② SỰ THẬT SUY RA (code): hình học sân khấu 3D (stage_facts) · hồ sơ Kho (must_keep, dạng) · liên tục shot kề
                               │
             ③ BỘ SINH GÓI (code): prompt ảnh / motion + ảnh tham chiếu + vai + model  ── dấu vân tay gói
                               │
             ④ NGƯỜI DUYỆT GÓI: lớp code (chặn) + lớp Claude khai enum (học việc → chặn)   ── trước tiền
                               │ đạt
             ⑤ GEN (tốn tiền)
                               │
             ⑥ QC SAU GEN: mệnh đề sinh từ BYĐ (Tổ QC), code đo + Claude khai enum, code kết luận
                               │ lệch
             ⑦ GEN LẠI: chẩn đoán gốc (chữ / ảnh / render / model) → đổi đúng đầu vào → quay lại ③④
                               │
             ⑧ SỔ LÀM ↔ KIỂM + BỘ CA VÀNG + SỐ ĐO từng lớp kiểm (bắt đúng / báo nhầm / lọt)
```

### 2.1 ① Bảng ý đồ shot (BYĐ)

Mở rộng `shot_specs` đã có của sân khấu 3D (V3, `core/stage_director.py`, prompt 29: `nhip`, `co`, `do_cao`, `goc`, `muc_dich`,
`thanh_phan[{vat, vai, vung, thay}]`) thành bảng đầy đủ cho mọi shot. Trường (enum khi có thể):

| Nhóm | Trường | Kiểu |
|---|---|---|
| Truyện | `nhip` (beat), `muc_dich` (vì sao shot tồn tại), `cam_xuc` | chữ ngắn + enum cảm xúc |
| Ai trong khung | `thanh_phan[]`: `vat` (mã Kho), `vai` chính/phụ/không_duoc_co, `vung` trái/giữa/phải × trên/giữa/dưới, `thay` mặt/lưng/nghiêng, `dang` (dạng trang phục Kho, vd yêu nữ d1/d2) | enum |
| Hành động | `bat_dau`, `dinh`, `ket_thuc` mỗi người: tư thế (enum: đứng / ngồi / ngã ngửa / bò / quỳ…) + bộ phận chạm đất + hướng nhìn | enum + chữ ngắn |
| Vật | `vat[]`: mã Kho, phần phải thấy / không được thấy (enum: thành ngoài / mặt trên / lòng / không) — mặc định do ② tính | enum |
| Máy | `co`, `do_cao`, `goc`, `chuyen_dong` (enum), kết quả giải máy `stage_camera` (code) | enum + số |
| Nơi chốn | `noi` (mã Kho + spot), thời gian, thời tiết, ánh sáng | enum |
| Âm / chữ | thoại (đã có), popup, phụ đề | đã có |
| Tự do | `mo_ta_them` — chữ trang trí, KHÔNG kiểm | chữ |

Ai điền: Đạo diễn (Claude) điền BYĐ thay cho chữ tự do (prompt 17/20/29 đổi đầu ra); code kiểm hợp lệ (enum, mã Kho có thật, người có
trong kịch bản, dạng trang phục có trong Kho). Dự án cũ: công cụ suy BYĐ nháp từ chữ cũ, mọi trường suy được đánh dấu `suy_tu_chu`
→ khung "Trước khi chạy" báo cần duyệt. Người dùng sửa shot = sửa BYĐ (Dashboard), không sửa prompt.

### 2.2 ② Sự thật suy ra (code, 0 USD)

- Hình học: `core/stage_facts.py` (đã có 10/10: thấy lòng/thành vật, khối thay thế, vùng khung, chân trời, góc ảnh mẫu) — mở rộng
  thêm: người (từ dàn cảnh sân khấu: thấy mặt/lưng, vùng), vật che (tia Blender đã có trong `stage_grid`).
- Kho: `must_keep`, dạng trang phục, chiều cao/kích thước, ảnh mẫu đã duyệt + góc chụp của ảnh mẫu (thêm trường `goc_anh_mau`).
- Liên tục: trạng thái cuối shot trước (tư thế, chỗ đứng, đồ trên người) → điều kiện đầu shot sau.
- Mâu thuẫn BYĐ ↔ sự thật (vd BYĐ "thấy lòng giếng" mà máy thấp hơn miệng giếng) → mục ĐỎ ngay khi Đạo diễn ghi (trước mọi gen).

### 2.3 ③ Bộ sinh gói

- **Ảnh**: khuôn prompt (`prompt_formula` — đã có phần) điền từ BYĐ: cỡ + máy → ai ở đâu, tư thế, thấy mặt/lưng → vật + phần thấy →
  nơi chốn, ánh sáng → câu sự thật hình học (`stage_facts`) → `mo_ta_them`. Ảnh tham chiếu chọn từ BYĐ: mỗi người đúng dạng trang phục,
  mỗi vật Kho + nhãn "chỉ lấy hình dáng/chất liệu, không lấy góc máy", render nền 3D, ảnh neo (chỉ khi cùng máy). Mỗi ảnh có vai.
- **Video**: khung đầu = ảnh đã duyệt của chính shot (kiểm mã job), motion sinh từ `bat_dau → dinh → ket_thuc` + `chuyen_dong` máy,
  khung cuối (nếu có) từ `ket_thuc`, ảnh tham chiếu video theo luật model (Kling / Seedance — `reference_reference_asset_prompting`).
- **Dấu vân tay gói** = băm(prompt cuối + danh sách ảnh + vai + model + tham số). Mọi lớp kiểm ghi theo dấu vân tay; gói không đổi →
  không kiểm lại (không tốn tiền lại).

### 2.4 ④ Người duyệt gói (trước tiền)

**Lớp code — chặn thật từ đầu** (chỉ những thứ chắc chắn):
- BYĐ hợp lệ; không còn trường `suy_tu_chu` chưa duyệt.
- Sự thật hình học không mâu thuẫn (prompt + BYĐ) — `stage_facts.contradictions`.
- Ảnh tham chiếu: đủ mỗi người trong khung một ảnh đúng dạng; không có ảnh người KHÔNG có trong khung; ảnh vật có nhãn góc khi máy khác
  góc ảnh mẫu; render nền có khi shot có máy 3D; ảnh neo chỉ khi cùng máy (`scene_storyboard.own_camera`).
- Video: khung đầu là ảnh đã duyệt hiện hành của shot; motion có đủ đầu-đỉnh-cuối; thời lượng hợp model.
- Gen lại: gói khác gói lần trước ở đúng thứ gây lỗi (N9).

**Lớp Claude — học việc trước** (đọc ĐÚNG gói: prompt cuối + ảnh tham chiếu thu nhỏ có nhãn vai + BYĐ):
- Code tách BYĐ thành các ý kiểm (vd "Kelly: ngã ngửa, hai tay chống sau", "giếng: chỉ thành ngoài").
- Claude khai từng ý: prompt có nói / không nói / nói trái; ảnh tham chiếu có kéo trái ý không (enum) + chỗ trong prompt (trích ≤ 12 từ).
- Code kết luận: 'trái' ở ý vai chính → đỏ; 'không nói' → vàng; 'không chắc' → vàng.
- Học việc: ghi `trainee_log` + so với ca vàng; đạt ngưỡng (mục 6) → chặn.

Hiển thị: một dòng mỗi shot ở thẻ ảnh/clip: "Gói shot 4: 9/9 ý ✅ · hình học ✅ · ảnh tham chiếu ✅" hoặc "🔴 ý 'ngã ngửa' prompt nói
'ngồi' — sửa ở BYĐ shot 4".

### 2.5 ⑥ QC sau gen

- Mệnh đề QC sinh từ BYĐ (thay cho đọc chữ shot bằng mẫu từ trong `core/qc_spec.py`) + sự thật hình học (đã nối 10/10).
- Lớp code: đo cỡ/mặt/sáng (lớp 0), chân trời giải tích, vùng người/vật bằng phát hiện (YuNet/khung) khi đo được.
- Lớp Claude: Tổ QC khai enum (cơ chế `qc_team` đã có) → `qc_rules` kết luận.
- Bật lại theo lộ trình: học việc trên dự án mới, đo theo mục 6, rồi chặn (quyết định 01/10: chỉ dự án mới).

### 2.6 ⑦ Gen lại

- Chẩn đoán gốc bằng code từ kết quả QC / ghi chú người dùng → loại gốc: BYĐ sai (người sửa) · chữ sinh sai (sửa khuôn) · ảnh tham
  chiếu kéo (đổi ảnh / nhãn vai) · render (sửa máy / khối) · model (đổi câu nhấn mạnh / đổi model).
- Đạo diễn viết lại (`prompt_rewrite`, đang bật) chỉ sửa phần thuộc gốc 'chữ'; ghi chú người dùng tách thành ý → ④ kiểm "đã xử lý /
  chưa / một phần" + không thoái lui (các ý đã đạt ở ảnh trước phải còn) + N9.
- Người dùng thấy: "Gen lại lần 2 · sửa 'tư thế ngã': ✅ · giữ 8/8 ý ✅ · đổi: chữ tư thế + bỏ ảnh neo cũ".

### 2.7 Thay đổi giữa chừng

Tổ rà soát tác động (`change_review`, bật 10/10) đọc **khác biệt BYĐ** (trường nào đổi) thay vì so chữ; luật code biết trường BYĐ nào ảnh
hưởng khâu nào (bảng WATCH chuyển sang trường BYĐ); gói của shot bị ảnh hưởng tự mất dấu vân tay → ④ kiểm lại trước gen.

### 2.8 ⑧ Sổ Làm ↔ Kiểm + Bộ ca vàng + số đo

- **Sổ** = mở rộng `devsys/decisions.json`: mỗi khâu thêm `kiem_truoc[]`, `kiem_sau[]`, `doc_tu` (BYĐ / gói / kết quả), `trang_thai`
  (chạy / học việc / tắt), `ton_tien`. Thêm các khâu code đang thiếu (prompt_formula, stage_facts, before_run, giải máy, render nền,
  end_popup, bộ sinh gói, người duyệt gói).
- **Test hợp đồng** (`tests/test_devsys_decisions.py` mở rộng): khâu `ton_tien` mà `kiem_truoc` rỗng → đỏ; lớp kiểm khai `doc_tu: chu_tu_do`
  → đỏ (phải đọc BYĐ hoặc gói); mỗi loại kiểm có ít nhất 1 ca vàng.
- **Bộ ca vàng** `tests/golden/` (mở rộng `tests/fixtures/stage_facts_golden.json`): mỗi ca = shot (BYĐ + máy + Kho), gói, (ảnh kết quả
  nếu có), lỗi đúng, lớp kiểm phải bắt. Ca từ mục 0 (≥ 15 ca: #8 trái/phải + mũ, #22 nền/trang phục/khẩu trang, #24 tháp/tường/máu-tóc/
  nghiêng/trăng/lòng giếng/khối/tư thế/bóng lướt). Lớp code chạy ca vàng trong bộ test (0 USD); lớp Claude chạy ca vàng bằng công cụ có
  trần `--max-usd` khi đổi prompt lớp đó.
- **Số đo** mỗi lớp kiểm (trang devsys "Làm ↔ Kiểm"): bắt đúng / báo nhầm / lọt (lọt = người dùng bắt sau) theo dự án; tiền kiểm so
  tiền gen.

## 3. Ma trận Làm ↔ Kiểm mục tiêu

| Khâu làm | Kiểm trước (đọc) | Kiểm sau | Trạng thái mục tiêu |
|---|---|---|---|
| L1 kịch bản | K1 dựng được, IP (kịch bản) | người | như cũ |
| L3 Đạo diễn → **BYĐ** | hợp lệ BYĐ + mâu thuẫn sự thật (BYĐ, ②) | "Trước khi chạy" | code chặn |
| L5 Kho / ảnh mẫu | hồ sơ đủ `must_keep`, `goc_anh_mau` | người duyệt Kho | code cảnh báo → chặn khi dùng |
| L6 sân khấu 3D | luật P/S/C solver (số) | ② stage_facts | có |
| L7 ảnh neo storyboard | ④ (gói) | ⑥ | học việc → chặn |
| L8–L9 gói + gen ảnh | ④ code + Claude (gói + BYĐ) | ⑥ Tổ QC (BYĐ) + người | code chặn; Claude học việc → chặn |
| L10 gen lại ảnh | ④ + N9 + "đã xử lý ý" | ⑥ | như L9 |
| L11 motion | ④ video (BYĐ hành động) | — | thay "rà motion theo nút" |
| L12–L13 gói + gen video | ④ video (khung đầu, motion, ref) | K16 đo clip + QC clip + người | code chặn; Claude học việc → chặn |
| L14 TTS / nhạc / SFX / phụ đề | K17 TTS; nhạc theo brief | người | như cũ (giai đoạn sau) |
| L15 dựng, popup | — | rough_cut_review (học việc) | giai đoạn sau |
| L16 thay đổi | Tổ rà soát (khác biệt BYĐ) | — | có |

## 4. Lộ trình theo đợt

Mỗi đợt: cờ riêng (TẮT mặc định), test đỏ → xanh, rà KỸ khi đụng tiền / chặn job / dữ liệu, cả bộ test trước gộp, quy ước 7.

| Đợt | Việc | Tốn tiền | Xong khi |
|---|---|---|---|
| **K0** Sổ Làm ↔ Kiểm + Bộ ca vàng (nền đo) | mở rộng `decisions.json` + test hợp đồng; ≥ 15 ca vàng từ mục 0; công cụ chạy ca vàng (code 0 USD; Claude có `--max-usd`); trang devsys "Làm ↔ Kiểm" | 0 | test hợp đồng chạy; bảng hiện đúng 6 khâu chưa kiểm (đỏ) |
| **K1** BYĐ | schema + kiểm hợp lệ (`core/shot_intent.py`); Đạo diễn điền BYĐ (prompt 17/20/29, cờ `shot_intent`); suy BYĐ nháp cho dự án cũ (đánh dấu `suy_tu_chu`); sửa BYĐ trên Dashboard | Claude khi chạy Đạo diễn (như cũ) | #24 có BYĐ đủ 9 shot, người dùng duyệt |
| **K2** Bộ sinh gói ảnh | prompt + ảnh tham chiếu sinh từ BYĐ + ②; dấu vân tay gói; so trước/sau trên #24, #22 (chạy khô, 0 USD) | 0 | prompt sinh ra không câu trái sự thật; người dùng duyệt 2–3 mẫu gói (một dòng) |
| **K3** Người duyệt gói ảnh | lớp code chặn; lớp Claude học việc; một dòng tiếng Việt; gen lại đi qua ④ + N9 | lớp Claude ≈ 0,02–0,04 USD/shot/gói đổi; đo thật #24 ≈ 0,2–0,4 USD (báo giá trước) | ca vàng ảnh: lớp code bắt 100 % ca thuộc nó; số đo Claude ghi |
| **K4** Gói + người duyệt video | khung đầu, motion từ BYĐ, ref video theo luật model; lớp code chặn; Claude học việc | như K3 | ca vàng video (khi có) |
| **K5** QC sau gen từ BYĐ | `qc_spec` đọc BYĐ; bật Tổ QC học việc dự án mới; chẩn đoán gốc cho gen lại | QC ≈ 0,02 USD/khung (đo GĐ3) | số đo đạt mục 6 → đề xuất chặn |
| **K6** Thay đổi theo BYĐ | `change_review` đọc khác biệt BYĐ; gói mất dấu vân tay → ④ | như hiện tại | Tổ rà soát không còn đọc chữ tự do |
| **K7** Vận hành | quy trình mục 7 vào `docs/CHUAN_XAY_DUNG.md` + CLAUDE.md; báo cáo số đo hàng tuần | 0 | — |

Thứ tự bắt buộc: K0 trước (đo được độ phủ trước khi sửa), K1 → K2 → K3 nối tiếp (mỗi đợt dùng đầu ra đợt trước); K4, K5 sau K3; K6 sau K1.

## 5. Chi phí ước tính (chưa đo, sẽ đo ở K3 và báo lại)

- Phát triển: 0 USD API (code + test); token Claude Code theo gói.
- Vận hành thêm mỗi dự án 9 shot: lớp Claude ④ ảnh + video ≈ 0,4–0,7 USD; QC ⑥ ≈ 0,2–0,4 USD; Tổ rà soát ≈ 0,03 USD/thay đổi.
  So với gen: ảnh ≈ 0,05 USD/ảnh, video 720p Seedance 2.0 ≈ 1–2 USD/clip → phần kiểm ≈ 5–10 % chi phí gen, đổi lại tránh gen lại.
- Ước tính dùng trần ×2 cho lời gọi chấm (đo 10/10: output QC ≈ 5k token, bảng ước thấp ≈ 40 %) — sửa bảng `LLM_STAGE_TOKENS` ở K0.

## 6. Tiêu chí nghiệm thu toàn quy trình

| Chỉ số | Ngưỡng |
|---|---|
| Ca vàng | 100 % ca có lớp kiểm được gán bắt đúng (lớp code: trong bộ test; lớp Claude: lần chạy có trần) |
| Độ phủ | 0 khâu tốn tiền thiếu kiểm trước (test hợp đồng) |
| Lọt | Trên 2 dự án mới liên tiếp: lỗi người dùng bắt mà máy lọt ≤ 1/dự án, và mỗi lỗi lọt thành ca vàng trong ngày |
| Báo nhầm | Lớp Claude ④/⑥ báo nhầm ≤ 10 % mục (đo học việc) trước khi chặn; trái/phải không tự chặn (bài học 01/10) |
| Chi phí kiểm | ≤ 10 % chi phí gen của dự án |
| Người dùng | Không phải đọc prompt: mọi quyết định qua một dòng tiếng Việt + nút |

## 7. Quy trình khi gặp lỗi mới (vận hành — thay cho "sửa ngay chỗ đó")

1. Ghi ca vàng (shot, gói, ảnh, lỗi đúng) — 0 USD.
2. Xác định khâu làm sinh ra lỗi (BYĐ / ② / ③ / model) và lớp kiểm lẽ ra phải bắt (theo Sổ).
3. Nếu chưa có lớp kiểm cho loại này → thêm loại vào sổ kiểm tương ứng (vd `FACTS`, mệnh đề QC) với đủ: suy ra / câu sinh / câu khai /
   code kết luận; nếu có mà lọt → sửa lớp đó.
4. Sửa nguồn (BYĐ / khuôn sinh), KHÔNG vá prompt của riêng ca đó.
5. Test: ca vàng mới đỏ trên code cũ, xanh sau sửa; cả bộ test.
6. Ghi số đo lớp kiểm (lọt +1) + bài học vào `.claude-memory`.

## 8. Rủi ro và cách giảm

| Rủi ro | Giảm |
|---|---|
| BYĐ cứng nhắc, mất sắc thái đạo diễn | giữ `mo_ta_them` tự do (không kiểm); enum mở rộng dần theo ca vàng |
| Dự án cũ phải chuyển đổi | công cụ suy BYĐ nháp + đánh dấu cần duyệt; dự án cũ không bắt buộc (như QC: chỉ dự án mới) |
| Chặn nhầm làm kẹt autopilot | lớp code chỉ chặn điều chắc; lớp Claude học việc trước; mọi chặn có nút Bỏ qua + lý do |
| Tốn tiền kiểm | dấu vân tay gói (không kiểm lại khi không đổi); trần cứng; số đo chi phí kiểm |
| Kế hoạch dài, nhiều phiên | mỗi đợt một nhánh, `TODO.md` + kế hoạch này là nguồn trạng thái; điểm nghỉ theo skill vòng làm việc |

## 9b. Người dùng chốt 10/10

1. BYĐ áp cho **dự án mới**.
2. Sửa BYĐ thay cho sửa prompt: **chờ giải thích rõ + điểm tốt** (đã gửi trong chat 10/10) rồi mới chốt.
3. Ngưỡng mục 6: **tạm giữ**.
4. Thứ tự K0 → … **giữ**: ảnh chuẩn thì video đỡ lỗi; **mức kiểm soát ảnh và video chặt, kỹ NHƯ NHAU** (K4 video có đủ lớp code + lớp
   Claude + mọi loại kiểm như K3, không phải bản nhẹ).
5. **Không phụ thuộc lỗi đã xảy ra**: dự án mới sinh lỗi mới, lỗi cũ lặp lại → nguồn độ phủ KHÔNG phải ca vàng. Sửa kế hoạch → mục 10.
6. Ảnh #24 shot 4/8 (10/10): mọi yếu tố đạt, riêng **màu giếng chưa ăn khớp toàn bối cảnh** → loại kiểm "hòa hợp ánh sáng / màu" (mục 10, L10).

## 10. Độ phủ theo cấu trúc (thay cho dựa vào lỗi cũ — người dùng 10/10 điểm 5)

Ca vàng chỉ còn là **kiểm hồi quy** (lỗi cũ không quay lại). Độ phủ đến từ 3 nguồn không phụ thuộc lịch sử:

**10.1 Mỗi ý trong BYĐ tự sinh ra phép kiểm của nó (theo cấu trúc).** Mỗi trường BYĐ có sẵn trong code: câu sinh vào gói (③), câu hỏi kiểm
gói (④), mệnh đề kiểm kết quả (⑥). Dự án mới có ý đồ mới → phép kiểm mới tự có, không cần ai từng gặp lỗi đó. Test hợp đồng: trường BYĐ
nào thiếu một trong ba → đỏ.

**10.2 Bảng loại lỗi chung (taxonomy) — mỗi loại BẮT BUỘC có cách kiểm, cho cả ẢNH và VIDEO:**

| # | Loại | Kiểm bằng code | Claude khai (enum) |
|---|---|---|---|
| L1 | Danh tính nhân vật | đếm mặt, so ảnh mẫu (embedding khi có) | có phải người X / không / không chắc |
| L2 | Trang phục / dạng | so màu vùng thân với ảnh mẫu (`palette_check`) | từng món must_keep: có / khác / không thấy |
| L3 | Số người, người lạ | đếm phát hiện | người không có trong BYĐ: có / không |
| L4 | Tư thế, hành động | (Pose khi có) | tư thế: enum từ BYĐ |
| L5 | Hướng nhìn, mặt/lưng | YuNet thấy mặt | mặt / lưng / nghiêng |
| L6 | Vị trí trong khung | phát hiện + vùng ba phần | vùng của từng thứ |
| L7 | Vật: có/không, phần thấy, hình dáng | hình học `stage_facts` | phần thấy, hình dáng (khối / thật) |
| L8 | Tỉ lệ, cỡ cảnh | đo mặt/khung, chiếu 3D | cỡ |
| L9 | Máy: góc, nghiêng, chân trời | giải tích từ máy 3D | chân trời ở ba phần nào |
| L10 | **Hòa hợp ánh sáng / màu** (vật "dán vào", khác tông) | thống kê màu-độ sáng vùng vật so nền quanh, so render (cùng nguồn sáng) | vật nào trông khác tông / dán vào: enum |
| L11 | Nơi chốn, nền | so render 3D (nét, chân trời), ảnh toàn cảnh | nền có thứ không có trong render: enum |
| L12 | Thời gian, thời tiết, ánh sáng | độ sáng, nhiệt màu | ngày/đêm, sương, nguồn sáng |
| L13 | Liên tục với shot kề | so trạng thái cuối/đầu | đồ / chỗ / tư thế giữ không |
| L14 | Lỗi tạo hình (tay, mặt méo, chữ) | — | có / không + chỗ |
| L15 | Thứ lạ không có trong BYĐ (máu, tóc, vật thừa) | — | **câu hỏi mở có giới hạn**: liệt kê ≤ 5 thứ thấy mà BYĐ không nói → code so danh sách "không được có" + đánh vàng thứ lạ |
| V1–V4 (video) | trôi hình, giật, môi, chuyển động máy | đo clip (đã có d42) | chuyển động khớp `bat_dau→dinh→ket_thuc` / máy |

Test hợp đồng: mỗi loại có ≥ 1 cách kiểm đang chạy hoặc học việc, cho ảnh và cho video (trừ loại chỉ áp một bên, ghi rõ).

**10.3 Phát hiện cái chưa biết.** L15 (câu hỏi mở có giới hạn) + mỗi lỗi người dùng bắt mà lọt được xếp vào một loại L1–L15; không xếp
được → thêm loại mới (bảng lớn dần theo cấu trúc, không theo từng ca). Số đo "lọt theo loại" chỉ ra loại nào kiểm yếu.

## 9. Điểm cần người dùng chốt trước khi build (bản gốc — xem 9b)

1. **Phạm vi BYĐ:** áp cho mọi dự án mới, dự án cũ chỉ khi gen lại (đề xuất) — hay chuyển cả dự án cũ?
2. **Người sửa shot trên Dashboard sửa BYĐ thay cho sửa prompt** (đề xuất) — chấp nhận ẩn ô prompt tự do (vẫn xem được ở "chi tiết")?
3. **Ngưỡng chặn** mục 6 (báo nhầm ≤ 10 %, lọt ≤ 1/dự án) — giữ hay đổi?
4. **Thứ tự đợt** K0 → K1 → K2 → K3 → (K4, K5, K6) → K7 — giữ hay ưu tiên video (K4) sớm hơn vì video đắt nhất?
5. **Ca vàng ban đầu:** dùng danh sách mục 0 (≥ 15 ca) — người dùng bổ sung lỗi nào khác từng thấy?
