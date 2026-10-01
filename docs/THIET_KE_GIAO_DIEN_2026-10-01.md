# Hệ thống thiết kế giao diện Dashboard (01/10/2026)

Lý do: người dùng — “Dashboard đang được thiết kế đồng bộ siêu kém”, phải rê chuột mới thấy nhiều ô (tab ⚙ bị chữ tối trên nền tối), viền khung
không rõ, chữ nhỏ khó đọc. Đã nghiên cứu cách các công cụ khác làm (nguồn ở cuối), rút thành quy tắc + bảng màu, áp dụng vào `dashboard/ui.py`
và `.streamlit/config.toml`. Quy tắc này là **bắt buộc cho mọi màn mới**.

## 1. Học từ công cụ khác (đã lấy được nội dung thật; chỗ không rõ ghi “chưa rõ”)
| Công cụ | Điều rút ra |
|---|---|
| Frame.io (duyệt video) | Trạng thái duyệt là nhãn cố định nhỏ (Needs Review / In Progress / Approved) hiện ngay trên thẻ; mọi hành động nằm trong khung player; bảng phím tắt mở bằng “?” |
| Runway | Sắp xếp + lọc theo loại / người tạo / ngày; thao tác hàng loạt; bảng credit & chi tiêu riêng. Hover-scrub chỉ là tiện ích, không phải cách duy nhất |
| Higgsfield | Hiện trạng thái bằng chữ (Queued / Processing); bài học: treo “Processing” hàng giờ không lý do là điều người dùng ghét → ta hiện thời gian đã chờ + nút thử lại |
| LTX Studio | Thẻ shot là đơn vị chính; tạo lại một shot không đụng phần khác |
| Descript | Một nội dung hiện ở 2 nơi (kịch bản + timeline); chọn Sáng / Tối / Theo hệ thống ở MỘT chỗ cố định |
| Linear | Ít màu, ít viền, sinh sáng/tối từ vài tham số; giảm nhiễu ở sidebar / tab / header |
| Vercel Geist | Thang 10 bậc cho mỗi màu, quy ước bậc nào dùng làm gì (1-3 nền, 4-6 viền, 9-10 chữ) → không ai tự chọn hex |
| GitHub Primer / Carbon / Atlassian | Màu theo vai trò (accent / success / attention / danger); trạng thái dùng ≥ 2 trong (màu, hình, ký hiệu) + chữ; chữ ≥ 4.5:1, UI/icon/viền ≥ 3:1; token tự đổi sáng/tối |

## 2. Quy tắc (áp dụng cho mọi màn)
1. Hành động chính luôn có **nhãn chữ hiện sẵn**; hover chỉ để thêm gợi ý, không phải cách duy nhất.
2. Mỗi vùng một nút chính (nền đặc); nút phụ có viền; nút nguy hiểm tách riêng + xác nhận.
3. Chữ thường ≥ **4.5:1**; chữ ≥ 24 px, icon, viền điều khiển, thanh tiến độ ≥ **3:1** (WCAG 1.4.3 / 1.4.11).
4. Viền ô nhập / nút / thẻ ≥ 3:1 so với nền kề.
5. Có focus ring (2 px, ≥ 3:1) ở sáng và tối.
6. Trạng thái = màu + ký hiệu + chữ; mỗi màu một nghĩa: xanh lá = ok, cam = đang chạy / chờ, đỏ = lỗi, xanh dương = thông tin.
7. Tiến độ luôn kèm số (% hoặc n/N), **màu theo %** (đỏ → cam → xanh dương → xanh lá); thanh tiền đảo ngược (đầy = xấu).
8. Thanh bước, tab, nút chọn hiện **đủ mọi lựa chọn** cùng lúc, mục chọn = nền đặc + chữ đậm.
9. Nhãn duyệt cố định: Cần duyệt / Đang làm / Đã duyệt / Từ chối, hiện trên thẻ.
10. Màn duyệt có thanh công cụ cố định: Duyệt / Từ chối + lý do / Tạo lại, kèm phím tắt trên nhãn (chưa có phím tắt thật — Streamlit không có sẵn).
11. Đơn vị duyệt là từng cảnh / shot.
12. Trang rỗng có 1 câu giải thích + 1 nút hành động kế tiếp.
13. Hộp “Việc cần bạn” xếp theo mức khẩn, mỗi dòng có nút vào thẳng.
14. Thang khoảng cách 4/8/12/16/24/32; thang chữ cố định; **không chữ nhỏ hơn 12 px, chữ chức năng (nút, trạng thái) ≥ 13–14 px**.
15. Gom hành động phụ vào một menu “Thêm” (có nhãn chữ).
16. Chi tiêu là một khối cố định có % và màu theo ngưỡng.
17. Nền tối không đen thuần; lớp nền sáng dần theo độ nổi; màu trạng thái tối có nền “soft” riêng; kiểm tỷ lệ từng cặp.
18. Mọi màu lấy từ **token** (biến CSS ở `dashboard/ui.py`), không chọn hex tại chỗ.
19. Sáng / Tối chọn ở một nơi (⚙ → Hệ thống → 🌙).
20. Dùng widget gốc của Streamlit khi có; CSS tùy biến bọc trong container có khóa riêng để không lan sang chỗ khác (class và `data-testid` đổi theo bản Streamlit — kiểm lại mỗi lần nâng cấp).

