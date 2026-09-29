# Bàn giao phiên 29/09 chiều — để phiên / tài khoản Claude khác làm tiếp trên cùng máy

Đọc trước: `CLAUDE.md` (quy ước), `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` (kế hoạch + trạng thái từng việc; % bằng `py tools/plan_progress.py`),
`TODO.md` (các mục "Cập nhật 2026-09-29 (5)–(9)"), `docs/BAO_CAO_SANG_2026-09-29.md`. Trả lời người dùng bằng tiếng Việt.

## Trạng thái (commit `0982328` trở đi, nhánh `main`)
- Tiến độ kế hoạch ≈ 74 %. 1391 test qua. Dashboard chạy từ `D:\AI-Video-Pipeline` (cổng 8501) — **cần khởi động lại** để chạy code mới.
- Đã xong hôm nay: S2, S3 (trừ S3.7 bỏ), S4.1/4.3/4.4, S4.5 (trừ đo khớp môi), S5.1–5.4, S5.6, S6.1–6.6, S7.0, S8.1, S9.6.
- S6.5 (người dùng duyệt 29/09): 4 cờ `verified: True` — director_two_pass, voice_direction, loudness_normalize, project_budget.

## Đang chờ người dùng
1. **Nâng trần đợt thử** để chạy A/B hành động S4.6: trần tổng 43,10 → 49,10 USD (đã chi 42,85), trần ảnh 135 → 141. Ước tính A/B ≈ 5,32 USD
   (3 khung Deepix 0,16 + 3 shot × {Seedance Fast ref-only 0,48 · Seedance 2.5 ref-only 0,92 · Kling khung đầu 0,32}); khóa trần 6 USD.
   Người dùng đã cho phép thử phần hành động — chỉ thiếu nâng trần. Dự án thử **#10** đã tạo (`tools/experiments/action_ab.py`); các bước:
   `py tools/experiments/group_test.py --project 10 --scene 1 frames` → `... --single --methods P2m,P2m25,S2 plan` → `submit` → `poll`
   (chạy từ `D:\AI-Video-Pipeline`). Xem từng clip, chấm: chuyển động tự nhiên, chân chạm đất, hiệu ứng kỹ năng Kenta đúng game, giữ nhân vật.
2. **Khớp môi S4.6** — thêm phương án (c) theo mẫu prompt của người dùng (`docs/PHAN_TICH_PROMPT_KHOP_MOI_2026-09-29.md`): một clip
   Seedance 2.5 cho cả đoạn thoại + track giọng cả đoạn + câu thoại & mốc giây trong prompt. Người dùng cho thử **cả 2 phong cách**
   (tả thực 3D và in-game) để so. Chưa code phần dựng prompt (c); ước tính trước khi gửi, thử "Generate Sample" trước.
3. **Chọn kịch bản K** (`docs/KICH_BAN_KIEM_K1_2026-09-29.md` bản 2, 12–14 s; gợi ý bản A "Chia đôi", đã sửa đúng kỹ năng Kenta).
4. **Góc dưới mái che**: `lower_yard` ≡ `level_22_4` (cùng một chỗ); ảnh 3 hướng ngày/đêm ở
   `D:\AI-Video-Output\2026-09-29_bo-boi-canh-thap-dong-ho\_to_anh_duoi_mai_che.jpg` — chờ chọn hướng / có thêm đèn cho đêm không.

## Việc miễn phí còn lại
- **S0.12**: agent phân tích video mẫu đang làm 11 video còn lại (18 trở đi) ghi vào `research/craft/s0_12/`; media tạm ở scratchpad của
  phiên cũ (`s012/`, xóa bằng `bash clean.sh vNN`). Nếu phiên cũ đã tắt: kiểm file nào đã viết, commit, giao lại phần thiếu (danh sách
  trong `research/craft/s0_12/TONG_HOP.md` mục Tồn đọng).
- Đo khớp môi bằng máy (S4.5 phần còn lại): đo điểm ảnh vùng miệng KHÔNG phân biệt được giọng đúng/sai trên 4 shot #8 — cần mô hình mốc
  môi + mẫu khớp môi đã xác nhận (sẽ có từ A/B khớp môi).
- S8 (chấm devsys + so sánh phần mềm ngoài) làm sau cùng, sau lần chạy K.

## Luật vận hành (từ bộ nhớ người dùng)
- Việc tốn tiền: ước tính trước, trần cứng khóa trước, hỏi từng lần. Việc miễn phí trong kế hoạch: tự làm tiếp.
- Mỗi đợt: test qua hết → commit + push `main` → `git pull` ở `D:\AI-Video-Pipeline` → cập nhật `TODO.md` + trạng thái kế hoạch.
- Kiến thức nghề là "tư liệu / gợi ý", không công thức cố định; "đã sửa" phải kèm bằng chứng chạy thật.
