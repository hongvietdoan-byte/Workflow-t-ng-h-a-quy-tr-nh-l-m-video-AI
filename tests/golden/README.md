# Bộ ca hồi quy (`tests/golden/`)

Định dạng chốt ở K0a (`docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` mục 3.9). Ca hồi quy chỉ để **kiểm hồi quy** — độ phủ đến từ
cấu trúc (bảng loại lỗi `devsys/error_types.json`, A5), không từ số ca.

Mỗi ca một tệp `cases/<id>.json` (tên tệp = `id`). Loader: `tests/golden/__init__.py` (`load_cases`, `problems`, `stage_facts_cases`).
Test định dạng: `tests/test_devsys_stages.py`; test chạy ca của lớp `stage_facts`: `tests/test_stage_facts.py`.

| Trường | Nghĩa |
|---|---|
| `id` | tên ca, chữ thường + `_` |
| `nguon` | lỗi xảy ra ở đâu / ai bắt (dự án, shot, ngày) |
| `ca_vang_tay` | `true` = BYĐ nhập tay từ dự án cũ (A1) — khi đó `byd` bắt buộc |
| `byd` | Bảng ý đồ shot theo `core/shot_intent.py` (hoặc `null` khi lớp phải bắt không đọc BYĐ) — phải qua `shot_intent.validate` không lỗi đỏ |
| `may` | máy sân khấu 3D (`stage_camera`: `location`, `look_at`, `lens`, `props` …) |
| `kho` | vật Kho liên quan: `{khóa: {name, desc_en, has_picture, …}}` |
| `goi` | gói gửi model: `image_prompt` / `motion_prompt`, `refs` [{vai, sha/đường dẫn}], `model` (phần nào có thì ghi) |
| `anh_ket_qua` | đường dẫn ảnh/clip kết quả (tùy chọn, `null` nếu ca chỉ kiểm trước tiền) |
| `loi_dung` | lỗi ĐÚNG phải bắt (một câu), hoặc "không có …" cho ca chống báo nhầm |
| `loai_loi` | id loại lỗi trong `devsys/error_types.json` (L1–L15, V1–V4, A1–A4) |
| `lop_phai_bat` | id điểm quyết định trong `devsys/decisions.json` (vd `d85` stage_facts, `d86` câu trái hình học) |
| `ky_vong` | theo lớp: `{"stage_facts": {facts, prompt_contains, prompt_not_contains, contradiction, judge}}`; lớp mới thêm khóa riêng |

Thêm ca: lỗi người dùng bắt mà lọt → xếp loại (mục 10 kế hoạch) → thêm một tệp `cases/<id>.json`; test tự chạy. Ca cũ
`tests/fixtures/stage_facts_golden.json` đã chuyển sang đây (K0a).
