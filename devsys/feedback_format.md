## Góp ý cho từng khoản trừ (`feedback`, tùy chọn — S8.1, 2026-09-29)
File này KHÔNG thuộc thang chấm (`rubric.md`): đổi nó không làm điểm cũ thành "thang cũ". Mỗi khoản trừ được (và nên) kèm một object
`feedback` để người đọc biết **vì sao trừ và sửa thế nào**; không có thì điểm vẫn hợp lệ.

```json
{"points": 4, "reason": "…", "evidence": ["TODO.md:26"],
 "feedback": {"why": "ảnh hưởng tới người dùng / chất lượng phim (1 câu)",
              "fix": "sửa cụ thể: file, hàm, việc (1–3 câu)",
              "files": ["core/x.py"],
              "verify": "nghiệm thu thế nào (test / đo / chạy thật)",
              "effort": "💻",
              "priority": 1}}
```
`effort`: 💻 code miễn phí · 💵 tốn tiền · 👤 người dùng làm / quyết. `priority`: 1 cao · 2 vừa · 3 thấp. Mọi chữ tiếng Việt có dấu.

Bản 2 (2026-10-03): khoản trừ mức `chan` / `lon` BẮT BUỘC có `feedback.fix` (≥ 10 ký tự) và `feedback.effort`; thiếu thì câu trả lời bị từ chối. Mức `nho` vẫn tùy chọn.
