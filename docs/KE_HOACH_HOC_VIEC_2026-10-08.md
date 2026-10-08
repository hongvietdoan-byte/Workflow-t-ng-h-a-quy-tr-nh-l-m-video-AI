# Kế hoạch: chế độ "học việc" (trainee) cho 7 cờ — 08/10/2026

**Quyết định người dùng 08/10:** 7 cờ `qc_team`, `scene_qc`, `scene_establishing`, `camera_setups`, `continuous_takes`, `end_frames`, `storyboard_auto_trust` không tắt. Chúng chạy như nhân viên thử việc:
- vẫn đưa ra quyết định, quyết định được **ghi lại và so với quyết định thật của người dùng**;
- **không tác động**: không chặn, không tự vẽ lại, không đổi ảnh/clip/prompt/nhóm gửi đi;
- vai tốn tiền vẫn chạy, ghi sổ chi tách riêng (stage `trainee_*`);
- **ngưỡng:** ≥ 80 % khớp trên ≥ 2 dự án → báo "🎓 đủ chuẩn — chờ duyệt". Người dùng duyệt cuối, không tự lên `verified`.

Nguồn: kiểm 22 cờ ở `docs/KIEM_22_TINH_NANG_KLD_2026-10-08.md`; kế hoạch do phiên con Plan khảo mã ngày 08/10 (số dòng tính theo commit lúc đó).

## 0. Rủi ro phải biết trước
1. **Tắt `scene_qc` ≠ không làm gì.** `qc_scene.enabled()` đang dùng để chọn nhánh. Khi nó tắt, QC Claude cũ chạy lại, có autofix (tự duyệt / tự gen lại): `autoqc.py:81-93`, `autopilot.py:453-466`, `autopilot.py:1278`, `known_issues.py:24`, `cost.py:498`.
   → Chỗ *chọn nhánh* dùng `active()` (bật hoặc học việc). Chỗ *có tác động* dùng `on()`.
2. **`qc_team` chỉ chạy bên trong `scene_qc`** (`qc_scene.run_ready_scenes`). Các chỗ gọi phải đổi sang `active()`, không thì `qc_team` không bao giờ chạy.
3. **Mù nhận định.** Người dùng không được thấy nhận định của vai trước khi tự quyết, nếu không phép so bị nhiễm. Hiện có 2 chỗ lộ: ghi chú "Tổ QC … block" trong `job_events`, và `layer0.json` hiện ở tab Video.
   → Khi học việc chỉ ghi vào `trainee_log`, chỉ hiện ở màn 🧪 sau khi người đã quyết.
4. **"Luôn chặn" cũng gần 80 %.** Trên #22, `qc_team` khớp 73 % còn "luôn chặn" đạt 76 %. Cần thêm điều kiện chống tỉ lệ nền (mục 3).
5. **Không ghi "trainee" vào `flags` của `feature_settings.json`.** Code cũ đọc giá trị đó bằng `bool(v)` nên sẽ thành BẬT thật. Phải lưu ở khóa riêng `"modes"`.
6. **`dashboard.env` đang bật cả 7 cờ bằng `FEATURE_X=1`.** Quy tắc mới: với 7 cờ này, `1` hạ thành học việc. Bật thật chỉ qua màn 🧪.

## 1. Cơ chế chung (`core/features.py`)

**Trạng thái thứ ba.** Thêm `"trainee": True` vào 7 cờ, viết dạng literal vì devsys đọc bằng `ast.literal_eval`. Hàm `state(name)` trả `on` / `trainee` / `off`, ưu tiên theo thứ tự:
1. Cờ đã gỡ (REMOVED).
2. Chọn trên màn 🧪: `modes` / `flags`.
3. Preset.
4. Biến môi trường. `FEATURE_X=trainee`; `1` với cờ học việc → học việc.
5. Mặc định.

**Hàm:**
- `on()` = `state == "on"`. Mọi chỗ gọi cũ an toàn, học việc không bao giờ vô tình tác động.
- Thêm `shadow()`, `active()`, `trainee_list()`, `save_settings(modes=…)`.
- `on_unverified()` / `pending()` tự loại cờ học việc.
- `REQUIRES["qc_team"] = ("scene_qc",)`, tính theo `active()`.

**Giao diện:**
- Màn 🧪 (`dashboard/header.py`): công tắc 3 nút "Tắt / 🎓 Học việc / Bật".
- Expander bản dựng (`step5.py`): tách "chưa kiểm thật" khỏi "🎓 đang học việc".
- devsys: thêm `mode`, `flags_trainee`, không trừ điểm.

