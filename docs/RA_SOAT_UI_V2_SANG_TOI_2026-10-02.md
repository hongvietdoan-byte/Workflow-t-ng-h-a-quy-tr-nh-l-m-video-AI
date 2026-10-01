# Rà soát giao diện v2 — chế độ SÁNG và TỐI (02/10/2026)

Phạm vi: bản demo 0 USD (`py tools/seed_demo.py`, provider mock, `FEATURE_UI_V2=1`, `DASHBOARD_AUTH=off`, cổng 8521), Streamlit 1.64.
Đi qua: ⌂ Tất cả dự án · Kịch bản · Storyboard (tab Ảnh + QC, tab Motion) · Video · Bản giao · 👥 Nhóm · 📊 Theo dõi; popover ⚙ (3 tab), 📥 Việc cần bạn, 💵 Tiền;
hộp thoại ⚙ → 📁 Kho tài nguyên, 🧪 Tính năng thử, 💵 → 💲 Bảng giá. Độ rộng 1440 (chính), 1280 (Kịch bản + ⚙ + Tính năng thử, sáng), 1100 (Storyboard, tối).
Đo bằng `tools/ui_contrast_audit.js` (bản mới — xem mục 4) + kiểm `read_console_messages` + log server (chỉ có lỗi WinError 10054 khi tải lại trang, không có exception của app).

## 1. Lỗi "thanh có mũi tên ▾ tàng hình ở chế độ tối" — nguyên nhân gốc

**Gốc:** Streamlit vẽ hộp thoại `st.dialog`, danh sách chọn, tooltip ở **cổng (portal) nằm ngoài `.stApp`**. Nền của cổng lấy từ theme gốc
`.streamlit/config.toml` (`base = "light"`, nền `#F7F8FA`), không theo 🌙. Trong khi đó chữ (nhãn ô nhập, giá trị ô chọn ▾, chú thích, nội dung mục gập,
nhãn công tắc, nút gửi form) lại nhận màu token tối `--text #F2F4FA` / `--muted #AEB8CE` → **chữ sáng trên nền sáng, tương phản 1.03–1.43:1 = tàng hình**;
khi rê chuột Streamlit phủ nền `rgba(150,176,202,.15)` nên chữ hiện "mờ mờ". Hai lỗi chồng lên nhau:
1. Cả CSS cũ (`DARK_CSS` trong `dashboard/ui.py`) lẫn `theme.css` chỉ tô `div[role="dialog"]` — nhưng ở Streamlit 1.64 hộp thoại là `section[role="dialog"]`
   bên trong `[data-testid="stDialog"] > div` (div này mới là thứ vẽ nền) → luật không bao giờ khớp hộp thoại (chỉ khớp popover).
2. `body` không được tô theo token; các luật màu chữ lại viết trong phạm vi `.stApp …` nên không tới được cổng.

Ngoài ra luật mục gập bị chia ở 3 nơi (CSS cũ đổi chữ tiêu đề thành `--primary` khi rê chuột, DARK_CSS, theme.css) — đã gộp về **một bộ luật cho mọi nơi**
(trang, hộp thoại, popover): tiêu đề luôn `--text` trên `--surface` ở cả 4 trạng thái thường / rê chuột / mở / đóng; rê chuột chỉ đổi nền `--raised` + viền nhấn.

**Cách sửa (tận gốc, chỉ trong lõi `dashboard/design/theme.css` + `tokens.py`, chỉ nạp khi cờ `ui_v2` bật):** `body` nhận `--bg/--text`;
`[data-testid="stDialog"] > div` nhận `--raised`, viền, bo góc, màu chữ; chữ/nhãn/chú thích trong hộp thoại theo token; bộ luật mục gập thống nhất;
ô chọn ▾ (`[data-baseweb="select"]`) + danh sách chọn + nhãn widget theo token ở mọi nơi.

**Lưu ý trung thực:** trên các màn chính của bản demo, tiêu đề `st.expander` ngoài trang vẫn đọc được trước khi sửa (đo: 0 tiêu đề < 4.5:1, kể cả lúc rê chuột);
chỗ tàng hình đo được là trong hộp thoại (⚙ → Kho tài nguyên, Tính năng thử, Bảng giá). Nếu trên Dashboard thật còn thấy ở chỗ khác → chụp ảnh đúng chỗ đó.

