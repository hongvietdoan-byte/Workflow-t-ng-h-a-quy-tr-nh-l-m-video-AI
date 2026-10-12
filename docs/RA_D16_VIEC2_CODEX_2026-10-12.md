# RÀ KỸ độc lập Đ16 việc 2 — 12/10/2026
- Worktree `codex/d16-viec2-khoa-dao-cu`, base `d932f1d1`; rà độc lập rồi sửa theo root giao; đã sửa gom 6 lỗi, chờ root đọc diff và kiểm gộp.
- Đọc diff 4 file + caller hẹp assets.scene_references, prompt_formula.issues, runner builder/_finish_args, common.scene_expander; related_areas xác nhận assets/autopilot/budget/cờ/UI.
- Đỏ: 6 test_review_* hỏng (0,76 s); xanh focused: 6 qua (0,62 s); nhóm cuối 4 file: **62 qua, 4,53 s**; git diff --check sạch.

## 6 lỗi đã sửa trong một vòng (giữ tái hiện/cách sửa để đối chiếu)
1. **P2 — core/prop_lock.py:256,264:** so màu bằng chữ nguyên văn làm mất thuộc tính đúng: `Kelly holds a black SKORP.` → `Kelly holds a SKORP.` dù Kho ghi “màu đen”.
   Đã sửa: bảng thuộc tính chuẩn song ngữ (black/đen, white/trắng, opaque/đục…), đối chiếu ngữ nghĩa cùng dạng; phủ định/thuộc tính phụ cần tránh coi là màu toàn món. Test giữ black/đen và opaque white/trắng đục, vẫn bỏ amber/translucent.
2. **P1 — core/prop_lock.py:237:** tính từ hợp lệ không có trong _COLOUR_RX chặn cả cụm: `A translucent white glue wall.` giữ nguyên translucent, trái dạng trắng đục.
   Đã sửa: nhận cụm thuộc tính đầy đủ (white/opaque/grey/brown…), phân loại từng thuộc tính rồi chỉ bỏ phần mâu thuẫn; dùng cùng parser cho suffix. Test `translucent white glue wall` → `white glue wall`, `opaque white` giữ, `glue wall is translucent white` giữ trắng/bỏ trong suốt.
3. **P2 — core/prop_lock.py:245–249:** regex generic khớp danh từ ghép khác đồ vật; `A red gun-shaped toy hangs by SKORP.` → `A gun-shaped toy hangs by SKORP.` mất màu toy.
   Đã sửa: span noun phải kết thúc cụm đúng loại, loại -shaped/-like và các noun head như toy/case/rack; áp cả alias generic. Test gun-shaped toy/gun case/glue bottle cạnh món khóa giữ màu; assault rifle/glue-grenade wall thật vẫn làm sạch.
4. **P1 — core/prop_lock.py:188,209,320:** nhãn tỉ lệ cắt ở dấu thập phân; mô tả `An SMG. Scale: 0.45 m long, 0.12 m wide.` → `Weapon scale: SKORP — 0.`.
   Đã sửa: kết thúc câu chỉ tại dấu chấm không nằm giữa hai chữ số; dùng cùng parser để gỡ nhãn khỏi form. Test Scale/Tỉ lệ 0.45 và 1.2 giữ nguyên số, không còn mảnh `45 m` trong prop sentence.
5. **P1 — core/prop_lock.py:206–214,332:** đọc toàn mô tả lấy tỉ lệ của skin không chọn; `(a) DEFAULT — SMG with a black stock; (b) skin Tiny — Scale: pistol-sized.` → default Prop lock đúng nhưng Weapon scale `pistol-sized`.
   Đã sửa: truyền selected variant/form vào weapon_scale; chỉ đọc metadata chung của chính asset và đoạn mô tả dạng đã chọn, không quét đoạn skin khác/source tag. Test default SMG + skin có Scale pistol-sized: default phải Estimated SMG; skin Tiny nhận riêng scale skin.
6. **P2 — core/prop_lock.py:190–193:** heuristic tỉ lệ ép hành động ngoài phạm vi: shot `Kelly aims SKORP with one hand.` còn câu đó nhưng tự thêm `hold two-handed` mâu thuẫn shot; rifle/shotgun mặc định ép stock at shoulder khi hạ súng/đeo súng.
   Đã sửa: AUTO chỉ mô tả kích cỡ/hình dáng; câu pose chỉ từ metadata người nhập hoặc có điều kiện theo hành động shot. Test one hand/lowered/slung giữ pose nguồn và không thêm mệnh lệnh trái shot.

## Hợp đồng/giới hạn
- Runner đổi tối thiểu action/fix: có lý do gốc lỗi; return realism_removed chưa đổi; không thấy đường tiền/job mới. Source/skin/OFF không bị ghi.
- UI caption đã đổi thành “sẽ bỏ” (preview từ scene), test cùng nhãn; không thay key/widget, không đổi return realism_removed.
- Chưa model thật, chưa GUI 1440/1280, chưa cả bộ Windows; test chậm UI bắt buộc bước gộp theo related_areas. Không commit/push/TODO/CODEX_TASKS/main/live.


## Kiểm cuối của phiên chính
- Đã đọc diff phần sửa sáu finding trước commit; giữ contract realism_removed và key widget.
- Kiểm riêng component Streamlit thật `common.scene_expander` trên CSDL bộ nhớ và dữ liệu giả, server QA cổng 8519; Playwright Chrome tại 1440×1000 và 1280×1000: 0 pageerror, 0 tràn ngang trang, caption 'sẽ bỏ: translucent amber', nguồn black SKORP/amber moonlight/red gun-shaped toy còn nguyên. Đã xem hai PNG `docs/images/d16/prop_lock_1440.png` và `prop_lock_1280.png`. Đây là QA component, chưa phải toàn Dashboard production; server QA đã dừng, không đụng 8501/8502.
- Không gọi API hoặc đọc/ghi dữ liệu sản xuất; chất lượng model và cả bộ Windows vẫn chờ phiên máy chính/tích hợp.