## 2. Lưu trữ và từng cờ

**Bảng mới `trainee_log`** (`CREATE TABLE IF NOT EXISTS` trong `core/db.py`):

| Cột | Nội dung |
|---|---|
| `at`, `feature`, `project_id`, `scene_id`, `job_id`, `story_scene` | |
| `subject` | `job:525` / `scene:2` / `group:2:C` / `stretch:1:3-6` / `end:248` / `gate:storyboard:<sha>` |
| `decision` | block / pass / redraw / flag / group / stretch / need_end / skip_gate / hold_gate / establish |
| `would_do`, `detail` | JSON |
| `cost_usd` | |
| `truth`, `truth_source`, `match`, `scored_at` | |

**Module `core/trainee.py`:** `record`, `label` (người chấm 1 cú bấm), `score_project`, `agreement`, `RULES`.

**Nguồn sự thật:** `review_log` của người, có `decided_at` sau `trainee_log.at`. Lần duyệt hàng loạt ở cổng ghi `gate_bulk`, báo riêng.

| Cờ | Tốn tiền | Học việc làm gì | So với |
|---|---|---|---|
| `qc_team` | ≈ 0,03 USD/khung (≈ 0,66/dự án) | `review_scene(shadow=True)`: vẫn gọi Claude chấm từng khung. Không `_hold`, không ghi chú, không `team.json`; ghi block/pass. Sổ chi stage `trainee_qc_team` (ánh xạ vào `claude_qc` của `project_budget.claude_stage`) | Người duyệt/loại ảnh |
| `scene_qc` (lớp 0) | 0 | `runner.py:1789`: chạy `check_frame`, không raise `RedrawWithFix`, không ghi `layer0.json`; ghi redraw/flag/pass. Đổi 4 chỗ chọn nhánh sang `active()` để QC cũ không sống lại | Người loại/duyệt. Chỉ số chính: độ chính xác của `redraw` |
| `scene_establishing` | ≈ 0,05 USD/ảnh | Vẽ vào thư mục riêng `establish/trainee/`. Không giữ shot chờ, không câu ánh sáng, không gửi ref; `picture()` không thấy ảnh học việc | Thẻ chấm 👍/👎 "đúng nơi chốn/ánh sáng?"; số đo phụ `background_match`. Cảnh trong nhà → `establish_skip_indoor` |
| `camera_setups` | 0 | Không thêm câu vào prompt Director. Sau khi ảnh duyệt đủ, ghi kế hoạch nhóm (`shots.setup_groups`) | Thẻ chấm "shot 3+4 quay chung được không?" |
| `continuous_takes` | 0 | Ghi kế hoạch đoạn liền (`shots.stretch_of`), cần `camera_setups` ở trạng thái active | Thẻ chấm; note "động tác bắt đầu lại" |
| `end_frames` | 0 (vẽ thử là tùy chọn) | `needed(ignore_route=True)`: ghi `need_end`, không vẽ ảnh, không gửi `last_frame` | Thẻ chấm "clip kết đúng `end_state` chưa?" |
| `storyboard_auto_trust` | 0 | `_qc_trusted`: ghi skip_gate/hold_gate rồi trả False, không `set_gates` | Fingerprint lúc người duyệt cổng: không đổi → đúng; có sửa → sai |

**Lưu ý chung:** khi `seedance_ref_groups` bật, `camera_setups` / `continuous_takes` / `end_frames` có lên chính thức cũng không có tác dụng. Màn 🧪 phải nói rõ điều này.

## 3. Ngưỡng "đủ chuẩn — chờ duyệt"
1. ≥ 2 dự án, **mỗi dự án** đạt ≥ 80 % khớp, và tỉ lệ gộp ≥ 80 %.
2. Số mẫu tối thiểu mỗi dự án:
   - `qc_team`, `scene_qc`: ≥ 15 khung; gộp lại ≥ 5 duyệt và ≥ 5 loại. Riêng `scene_qc`: ≥ 8 lần `redraw`.
   - `scene_establishing`: ≥ 3 cảnh.
   - `camera_setups`: ≥ 3 nhóm.
   - `continuous_takes`: ≥ 2 đoạn.
   - `end_frames`: ≥ 3 shot.
   - `storyboard_auto_trust`: gộp ≥ 4 sự kiện, ≥ 2 lần `skip_gate`, **và** `look_trust.trusted`.
