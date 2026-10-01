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

## 5. Thông tin theo mức ưu tiên (người dùng yêu cầu 01/10) — chi tiết vào dấu ⓘ
- **P1 — luôn hiện:** trạng thái (nhãn/pill), nút hành động chính, lỗi chặn, tiền sắp hết.
- **P2 — một dòng tóm tắt:** vd. “3 khung cần duyệt · QC thấp nhất 0.79”, “Bible đã khóa · 4 nhân vật”.
- **P3 — vào ⓘ (`components.info(key)` hoặc `components.line(text, details_md, key)`):** giải thích dài, danh sách, số đo chi tiết, lý do/nguồn, hướng dẫn, ghi chú QC dài, lịch sử, cảnh báo ít quan trọng, mô tả tùy chọn, mọi đoạn `st.caption` dài.
- **P4 — không hiện:** thông tin lặp lại ở nơi khác, mã nội bộ, đường dẫn file, thông tin mà người dùng thường không cần.
- Quy tắc áp dụng: không đoạn văn bản thường nào dài hơn ~2 dòng ở ngoài; danh sách > 3 mục → tóm tắt + ⓘ; mỗi thẻ tối đa 1 dòng phụ; tooltip `help=` của widget chỉ để bổ sung, không thay cho nhãn. Nút ⓘ luôn hiện chữ “ⓘ” (không chỉ hiện khi rê chuột).
- Không được mất thông tin: nội dung đưa vào ⓘ phải đầy đủ như cũ.
