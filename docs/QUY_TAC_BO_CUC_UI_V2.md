# Quy tắc bố cục + hợp đồng nhánh — Giao diện v2 (S13)

Mọi nhánh (B, D, E, F, G) phải đọc file này, `docs/THIET_KE_GIAO_DIEN_2026-10-01.md` (quy tắc + token) và `docs/KE_HOACH_GIAO_DIEN_V2_2026-10-01.md` (kế hoạch). Nguồn thành phần: `dashboard/design/components.py`, xem mẫu chạy được ở `dashboard/design/preview.py` (mở bằng bật cờ `ui_v2` rồi `?step=design`).

## 1. Sở hữu file (không được sửa file của nhánh khác)
| Nhánh | Được sửa | Không được đụng |
|---|---|---|
| B Khung ứng dụng | `dashboard/app.py`, `dashboard/header.py`, `dashboard/design/screens/shell.css`, `dashboard/design/screens/shell_*.py`, `tests/test_ui_shell.py` | mọi thứ khác |
| D Dự án + Nhóm + Theo dõi | `dashboard/home.py`, `dashboard/team_screen.py`, `dashboard/admin.py`, `dashboard/design/screens/home.css`, `team.css`, `monitor.css`, `tests/test_ui_home.py` | |
| E Kịch bản | `dashboard/steps/step1*.py`, `dashboard/design/screens/script.css`, `script_*.py`, `tests/test_ui_script.py` | |
| F Storyboard | `dashboard/steps/step2.py`, `step3.py`, `dashboard/design/screens/storyboard.css`, `storyboard_*.py`, `tests/test_ui_storyboard.py` | |
| G Video + Bản giao | `dashboard/steps/step4.py`, `step5.py`, `dashboard/design/screens/video.css`, `deliver.css`, `video_*.py`, `deliver_*.py`, `tests/test_ui_video.py`, `tests/test_ui_deliver.py` | |
| Lõi (người tích hợp) | `dashboard/design/{tokens.py,theme.css,components.py,preview.py}`, `dashboard/ui.py`, `.streamlit/config.toml`, `core/features.py`, `devsys/areas.json`, `docs/*` | các nhánh KHÔNG sửa; cần thêm thành phần/token → ghi vào mục "Đề nghị cho lõi" cuối báo cáo, tự làm bản tạm trong file `screens/` của mình |
- `dashboard/common.py`: chỉ được THÊM hàm mới ở cuối file, không đổi/xóa hàm cũ.
- Không sửa test cũ trừ khi test đó thuộc màn của nhánh bạn và chỉ vì tên nút/nhãn mới; không xóa test.

## 2. Quy ước tên (chống trùng khóa)
- Khóa container/widget MỚI có tiền tố nhánh: `shell-…`, `home-…`, `team-…`, `mon-…`, `script-…`, `sb-…`, `vid-…`, `del-…`; thẻ kính dùng `components.card("<tiền tố>-<id>")` → class `st-key-card-<tiền tố>-<id>`.
- **Giữ nguyên khóa (`key=`) của mọi widget cũ** (hàng trăm test AppTest bám vào chúng) và nhãn nút mà test dùng; đổi thì sửa test của màn mình.
- CSS riêng của nhánh chỉ đặt trong `dashboard/design/screens/<tên>.css` (tự được nạp khi cờ bật), selector bắt đầu bằng `.st-key-<tiền tố>-…` hoặc `.st-key-card-<tiền tố>-…`. Cấm selector class emotion (`st-emotion-cache…`), cấm sửa `[data-testid]` toàn cục, cấm `!important` trừ khi ghi đè lõi trong phạm vi khóa của mình.

