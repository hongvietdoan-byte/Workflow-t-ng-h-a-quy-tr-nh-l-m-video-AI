# CX21-GOLDEN3 — nghiệm thu golden #24/#27 lần 3

Ngày chạy: 21/10/2026, Asia/Saigon. Báo cáo này chỉ ghi số đo và chẩn đoán đã lược bỏ; không chứa CSDL, gói gửi, prompt, ảnh hoặc credentials.

## Nguồn và giới hạn

- Mã công cụ/pipeline: `cloud/v31-m2-tichhop` tại `9746a6ea` (worktree tạm ngoài repository: `D:/AI-Video-Output/golden-wt3`). Không sửa công cụ khi lỗi.
- CSDL mới: mở `file:///D:/AI-Video-Pipeline/data/manifest.sqlite?mode=ro`, dùng SQLite backup tới `D:/AI-Video-Output/golden-snapshot-3/manifest.sqlite`. Không ghi dữ liệu live; `ref-root` chỉ đọc là `D:/AI-Video-Pipeline`.
- Chọn mọi `scene_id` có `jobs.type IN ('image_gen','video_gen')` thuộc dự án 24/27; dùng `latest_per_type=True`, theo nguồn final/draft của công cụ, không lựa ca để nâng tỉ lệ đạt.
- Capture và replay bằng native Python 3.14; worker có môi trường whitelist, provider giả, mạng/gửi/poll/subprocess bị chặn trong sandbox của công cụ. 0 USD, không tạo job hay migration production.
- Fixture, manifest, CSDL và kết quả chi tiết nằm ngoài Git tại thư mục snapshot trên. Nhánh báo cáo chỉ chứa tài liệu này.
- Đã kiểm worktree công cụ sạch rồi gỡ bằng `git worktree remove D:/AI-Video-Output/golden-wt3`; giữ snapshot/fixture ngoài Git phục vụ chủ công cụ rà. Không xóa asset hay dữ liệu thật.

## Cờ và cấu hình public

`core.features.state()` từ mã máy chính, đọc lựa chọn trên màn 🧪 và chỉ các khóa `FEATURE_<tên cờ catalog>` cụ thể. Không đọc credentials hay xuất môi trường thô. Chỉ lưu bool cờ: 153 tên; sau ép 29 cờ V3.1 mới TẮT, còn 104 cờ BẬT. Các tên có trong catalog nhánh tích hợp mà chưa có trên live đều thuộc danh sách experimental và TẮT; không tự đoán cờ legacy thiếu.

Danh sách explicit 29 cờ experimental (catalog `verified: False`, nhãn/lý do V3.1):

`budget_notice_d01`, `byd_v2_levels`, `continuity_shadow`, `continuity_state`, `diag_merge`, `field_guard`, `final_black_freeze`, `fit_durations_review`, `horizon_needs_sky`, `image_pregen`, `insert_inherit`, `narration_offscreen`, `pause_before_submit`, `poll_claim`, `qc_evidence`, `qc_false_alarm_fix`, `refusal_skip_same_picture`, `release_gate`, `repair_router`, `router_first_frame`, `send_estimate`, `send_preview_panel`, `sent_package_relpath`, `stage_props_byd`, `stale_code_alarm`, `video_qc_shadow`, `whitebox_height_dummy`, `world_map`, `world_map_sentences`.

`public-config.json` là `{}`: không nạp `dashboard.env` hoặc loader khóa. Model ảnh/video lấy từ `jobs.model` bằng cơ chế pin của công cụ C-GOLDEN2; provider/envelope lấy từ bản ghi job. Chưa có bằng chứng môi trường hiệu lực của tiến trình Dashboard khác với tiến trình chụp; báo cáo không khẳng định đã tái tạo mọi giá trị config lịch sử lúc gửi.

## Chẩn đoán gốc đã quan sát

Worker bị chặn đọc `data/skills` với `diagnostic.kind = data`. Allowlist `tools/golden_db_replay.py:_worker.allowed()` chỉ cấp project/knowledge/prompts/pricing/feature settings/provider rules và asset refs cụ thể; chưa cấp kho hồ sơ kỹ năng. Trong khi baseline sản xuất dùng `skill_dossier`, `core/skill_dossier.py:names()` cần kiểm thư mục đó. Đây là thiếu dependency của công cụ nghiệm thu; không chứng minh pipeline đã đổi gói.

Không mở rộng allowlist, tắt cờ legacy, đổi baseline hay sửa fixture để đạt. Chủ công cụ cần xem xét quyền đọc dependency cụ thể và khóa manifest phù hợp, rồi chạy lại nghiệm thu trên snapshot mới/được duyệt.