## 3. Token (đã tính tỷ lệ tương phản)
| Token | Sáng | Tối |
|---|---|---|
| nền trang `--bg` | #F7F8FA | #0F1115 |
| nền thẻ `--surface` | #FFFFFF | #171A21 |
| nền nổi `--raised` | #FFFFFF | #1F232C |
| viền `--border` | #7C879A (3.63 trên thẻ) | #657086 (3.49) |
| viền mạnh `--border-strong` | #5F6B7E | #8791A3 |
| chữ `--text` | #111827 (17.7) | #F2F4F8 (15.8) |
| chữ phụ `--muted` | #4B5563 (7.6) | #AAB2C0 (8.2) |
| chữ vô hiệu `--disabled` | #6B7280 (4.8) | #7C8596 (4.7) |
| chủ đạo `--primary` / chữ trên nó | #2F5BEA / #FFFFFF (5.5) | #7C9CFF / #0F1115 (7.3) |
| focus `--focus` | #1D4ED8 | #9DB6FF |
| ok / nền | #13693A / #E3F6EA | #6EE7A0 / #10281B |
| warn / nền | #8A4B00 / #FFF1D6 | #FBBF55 / #2E2108 |
| bad / nền | #B42318 / #FDE8E6 | #FF8B80 / #34130F |
| info / nền | #1D4ED8 / #E4EDFF | #8FB2FF / #122046 |

## 4. Đã làm (01/10) và còn lại
- ✔ Token + nền tối + viền 1.5 px đậm (cả khối `stVerticalBlock` có viền) + focus ring + tab hiện đủ với trạng thái chọn nền đặc + màu theo % cho thanh tiến độ + cỡ chữ tối thiểu 12 px + nút chọn dạng chip.
- ✔ Công cụ đo: `tools/ui_contrast_audit.js` (mục 5) trên từng màn để liệt kê chữ < 4.5:1 và chữ < 12.5 px.
- ☐ Chưa làm: phím tắt thật cho màn duyệt (cần component ngoài), thanh công cụ duyệt cố định, nhãn duyệt cố định trên thẻ ảnh / clip, menu “Thêm” gom nút phụ, thời gian đã chờ + nút thử lại cho job treo, bảng dữ liệu (canvas) chưa đổi nền tối.

## 5. Cách kiểm
Mở màn cần kiểm ở cả 2 giao diện (`?theme=dark`), dán `tools/ui_contrast_audit.js` vào console trình duyệt (so màu chữ với nền hiệu lực của từng phần tử có chữ, in những phần tử < 4.5:1 và chữ < 12.5 px). Mục tiêu: 0 phần tử, trừ chữ trang trí.

## Nguồn
Frame.io help (player page, shortcuts) · Runway changelog / help · Higgsfield help center · LTX Studio và Descript help/review · Linear “How we redesigned the Linear UI” · Vercel Geist colors · GitHub Primer color · Carbon status indicator · Atlassian color foundations · WCAG 2.2 (1.4.3, 1.4.11) · Streamlit theming docs.
Ghi chú: bảng màu ở mục 3 là đề xuất của ta (không phải màu công khai của hãng nào).
