# Dựng (Editor) — Vùng an toàn đặt chữ (V4 GĐ4, 2026-09-25 — chờ người dùng duyệt)

> Nguồn kiến thức của vai **Dựng** (`editing.md` E7). Mỗi số ghi nguồn + mức tin cậy; nguồn đầy đủ ở `knowledge/sources.md` mục GĐ4 [En].

## Vì sao
Video ngắn 9:16 được xem trong app: phía trên có thanh tab/tìm kiếm, phía dưới có tên tài khoản, chú thích, nhạc, nút; cột phải có nút
thích/bình luận/chia sẻ. Chữ (phụ đề, thông báo hệ thống, card cuối) nằm dưới lớp giao diện đó = người xem không đọc được → mất thông tin
câu chuyện. Vì vậy chữ luôn đặt trong vùng an toàn **chung** của mọi nền tảng sẽ đăng, trừ khi chỉ đăng một nền tảng.

## Số liệu (khung 1080×1920)
| Nền tảng | Trên | Dưới | Trái | Phải | Nguồn · tin cậy |
|---|---|---|---|---|---|
| Instagram / Facebook Reels (Meta) | 14% (269 px) | 35% (672 px) | 6% (65 px) | 6% (65 px) | Meta Ads Guide — Instagram Reels [E9] (chính thức, cho quảng cáo) · **cao** |
| YouTube (video dọc — Google Ads) | 288 px (15%) | 672 px (35%) | 48 px (4,4%) | **192 px (17,8%)** | Google Ads Help, hình vùng an toàn video dọc [E12] (chính thức, cho quảng cáo; **Shorts thường không có số chính thức**) · **cao** |
| TikTok | ~108–130 px | ~320–484 px | ~44–60 px | ~120–140 px | Tài liệu chính thức chỉ nói vùng an toàn đổi theo độ dài chú thích và nút tương tác; số px chỉ có trong file mẫu tải về [E6][E7]; số ở đây từ nguồn thứ cấp [E34] · **thấp–trung bình** |

**Vùng an toàn chung (lấy biên lớn nhất mỗi phía của các nguồn chính thức, cộng TikTok thứ cấp):** trên 15%, dưới 35%, trái 6%, phải 18%
→ hộp chữ ≈ x 65–886, y 288–1248 trên khung 1080×1920 (code đặt lề dưới 36% — thêm 1% đệm so với 35% chính thức). Khung khác tỉ lệ thì quy đổi theo phần trăm. Code: `core/subtitles.py`
`SAFE_TOP 0,15 · SAFE_BOTTOM 0,36 · SAFE_LEFT 0,06 · SAFE_RIGHT 0,18` (phải sửa từ 6% lên 18% ở GĐ4).

## Nguyên tắc đặt chữ theo từng khung hình
1. **Trong vùng an toàn chung** (trên) — luật cứng, code đặt lề.
2. **Không đè mặt và hành động chính**: dò mặt trên khung thật (YuNet, `text_placement`) ở đầu/giữa/cuối mỗi câu; không có model dò mặt thì suy
   theo cỡ cảnh + góc trong bảng shot. Chữ đặt ở phần khung trống; cận mặt → dời cả câu lên dải trên. Ngoại lệ: card cuối nền tối toàn khung.
3. **Phụ đề** một vị trí cố định cả video (dải dưới của vùng an toàn) để mắt người xem không phải tìm; chỉ dời khi khung đó có mặt ở đúng dải đó,
   và dời cả câu.
4. **Chữ hệ thống/thông báo game** (vd "Maxim đã bị hạ.") kiểu thông báo trong game (dải trên của vùng an toàn, giữa, vàng trên nền tối), khác
   kiểu phụ đề để người xem không nhầm là lời thoại.
5. **Tốc độ đọc**: ≤ 17 ký tự/giây (Netflix: 20 cho người lớn, 17 cho trẻ em [E23]); hiển thị ≥ ~0,83 s (20 khung ở 24 fps), hai câu cách
   ≥ 2 khung, chữ ở lại ~0,5 s sau khi hết tiếng nếu không vướng điểm cắt [E24]. TikTok khuyên chữ trên màn hình 5–10 từ/giây [E5] — nhanh hơn
   chuẩn phụ đề, nên phụ đề thoại vẫn dùng mức Netflix.
6. **Cỡ chữ**: chưa có số chính thức (trang BBC không tải được) — tạm: chiều cao chữ hoa ≥ ~3% chiều cao khung (~55–60 px ở 1920), có viền
   hoặc nền mờ [KN]; code mặc định cỡ "Vừa" = 6,5% cạnh ngắn.

## Tự rà
- Chữ nào nằm ngoài hộp an toàn? Chữ nào đè mặt? Người xem có kịp đọc hết không? Có phân biệt được thoại với thông báo game không?
- Thu nhỏ khung về ~360×640 (cỡ màn điện thoại cầm xa) chữ còn đọc được không?
