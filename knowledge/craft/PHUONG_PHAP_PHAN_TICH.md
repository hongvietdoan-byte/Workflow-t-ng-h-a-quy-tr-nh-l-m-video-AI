# Phương pháp học và phân tích kỹ thuật làm phim (S0.10, 2026-09-29)

> Người dùng 2026-09-29: máy quay, góc, chuyển động, dựng, âm thanh rất đa dạng — mỗi lần dùng có **ý đồ riêng theo tình huống**, không có
> nghĩa mặc định. Ba nghề (Đạo diễn, Quay phim, Dựng) cần chuyên môn sâu và nền tảng rộng: xem nhiều mẫu, đọc nhiều tài liệu chuyên môn,
> và **phân tích cho chính xác**. File này là cách làm chung cho mọi lần học từ phim mẫu hoặc tài liệu (`knowledge/craft/`, `research/`).

## 1. Bốn tầng của một nhận xét — không nhảy tầng
| Tầng | Ghi gì | Ví dụ |
|---|---|---|
| **Quan sát** | điều thấy / nghe / đo được, có mốc giây, không diễn giải | "2:20,6–2:21: máy bay lên xuyên đèn chùm rồi hạ xuống mặt bàn, không có điểm cắt" |
| **Ý đồ trong ngữ cảnh** | vì sao **ở chỗ này** làm vậy — dựa vào truyện, nhân vật, nhịp; ghi **độ tin** (chắc / có thể / đoán) | "có thể: đánh dấu bước sang thế giới siêu thực của đoạn cuối" |
| **Kỹ thuật (tư liệu)** | cách làm + **nhiều** ý đồ nó có thể phục vụ + điều kiện dùng + ví dụ ≥ 2 mẫu + nguồn | mục trong `knowledge/craft/` |
| **Gợi ý cho pipeline** | chỉ khi đã có ≥ 2 mẫu khác nhau **hoặc** nguồn chuyên gia xác nhận; ghi là gợi ý, kèm khi nào **không** dùng | Đ / Q / E trong `knowledge/roles`, `knowledge/editor` |

Một mẫu → chỉ đến tầng 2. Không viết "X = nghĩa Y". Viết "ở [phim, mốc giây], X được dùng để Y, vì [ngữ cảnh]".

## 2. Trước khi kết luận
- **Soi đủ kỹ trước khi khen / chê:** 1 khung/giây để có bức tranh chung; ≥ 5–10 khung/giây quanh chỗ định nhận xét (chuyển động, điểm nối).
  Đo được thì đo (độ dài shot, độ to, mức chuyển động) — ghi cách đo.
- **Tách "clip này làm" khỏi "nên làm":** quy ước của một thể loại (MV cắt theo câu hát) không phải luật của thể loại khác.
- **Đối chiếu kiến thức sẵn có:** đọc mục liên quan trong `knowledge/` trước khi thêm; mâu thuẫn thì ghi rõ và giải quyết, không thêm song song.
- **Đoán thì ghi là đoán:** "[suy luận]" — nhất là về cách người làm đã làm (prompt, model, số lần sinh lại, có dùng tham chiếu không).
- **Chuyển động / diễn xuất đến từ chỉ đạo:** khi thấy diễn tốt, câu hỏi là "cần truyền đạt gì để model / diễn viên hiểu cảnh và làm được
  như vậy" (tình huống, động cơ, chuỗi hành động, chi tiết cơ thể, nhịp) — không mặc định "họ có video mẫu".

## 3. Nguồn tài liệu — chọn thế nào
- Ưu tiên nguồn **công khai, mục đích chia sẻ kinh nghiệm**, từ **người làm nghề có tên tuổi / chuyên gia**: phỏng vấn, bài viết, bài nói,
  lớp học mở của nhà quay phim, dựng phim, âm thanh, đạo diễn; tạp chí nghề; tài liệu chính thức của công cụ.
- Ghi cho mỗi nguồn: tác giả + vai trò / thành tựu, đường link, ngày đọc, độ tin (cao: chính người làm nói về việc mình làm / tổ chức nghề;
  vừa: trang giáo dục có biên tập; thấp: tổng hợp không nguồn).
- **Bản quyền:** tóm ý bằng lời của dự án, trích nguyên văn ≤ 15 từ khi cần, không chép bài; không lưu hình / âm của phim mẫu (chỉ mốc giây,
  số đo, nhãn).

## 4. Mẫu một mục kỹ thuật (`knowledge/craft/<nhóm>.md`)
```
### <Tên kỹ thuật> (tên tiếng Anh thường gặp)
- Cách làm: …(máy / diễn / dựng / âm thanh làm gì, cụ thể)
- Có thể phục vụ: ý đồ A (ví dụ …) · ý đồ B (ví dụ …) · … — ý nghĩa do ngữ cảnh, không cố định
- Khi hợp / khi không: …
- Ví dụ: [mẫu 1, mốc giây, ý đồ ở đó] · [mẫu 2, …]
- Với video AI: làm được bằng cách nào (prompt / tham chiếu / dựng), giới hạn model
- Nguồn: [tác giả — vai trò, link, ngày đọc, độ tin]
```

## 5. Mẫu gắn nhãn một phim mẫu (`research/craft/<mã>/`)
Mỗi shot: mốc vào / ra · cỡ cảnh · góc · chuyển động máy · chuyển cảnh vào · diễn xuất / hành động chính · âm thanh (thoại / nhạc / hiệu
ứng / lặng) · **kỹ thuật đáng học** (tên theo kho) · **ý đồ ở đây** (+ độ tin). Tóm tắt phim: thể loại, độ dài, số shot, 3–5 kỹ thuật nổi
bật kèm mốc giây.

## 6. Thứ tự học (người dùng chốt 2026-09-29)
Phim ngắn (short film) → short drama → hành động → MV ca nhạc → phim CGI có kỹ xảo → (sau) thể loại khác.