## 2. Bảng lỗi

| # | Màn / vùng | Chế độ | Mô tả | Nguyên nhân gốc | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|---|
| 1 | Hộp thoại 🧪 Tính năng thử | tối | Nền trắng, 105 chữ < 4.5:1 (nhãn "Preset/Tìm", công tắc "Bật" 1.03:1, mô tả 1.43:1) | cổng `st.dialog` không theo token (mục 1) | **Đã sửa** → 0 | `anh_ui_v2/ra_soat_2026-10-02/truoc_toi_tinh_nang_thu.jpg` → `sau_toi_tinh_nang_thu.jpg` |
| 2 | Hộp thoại 📁 Kho tài nguyên | tối | Nền trắng; nhãn "Game / loại nội dung", giá trị ô chọn ▾, chú thích, nội dung mục gập mở gần như tàng hình | như #1 | **Đã sửa** → 0 | `truoc_toi_kho_tai_nguyen(_zoom).jpg` → `sau_toi_kho_tai_nguyen.jpg`, `sau_toi_kho_tai_nguyen_re_chuot.jpg` (đang rê chuột) |
| 3 | Hộp thoại 💲 Bảng giá | tối | Nền trắng, 5 chữ < 4.5:1 (nút "💾 Lưu bảng giá" 1.03:1); bảng `st.data_editor` (canvas) trắng | như #1 + canvas vẽ theo theme gốc | **Đã sửa** → 0; bảng canvas đảo màu ở nền tối (token `--canvas-filter`) | `truoc_toi_bang_gia.jpg` → `sau_toi_bang_gia.jpg` |
| 4 | Mọi `st.dataframe`/`st.data_editor` | tối | Nền sáng lạc trong chế độ tối (panel admin) | canvas không đọc CSS | **Đã sửa (lưới an toàn)**: `filter: var(--canvas-filter)` = `invert(.92) hue-rotate(180deg)` ở tối, `none` ở sáng. Bảng quan trọng vẫn nên chuyển sang `components.table` | ảnh Bảng giá sau |
| 5 | Chú thích `st.caption` ở Kịch bản (13), Storyboard (17), Video (2), Bản giao (2), Theo dõi (2), popover ⚙/💵 | sáng (2.87:1), tối trong popover (3.84:1) | Chữ chú thích mờ | Streamlit 1.64 tự đặt `opacity: .6` cho một số `st.caption` → màu `--muted` (đã ≥ 4.5) bị mờ thêm; bộ đo cũ bỏ qua opacity nên không thấy | **Đã sửa**: `[data-testid=stCaptionContainer]{opacity:1}`; bộ đo mới tính opacity | số liệu mục 3 |
| 6 | ⚙ → "Ai duyệt ảnh/clip" (viên chọn) + mọi radio dạng pill `mode_/filter_/level_/home_status` | tối | Viên đang chọn: chữ trắng trên `--primary #8F7BFF` = 3.26:1 | CSS cũ tô nền `--primary` (đổi sang tím sáng ở token tối) | **Đã sửa**: nền `--grad-primary` (chữ trắng ≥ 4.5 ở mọi điểm dừng) | `truoc_toi_popover_caidat.jpg` → `sau_toi_popover_caidat.jpg` |
| 7 | Chữ màu cũ `:orange[]` (vd. "Nhập tên để lượt gen được ghi cho bạn." trong ⚙) | sáng 3.42:1 | Cam Streamlit `#E2660C` | màu nội dòng của theme sáng; CSS cũ chỉ có bộ lọc sáng cho chế độ tối; `:gray[]` `#31333F` gần như tàng hình ở nền tối | **Đã sửa**: ánh xạ đỏ/cam/vàng/xanh lá/xanh dương/tím/xám → `--bad/--warn/--ok/--info/--primary/--muted`, bỏ bộ lọc | `sau_sang_tinh_nang_thu_1280.jpg` (dòng cam trong ⚙) |
| 8 | Hộp `st.info`/`st.warning` (vd. "🔄 Đang tạo 1 ảnh…" ở Storyboard) | tối | Chữ xanh đậm `rgb(0,84,163)` trên nền tối 2.36:1 | màu chữ alert theo theme sáng | **Đã sửa**: chữ alert = `--text`, viền trái màu theo loại (`--info/--warn/--bad/--ok`) | audit Storyboard tối 1 → 0 |
| 9 | Mục gập (expander) mọi nơi | cả hai | Luật màu chia 3 nơi, rê chuột đổi chữ sang màu nhấn | xem mục 1 | **Đã sửa** (thống nhất) | `sau_toi_theo_doi_muc_gap.jpg` |
| 10 | Hero cột phải (mọi màn dự án) | cả hai, rõ ở 1100 px | Nhãn "🎚 Mức tự động" cách xa 3 nút chọn; cột trái có khoảng trống dọc lớn giữa pill và "Việc tiếp theo" | bố cục 2 cột `project_hero` (nhánh B) | **Đề xuất** (đổi bố cục): đặt nhãn sát nút, "Việc tiếp theo" ngay dưới pill, cột phải thu gọn | `toi_1100_hero_thua_doc.jpg` |
| 11 | Thanh trên ở 1100 px | cả hai | Chữ "AI Video Pipeline" ẩn, chỉ còn logo | co giãn của thanh trên | **Đề xuất** (chấp nhận được; cân nhắc tooltip) | `toi_1100_hero_thua_doc.jpg` |
| 12 | ⚙ → mục gập "ⓘ Chỉnh QC, khung, thể loại ở đâu · 'Thứ rẻ' là gì" | cả hai | Nhãn bị cắt ở popover rộng 390 px | `shell_parts.fold` dùng expander trong popover (bản tạm, TODO D) | **Đề xuất**: rút gọn nhãn ("ⓘ Chỉnh ở đâu?") khi làm `components.info` dùng được trong popover | `sau_toi_popover_caidat.jpg` |
| 13 | Nền mờ phía sau hộp thoại | tối | Lớp phủ `rgba(150,176,202,.25)` (xám xanh sáng) — trang phía sau không tối đi | theme gốc | **Đề xuất**: token `--scrim` (tối: `rgba(0,0,0,.55)`) | `sau_toi_bang_gia.jpg` |

