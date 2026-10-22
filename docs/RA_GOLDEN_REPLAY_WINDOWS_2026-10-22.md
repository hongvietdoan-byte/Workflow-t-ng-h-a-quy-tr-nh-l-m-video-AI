# Rà golden replay Windows (C-GOLDEN8-FIN) — 22/10

Nhánh `cloud/v31-golden8-fin` = `origin/claude/golden-replay-windows` @302afef2 + merge `origin/main` + sửa vòng rà này.
Làm thay cloud-E trên máy chính Windows (Python 3.14 native → các test `needs_native_314` CHẠY THẬT, không skip). 0 USD.

## 1. Số đo golden (đã có — máy chính, công cụ c21dac7b, mã thoát 0)

| Lượt | SAME | DIFF | ONE_FAIL | BOTH_FAIL | Ca Kho chủ thể giả | ĐẠT |
|---|---:|---:|---:|---:|---:|---|
| Chính (pause_before_submit + poll_claim TẮT) | 127 | 0 | 0 | 31 | 21 | có |
| Phụ (pause_before_submit + poll_claim BẬT) | 127 | 0 | 0 | 31 | 21 | có |

Đọc lại tệp `D:/AI-Video-Output/golden-snapshot-8mc/ab_main.json`, `ab_flags_on.json` lúc rà: đúng số trên; 31 BOTH_FAIL ở CẢ HAI lượt
đều `{"status": "INSUFFICIENT_INPUT", "reason": "prepare giữ (_hold)"}` (không ca nào "dependency thiếu hoặc sandbox chặn").
So GOLDEN7 117/0/0/41 (đo TRƯỚC bản vá Windows): 10 ca 'operation' (Kho chủ thể) nay SAME. Theo dự án: #24 15/0/0/9, #27 28/0/0/16,
#31 78/0/0/0, #33 6/0/0/6.

## 2. Rà diff origin/main...HEAD (tools/golden_*, tests/)

