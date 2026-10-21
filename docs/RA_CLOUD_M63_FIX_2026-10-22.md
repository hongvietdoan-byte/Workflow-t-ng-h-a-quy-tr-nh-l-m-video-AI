# C-M63-FIX — sửa lỗi rà phiên chính 22/10 (M6.3 + M7.4) — cloud-C

- Nhánh: `cloud/v31-m63-fix`, tách từ `origin/main`.
- 0 USD.
- Cờ `gen_auth_shadow` vẫn TẮT. Cờ TẮT thì các đường mới không đọc gì.

## VỪA — mọi đường gửi tiền đều qua cổng shadow
- Thêm `gen_auth.shadow_send(conn, project_id, scene_id, kind, model, route, data_dir, origin)`. Hàm này được gọi NGAY trước `slot.send` ở 6 đường gửi thẳng, không qua runner:

  | Tệp | Đường | Nguồn gốc |
  |---|---|---|
  | `core/end_frames.py` | khung cuối (`end_frame`) | tự động |
  | `core/quality_samples.py` | phép thử chất lượng (`quality_sample_<kind>`), cả nhánh `submit_final_from_sample` | người bấm |
  | `core/lipsync.py` | khớp môi (`lipsync`) | tự động |
  | `core/scene_establish.py` | ảnh toàn cảnh (`establishing` / `trainee_establishing`) | tự động; không gắn shot |
  | `core/costume.py` | bộ ảnh nhân vật (`character_set`) | người bấm; không gắn shot |
  | `core/experiments.py` | thử multi-shot (`kling_multishot`) | người bấm; mỗi shot THẬT SỰ đi một dòng |

- Mỗi dòng jsonl mang `route` + `origin`. Cổng không chặn, không ghi CSDL.
- Đường gửi thẳng **không phải lượt gen / làm lại của shot**, nên:
  - KHÔNG kiểm trần lượt, điều kiện tự sửa và model. Khớp môi dùng model riêng `lipsync-2-pro`; nếu kiểm thì mọi dòng sẽ bị báo `MODEL_NOT_APPROVED`.
  - Chỉ ghi lại, kèm kiểm trùng job đang chạy và gửi chưa rõ kết quả.
  - **Có tính các đường này vào trần lượt shot hay không là câu hỏi cho M6-B / EP** (đã nêu ở báo cáo M6.3).
- Test giữ: quét AST, mọi hàm có `slot.send(provider.submit` trong 6 module trên đều có `gen_auth.shadow_send(` ĐỨNG TRƯỚC.

## THẤP — đếm lượt clip nhóm + hiệu năng
- `attempts()` đếm thêm job của shot KHÁC có `sent_group` chứa id shot này. Đó là clip nhóm Seedance / multi-shot do shot đầu gửi.
  - Job đi kèm đã nhận cùng task (`external_id` của leader) không đếm 2 lần.
  - Câu SQL tách bằng `UNION`: nhánh `scene_id=?` dùng chỉ mục; nhánh nhóm chỉ quét trong dự án của shot.
- Ngân sách tự sửa:
  - tính **một lần cho cả lượt gửi** (leader + các shot nhóm, `memo`) thay vì N lần trong `SPEND_LOCK`;
  - mỗi khoản chi chỉ vào MỘT bên — lượt đầu hoặc làm lại — không đếm khoản chi của leader 2 lần.
- Bảng giá cache 60 giây (`_PRICING_CACHE`).
- Bỏ bản cache ngân sách toàn cục ở commit đầu. Khóa `id(conn)` có thể trùng sau khi kết nối đóng, và không thấy `grants.jsonl` đổi (rà mục 4).

## THẤP (M7.4) — mã dừng autoqc không bao giờ xóa
- `_codes` được xóa khi:
  - một lượt MỚI bắt đầu (`_work` / `_video_work`, trước khi mở CSDL);
  - lượt dừng vì lỗi khác (`_fail` không có mã);
  - gọi `clear_error` / `clear_video_error` (trước đây hàm sau không xóa mã video).
- KHÔNG cho mã hết hạn theo `RETRY_AFTER`. M7.4 cố ý giữ mã QUA cửa sổ đó, vì vòng nền chỉ phân loại "kẹt" sau AUTOQC_TRIES vòng (`test_autoqc_keeps_the_stop_code_past_the_retry_window`). Khi lỗi hết hạn, vòng nền chạy lượt mới → mã cũ bị xóa ở đầu lượt, nên vẫn không còn báo nhầm "Claude không dùng được".

## Rà soát (quy tắc 7) — 10 mục, đã sửa hết
| # | Mức | Vấn đề | Sửa |
|---|---|---|---|
| 1 | TB | Mọi đường gửi thẳng gán `origin='auto'` → báo giả BUDGET_EXCEEDED / NO_CAUSE / ATTEMPTS_EXHAUSTED | Đường gửi thẳng ghi riêng; `origin=None` cho nút người bấm |
| 2 | TB | Khớp môi luôn bị báo MODEL_NOT_APPROVED | Đường gửi thẳng bỏ kiểm model; multi-shot truyền model thật `kling-v3-omni` |
| 3 | THẤP–TB | `id<>NULL` làm DUPLICATE_INFLIGHT không bao giờ bật | `_busy` dùng `(? IS NULL OR id<>?)` |
| 4 | THẤP–TB | Cache ngân sách toàn cục khóa theo `id(conn)` | Bỏ; dùng `memo` theo lượt |
| 5 | THẤP–TB | `json_each` + `OR` quét mọi job | Dùng `UNION` có chỉ mục |
| 6 | THẤP | Khoản chi của leader bị đếm 2 lần | Khử trùng |
| 7 | THẤP | Multi-shot ghi cả shot bị cắt | `scenes[:len(shots)]` |
| 8 | THẤP | `latest_per_job` gộp các đường | Khóa thêm `route` |
| 9 | THẤP | Cache bảng giá rò giữa các test | Fixture autouse xóa cache |
| 10 | THẤP | Trường thời gian của `_codes` không ai đọc | Bỏ |

## Test
- `tests/test_v31_m63_gen_auth.py` thêm 10 test. Trên code cũ: 7 test của commit đầu đều đỏ.
- Các test liên quan xanh: end_frames, quality_samples, lipsync, costume, scene_establish, bg_autoqc, runner, M7.4.
- Full suite: xem dòng cuối.