## 3. Quy tắc bố cục (mọi màn)
1. Cấu trúc trên xuống: **hero của màn** (`components.hero` + `hero_html` + vài `stat`) → **thanh công cụ** (tìm/lọc/sắp xếp, tối đa một hàng) → **nội dung chính** (lưới thẻ hoặc danh sách) → **một** thanh hành động dính ở cuối (nếu màn có hành động hàng loạt) → mục “Tinh chỉnh” gập (việc hiếm dùng).
2. Mỗi vùng chỉ **một nút chính** (type="primary" = gradient); phần còn lại secondary; nút nguy hiểm tách riêng, có xác nhận.
3. Lưới thẻ: 4 cột ≥ 1280 px (khung ảnh dọc), 3 cột cho thẻ rộng (dự án, clip); không lồng quá 2 tầng `st.columns`.
4. Khoảng cách theo thang 4/8/12/16/24/32; cỡ chữ theo `tokens.TYPE`, không chữ < 12 px; màu chỉ lấy từ biến CSS (`var(--ok)`, `var(--primary)`…), **không viết hex trong màn**.
5. Trạng thái luôn dùng `components.pill` / `frame_state_pill` / `meter` (nhãn cố định: Cần duyệt · Đang làm · Đã duyệt · Từ chối · Lỗi · Chờ gen); tiền dùng `meter(..., invert=True)`.
6. Nút luôn có **nhãn chữ** (kèm emoji được); không điều khiển nào chỉ hiện khi rê chuột; trạng thái rỗng dùng `empty_state` + một nút hành động.
7. Bảng quan trọng dùng bảng HTML `v2-table` (nền theo giao diện), không dùng `st.dataframe` (canvas luôn sáng).
8. Không bỏ **bất kỳ điều khiển cũ nào**: gom vào “Tinh chỉnh”/menu có nhãn nhưng vẫn truy cập được. Cuối báo cáo nộp **bảng đối chiếu** (điều khiển cũ → vị trí mới).
9. Giao diện v2 chỉ áp dụng khi cờ `ui_v2` bật (`dashboard.ui.v2_on()`); khi tắt, màn phải chạy y như cũ. Cách làm: giữ nhánh mã cũ và thêm nhánh mã mới theo `v2_on()`, hoặc dùng cùng mã với CSS chỉ nạp khi cờ bật. Không làm hỏng chế độ tắt cờ (test cũ chạy với cờ tắt).

## 4. Việc phải chạy / nộp
- Chỉ chạy test mục tiêu: file test của nhánh + các test cũ của màn mình (`py -m pytest -q tests/test_dashboard.py tests/test_screens_dashboard.py <file của bạn> -p no:cacheprovider`). KHÔNG chạy cả bộ.
- Kiểm bằng mắt: chạy `preview_start` với tên cấu hình riêng (cổng riêng, xem `.claude/launch.json`; nếu chưa có thì thêm cấu hình trong worktree của bạn), đăng nhập, bật cờ `ui_v2` (⚙ → 🧪), chụp ảnh sáng + tối, và chạy `tools/ui_contrast_audit.js` (0 chữ < 4.5:1, 0 chữ < 12 px trừ emoji).
- Commit trên nhánh `ui/<tên>` của bạn (không push, không đụng `main`). Báo cáo cuối (tiếng Việt): file đã đổi, bảng đối chiếu điều khiển cũ → mới, ảnh chụp (đường dẫn), kết quả test, “Đề nghị cho lõi”, việc chưa xong.

## 5. Thông tin theo mức ưu tiên (người dùng yêu cầu 01/10) — chi tiết thành chú thích (tooltip + popover), KHÔNG còn nút ⓘ
- **P1 — luôn hiện:** trạng thái (nhãn/pill), nút hành động chính, lỗi chặn, tiền sắp hết.
- **P2 — một dòng tóm tắt:** vd. “3 khung cần duyệt · QC thấp nhất 0.79”, “Bible đã khóa · 4 nhân vật”.
- **P3 — vào chú thích (`components.line(text, details_md, key)`, `components.note(kind, text, summary, key)` hoặc `with components.info(key, anchor=…)`):** giải thích dài, danh sách, số đo chi tiết, lý do/nguồn, hướng dẫn, ghi chú QC dài, lịch sử, cảnh báo ít quan trọng, mô tả tùy chọn, mọi đoạn `st.caption` dài.
- **P4 — không hiện:** thông tin lặp lại ở nơi khác, mã nội bộ, đường dẫn file, thông tin mà người dùng thường không cần.
- Quy tắc áp dụng: không đoạn văn bản thường nào dài hơn ~2 dòng ở ngoài; danh sách > 3 mục → tóm tắt + chú thích; mỗi thẻ tối đa 1 dòng phụ; tooltip `help=` của widget chỉ để bổ sung, không thay cho nhãn.
- Không được mất thông tin: nội dung đưa vào chú thích phải đầy đủ như cũ (tooltip rút gọn ≤ ~420 ký tự, popover có ĐỦ).

