# CX21-GOLDEN5 — so A/B trên cùng snapshot, Windows native 3.14

Ngày 21/10/2026, Asia/Saigon. Chỉ đọc, **0 USD**; không sửa pipeline/công cụ, không ghi dữ liệu thật, không gọi provider. Báo cáo không chứa prompt, payload, CSDL, ảnh, môi trường hay credentials.

**Kết luận nghiệm thu: CHƯA ĐẠT — negative control native còn đỏ.** Bảng A/B bên dưới giữ nguyên kết quả công cụ, không thay thế việc xác minh công cụ phát hiện được cây code bị sửa.

## Nguồn đã khóa

- A: `origin/main` tại **`eb7fd954`**, worktree tạm `D:/AI-Video-Output/golden-a5`.
- B: `origin/cloud/v31-m2-tichhop` tại **`9746a6ea`**, worktree tạm `D:/AI-Video-Output/golden-b5`. Đã đọc tin mới nhất của hộp thư; chưa có nhánh tích hợp thay thế được chỉ rõ, không tự gộp thêm nhánh vào B.
- Công cụ: `origin/cloud/v31-golden5` tại **`46f81fc0`**, code `f0fc068c`; worktree `D:/AI-Video-Output/golden-tool5`.
- Snapshot **MỚI**: SQLite backup từ `file:///D:/AI-Video-Pipeline/data/manifest.sqlite?mode=ro` tới `D:/AI-Video-Output/golden-snapshot-5/manifest.sqlite`; không tái dùng snapshot 3/4. Cả A/B dùng cùng snapshot/cờ/ref-root live chỉ đọc.
- **Baseline tái dựng** theo `v31-ep-golden-ab-acceptance-2026-10-21`: trạng thái hiệu lực sản xuất hiện có, chỉ các cờ mới V3.1 TẮT. Preflight phủ catalog của cả hai cây: 153 tên cờ, 104 BẬT, 29 experimental TẮT; `public_config = {}`, model/provider theo job và cơ chế pin của công cụ. Không đọc `dashboard.env` hay credentials.
- Native spawn bằng `ProcessStartInfo.Environment.Clear()` + whitelist HOME/USERPROFILE/TEMP ngoài repo; lấy baseline chỉ chuyển FEATURE có tên trong catalog và giá trị bool/chế độ. Worker thay object `os.environ` bằng dict giả trước import core, provider giả/cached registry, cấm mạng/gửi/poll/ghi nguồn/subprocess; mỗi worker timeout 120 giây, toàn lượt có owned-process budget 30 phút.

Chạy đúng `main_ab --ab` của công cụ với #24/#27/#31/#33. Wrapper chỉ ghi checkpoint số đếm/status/diagnostic đã lọc, không đổi đầu vào, raw package hay comparator. Chọn 158 ca mới nhất mỗi shot/loại: #24 = 24, #27 = 44, #31 = 78, #33 = 12. Không loại BOTH_FAIL hoặc chọn ca tốt để nâng kết quả.

29 experimental explicit:

`budget_notice_d01`, `byd_v2_levels`, `continuity_shadow`, `continuity_state`, `diag_merge`, `field_guard`, `final_black_freeze`, `fit_durations_review`, `horizon_needs_sky`, `image_pregen`, `insert_inherit`, `narration_offscreen`, `pause_before_submit`, `poll_claim`, `qc_evidence`, `qc_false_alarm_fix`, `refusal_skip_same_picture`, `release_gate`, `repair_router`, `router_first_frame`, `send_estimate`, `send_preview_panel`, `sent_package_relpath`, `stage_props_byd`, `stale_code_alarm`, `video_qc_shadow`, `whitebox_height_dummy`, `world_map`, `world_map_sentences`.

## Kiểm chứng công cụ — negative control CHƯA ĐẠT

Chỉ chạy **một** test native cần máy chính: `tests/test_golden5.py::test_real_worker_two_code_trees_same_and_one_line_changed`, không chạy lại bộ broad. Môi trường/CSDL/credentials/ảnh đều giả; thay OBJECT `os.environ` bằng dict giả trước import pytest/core, `--tb=no`, JUnit ngoài Git, trần owned process 300 giây.

**1 failed trong 21,61 giây**, không timeout. Test tới assertion sau khi sửa một dòng `sent_package.py` của cây B nhưng vẫn có `DIFF + ONE_FAIL = 0` (`assert ((0 + 0) >= 1)`). Vì vậy negative control chưa chứng minh phát hiện thay đổi cây code như test yêu cầu. Không sửa/nới test hay tự gán nguyên nhân từ số đếm này.

