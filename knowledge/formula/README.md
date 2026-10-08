# Sổ công thức prompt (F0 → F1-A, 09/10/2026)

Nguồn: `docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md` (người dùng đã duyệt 09/10), 9 shot #22 Khủng Long Đỏ, góp ý #24 Teasing
(`docs/RA_SOAT_TRUOC_GEN_LAI_24_2026-10-08.md`). Áp cho mọi dự án Free Fire. Code kiểm: `core/prompt_formula.py` (cờ `prompt_formula`).

- `anh_khung_dau.md` — 9 phần của prompt ảnh khung đầu.
- `motion.md` — 8 phần của prompt motion + 2 phần mới từ #24.

## Công thức cố định CÁI PHẢI QUYẾT, không cố định CÂU
Một prompt = **khung** (những điều bắt buộc phải có quyết định) + **phần sáng tạo** (Đạo diễn viết tự do cho kịch bản này). Sổ này
nói "phải nói về điều gì, lấy từ đâu, vì sao"; ví dụ #22 là để hiểu, không phải câu bắt buộc chép lại.

- **Phần có điều kiện** chỉ bật khi đúng tình huống (ảnh OUTFIT có người mẫu → khóa tóc; vật lao sát người → đường đi; cùng setup
  shot trước → "cùng máy, cùng chỗ"). Không có tình huống thì không nhồi câu.
- **Biến thể theo loại shot** (`prompt_formula.shot_kind`): thoại · hành động · nhảy theo video mẫu · cận đồ vật · toàn cảnh mở ·
  quái/sinh vật · hiệu ứng kỹ năng · khác. Mỗi loại một bộ phần bắt buộc.
- **Code kiểm phần, không kiểm chữ**: thiếu phần → cảnh báo; hai phần mâu thuẫn, luật sai loại nhân vật, chi tiết ghê không tiết
  chế, vật lao sát người không đường đi → đỏ. Người sửa tay vẫn được; hệ thống chỉ báo khi sai khung.
- **Thứ tự nên viết**: phong cách → khung → nhân vật + hành động (phần thay đổi giữa các shot) → nền (gọn) → ánh sáng → khóa/luật →
  chốt chất lượng. Lý do: motion 7–9 #22 lặp ~1.200 ký tự nền + trang phục, đẩy hành động xuống cuối, gần trần 4.000 ký tự Seedance.

## Bài học dùng theo 3 tầng
| Tầng | Là gì | Dùng thế nào | Ví dụ |
|---|---|---|---|
| 1. Luật cứng FF | đúng ở mọi dự án FF, sai là hỏng | code kiểm (đỏ), sẽ chặn trước khi gửi | ≥ 18 tuổi; nhân vật đúng hồ sơ; nền theo render 3D; tiết chế ghê; phụ kiện giữ trạng thái thiết kế |
| 2. Công thức khâu | các phần bắt buộc của prompt mỗi loại shot | thiếu phần thì báo (cảnh báo) | 9 phần ảnh, 8 phần motion |
| 3. Kinh nghiệm theo ngữ cảnh | đúng trong điều kiện cụ thể, có độ tin | chỉ đưa cho Đạo diễn/Quay phim khi ngữ cảnh khớp, kèm lý do + độ tin; được chọn không theo nhưng phải ghi vì sao | "clip dài trên nền có mốc → máy gần tĩnh" (1 dự án); "ref-only → thêm câu chốt tóc" |

Mỗi bài học ghi: **áp khi nào** · **vì sao** · **bằng chứng** (dự án/shot) · **độ tin** · **tầng**. Dự án sau đánh đổ → hạ tầng hoặc
gỡ (không xóa, ghi lý do). Chỗ hỏng của #24 chính là sai tầng: "không mắt phát sáng" là kinh nghiệm tầng 3 (đúng cho NGƯỜI) bị đặt như
tầng 1 → áp cho yêu nữ mắt đỏ.

## Lớp dò sau MỖI lượt Đạo diễn viết / viết lại (mục 4b)
1. Kiểm khung (thiếu phần, mâu thuẫn, ghê, luật sai loại nhân vật) — `check_image` / `check_motion`.
2. So với bản trước: chỉ dài thêm mà không bỏ/thay câu cũ → cảnh báo "trồng thêm"; câu mới mâu thuẫn câu cũ → đỏ — `growth_check`.
3. Cùng món đồ của cùng nhân vật khác màu giữa các shot → cảnh báo — `cross_shot` (trang phục phải lấy MỘT nguồn: hồ sơ Kho).

Kết quả: `scenes.data["formula_check"]`, ⚙ Chẩn đoán (mã `prompt_formula`), báo cáo Đạo diễn (mục liên tục). `red_issues(conn,
scene_id, kind)` trả lỗi đỏ cho cổng gửi gen (phiên chính nối vào `_blocked`).
