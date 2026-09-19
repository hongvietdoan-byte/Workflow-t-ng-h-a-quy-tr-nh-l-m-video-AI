# Bộ đánh giá Director (Bước 1 và Bước 3)

Mục đích: đo và cải thiện chất lượng prompt Director bằng dữ liệu, thay vì cảm tính. Người duyệt hiện tại: **chủ dự án (duyệt tạm)**; khi có chuyên gia biên kịch/đạo diễn thì họ thay phần chấm thẩm mỹ.

- `cases.json` — 12 mẫu (action, horror, drama, epic, cyberpunk, fantasy môi trường, bẫy IP, sci-fi, võ thuật, boss reveal, liên tục nhân vật, cận cảnh cảm xúc). Mỗi mẫu có `expect` (chấm tự động) và `review_questions` (bạn chấm đạt/chưa đạt).
- `golden.json` — đáp án viết tay cho 3 mẫu (`action_chase`, `horror_corridor`, `ip_trap_amazon`), cũng là ví dụ few-shot trong prompt Director. **9 mẫu còn lại là "held-out"** để đo thật, vì AI chưa được xem đáp án.

## Vòng chạy (mỗi vòng ~30–60 phút)
1. Lấy prompt cho một mẫu: `py -m core.evalset prompt drama_farewell` → dán vào chat Claude, nhận JSON (Bước 1).
   Với Bước 3: `py -m core.evalset prompt drama_farewell --motion` (dùng `analysis` đã có).
2. Gom kết quả vào một file, ví dụ `eval/run1.json`:
   ```json
   {"drama_farewell": {"analysis": { ... JSON Bước 1 ... }, "motion": { ... JSON Bước 3 ... }}}
   ```
3. Chấm tự động: `py -m core.evalset score eval/run1.json` → xem mẫu nào fail và vì sao (ngôn ngữ, độ dài, tái dùng mô tả nhân vật, từ cấm/IP, camera...).
4. Sinh phiếu duyệt: `py -m core.evalset sheet eval/run1.json eval/run1_review.md` → mở file, tick `[x]` các câu thẩm mỹ đạt, ghi nhận xét.
5. Chỉnh `prompts/` hoặc `knowledge/` theo lỗi lặp lại, chạy vòng mới. Khi điểm held-out ổn định cao và bạn hài lòng về thẩm mỹ, **khóa version** (ghi vào `knowledge/` và TODO).

## Cách đọc kết quả
- **Điểm tự động** chỉ đo phần khách quan (đúng cấu trúc, tiếng Anh, độ dài, dùng lại mô tả nhân vật, không có tên IP, có camera hợp thể loại). Điểm cao chưa chắc đẹp.
- **Phiếu thẩm mỹ** mới quyết định. Nếu điểm tự động cao nhưng bạn chấm thẩm mỹ thấp, cần thêm/sửa kiến thức trong `knowledge/genre_guides.md`.
- File `run*.json` là dữ liệu thử nghiệm, có thể giữ lại trong `eval/` để so sánh các vòng.
