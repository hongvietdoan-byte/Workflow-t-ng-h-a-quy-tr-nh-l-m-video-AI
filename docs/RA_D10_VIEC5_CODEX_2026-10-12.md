# Tự rà Đ10 việc 5 — 12/10/2026

Nhánh `codex/d10-viec5-khung`, nền `167fb37`; RÀ NHẸ vì đổi đề sau cờ mặc định TẮT.
Chưa commit/push: phiên chính cần đọc diff + test trước commit theo CLAUDE.md §7.

- `change_review_frames` dùng `features.on`, verified=False; REQUIRES báo cần `change_review`.
- OFF mở `30_change_review.md` gốc không sửa; nhãn rỗng, không thêm duration/BYĐ. Snapshot lấy trước sửa so UTF-8 từng byte xanh.
- ON dùng `30_change_review_frames.md`: thay hẳn mục 1 cũ để không giữ chỉ dẫn khớp đầu với cuối; START/TRANSITION/END, bốn nhịp không đếm câu.
- BYĐ giữ đầy đủ thành phần/dạng, hành động và ngoại lệ, không cắt cuối ở 500 chữ; ca dài xác nhận ket_thuc/ngoại lệ còn đủ.
- Ảnh đã duyệt thuộc START theo chỉ dẫn nhưng caller chỉ gửi chữ. Prompt cấm bịa đã nhìn ảnh, thiếu bằng chứng → khong_chac.
- Không thêm luật quyết định quan sát; `validate`, `decide`, đóng mục, mã chặn, số lời gọi và sổ chi giữ nguyên.
- `claude_review` là caller build_prompt duy nhất; `bg_poll.change_review_round` vẫn qua enabled; runner/autopilot chỉ đọc blocking;
  before_run/UI chỉ đọc mục/cờ. Không sửa các caller, widget keys, cache hoặc đường gửi tự động/hàng loạt.
- Chạy `py tools/related_areas.py core/change_review.py core/features.py prompts/30_change_review_frames.md tests/test_change_review_frames.py`:
  vùng own core_infra; caller rộng do features dùng chung, có autopilot/step1/step4/dashboard; test CHẬM bắt buộc ở gộp.
- Tự kiểm §2b.5: không nới test/ngưỡng, không path theo cwd (ca chdir xanh), không bật mặc định, không so bỏ dấu, không sandbox/network,
  nhãn tách dữ liệu, không thêm lời gọi tốn tiền/đụng sản xuất. areas khai prompt/fixture/knowledge/test/cờ, giữ nguyên version.
- `.gitattributes` ép snapshot LF để clone Windows không đổi byte fixture.

Bằng chứng: đỏ **4 failed, 16 passed** (thiếu nhãn/nguyên tắc/BYĐ/cờ); xanh **20 passed**;
bàn giao **21 passed** (thêm kiểm BYĐ dài + cwd), cùng hai file test trong một lệnh, tổng 3 lượt pytest.
`git diff --check` xanh. Không chạy Claude/API; chưa thử thật. Ca vàng tái dựng từ mô tả #24, không đọc data.
Rủi ro khi ON: BYĐ đầy đủ có thể tăng token/ước tính lời gọi hiện có; chất lượng kết luận Claude chưa đo.
Việc mở: root rà diff trước commit, cả bộ Windows trước gộp; chưa bật cờ.

Rà khâu liên quan độc lập (agent Đ10v6, trước commit): không finding chặn; đã đối chiếu OFF byte, ON nhãn/BYĐ và caller claude_review/decide/sổ chi. Root đọc diff, prompt và test; không thêm lượt API.
