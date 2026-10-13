# Danh sách sửa GỘP — chuỗi ảnh → video chất lượng cao (#27, trước tập 2) — 13/10 tối

Nguồn (đọc theo số dòng, không đọc lại cả file):
- `docs/handoff/RA_GOC_VIDEO_P27_2026-10-13.md` — gốc lỗi 53 job video bị loại (bảng gốc dòng 12–34) + **V1–V13** (dòng 35–152), cờ (153–163).
- `docs/handoff/RA_CHUOI_ANH_VIDEO_2026-10-13.md` — rà code đường một shot: **C1–C9** (dòng 15–105), trạng thái lỗi đã biết #5–#8 (dòng 7–14).
- Bấm thử Dashboard bản sao (mục U dưới đây).

## Kết luận một dòng
≈ 60 % job video hỏng vì **đầu vào đổi SAU khi gen** (ảnh duyệt rồi mới thấy sai 25 job, sửa motion sau gen 12, nhóm Seedance kéo shot đạt gen lại, QC tự sửa bản cao → chắc chắn hỏng); phần còn lại là model vẽ sai kiến trúc / vật kỹ năng (shot 16–17) do prompt video cho plate 3D "thắng" ảnh khung đầu + từ khóa skin.

## U — bấm thử Dashboard bản sao (8541, nhà cung cấp giả, CSDL sao 13/10 20:4x, chặn ghi `data/` thật)
- **U1 xác nhận C1 trên giao diện:** shot 17 (S08·1, scene 285): `quality_tier.state` = `final_ok` → pill "Bản cao ✓", không còn nút ⬆, trong khi bản cao 905 nằm ở `trash/` và clip đang dùng là nháp Kling 915 (`videos/17.mp4`, std 480p). Gốc thêm: `state()` (`core/quality_tier.py:354-373`) tin MỌI final đã duyệt, không đối chiếu `takes.used` / nháp gốc của final = nháp người duyệt mới nhất. → sửa cùng C1.
- **U2 xác nhận C7:** hộp thư (`core/inbox.items`) #27 không có dòng nào cho shot 17 (bản cao mất), cho "nháp đã duyệt chờ gen bản cao" (shot 3 S02·1); chỉ "Lỗi gen shot 2, 20", "Duyệt 9 clip".
- **U3 xác nhận C4/C8:** Bước 3 không có ô 🏁 end_state, không có khung Rà soát; 22/22 motion "Đã duyệt".
- **U4 (nhẹ, giao diện) nhãn model/bậc lệch giữa Bước 3 và Bước 4:** S08·1 Bước 3 "Kling 3.0 Omni · pro", thẻ Bước 4 dòng clip "Kling std 1.5 s"; S08·3 Bước 3 "Seedance 2.5 · 480p", Bước 4 "Seedance 2.0 720p"; S02·1 "Kling pro ≈ 0.37" nhưng nút ⬆ "≈ 0.24 USD". Một nhãn là model ĐÃ dùng cho clip, một là model SẼ dùng — ghi rõ "clip hiện tại" / "lần gen tới". Shot `direct_ok` (S03·3, S08·3) thẻ Bước 4 không hiện pill "Cao luôn ✓".
- **U5 (nhẹ, mã) `final_cut.measured_size`** (`core/final_cut.py:98-102`) dò đường tương đối theo THƯ MỤC MÃ, khác `assets._resolved` (cwd trước) → chạy mã từ worktree/bản sao: mọi bản cao thành "không đo được clip gốc" → "Bản cao · chờ duyệt". Trên máy chính không lộ. Sửa: thử cwd trước rồi gốc repo (như `assets._resolved`).

## Nhóm sửa (MỘT vòng mỗi nhóm; file chung → cùng phiên)

| Phiên | Vùng file | Lỗi | Mức rà |
|---|---|---|---|
| **S1 Vòng đời job + bậc chất lượng** | `core/quality_tier.py`, `core/pipeline.py` (approve, QC-fix 539-546), `core/autopilot.py:993-1002`, `core/batch.py`, `core/runner.py` (tiền tố fail bản cao), `core/inbox.py`, `core/final_cut.py:98`, `dashboard/quality_ui.py`, `dashboard/steps/step4.py` | C1+U1, C2, C3, C7+U2, V6, U4, U5 | KỸ (tiền + vòng đời job) |
| **S2 Gói gửi video (công thức prompt + ref)** | `core/seedance_refs.py`, `core/prompt_formula.py`, `core/skill_objects.py` | V1, V4, V5 (thang đánh dấu), V8, V9, V10, V13 | KỸ (đổi prompt gửi tiền) |
| **S3 Khung cuối + kiểm bố cục** | `core/end_frames.py`, `core/framing_guard.py`, `core/runner.py:907-920, 1254-1412` (`_wait`/`_end_frame`), `core/motion_physics.py`, Dashboard Bước 3/4 (khung cuối) | C5, C6, V2, V3, V5 (fallback runner), V12 | KỸ |
| **S4 Rà soát + cổng duyệt ảnh + QC video** | `core/db.py` (trigger), `core/llm_io.py`, `core/change_review.py`, `dashboard/steps/step3.py`, `core/runner.py:396`, `core/plate_anchor.py` + duyệt ảnh Dashboard, `core/claude_tasks.py:166-206` | C4, C9, V7, V11, ô end_state Bước 3 (lỗi 6) | KỸ |
| **Cấu hình (hỏi người dùng)** | `data/feature_settings.json` | C8 bật `end_state_fresh` | — |

Thứ tự (theo job tiết kiệm): S1 + S2 song song (khác file) → S3 + S4 (S3 và S1 cùng `runner.py` khác đoạn → S3 sau khi S1 gộp). Cả bộ test MỘT lần ở bước gộp.

## Trạng thái
- 13/10 ~21:30: rà xong (V1–V13, C1–C9, U1–U5). Vòng sửa: chưa bắt đầu.
