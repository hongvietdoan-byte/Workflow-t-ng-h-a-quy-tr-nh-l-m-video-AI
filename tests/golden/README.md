# Bộ ca hồi quy (`tests/golden/`)

Đ20 M1.9a: fixture chụp sổ gói gửi là định dạng riêng `fixture_version=1` từ `tools/golden_capture.py`, không bỏ vào `cases/` của loader K0a. `tests/test_golden_replay.py` dựng fixture tổng hợp từ SCHEMA thật; kiểm read-only, thiếu trường/hash, thứ tự ref và comparator byte. Replay biên `_build_package` ảnh/video từ `package_inputs.json` đã có (baseline đóng băng độc lập); toàn tuyến `_submit_args` và đánh giá chất lượng thật vẫn **OPEN**; xem `docs/RA_D20_VIEC2_CODEX_2026-10-20.md`.

Định dạng chốt ở K0a (`docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` mục 3.9). Ca hồi quy chỉ để **kiểm hồi quy** — độ phủ đến từ
cấu trúc (bảng loại lỗi `devsys/error_types.json`, A5), không từ số ca.

Mỗi ca một tệp `cases/<id>.json` (tên tệp = `id`). Loader: `tests/golden/__init__.py` (`load_cases`, `problems`, `stage_facts_cases`).
Test định dạng + chỉ tiêu K0b (≥ 15 ca, ≥ 2 âm/chữ/dựng, ≥ 3 có BYĐ + gói): `tests/test_devsys_stages.py`; test chạy ca của lớp `stage_facts`: `tests/test_stage_facts.py`.

| Trường | Nghĩa |
|---|---|
| `id` | tên ca, chữ thường + `_` |
| `nguon` | lỗi xảy ra ở đâu / ai bắt (dự án, shot, ngày) |
| `ca_vang_tay` | `true` = BYĐ nhập tay từ dự án cũ (A1) — khi đó `byd` bắt buộc; ca không đọc BYĐ (vd `world_rules`) để `false` + `byd: null` |
| `byd` | Bảng ý đồ shot theo `core/shot_intent.py` (hoặc `null` khi lớp phải bắt không đọc BYĐ) — phải qua `shot_intent.validate` không lỗi đỏ |
| `may` | máy sân khấu 3D (`stage_camera`: `location`, `look_at`, `lens`, `props` …) |
| `kho` | vật Kho liên quan: `{khóa: {name, desc_en, has_picture, …}}` |
| `goi` | gói gửi model: `image_prompt` / `motion_prompt`, `refs` [{vai, sha/đường dẫn}], `model` (phần nào có thì ghi) |
| `anh_ket_qua` | đường dẫn ảnh/clip kết quả (tùy chọn, `null` nếu ca chỉ kiểm trước tiền) |
| `loi_dung` | lỗi ĐÚNG phải bắt (một câu), hoặc "không có …" cho ca chống báo nhầm |
| `loai_loi` | id loại lỗi trong `devsys/error_types.json` (L1–L15, V1–V4, A1–A4) |
| `lop_phai_bat` | id LỚP KIỂM trong `devsys/decisions.json` — phải có vai `kiem` trong `devsys/stages.json` "vai" (test hợp đồng, thẩm định 4): vd `d86` câu trái hình học, `d95` khóa nhận diện (identity_declare), `d96` luật thế giới (world_rules), `d12` rà thoại, `d48` duyệt bản thô |
| `lop_lam` | (tùy chọn) id bộ SINH / bộ LÀM liên quan — không phải lớp kiểm: vd `d85` stage_facts.derive sinh câu sự thật, `d38` gắn tên người nói, `d91` ghép popup, `d09` Đạo diễn viết prompt |
| `ky_vong` | theo lớp: `{"stage_facts": {facts, prompt_contains, prompt_not_contains, contradiction, judge}}`; lớp mới thêm khóa riêng: `identity_declare` {nhan_vat, vat (khóa sân khấu trong BYĐ `thanh_phan` — món lọc theo cỡ cảnh / mặt-lưng / có trong khung), khoa, trang_thai {món: co/thieu/thieu_mau/sai_mau/khong_can}} (chạy ở `tests/test_identity_declare.py`), `shot_intent` / `do_tu_the` (chưa có lớp chạy — ghi kỳ vọng; `tu_the` theo `core/shot_intent.TU_THE`, có `nga_ngua`), `world_rules` {luat [luật theo `core/world_rules.py`], hoi [{vat, loai, ngu_canh, du_an, shot, hom_nay, ra: [id luật theo thứ tự]}], lop_chay} (chạy ở `tests/test_world_rules.py`), `am_chu` {thoai [{cau, nguoi_noi_byd, nguoi_noi_goi, ket_qua}], lop_chay} và `dung` {popup {tren, giu_khung, giay_giu, shot_nen_toi, ket_qua}, lop_chay} (ca âm/chữ/dựng — chưa có lớp chạy, K6: `lop_chay` BẮT BUỘC nói rõ lớp nào sẽ chạy) |

**Kỳ vọng "chết" bị cấm (thẩm định 4 #4):** khóa `ky_vong` có lớp chạy trong test = `tests/golden.LOP_CHAY` (`stage_facts`,
`identity_declare`, `world_rules`). Khóa khác (`am_chu`, `dung`, `do_tu_the`, `shot_intent`) chưa lớp nào chạy → bắt buộc ghi
`"chua_co_lop": "<đợt>"` trong khóa đó (đợt thuộc `devsys/stages.DOT`, vd `K1a` / `K5` / `K6`) — `golden.problems` + test hợp đồng
`tests/test_devsys_stages.py` báo đỏ nếu thiếu, và đỏ nếu khóa có lớp chạy lại ghi `chua_co_lop`. Có lớp chạy rồi → xóa `chua_co_lop`,
thêm khóa vào `LOP_CHAY` + test chạy ca.