3. **Chống tỉ lệ nền:**
   - Khớp cân bằng ≥ 75 %.
   - Hơn chiến lược "luôn nói nhãn đông nhất" ≥ 5 điểm.
   - Báo riêng "quá chặt" và "quá lỏng".
4. Chỉ tính cặp mà vai quyết **trước** người.

Chấm điểm lúc giao bản (`snapshot_after_delivery`) và bằng nút "Chấm lại" (0 USD). Màn 🧪 hiện: độ khớp từng dự án, khớp cân bằng, mức nền, tiền đã chi, còn thiếu gì, và thẻ chấm 👍/👎.

## 4. Test (viết đỏ trước) và rủi ro

**Test:**
- `test_feature_settings`: thứ tự `state()`; env `1` → học việc; `modes` không lọt vào `flags`.
- `test_trainee` (mới): fixture #22 — 37 khung, 28 loại / 9 duyệt → "luôn chặn" phải `ready=False`.
- `qc_team` học việc: 0 `scene_qc_hold`, 0 ghi chú, sổ chi `trainee_qc_team`.
- `scene_qc` học việc: không `RedrawWithFix`, QC cũ không chạy.
- `scene_establishing` học việc: không chặn `_wait`, không ref, không câu ánh sáng.
- `camera_setups` / `end_frames` / `storyboard_auto_trust` học việc: không đổi `group_of`, `last_frame`, cổng.
- devsys: có `mode`.

**Mức rủi ro "không tác động":**
- **Cao:** `scene_qc` (dễ quên một chỗ chọn nhánh), `qc_team` (ghi chú và hàng hold nằm chung `_hold`), `scene_establishing` (4 lối rò).
- **Trung bình:** mù nhận định; sự thật yếu ở các vai cần thẻ chấm.
- **Thấp:** tiền (trần chỉ cảnh báo).

## 5. Thứ tự làm (~1.000 dòng mã + ~670 dòng test, 3–4 phiên con)

| Bước | Nội dung |
|---|---|
| B0 | **Chốt với người dùng** (xem mục 6) |
| B1 | `features.py` + test |
| B2 | `trainee_log` + `core/trainee.py` + test |
| B3 | Các cờ 0 USD: `scene_qc` lớp 0 + 4 chỗ chọn nhánh, `storyboard_auto_trust` |
| B4 | Kế hoạch 0 USD: `camera_setups` / `continuous_takes` / `end_frames` |
| B5 | `qc_team` chạy bóng (tốn tiền) |
| B6 | `scene_establishing` chạy bóng (tốn tiền) |
| B7 | Giao diện 🧪 + expander bước 5 + devsys |
| B8 | Tài liệu: `CHUAN_XAY_DUNG`, `known_issues`, `why` của 7 cờ, TODO |

Thứ tự phụ thuộc:
- B1 → B2 đi trước.
- B3 và B4 làm song song.
- B5 và B6 sau B3.
- B7 cuối cùng.

Chỉ ghi "đã xong" sau một dự án thật chạy học việc và có `trainee_log` thật (luật 8).

## 6. B0 — đã chốt 08/10
Người dùng chọn: (1) QC Claude cũ **giữ tắt**; (2) **ẩn** nhận định tới khi người quyết; (4) **thẻ 👍/👎 sau dự án**; làm **hết B1→B8**, ngưỡng như mục 3.
Mặc định Claude chọn (đổi được): (3) preset `stable` → cờ học việc TẮT (stable = chỉ cờ đã kiểm), preset `experimental` → học việc; (6) tiền học việc ánh xạ vào trần `claude_qc` (trần chỉ cảnh báo) + dòng "🎓 Học việc" riêng trong báo cáo tiền; (7) `camera_setups` học việc KHÔNG thêm câu vào prompt Director.

Câu hỏi B0 gốc:
1. `scene_qc` học việc giữ QC Claude cũ **tắt** (không quay về QC cũ).
2. Mù nhận định tới khi người quyết.
3. Preset stable/experimental đối với cờ học việc.
4. Thẻ chấm 1 cú bấm cho `scene_establishing` / `camera_setups` / `continuous_takes` / `end_frames`.
5. Định nghĩa ngưỡng ở mục 3.
6. Tiền học việc tính chung trần `claude_qc` hay là dòng riêng.
7. `camera_setups` học việc không thêm câu vào prompt Director.