Không phát hiện: chữ < 12 px (0 ở mọi màn), cuộn ngang ở 1100 px, nhãn bị "…" ở Storyboard 1100 px, exception trong log server, lỗi console của app.

## 3. Số liệu `ui_contrast_audit.js` (chữ < 4.5:1 · chữ < 12 px), 1440 px trừ khi ghi khác

| Vùng | Tối trước | Tối sau | Sáng trước | Sáng sau |
|---|---|---|---|---|
| ⌂ Tất cả dự án | 0 · 0 | 0 · 0 | 0 · 0 | 0 · 0 |
| Kịch bản (1280 sáng: 0 · 0 sau) | 0 · 0 | 0 · 0 | 13 · 0 | 0 · 0 |
| Storyboard — Ảnh + QC | 1 · 0 | 0 · 0 | 17 · 0 | 0 · 0 |
| Storyboard — Motion | 0 · 0 | 0 · 0 | — | — |
| Video | 0 · 0 | 0 · 0 | 2 · 0 | 0 · 0 |
| Bản giao | 0 · 0 | 0 · 0 | 2 · 0 | 0 · 0 |
| 👥 Nhóm | 0 · 0 | 0 · 0 | 0 · 0 | 0 · 0 |
| 📊 Theo dõi (mở 4 mục gập) | 0 · 0 | 0 · 0 | 2 · 0 | 0 · 0 |
| ⚙ Dự án / Tài nguyên / Hệ thống | 2 / 1 / 1 | 0 / 0 / 0 | 1 (tab Dự án) | 0 / – / 0 |
| 📥 Việc cần bạn | 0 | 0 | — | — |
| 💵 Tiền | 3 | 0 | — | — |
| Hộp thoại 🧪 Tính năng thử | **105** | 0 | — | 0 (1280) |
| Hộp thoại 📁 Kho tài nguyên | (bộ đo chạy nhầm vùng — xem ảnh) | 0 | — | — |
| Hộp thoại 💲 Bảng giá | 5 + bảng canvas trắng | 0 | — | — |
| Storyboard 1100 px | — | 0 · 0 | — | — |

"—" = chưa đo ở chế độ đó. Bộ đo **trước** đã là bản mới (tính opacity); với bộ đo cũ, các lỗi #5 không hiện ra.

