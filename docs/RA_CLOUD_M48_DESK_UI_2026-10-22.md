# C-M48-DESK-UI — Bàn đạo diễn 3D, Đợt 1: giao diện (22/10)

- Nhánh: `claude/v31-m48-desk-ui` (từ `origin/main` có lõi `core/stage_desk.py`). **Chưa gộp main.**
- 0 USD: không gọi Claude/API, không ghi CSDL thật, không đụng `data/`, `dashboard.env`, D:\AI-Video-Output.
- Kế hoạch: `docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md` mục 3, 4, 9, 10, 12. Sổ quyết định `v31-ep-stage-desk-actions-2026-10-21` (S-A … S-G).

## Đã làm

| File | Thay đổi |
|---|---|
| `dashboard/stage_desk_ui.py` (MỚI) | `render_scene(p, pid, data_dir, scene)`: hàng nút một cảnh. Cờ TẮT → trả ngay, không đọc/vẽ gì |
| `dashboard/stage_view_ui.py` | import + MỘT dòng gọi `stage_desk_ui.render_scene(...)` ở cuối expander từng cảnh |
| `core/features.py` | cờ `stage_desk_ui`: TẮT, `verified False`, không `costs`; `REQUIRES["stage_desk_ui"] = ("stage_view_ui",)` |
| `tests/golden/package_inputs.json` | `stage_desk_ui: false` (image + video) |
| `devsys/areas.json` | khu step2: code + test + cờ (không tăng version) |
| `tests/test_v31_m48_desk_ui.py` (MỚI) | 19 test |

### Hành vi
- **Nút** = `stage_desk.scene_status()["buttons"]` (lõi chọn theo phase), mỗi nút gọi đúng một hàm lõi:
  N1 `check_inputs` · N2 `estimate` · N3 `write_prompt` · N4 `load_answer` · N5 `build_sheet` · N6 `approve` · N7 `return_` · N8 `reset` ·
  N9 `rerender` · N10 `score` · N11 `render_plates`. Không có N12 / N13.
- **Danh tính:** `user = common.access_user()`; `who = write_guard.actor("human", email)`. Phiên mở bằng `?op=claude` →
  `actor("ai", "phien_claude_dashboard")` và **không thấy** Duyệt / Trả lại.
- **S-B:** N6/N7 chỉ hiện khi `stage_crew_user_approve` bật + người (không phải phiên Claude) + `stage_desk.is_executive_producer(conn, pid, user)`.
  Ngược lại hiện câu "chỉ Executive Producer…". Lõi vẫn kiểm lại khi bấm.
- **N6:** giữ `scene_status()["marks"]` lúc MỞ màn duyệt (session_state) → `approve(expected_marks=…)`; bỏ dấu sau khi duyệt xong / máy đổi xen giữa.
  Tích xác nhận bắt buộc; shot đã vẽ ảnh → ô xác nhận riêng → `confirm_drawn=True` (Q-D).
- **Xác nhận trước đổi dữ liệu:** N4 (nạp trả lời), N6, N9 (+ ô riêng cho shot đã vẽ), N11 — chưa tích thì không gọi lõi, báo câu.
  N8: lần bấm đầu gọi `reset(confirm=False)` → hiện `preview.say` + nút "Xác nhận làm lại" (`confirm=True`) / "Hủy".
- **N7:** mỗi shot một ô ý đồ; không có ý đồ nào → báo, không gọi.
- **N4:** dán JSON; ô trống → đọc `crew/tra_loi_<phase>.json` trong thư mục đoạn (`stage_desk.seg_dir`, theo `data_dir`). JSON sai → báo, không gọi.
- **Đang chạy / khóa S:** khóa S của người khác (không cũ), `running`, hoặc tiến độ `running` → mọi nút trừ 💲 Ước tính bị `disabled`; hiện
  `lock_line` + tiến độ (bước + 5 dòng log cuối) + nút "🔄 Xem tiến độ". Tiến độ `done` / `error` / `interrupted` đều nói câu (kể cả `missing`/`gate` của N1).
- **K1 chưa có** → gợi ý bấm 🔍 Kiểm đầu vào trước. Đầu vào đổi, đã duyệt bởi, shot máy thường, làm lại / tài nguyên cũ sau làm lại → câu hiển thị.
- Lỗi lõi (`errors`) hiện bằng `st.error`, không nuốt.

## Test (đỏ → xanh)
`tests/test_v31_m48_desk_ui.py` — 19 đỏ (commit `4873496a`) → 19 xanh. AppTest `from_function`, lõi MOCK:
cờ/REQUIRES/golden/areas; cờ TẮT không gọi `st`/lõi; màn XEM cờ bàn TẮT không có `st.button`; một dòng gọi trong expander;
nút theo danh sách lõi + gọi đúng hàm/đối số; phase xong (N9/N10/N11 + xác nhận); N6 xác nhận + marks + user; N6 shot đã vẽ;
N7 ý đồ; không phải EP không thấy Duyệt; phiên Claude không duyệt được + actor ai; N8 xem trước → xác nhận; N4 JSON sai/đúng;
đang chạy khóa nút + tiến độ; khóa người khác; lỗi được nói; tiến độ done/error/interrupted; K1 thiếu; quét nguồn (không `os.environ`/`FEATURE_`/API/SQL).