Ca chống báo nhầm (đúng là "không có lỗi"): `chong_bao_nham_giay_o_can_mcu` (MCU không đòi giày), `chong_bao_nham_lung_mat_na_choker`
(quay lưng không đòi mặt nạ / choker), cùng các ca `loi_dung` "không có …".

Thêm ca: lỗi người dùng bắt mà lọt → xếp loại (mục 10 kế hoạch) → thêm một tệp `cases/<id>.json`; test tự chạy. Ca cũ
`tests/fixtures/stage_facts_golden.json` đã chuyển sang đây (K0a).

Nhánh C: `blockout` {plan, cho_dung (tùy chọn), vat_kich_ban (tùy chọn), codes} chạy ở `tests/test_blockout.py`, lớp kiểm d97 CHƯA nối pipeline. Ca tổng hợp kiểm thiếu khối/chồng lấn; có lớp test chạy nên không ghi chua_co_lop.


Đ20 bổ sung: `package_inputs.json` chứa args/kwargs/sent_kwargs/meta/job trước lắp gói,
manifest SHA256 ref, provider/model/tier, flags (legacy ON giữ riêng experimental OFF),
timestamp/external id và baseline UTF-8 viết độc lập. Ref `ref.bin` tổng hợp là bytes
`synthetic`; test dựng file trong thư mục tạm rồi gọi **ImageRunner/VideoRunner._build_package**
hiện tại. Không sinh lại baseline trong test. `replay_builder` chỉ lắp gói, provider stub
chỉ mang tên fake/clipai/deepix, không tạo client/registry, gửi/poll/mạng/subprocess bị chặn.
Không hỗ trợ nâng nháp `_from_sample` vì còn cần snapshot CSDL nguồn.

Chụp có thể thêm `--input-snapshots-file <inputs.json>` (object job id → input snapshot).
Sidecar phải được đóng băng **trước** lắp gói, không tái tạo args từ sent_package; tool
chỉ đính kèm sidecar, không chứng nhận xuất xứ/độ đầy đủ. Ref vật lý phải có trong ref-root.
Dùng `replay_builder(job["input_snapshot"], ref_root=...)` rồi `compare_compat` với raw
baseline ở fixture; `check_correctness` chạy với kỳ vọng viết riêng, không lấy golden
làm chuẩn đúng. Chưa có sidecar sản xuất → giữ OPEN, không suy ngược cho đủ dữ liệu.

CX20-2b (21/10): db_package_expected.json là baseline byte tổng hợp đóng băng (prompt ảnh cube, motion cube rotates, PNG đỏ16x16); test không sinh lại expected. tools/golden_capture.py --database-replay --latest-per-type lấy args bằng prepare/build thật từ DB readonly, không cần sidecar; tools/golden_db_replay.py nhận nhiều --fixture. Manifest ghi DB/schema/HEAD/cờ/public config và file/stat/missing dependencies; DATA_CHANGED/INSUFFICIENT_INPUT tách CODE_MISMATCH. Xem RA_D20_VIEC2B_CODEX_2026-10-21.md: dữ liệu thật #24/#27 và M2 acceptance vẫn OPEN.
CX21-GOLDEN (21/10): `--latest-per-type` chọn job final/upscale thiếu prompt sẽ lần
`source_job_id` trong cùng project/scene/type về bản nguồn có prompt. Fixture ghi
`selected_job_id` (bản cuối) và `id` (bản nguồn thực sự được dựng/so byte). Chuỗi nguồn
thiếu, khác phạm vi hoặc vòng lặp → INSUFFICIENT_INPUT riêng ca, các ca khác vẫn chạy.
VFS cấp thêm quyền chỉ đọc đúng FILE ảnh được job tham chiếu trong
`data/_plates3d/cache/` hoặc `data/assets/<id>/`; không mở cả cây thư mục. File đọc
vẫn được đóng băng SHA256 trong dependency manifest. Diagnostic chặn ghi loại và
path tương đối root; path ngoài root được thay `<outside-root>`, không xuất payload.

Chọn shot nghiệm thu: ưu tiên bản nguồn có envelope đầy đủ, refs còn nguyên hash,
scene/motion/asset/config chưa đổi từ lúc gửi. BUILT nhưng byte khác ngay khi capture
(ví dụ lịch sử job 660/846/909) vẫn INSUFFICIENT_INPUT; không đổi baseline, không gắn
matched_at_capture=True để nâng thành COMPAT. Chọn shot khác hoặc dùng snapshot
lịch sử đúng thời điểm gửi. Chỉ phiên máy chính chạy các lệnh sau trên snapshot được duyệt:
```
<python-native-3.14> tools/golden_capture.py --db <snapshot>/manifest.sqlite --project 24 --shot <scene> --flags-file <snapshot>/compat-flags.json --public-config-file <snapshot>/public-config.json --ref-root <snapshot-ref-root> --purpose compat --database-replay --latest-per-type --output <fixture-moi>.json
<python-native-3.14> tools/golden_db_replay.py --fixture <fixture-moi>.json --db <snapshot>/manifest.sqlite --ref-root <snapshot-ref-root> --output <replay-moi>.json
```
Lặp cho project 27; cần ≥3 shot ảnh + ≥3 shot video COMPAT mỗi dự án, 0 CODE_MISMATCH.
Nghiệm thu thật #24/#27 vẫn OPEN cho tới khi chủ máy xác nhận đủ số đo.
