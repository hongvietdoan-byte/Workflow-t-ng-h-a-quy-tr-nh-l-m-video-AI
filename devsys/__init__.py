"""AI Development System: theo dõi quá trình sửa/cập nhật dashboard + đo mức hoàn thiện thật sau mỗi thay đổi.

Chạy:  Start-DevSystem.bat  (hoặc  py -m streamlit run devsys/app.py --server.port 8502)
- devsys/collect.py   số đo miễn phí, đọc thẳng từ repo (git, test, TODO.md, cờ tính năng, diag)
- devsys/scores.py    đọc / chuẩn hóa / gộp file điểm (điểm do code cộng lại từ các khoản trừ có bằng chứng)
- devsys/scorer.py    người chấm AI (Claude qua client có sổ chi của dự án, stage "devsys") + bản giả lập
"""
