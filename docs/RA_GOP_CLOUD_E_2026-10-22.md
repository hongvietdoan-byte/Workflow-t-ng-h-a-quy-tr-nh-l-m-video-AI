# Rà + gộp 2 nhánh cloud-E (22/10)

Nhánh tích hợp `claude/gop-cloud-e-2210` (từ origin/main f166a453). Gộp:
- `origin/cloud/v31-clone-intent` @ a84dc430 (C-CLONE-INTENT)
- `origin/cloud/v31-r1-rel` @ 140e2484 (C-R1-REL)

Không xung đột (hai nhánh không chạm cùng file). `devsys/areas.json` version 91 → 92 (một lần). 0 USD, không chạm `data/`.

## C-CLONE-INTENT — rà
Đúng: `clone_project(with_rows=False)` bỏ thêm `director_intent_raw`; `render_settings` qua `project_defaults._carried` (cùng luật dự án
mới: giữ cách dựng, bỏ mốc nhạc / popup / chữ card). Chỉ ĐỌC dự án gốc (không UPDATE nguồn); không gọi API; không đường dẫn tương đối.
`with_rows=True` không đổi. `render_settings` = NULL khi nguồn trống — mọi chỗ đọc đều `or "{}"` (kiểm lại delivery.get_settings trong test).

| Mức | Lỗi | Xử lý |
|---|---|---|
| VỪA | `tools/pilot_setup.py` gọi `clone_project(with_rows=False)` nhưng dùng LẠI kế hoạch Đạo diễn của nguồn (director_raw) → sau nhánh, dự án thử mất `director_intent_raw` (duyệt bản thô `editor_review` mất focus/peak/target_s) — hồi quy, câu hỏi cloud nêu trong báo cáo | ĐÃ SỬA: `pilot_setup.carry_same_plan` chép lại `director_intent_raw` (nguyên văn như trước nhánh) + render_settings (card tắt như cũ). Test `test_clone_intent.py::test_pilot_trial_keeps_same_plan_intent` (đỏ trên a84dc430: hàm chưa có / ý đồ mất → xanh) — kiểm luôn dự án gốc không đổi |
| THẤP | Hộp thoại nhân bản (`dashboard/header.py` ô "Giữ nguyên các cảnh/shot") không nói bản chạy lại Đạo diễn bỏ ý đồ + mốc dựng cũ | ĐÃ SỬA (chữ help, 2 dòng) |
| THẤP | `story_scenes.data` vẫn chép nguyên — có trường cấp cảnh Đạo diễn cũ ghi vào (emotional_intent, beat, mood…, `shots.store_plan`); Đạo diễn mới ghi đè khi chạy, nhưng `intent_all` trước lần chạy đó đọc nhầm của phim cũ | GHI LẠI, không sửa (lẫn với trường kịch bản; cần quyết định riêng) |

## C-R1-REL — rà
Đúng: test cũ giữ nguyên (chỉ THÊM test, không nới); bên khung tuyệt đối giữ như cũ trừ thông điệp + số đo; "of frame/centre/camera/màn
hình" vẫn là bên khung; X lạ → KHÔNG RÕ (không im lặng); ngưỡng `REL_MIN_DEG=5` có tên; `relations_at` không TypeError với valid_from chuỗi.
Chỉ công cụ đọc gọi (`tools/position_invariants.py`); `position_sentence` (stage_view_ui) chỉ đổi cách lọc quan hệ (cùng kết quả với số).

| Mức | Lỗi | Xử lý |
|---|---|---|
| VỪA | `core/world_map.name_spots` khớp tên KHÔNG theo nguyên từ → tên ngắn trên map khớp giữa từ ("Ma" trong "machine"/"man"): "Kelly stands to the right of the machine" thành quan hệ "Kelly bên phải Ma" (báo sai) và bỏ kiểm bên khung | ĐÃ SỬA: `(?<!\w)…(?!\w)`. Test `test_v31_3d_goc_b.py::test_rel_short_name_does_not_match_inside_a_word` đỏ → xanh |
| THẤP | Tiếng Việt "Kelly bên phải Yêu nữ bên trái" (không dấu phẩy) đọc thành quan hệ tương đối | GHI LẠI (hiếm; câu thật thường có dấu phẩy tách vế) |
| THẤP | `_side_claims` cũ (bên khung) vẫn khớp tên không theo nguyên từ (có từ trước nhánh) | GHI LẠI — đổi sẽ đổi hành vi bên khung tuyệt đối, ngoài phạm vi |
| THẤP | `world_map.review` (M3.3) chưa gọi kiểm tương đối; "right of <vật lạ>" ở đó nay không còn gán bên khung | GHI LẠI (cloud đã nêu; chưa có chỗ gọi thật) |

## Quy ước 7
`py tools/related_areas.py <file đổi>` → step4 (compare), autopilot (pilot_setup), plates3d (world_map), dashboard_ui/budget (header),
gọi tới: dashboard/admin.py (chỉ metrics/scores — không gọi clone), core/layout_facts.py (load/entities_at — không đổi),
dashboard/stage_view_ui.py (position_sentence — chỉ refactor relations_at). Không thấy hành vi bị đổi theo khác ngoài 2 lỗi VỪA trên.

## Test
- Bộ liên quan: test_clone_intent 4/4, test_v31_3d_goc_a+b 244 passed.
- Cả bộ (`-n 8`, 24 phút): **7958 passed, 8 failed**, 10 skipped, 22 xfailed. 8 đỏ đều ở file KHÔNG liên quan nhánh
  (test_mockup_ban_dung_d11 ×2 trình duyệt, test_v31_fix4 ×5 giao diện AppTest, test_voice_speed ×1 giao diện) — chạy lại riêng ba file
  trên nhánh này: **24/24 passed** → đỏ do tải song song (hết giờ giao diện/trình duyệt), không do nhánh.