Lưu ý độc lập khi đọc thống kê: `replay_fixture()` chuyển capture không có manifest thành `INSUFFICIENT_INPUT`, kể cả capture đã phân loại `DATA_CHANGED`. Báo cáo giữ riêng bảng capture và replay để không mất nguyên nhân; chưa tự sửa vì đề chỉ yêu cầu nghiệm thu.

## Kết quả

**KHÔNG ĐẠT. Chưa mở khóa gộp M2.** 0 CODE_MISMATCH không có nghĩa là đạt khi không có đủ ca COMPAT.

| Dự án | Ca chọn | COMPAT | DATA_CHANGED (replay) | CODE_MISMATCH | INSUFFICIENT_INPUT | Shot ảnh COMPAT | Shot video COMPAT |
|---|---:|---:|---:|---:|---:|---:|---:|
| #24 | 24 | 0 | 0 | 0 | 24 | 0 | 0 |
| #27 | 44 | 0 | 0 | 0 | 44 | 0 | 0 |

Ngưỡng: mỗi dự án ≥3 shot ảnh + ≥3 shot video COMPAT, toàn bộ 0 CODE_MISMATCH. Không dự án nào đạt.

Phân loại ngay tại capture (không bị bước replay đổi nguyên nhân):

| Dự án | BUILT | DATA_CHANGED | INSUFFICIENT_INPUT |
|---|---:|---:|---:|
| #24 | 0 | 0 | 24 |
| #27 | 3 | 1 | 40 |

Chẩn đoán capture theo nhóm (không có prompt/payload):

- 4 ca: `INSUFFICIENT_INPUT`; chuỗi source_job_id thiếu/hỏng hoặc không an toàn; kind `—`, path `—`.
- 60 ca: `INSUFFICIENT_INPUT`; worker thiếu dependency hoặc schema; kind `data`, path `data/skills`.
- 1 ca: `DATA_CHANGED`; builder đòi tệp nền/Kho khác refs đã gửi (dữ liệu sân khấu/Kho đổi sau ngày gửi): data/_plates3d/cache/74afb2490f1319bd5ad6/plate.png; kind `data`, path `data/_plates3d/cache/74afb2490f1319bd5ad6/plate.png`.
- 3 ca: `BUILT`; worker dựng được; chưa khẳng định khớp byte lịch sử; kind `—`, path `—`.

Nhóm BUILT không tự nâng thành COMPAT; comparator vẫn đối chiếu gói lịch sử. Không thay `matched_at_capture`/baseline/hash để ép qua.

Snapshot CSDL được giữ ngoài Git, SHA256 đóng băng: `1546aa95a6088bd719f1ffbbc4bdbd785e251957da2b0928587306b7a0efd6e6`.

## Test công cụ trên native Python 3.14

Chạy đúng nhóm liên quan: `tests/test_golden_replay.py`, `tests/test_golden_db_replay.py`, `tests/test_golden2.py`, với `-q --tb=no -p no:cacheprovider`. Thay object `os.environ` bằng dict giả trước import pytest; HOME/USERPROFILE/TEMP ngoài repository, không nạp credentials. Không chạy cả bộ và không sửa/nới test.

**INCOMPLETE, không xanh:** bắt đầu 19:10:18; dừng đúng process pytest thuộc lượt này lúc 19:25 sau trần 15 phút. Luồng vẫn tiến triển (đã hiện 64% rồi thêm nhiều test), không kết luận treo. Trước khi dừng đã thấy **ít nhất 8 dấu F**, chưa có summary nên không đoán số pass/tổng test hay tên test thất bại. Kiểm cây process lúc dừng không có process con còn chạy; không dừng Dashboard/Blender/tiến trình của phiên khác. Chưa xác nhận kết quả cuối của test worker 3.14 bắt buộc. Không chạy lại để kéo dài lượt nghiệm thu sau khi đã đủ 68 ca thật thất bại.

Đã phát hiện tĩnh `tests/golden/package_inputs.json` trên nhánh tích hợp thiếu `sent_package_relpath: false` ở cả input ảnh/video, trong khi catalog có cờ mới `verified: False`. `validate_compat_flags()` fail-closed khi thiếu cờ. Không tự sửa fixture trong việc nghiệm thu này; đây là lỗi cần chủ nhánh tích hợp tiếp nhận.

Đây là nhiệm vụ chạy nghiệm thu và ghi báo cáo, không thay mã triển khai nên không có vòng viết test đỏ → sửa code → xanh trong nhánh báo cáo. Test đỏ thực tế được giữ và báo rõ.
