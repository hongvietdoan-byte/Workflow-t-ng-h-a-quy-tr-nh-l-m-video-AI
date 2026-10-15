# HANDOFF — #31 hai việc mở trước gen ảnh (15/10)

Nhánh: `worktree-agent-a1a00d090810d2bcc` (chưa push, chưa gộp main).

## 1. prompt_formula ĐỎ 5 shot (cảnh 4·1, 5·2, 6·1, 6·2, 8·2 = scenes 321, 325, 327, 328, 334)
Bằng chứng (CSDL máy chính, chỉ đọc): ba gốc khác nhau
- 321, 334: "blood stains" chép từ hồ sơ trang phục (Lính địch áo choàng, Sứ giả bóng đêm) — Quay phim không biết chữ hồ sơ cũng phải gợi.
- 327, 328: vật kịch bản bắt buộc "cái xác" → "corpse … everything in focus", không câu gợi.
- 325: "Purple-red glow from door 1 bleeds in" — ánh sáng loang, bộ từ ghê (looks._GORE) đọc nhầm thành máu.
Sửa công thức:
- `core/looks.py`: "bleed" có từ ánh sáng/màu đứng trước trong cùng mệnh đề không là chữ ghê (`_gore_iter`); bộ từ khác giữ nguyên.
- `core/prompt_formula.py`: thông báo ĐỎ `luat_ff` thêm cách sửa cụ thể (câu gợi mẫu + "everything in focus except the hinted …",
  vết trên áo, "spills" thay "bleeds"). Ngưỡng không đổi.
- `prompts/17_director_shots.md` (luật cứng FF) + `prompts/20_dp_scene_shots.md`: ba ca trên + câu mẫu; fixture
  `tests/fixtures/ambient_motion_off.json` dựng lại (chỉ khác đúng các dòng này).
Kiểm 0 USD trên #31: 325 hết ĐỎ; 321/327/328/334 vẫn ĐỎ với thông báo mới; áp câu gợi mẫu vào 4 prompt thật → hết ĐỎ.
Lưu ý: ảnh KHÔNG bị chặn gửi bởi 5 ĐỎ này (runner tự thêm câu "Gore restraint" cho ảnh FF) — ĐỎ chỉ ở ⚙ Chẩn đoán / formula_check.

## 2. BYĐ cảnh 8 shot 1–4 "shot: thiếu trường bắt buộc" sau 2 vòng sửa
Gốc: khuôn trả lời lượt sửa `{"canh", "shot", "byd": {…}}` đặt số shot NGOÀI byd → Đạo diễn bỏ `shot` bên trong; code không lấy
số đó → hai vòng trả tiền không lấp được. Sửa `core/director_byd.py`: `_own_number` điền `shot` (shot_no của hàng đã lưu, không có thì
vị trí) cả lượt đầu lẫn sau lượt sửa, đếm `so_shot_theo_vi_tri`; khuôn sửa ghi rõ `"byd": {"shot": <số shot>, …}`.
Kiểm 0 USD trên #31: 4 shot cảnh 8 → hết ĐỎ, 0 VÀNG; 24 shot khác đã có `shot`.

## Áp dụng cho #31 (không tự sửa CSDL)
- Shot 325: không cần làm gì sau khi gộp (ĐỎ tính lại từ prompt).
- 321/327/328/334: sửa tay `image_prompt` qua ô sửa trường shot sẵn có (0 USD, llm_io save → on_prompt_saved kiểm lại) theo câu mẫu
  trong thông báo; hoặc để runner tự thêm câu Gore restraint khi gửi ảnh (đã có). Chạy lại Quay phim 4 cảnh không cần.
- BYĐ cảnh 8: `py tools/byd_fill.py --project 31` (chạy khô) rồi `--yes --max-usd 0.05` — code mới điền số shot, không gọi Claude
  (0 USD); hoặc để VÀNG (không khâu nào đọc `byd.shot`).

## Test
`tests/test_p31_gore_byd_formula.py` (mới, khai vào devsys/areas.json khu step1): đỏ 7/9 trước sửa → xanh; bộ liên quan 213 qua.
