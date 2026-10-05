# HANDOFF — S14.21 (Bộ não prompt Đợt 3: khung nhập kịch bản hội thoại)

Nhánh `s14-21-script-box` (từ origin/main 43f5162). Chưa push, chưa sửa TODO.md / kế hoạch.

## Đã làm
- `core/idea_to_script.py`: `classify(text)` 0 USD (`script` / `idea` / `unsure`, theo bảng kế hoạch; vùng xám = hỏi);
  `wish` cho `build_prompt` / `_ask` / 4 lượt; `state["wishes"]` nhớ qua lượt, chạy lại lượt n bỏ wish lượt > n;
  `directions_input_changed()` (C8). Wish rỗng → prompt byte-identical (test so với bản `build_prompt` đóng băng trong test).
- `prompts/23_idea_to_script.md`: khối mới `## YÊU CẦU THÊM` ở CUỐI file, chỉ ghép vào prompt khi có wish.
- `dashboard/steps/step1_box.py` (mới): khung hội thoại. Một `st.chat_input` (key `box_in_{pid}`, accept_file) — không gọi model;
  📎 popover chứa `st.file_uploader(key=up_{pid})` nguyên xi; ✍ Sửa toàn văn (`ui.fold`, `paste_{pid}`); dòng "Hiểu là …" + nút ghi đè
  (`box_mode_script_/box_mode_idea_{pid}`, lưu `in_mode_{pid}`); nhánh ý tưởng: ⚙ Thiết lập (`st.form idea_form_{pid}` trong `ui.fold`) +
  các lượt có giá; chữ ngắn khi ý tưởng đang chạy = lời "nói thêm" (`box_wish_{pid}`) cho lượt có giá kế tiếp, bỏ được.
- `dashboard/steps/step1_idea.py`: `idea_panel` tách thành `idea_settings_form` + `turn_questions/_directions/_outline/_script` + `idea_turns`;
  `_paid` giữ nguyên; "↻ Hỏi lại 3 hướng khác" có nhãn giá và chỉ bật khi đầu vào đổi.
- `dashboard/steps/step1.py`: `analyse_script()` module-level (thay closure); cờ BẬT → `step1_box.script_box`, cờ TẮT → 2 tab cũ y hệt.
- `dashboard/steps/step1_v2.py`: nhãn expander "Nhập / thay" đổi khi cờ bật (cờ tắt giữ chữ cũ).
- `devsys/areas.json`: khai `step1_box.py` (không đổi version).

## Lệch kế hoạch
- Câu "yêu cầu thêm ưu tiên nhưng không phá ràng buộc cứng" KHÔNG đặt ở `## CHUNG` (sẽ đổi prompt cả khi wish rỗng → vỡ C3),
  mà ở khối `## YÊU CẦU THÊM` chỉ gửi khi có wish.
- Ô wish = chính `chat_input` (chữ ngắn khi đang làm ý tưởng), không thêm ô thứ hai.
- `paste_` fold mặc định MỞ (gập thì widget không vẽ → mất khóa trong cây; chữ vẫn giữ ở `box_text_{pid}`).

## Phát hiện: replay S11.2 đã miss TRƯỚC thay đổi này
`py tools/experiments/idea_script_eval.py --db <bản sao DB> --limit 2 --replay data/idea_golden/runs/20261001-163630/calls.jsonl`
trên origin/main (chưa có code S14.21) → 2/2 ý tưởng `replay_miss` ngay lượt 1. Kho (assets) không đổi từ 26/09, knowledge
screenwriter/dialogue_craft/genre_guides không đổi, build_prompt không đổi → nguyên nhân chưa rõ (có thể tên/alias Kho sửa tại chỗ,
hoặc bản ghi chạy từ cây làm việc khác). Cổng S14.22 bước 2 ("0 miss") cần quyết lại: ghi bản ghi mới hoặc dùng test đóng băng.

## Việc mở
- S14.22 (cổng bật cờ) chưa làm; cờ `idea_to_script` vẫn TẮT, verified=False.
- Chưa chụp giao diện thật (chỉ AppTest); chưa chạy Claude thật với wish có chữ.
