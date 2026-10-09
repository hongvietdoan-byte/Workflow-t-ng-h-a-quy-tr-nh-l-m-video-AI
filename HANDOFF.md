# HANDOFF — KLD-10 nối dialogue_chat vào khung chat Kịch bản (09/10)

## Đã xong
- `core/script_chat.py`: `send` dùng `dialogue_chat.prompt/parse`; tin assistant lưu `proposals` [{id Px, line, speaker, old, new, why, state}];
  `append(..., **extra)`; `_set` / `_set_state` ghi lại trường (cả mảng proposals) bằng một câu `json_set`.
  Áp dụng chỉ khi `apply` có giá trị + `approved(tin cuối của người)` + đề xuất còn mở; có tin "Đã áp dụng …" (kèm `undo`, `after`).
  `undo(p, pid, i)` khôi phục thoại cảnh + đoạn kịch bản cảnh + kịch bản dự án; từ chối khi đã hoàn tác hoặc thoại đã đổi sau đó.
  Đề xuất trỏ câu không có / áp dụng không đồng ý / đề xuất đã đóng → ghi ⚠ trong tin (không im lặng).
- `intent`: `is_dialogue_talk` (so có dấu, chặn biên chữ; "ok" một mình vẫn 'ask').
- `core/llm_runner.py`: `script_chat` max_tokens 1500 → 3000 (test cũ cập nhật số).
- `core/dialogue_chat.py`: sửa lệch chỉ số khi cảnh có dòng thoại rỗng (`dial[n]` thay `spoken[n]`).
- `dashboard/steps/step1_box.py`: `_messages(p, pid, messages, start)` + thẻ đề xuất (D.card + D.pill, câu cũ gạch ngang, câu mới, lý do, trạng thái),
  nút "↩ Hoàn tác · 0 USD" (in-run, không fragment).
- Test: `tests/test_script_chat_kld10.py` (intent, send/apply/undo, AppTest UI); `devsys/areas.json` khai file mới (không tăng version).

## Đang dở / việc mở
- Chưa thử trên dashboard thật với Claude thật (tốn tiền) — cần người dùng gõ thử.
- `_user_locked` của trường dialogue vẫn giữ sau hoàn tác (update_scene đánh khóa tay) — chấp nhận.
- Khi đang viết ý tưởng, câu có "thoại"/"câu N" giờ đi vào chat (gọi Claude) thay vì làm "nói thêm".

## Bước kế
- Merge nhánh vào main, cập nhật TODO.md (mục KLD-10), chạy thử thật một lượt.