| Mức | Chỗ | Nhận định | Xử lý |
|---|---|---|---|
| — (đạt) | tools/golden_db_replay.py:653 `upload` | Giả upload chỉ khi `request["code_root"]` (= --ab); capture/replay thường `refuse("subject_library_upload")`. Asset tất định theo sha256 NỘI DUNG tệp → ảnh khác ⇒ asset_uri khác ⇒ gói khác ⇒ DIFF; nhãn khác ⇒ `simulated_uploads` khác ⇒ DIFF. Có test hai chiều (`test_subject_upload_is_simulated_only_in_ab_and_deterministic`). | — |
| — (đạt) | :669 `canonical_mark` + :441 `fresh_dirs` | --ab: thư mục ra của mark() chỉ nhìn scratch → mỗi cây dựng lại ảnh bằng code của mình (trước: cache ref-root do code LỊCH SỬ dựng che DIFF khi B sửa mark/clean). Khóa tên tệp = sha1(abspath nguồn) — cùng ref-root ⇒ cùng tên ở A và B. | — |
| — (đạt) | :453 hỏi tồn tại lần 2 | Capture: lần 1 ghi {stat}, lần MỞ sau ghi đè sha; replay theo dạng đã ghi cho MỌI lần hỏi → nhất quán. | — |
| — (đạt) | đối chứng âm | `test_golden5::test_real_worker_two_code_trees_same_and_one_line_changed` CHẠY THẬT (3.14 native) và xanh: đổi 1 dòng builder ⇒ DIFF = số SAME. | — |
| — (đạt) | cwd / `\` vs `/` | `relpath` trả `as_posix()`; so `fresh_dirs` bằng tên posix; scratch = cwd do tiến trình cha đặt; `is_relative_to` của WindowsPath không phân biệt hoa/thường. | — |
| THẤP | :776 `compare_ab` | DIFF do `simulated_uploads` chỉ báo hai độ dài (cùng số lượt, khác ảnh → a=1, b=1, không đọc được). | ĐÃ SỬA: dùng `first_diff` → `simulated_uploads[0].sha` (vị trí ký tự, không nội dung). Chỉ đổi phần mô tả, trạng thái không đổi. |
| THẤP | :711 `_failure_answer` | Ngoại lệ code lõi có thuộc tính `diagnostic` không phải dict → TypeError ngay trong nhánh except (worker không ghi response.json). Chưa gặp trên data thật. | ĐÃ SỬA (fallback {kind: tên lớp}). |
| THẤP | :418 `_scratch_parents` | Chặn junction chỉ kiểm thư mục MỚI tạo; junction/symlink đã có sẵn trong scratch không kiểm ở đường ghi (scratch là thư mục tạm mới; os.symlink ra ngoài đã bị audit hook chặn). | Ghi nhận, không sửa. |
| THẤP | :920 `run_ab` except | `reason: str(e)[:200]` (lỗi phía cha) chưa dùng `_failure_answer`. | Ghi nhận (ngoài đề bài; không gặp ở hai lượt). |
| VỪA (quy ước) | devsys/areas.json | `tests/test_golden_replay_windows.py` (tệp mới) chưa khai khu vực. | ĐÃ SỬA (step2.tests). |

Không có lỗi CAO.

## 3. Việc mở trong HANDOFF

**(a) Nhánh except `tools/golden_capture.py`** — ĐÃ SỬA: dùng chung `_failure_answer` (loại thao tác + `positions` tệp:dòng); KHÔNG
mang `_WORKER_STATE` (tiến trình cha). Giữ `matched_at_capture: False` + reason cũ; DataChanged phía cha → DATA_CHANGED không `paths`
→ `replay_fixture` vẫn coi là INSUFFICIENT_INPUT như trước.

**(b) `refuse()` làm ca code nuốt ngoại lệ chuyển BUILT → INSUFFICIENT_INPUT — ĐÚNG, giữ.** Trước đây `forbidden()` không ghi vào
`denied`, nên khi code lõi bắt rộng (`except Exception` — ví dụ cắt giọng khớp môi gọi ffmpeg qua subprocess, rồi "gửi không kèm giọng")
worker dựng tiếp một gói KHÁC gói sản xuất (sản xuất đã gọi được ffmpeg/provider/Kho) mà vẫn BUILT → so lịch sử ra CODE_MISMATCH giả,
so A/B có thể SAME trên gói suy biến. `refuse()` ghi `denied` như `block()` của audit hook → fail-closed, đúng CHUAN_XAY_DUNG (không im lặng
khi thiếu đầu vào). Tác động số đo: 0 ca (31 BOTH_FAIL đều `_hold`, trả về TRƯỚC chỗ kiểm `denied`). Test ghim:
`test_swallowed_refused_operation_is_insufficient_not_built`.

**(c) listdir/scandir sau khi ghi chỉ thấy scratch** — `locate()` trả thư mục scratch nếu nó đã tồn tại → nội dung ref-root cùng thư mục
bị che. Không làm lệch kết quả A/B: hai cây chạy cùng snapshot, cùng chuỗi thao tác tới chỗ code khác nhau, nên cùng bị che như nhau;
đường dựng gói (core/runner.py, sent_package.py, seedance_refs.py, subjects.py) không có lời gọi listdir/scandir/glob/iterdir. Rủi ro
còn lại (THẤP): một sửa đổi ở B dựa vào liệt kê thư mục đã bị ghi trong lượt thì A và B cùng thấy thiếu → có thể che DIFF; với capture so
lịch sử thì chỉ gây CODE_MISMATCH giả (không che). Trước bản vá các ca này hỏng FileNotFoundError, nên không ca nào xấu đi. Riêng thư mục
`fresh_dirs` (mark) chỉ-scratch là CỐ Ý. Không sửa (gộp liệt kê scratch ∪ ref-root sẽ đổi hành vi so sánh → phải đo lại, không có ca cần).

## 4. Test

- Đỏ → xanh: `test_capture_except_branch_uses_the_shared_failure_answer`, `test_failure_answer_tolerates_a_foreign_diagnostic_attribute`,
  `test_simulated_uploads_diff_names_the_first_differing_entry` (tests/test_golden_replay_windows.py). Ghim (b):
  `test_swallowed_refused_operation_is_insufficient_not_built` (xanh từ c21dac7b).
- Test golden (6 tệp): 184 passed, 1 skipped (symlink cần quyền Windows).
- Quy ước 7: `tools/related_areas.py` → khu vực step2 + devsys; không khu vực nào GỌI module đổi ngoài tools/golden_* (pilot_a chỉ
  nêu tên tệp test; test_v31_m72 kiểm chuỗi FEATURE_BASELINE — còn nguyên).
- Cả bộ: xem mục 5.

## 5. Cả bộ test (một lần, máy chính Windows)

`PYTHONUTF8=1 py -m pytest -q -n 8 -p no:cacheprovider -rf` trên commit 4c21a752 (đã merge origin/main):
**7923 passed, 10 skipped, 22 xfailed, 0 failed** (24 phút 13 giây). Không có đỏ nào, kể cả đỏ có sẵn trên main.

## 6. Có cần chạy lại golden trên máy chính?

**KHÔNG.** Vòng này không đổi hành vi so sánh: (1) `compare_ab` chỉ đổi phần mô tả `first_diff` của DIFF do `simulated_uploads` (cả hai
lượt 0 DIFF); (2) `_failure_answer` chỉ khác khi `diagnostic` không phải dict (chưa gặp — hai lượt chạy hết, mã thoát 0); (3) nhánh except
golden_capture chỉ dùng khi chụp (capture), không dùng ở --ab. Số 127/0/0/31 (cả hai lượt) giữ nguyên giá trị.
