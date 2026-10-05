# Kế hoạch phân tích kênh TikTok `@freefire_kelly_official` làm tài liệu tham khảo (05/10/2026)

> Người dùng đề xuất 05/10 sau khi chấm S14.22 (5/5 kịch bản Biên kịch khó dựng chuẩn). Theo dõi ở việc **S14.32** (`docs/KE_HOACH_SUA_SAU_DU_AN_8.md`).

## 0. Vì sao
- Kênh chính thức xoay quanh **Kelly**, dựng gần như hoàn toàn bằng **3D** — đúng loại nội dung pipeline muốn làm.
- Kênh đã giải sẵn bài toán "thứ khó dựng": ví dụ clip [7665285092293578005](https://www.tiktok.com/@freefire_kelly_official/video/7665285092293578005) (11 s) quay **Kelly ngoài đời (3D) chơi game cùng đồng đội**, KHÔNG quay màn hình điện thoại; thay vào đó **thanh máu + tên + số thứ tự trong đội hiện trên đầu nhân vật** → người xem vẫn hiểu "trong trận sắp hết máu". Đây là kỹ thuật **né cái không dựng được bằng góc máy / lớp phủ** (người dùng chỉ ra).
- Mục tiêu: rút ra cách kênh kể chuyện, chọn bối cảnh, góc máy, lớp phủ (HUD trên đầu, chữ), nhịp, âm thanh — đưa vào kiến thức của Biên kịch / Đạo diễn / Dựng để kịch bản **dựng chuẩn được**.

## 1. Quy mô kênh (đọc danh sách 05/10, chưa tải video)
- 493 clip, trung bình 15,3 s (dài nhất 68 s), tổng ≈ 2 giờ. View: cao nhất 51,2 triệu; trung vị ≈ 586 nghìn.
- Danh sách id | giây | view | tiêu đề lưu ở thư mục tạm của phiên (`kelly_list.txt`); lần chạy thật lưu `data/ref_kelly/list.tsv` (ngoài git).

## 2. Chọn mẫu (không tải cả kênh)
- **Đợt 1 — 40 clip:** 20 clip view cao nhất (cái gì làm nên hit) + 10 clip mới nhất (cách làm hiện tại) + 10 clip chọn theo chủ đề lặp lại (Maxim, đồng đội / "bodyguard squad", POV, thú cưng, thể thao…) để phủ đủ dạng.
- Dung lượng ≈ 0,2 MB/giây video → 40 clip × ~15 s ≈ **120–150 MB**, lưu `data/ref_kelly/<id>.mp4` (NGOÀI git). **Tải file phải hỏi người dùng** (tên + nguồn + dung lượng).
- Đợt 2 (nếu Đợt 1 có ích): thêm 40 clip theo dạng còn thiếu.

## 3. Cách phân tích (0 USD Claude API)
1. `py tools/reference_video.py sheets <clip.mp4> <work_dir>` — cắt shot, khung giữa mỗi shot, bảng ảnh (có sẵn, 0 USD).
2. `py tools/audio_listen.py` — tách thoại / nhạc / hiệu ứng, chép lời (có sẵn, 0 USD).
3. Gán nhãn **trong phiên Claude Code** (đọc bảng ảnh như ảnh — luật đọc tài liệu đầy đủ cả hình) rồi `py tools/reference_video.py save <work_dir> KELLY <labels.json>` — không gọi Claude API (tốn hạn mức phiên, không tốn USD). Gán nhãn bằng Claude của Dashboard (`label`) chỉ dùng khi người dùng duyệt tiền.
4. Mỗi clip ghi theo phiếu (mục 4); `py tools/reference_video.py stats KELLY` ra số đo chung.

## 4. Phiếu cho mỗi clip
| Trục | Ghi gì |
|---|---|
| Định dạng | POV / tiểu phẩm / phản ứng / trend / meme…; độ dài; số shot; shot TB |
| Hook 3 s đầu | cái gì giữ người xem (câu thoại, hành động, chữ trên màn) |
| Bối cảnh | nơi nào (ngoài đời 3D? map FF? khu vực nào?) — có trong Kho của mình chưa, có 3D chưa |
| **Né thứ khó dựng** | cảnh "trong game" được thể hiện thế nào khi không quay màn hình: HUD trên đầu (máu / tên / số đội), chữ, âm thanh game, cắt cảnh, góc lưng, phản ứng mặt… |
| Nhân vật + trang phục | ai, mặc gì (mặc định hay skin), biểu cảm / diễn xuất 3D |
| Góc máy + chuyển động | cỡ cảnh, máy tĩnh / đẩy / lắc, chuyển cảnh |
| Lớp phủ | chữ, emoji, HUD, phụ đề — vị trí trên khung dọc |
| Âm thanh | thoại (ngôn ngữ), nhạc trend, hiệu ứng game, khoảng lặng |
| Cú chốt | kết bằng gì; có CTA không |
| Dựng được bằng pipeline? | ✅ có tài nguyên + kỹ thuật / ⚠ thiếu gì (tài nguyên, tư liệu, công cụ) |

## 5. Đầu ra
- `knowledge/ff_styles/kelly_official.md` — phong cách kênh (số đo + luật **gợi ý**, có dẫn chứng = id clip + mốc giây; không bắt buộc, trộn được — luật "phong cách tham khảo là gợi ý").
- `knowledge/craft/ne_canh_kho_dung.md` — **danh mục kỹ thuật né cảnh không dựng được** (HUD trên đầu thay màn hình điện thoại, …) kèm điều kiện dùng; Biên kịch + Đạo diễn đọc (sau cờ, TẮT mặc định — như S14.20).
- Danh sách "định dạng kịch bản dựng chắc được" → đưa vào S14.31 (Biên kịch chỉ viết thứ dựng được) và bộ ý tưởng đo lại S14.22.
- Danh sách tài nguyên còn thiếu (bối cảnh 3D, lớp HUD trên đầu…) → việc tạo tài nguyên sau (hỏi tiền).
- Báo cáo ngắn `docs/PHAN_TICH_KENH_KELLY_<ngày>.md` để người dùng duyệt trước khi đưa luật vào prompt.

## 6. Luật
- Video tham khảo **chỉ để học**, không cắt ghép / không dùng lại hình của kênh (cùng tinh thần "tư liệu gameplay chỉ để AI hiểu").
- Kỹ thuật quay / dựng không có nghĩa cố định; không khái quát từ 1 clip — luật cần ≥ 3 clip dẫn chứng.
- Video và khung hình nằm ngoài git (`data/ref_kelly/`), repo chỉ giữ chữ + số đo.
- Không im lặng khi clip không tải được / bị chặn (ghi lý do vào danh sách).

## 7. Chi phí + thứ tự
- 0 USD Claude API (gán nhãn trong phiên). Tốn hạn mức phiên Claude Code: ước ≈ 40 clip × (đọc 1–2 bảng ảnh + chép lời) — chia 2–3 lượt, mỗi lượt 1 phiên con, điểm nghỉ theo skill.
- Thứ tự đề xuất: chạy song song / ngay sau S14.31 phần luật (S14.31 có thể dùng ngay kỹ thuật HUD trên đầu người dùng đã chỉ); kết quả Đợt 1 bổ sung vào S14.31 trước khi ghi bản ghi Biên kịch mới.