## 6. Chú thích (tooltip) — thay nút tròn ⓘ (người dùng 02/10)
Nút tròn “i” bị bỏ. Thông tin P3 hiện **ngay trên chính dòng / nhãn / thẻ cần giải thích**:
1. **Dòng có chú thích** (`components.line`, `components.note`, `components.info(key, anchor=<HTML>)`): trông như chữ thường — KHÔNG gạch chân, KHÔNG nháy. Con trỏ đổi thành dạng “help”; **rê chuột hoặc focus bàn phím** → nền nhấn nhẹ + tooltip (tự vẽ bằng CSS từ `data-tip`, nền `--raised`, chữ `--text` ≥ 14,7:1 sáng/tối, 13 px); **bấm / chạm / Enter** → popover đầy đủ (máy cảm ứng và bàn phím không phụ thuộc rê chuột). Tooltip tự ẩn khi popover đang mở. Nút popover nằm đè kín dòng nhưng trong suốt, tên truy cập “Chi tiết”.
2. **Không có nhãn để gắn** (`components.info(key, label="…")` không có `anchor`): liên kết chữ nhỏ có nhãn (vd. “Chú thích”, “Giải thích số liệu”, “Xem cả N lưu ý”) — không viền, không hình tròn.
3. **Trong popover** (popover không lồng được): `components.tip(html, md)` (tooltip CSS thuần, `tabindex=0` nên chạm/focus cũng hiện) hoặc mục gập `shell_parts.fold(label, md)` (nhãn “Chi tiết · …”).
4. **Biến thể gây chú ý `attention=True`** (`info` / `line` / `note` / `tip(…, key=…, attention=True)`) — **MẶC ĐỊNH TẮT**, chỉ cho thông tin MỚI / BẤT THƯỜNG / CẢNH BÁO thật sự (hiện dùng: cảnh báo “Code đã đổi sau khi Dashboard khởi động”). Vầng sáng mờ `--primary` 3 nhịp × 2 s (`animation-iteration-count` hữu hạn) rồi dừng; Python chỉ gắn lớp `v2-attention` ĐÚNG LẦN ĐẦU phần tử hiện ra trong phiên (`components._first_time`), nên rerun — kể cả `autopilot_progress` làm mới 5 s — không nháy lại; `prefers-reduced-motion`: vầng tĩnh, không animation. Không đè lên nút chính / cảnh báo (chỉ là `box-shadow`, không đổi bố cục). Thông tin thường xuyên (QC, ước tính, ghi chú) KHÔNG dùng biến thể này.
5. **Khóa ổn định:** khóa `key` của chú thích phải giống nhau giữa các lần rerun của một fragment tự làm mới (khóa đổi = phần tử mount lại = popover đang mở bị đóng). Fragment như `autopilot_progress` dùng `step1_v2.reset_scope("ap")` + `cap(..., scope="ap")`.
6. Văn bản trong thuộc tính HTML luôn qua `components._attr` (escape + xuống dòng = `&#10;`); dòng trống trong khối HTML làm Markdown cắt đôi khối.

### Thành phần dùng chung ở lõi (`dashboard/design/components.py`) — các màn dùng thay bản tự viết
| Hàm | Việc |
|---|---|
| `note(kind, text, summary, key)` | thay `st.info/warning/success`: nhãn + một dòng tóm tắt, cả đoạn ở chú thích (`step1_v2.say` gọi hàm này) |
| `version_strip(n, current)` | dải phiên bản chỉ-đọc v1…vN, tự xuống dòng (dải bấm được ở `storyboard_cards._version_strip` bọc trong `vers-*` + CSS cùng ý) |
| `confirm_all(key, ids, label, question, container, yes_label, primary, stretch)` | một nút → hỏi Có/Không; `common.confirm_all` và bản “nút chính” của Storyboard gọi hàm này |
| `cta_box(key)` / `cta(label, key)` | nút chính lớn (3,5 rem, chữ 17 px, toàn chiều rộng) — CSS `[class*="st-key-cta-"]` |
| `grid(count, cols)` | lưới n cột cho thẻ (Tất cả dự án 3 cột, Storyboard 4 cột) |
| `data_table(rows, …)` | thay `st.dataframe` chỉ-đọc: v2 → bảng HTML theo sáng/tối, cờ tắt → `st.dataframe` như cũ (qua `dashboard.common`) |
| `colored(kind, text)` | thay `:orange[]/:green[]/:red[]`: v2 → `.v2-warn-text / .v2-ok-text / .v2-bad-text` (token) |
| `tip(html, md)`, `md_plain(md)` | tooltip CSS thuần; markdown → chữ thường ngắn |