## 4. Bộ đo `tools/ui_contrast_audit.js` — đã nâng cấp
- Tính **độ mờ thực** (opacity của phần tử × các cha × alpha của màu chữ, trộn với nền) — trước đây chữ bị `opacity .6` vẫn tính là đạt.
- Bỏ qua chữ trên nền gradient (nút chính, viên chọn đang chọn) vì đã kiểm bằng `tokens.promised_pairs`; bỏ qua icon vật liệu.
- Hằng `ROOT` để quét riêng một vùng (vd. `'[data-testid="stDialog"]'`). Lưu ý: popover/hộp thoại có bản sao ẩn trong DOM — chọn phần tử đang hiện.

## 5. Điểm giao diện từng màn (1–10: dễ đọc · nhất quán · bố cục · tương phản), trước → sau

| Màn | Trước | Sau | Ghi chú |
|---|---|---|---|
| ⌂ Tất cả dự án | 8 | 8 | gọn, 0 lỗi đo; thẻ dự án 1 cột khi ít dự án |
| Kịch bản | 7 | 8.5 | chú thích mờ (sáng) đã hết; hero cột phải thưa (#10) |
| Storyboard — Ảnh + QC | 7 | 8.5 | chú thích thẻ khung mờ (sáng) + alert xanh đậm (tối) đã hết |
| Storyboard — Motion | 8 | 8 | đã nền tối đúng; hero thưa (#10) |
| Video | 7.5 | 8 | |
| Bản giao | 8 | 8.5 | |
| 👥 Nhóm | 8.5 | 8.5 | |
| 📊 Theo dõi | 8 | 8.5 | mục gập đồng nhất |
| Popover ⚙ | 7 | 9 | viên chọn đọc được, dòng tài khoản rõ; nhãn ⓘ bị cắt (#12) |
| Popover 📥 / 💵 | 9 / 7.5 | 9 / 9 | |
| Hộp thoại (Tính năng thử, Kho tài nguyên, Bảng giá) — tối | 2 | 9 | trước: nền trắng + chữ tàng hình; bảng canvas đảo màu là lưới an toàn |

## 6. File đã đổi
- `dashboard/design/theme.css` (lõi): khối "rà soát sáng/tối 02/10" — cổng/hộp thoại, mục gập thống nhất, ô chọn ▾, chú thích, viên chọn, alert, chữ màu cũ, canvas, nút gửi form.
- `dashboard/design/tokens.py`: token `canvas-filter` (tối: đảo màu, sáng: `none`).
- `tools/ui_contrast_audit.js`: tính opacity, bỏ qua nền gradient, `ROOT`.
- `tests/test_ui_v2_core.py`: `test_portals_and_folds_follow_the_theme`.
- Không đổi hành vi nghiệp vụ, không xóa/đổi `key=` nào, không đổi mặc định cờ `ui_v2`; chế độ tắt cờ không bị ảnh hưởng (mọi luật nằm trong `theme.css` chỉ nạp khi cờ bật).

## 7. Việc còn lại
- Kiểm trên **Dashboard thật** (cổng 8501, cần khởi động lại để nạp `tokens.py`) ở chỗ người dùng đã thấy lỗi; nếu tiêu đề mục gập ngoài trang vẫn mờ → chụp ảnh đúng chỗ.
- Đề xuất #10–#13 (bố cục hero, thanh trên < 1280, nhãn ⓘ trong popover, nền mờ hộp thoại) — cần duyệt vì đổi bố cục/nhánh B.
- Chưa quét: panel Chuyên gia ở Video (cần bật 🧠), ca "Tự động đang chạy", các hộp thoại khác (Kho kiến thức, Bài học, Giới hạn hệ thống, Lịch sử & thùng rác, Phân quyền, Đợt thử & Claude), 1100 px các màn ngoài Storyboard, dữ liệu thật (#8).
- Ánh xạ chữ màu cũ bám giá trị RGB của Streamlit 1.64 → khi nâng Streamlit phải chạy lại bộ đo; về lâu dài thay `:orange[]…` bằng `.v2-warn-text`/pill.
- `DARK_CSS` cũ trong `dashboard/ui.py` có luật trùng/lỗi thời (`div[role="dialog"]`) — dọn khi bỏ nhánh mã cũ (sau khi `ui_v2` mặc định bật).
