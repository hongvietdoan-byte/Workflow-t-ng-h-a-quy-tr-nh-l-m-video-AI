# HANDOFF — nhánh `claude/tap2-c-side-pose` (14/10)

Việc: thử D6 #28/#29 — Kelly núp sai bên + shot 3 BYĐ 'quỳ' trái kịch bản "đứng sát, núp".

## Đã làm
- `core/side_truth.py` (mới, cờ `side_truth`, verified False): CHỈ vế kịch bản gốc khớp shot (script_pose.script_poses) có
  "bên/phía/sang/qua/tay + trái/phải" (có dấu; "phải núp" không khớp) + máy sau lưng (plate_choice.is_behind) / trước mặt (chữ máy
  của shot) → câu "Sides: … = FRAME-LEFT/RIGHT" chèn prompt ảnh (runner), khung cuối (end_frames._side_guard), video (runner
  _submit_args, chừa chỗ trong reserve Seedance; nhánh khác quá trần → không thêm + VÀNG; Kling multishot bỏ qua). D6 viết lại mất câu →
  `kept_after_rewrite` gắn lại nguyên văn (quá trần → bản code ghép). Không chắc máy / góc nghiêng / nhiều nhân vật mà chữ máy không nêu
  tên người được nói tới → VÀNG `side_truth`, không đoán. Không đọc `action` của Đạo diễn (hay viết theo người xem — #24 shot 12).
- `core/script_pose.fix_standing` (cờ `script_pose_fix`): kịch bản chỉ "đứng" (không "đứng dậy/ngồi xuống…"), BYĐ đúng một người toàn
  quỳ/ngồi, `byd` không khóa tay → đổi đứng (+ chạm đất gối/mông → bàn chân), ghi `sua_tu_the` + diag `script_pose_fix` (chỉ ra chữ
  crouch/kneel còn trong prompt ảnh Đạo diễn). Gọi sau lượt Đạo diễn (`llm_io.store_scene_analysis`) và sau chia lại cảnh
  (`director_two_pass`). Ca mơ hồ giữ VÀNG `script_pose`.
- Kiểm chỉ đọc CSDL thật: #28/#29 shot 3 → sửa đứng + FRAME-LEFT (máy sau lưng); #22/#27 không sửa tư thế; #24 shot 6 (ngồi↔bò) giữ VÀNG.

## Cache D6
Không cần làm mới tay: khóa cache `chat_prompt.fingerprint` gồm bản code ghép + ý đồ (BYĐ) → shot có câu mới / BYĐ đổi tự trượt cache
(một lượt D6 mới ≈ 0,04 USD/shot khi gen lại); shot khác giữ cache.

## Còn mở
- Ghép vế kịch bản ↔ shot (script_pose) yếu: #28 shot 4 "chạy tiếp 5 bước về bên trái" khớp nhầm vế khác → không có câu (im, không sai).
- Prompt ảnh tiếng Anh của Đạo diễn vẫn "crouches" sau khi BYĐ sửa — chỉ báo VÀNG, chưa sửa chữ.
- Hai cờ mới chưa gen thật (bật ở 🧪 / preset experimental tự bật).
- Chia lại một cảnh chạy fix/diag cả dự án (diag trùng gộp trong 10 phút).