Theo chỉ dẫn root, vẫn chạy hết 158 ca thật để thu bảng theo đề, nhưng **KHÔNG THỂ chốt nghiệm thu ĐẠT khi negative control còn đỏ**, kể cả bảng A/B có 0 DIFF. Chưa chạy lại test hay công cụ sau lỗi này.

## Kết quả A/B

**CHƯA ĐẠT nghiệm thu: negative control native còn đỏ.** Bảng theo comparator công cụ: **đạt ngưỡng số đếm**. Không đổi trạng thái để ép đạt.

| Dự án | Ca | SAME | DIFF | BOTH_FAIL | ONE_FAIL |
|---|---:|---:|---:|---:|---:|
| #24 | 24 | 15 | 0 | 9 | 0 |
| #27 | 44 | 28 | 0 | 16 | 0 |
| #31 | 78 | 78 | 0 | 0 | 0 |
| #33 | 12 | 6 | 0 | 6 | 0 |

Tổng: `{"SAME": 127, "DIFF": 0, "ONE_FAIL": 0, "BOTH_FAIL": 31}`. Dự án không có SAME: `[]`. Mã thoát công cụ: `0`; thời gian A/B `1485.815` giây.

Các ca DIFF / ONE_FAIL (chỉ định danh và trường/lý do đã lọc):

- Không có DIFF / ONE_FAIL theo comparator.

BOTH_FAIL theo lý do A/B (không suy thành tương thích):

- 31 ca: A `prepare chờ hoặc cần draft lịch sử`; B `prepare chờ hoặc cần draft lịch sử`.

History tham khảo (không quyết nghiệm thu):

- A: `{"NO_SENT": 6, "NOT_BUILT": 29, "DIFF_FROM_SENT": 118, "SAME_EXCEPT_FINGERPRINT": 5}`.
- B: `{"NO_SENT": 6, "NOT_BUILT": 29, "DIFF_FROM_SENT": 118, "SAME_EXCEPT_FINGERPRINT": 5}`.

SHA256 snapshot CSDL: `3457436cb95802ef8590899db860f39ec47cf339e8f182cc6919a879cefd6e39`. Snapshot được backup mới từ nguồn live mode=ro, kể cả khi SHA trùng bản cũ.

## Giới hạn và bàn giao

- SAME/DIFF/ONE_FAIL/BOTH_FAIL giữ đúng comparator. ONE_FAIL tính như lệch; BOTH_FAIL không phải bằng chứng tương thích. Ngưỡng bảng: 0 DIFF, 0 ONE_FAIL, mỗi dự án ≥1 SAME. History chỉ là tham khảo, không dùng làm điều kiện đạt.
- Job chưa từng gửi dùng envelope giả cố định cho cả A/B theo công cụ; những ca đó không chứng minh đường Kho chủ thể ClipAI. Baseline tái dựng không phải snapshot cấu hình lịch sử; A/B không chứng nhận correctness/chất lượng hình ảnh hay quyền bật cờ sản xuất.
- Đọc diff `--ab` trước chạy: worker import core/prompts/knowledge của `code_root`, dữ liệu từ ref-root. Có điểm cần chủ công cụ rà: kiểm chữ ký sau worker vẫn dùng `_plain(name, ref_root)` trong khi prompts/knowledge có thể được đọc từ `code_root`; nếu gặp ONE_FAIL/DATA_CHANGED phải phân biệt lỗi công cụ với hồi quy code. Không tự sửa.
- Guard Python/audit không phải sandbox OS; giới hạn native C và `nt._path_exists` đã ghi ở báo cáo GOLDEN4, không được xóa bằng một bảng SAME. Không tự đọc/log bí mật hoặc nới denylist.
- JSON kết quả, checkpoint, CSDL và JUnit chỉ nằm tại `D:/AI-Video-Output/golden-snapshot-5/`, ngoài Git. Nhánh này chỉ có báo cáo; phiên chính quyết định bước sửa/nghiệm thu/gộp tiếp theo.
- Đã hoàn tất 316 lượt worker, không có timeout. Native test đã kết thúc; không còn owned process của lượt này. Kiểm cả ba worktree tạm sạch rồi gỡ bằng `git worktree remove`; giữ snapshot/fixture ngoài Git, không xóa asset/dữ liệu thật.