Chạy cùng: `test_v31_stage_view.py`, `test_v31_m48_desk_core.py`, `test_feature_settings.py`, `test_golden_replay.py`,
`test_devsys_pipeline_maps.py`, `test_access_ui.py` → **232 passed**. `py -m core.decisions check` khớp.

## related_areas + tự kiểm
- Khu: step2 (file mới + màn XEM), core_infra (`features.py` — chỉ THÊM một cờ + một dòng REQUIRES, không đổi cờ cũ), devsys (areas.json),
  plates3d (golden). Khu gọi `features.py` không bị đổi hành vi (không đọc cờ mới).
- Không nới test cũ nào; đường dẫn đều từ `data_dir`; không nút nào gọi tiền (N2 chỉ đọc bảng giá); cờ mặc định TẮT → Bước 2 như cũ.

## Rủi ro / việc mở
1. Cờ **không** ở `OPT_IN_ONLY` (đúng kế hoạch mục 9): preset Thử nghiệm sẽ bật cùng `stage_view_ui` → EP thấy nút ghi máy (có xác nhận). Cần thì thêm vào `OPT_IN_ONLY`.
2. Chưa bấm thử trên Dashboard thật / #31 (test 14 kế hoạch, máy chính); chưa chụp màn Playwright.
3. Chưa có N14 / N15 / N16 / bảng đối chiếu "đã khai ↔ đo được" / ảnh `top_beats.png` (Đợt 2 hoặc việc sau).
4. Chế độ CHỈ XEM của `access_ui` khóa luôn nút 💲 Ước tính / 🔄 (thận trọng, không sai).
5. `stage_view_ui` thêm 2 dòng (import + gọi), không phải 1.

## Rà kỹ + vòng sửa (22/10 tối, agent rà độc lập → một vòng sửa)
Rà kỹ báo 9 mục (0 CAO, 5 VỪA, 4 THẤP). Đã sửa, mỗi mục một test `test_ra*` trong `tests/test_v31_m48_desk_ui.py` (chạy trên mã CŨ:
10/10 đỏ; mã mới: xanh):
1. Ô xác nhận N4 / N6 / N9 / N11 không bỏ tích sau khi bấm → bấm lần sau chạy lại thao tác ghi không hỏi. Sửa: `run()` ghi danh sách ô
   cần bỏ tích, đầu lượt vẽ kế (trước widget) đặt False (`test_ra1`).
2. Lõi ném ngoại lệ làm sập Bước 2 → `run()` bắt, nói "lõi lỗi …" (`test_ra2`).
3. Chặn phiên Claude dựa vào `?op=` tự khai, hạ được bằng `?op=nguoi` → chốt MỘT CHIỀU `common.op_claude_seen()` (đặt ở
   `capture_op_source` + lúc đọc). Giới hạn còn lại: phiên Claude không bao giờ mở `?op=claude` thì không phân biệt được (`test_ra3`).
4. Lõi N4 / N8 / N9 / N11 không kiểm quyền dự án → `stage_desk._need_edit` (`access.require(conn, pid, user, "edit")`), tham số mới
   `user=None` (None = CLI / autopilot / đăng nhập TẮT: như cũ); UI truyền `common.access_user()` (`test_ra4_*`).
   **Câu hỏi EP (chưa tự quyết):** N9 "Render lại từ câu trả lời đã lưu" sau phase `xong` ghi lại máy đã được EP duyệt — có phải chỉ EP
   được bấm không? Hiện: ai có quyền SỬA (kể cả phiên `?op=claude`, actor "ai") đều bấm được, có xác nhận.
5. Cờ `stage_desk_ui` vào `OPT_IN_ONLY` — preset Thử nghiệm không tự bật nút ghi máy / nền 3D (`test_ra5`).
6. Sau bấm `st.rerun()` → trạng thái / nút vẽ lại theo lõi; câu kết quả hiện một lần (`test_ra6`).
7. Docstring "không theo cwd" sai (common.DATA tương đối) → sửa câu, câu báo in đường tuyệt đối (`test_ra7`).
8. Tiêu đề màn XEM bỏ chữ "(chỉ xem) … dùng CLI" khi bàn bật (`test_ra8`). **Tồn đọng:** `scene_status` vẫn chạy cho mọi cảnh mỗi
   lần vẽ lại (expander Streamlit không báo đóng / mở; muốn lười phải thêm công tắc mở bàn — đổi thao tác) → đo thời gian trên #31 trước.
9. Test đường THẬT `is_executive_producer` + `_need_ep` qua giao diện (CSDL tệp tạm): đăng nhập BẬT chủ dự án / người chỉ sửa, đăng nhập
   TẮT, phiên `?op=claude` dùng đăng nhập EP (`test_ra9`).
