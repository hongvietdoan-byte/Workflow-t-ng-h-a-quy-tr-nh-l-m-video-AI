# Bàn giao CX23-M23B — Codex 3 — 24/10/2026

- Trạng thái: tạm dừng tại checkpoint theo EP 23:07 và trả lời phiên chính 23:24; M23B chưa hoàn tất, không báo `xong`.
- Adapter forms: cùng một `dang` ở mọi nhịp được chọn; dạng khác nhau theo nhịp giữ REVIEW và yêu cầu tách shot. Biến thể vật `vat[].bien_the` đọc/kiểm qua `kho_profile`, không đọc profile trong caller; dạng mặc định theo thứ tự `forms` của M0.9. BYĐ không khai `bien_the` thì không báo nhầm là thiếu; mã Kho sai kiểu vẫn giữ cảnh báo chưa kiểm được.
- Tương thích cờ: `kho_forms_v2` TẮT giữ lỗi cấu trúc cũ cho `dang` rỗng; cờ BẬT cho phép để adapter phát REVIEW, và thiếu ngữ cảnh, thiếu asset hoặc hồ sơ Kho v1 đều được báo chưa kiểm được.
- Hồ sơ v2 hỏng được `read()` đánh dấu `_read_error`; khi BYĐ chưa chốt `dang`/`bien_the`, adapter trả REVIEW “không kiểm được” thay vì coi fallback `forms=[]` là hồ sơ không có biến thể. `gaps` thông thường (ví dụ chưa tách mặt/tóc) không tự làm vô hiệu kiểm forms.
- `kho_profile.write_fields` dùng CAS/revision chung cho hồ sơ v1/v2, bảo toàn trường v1 lạ, không cho ghi trực tiếp trường hệ thống, giữ giá trị đã khóa trước ghi tự động và trả `ProfileConflict.diff` khi stale.
- `location_pack.set_model3d` / `set_script_view` gọi guard chung với revision của snapshot ban đầu; interleaving writer tạo conflict, không ghi đè cập nhật cạnh tranh. Hai hàm vẫn commit như hành vi cũ; có thể truyền `actor` và `expected_revision`. Khi chỉ cập nhật metadata model3d, `save()` giữ trạng thái `approved` hiện có dù hồ sơ địa điểm không có các trường nhân vật.
- Đã rebase nhánh `codex/v31-m23b` lên main hiện tại `5d72cf7d`.
- Bằng chứng: chạy tuần tự 9 test liên quan gồm `test_kho_profile_v2`, `test_kho_profile_provenance`, `test_location_pack`, `test_v31_m21_byd_v2`, `test_kho_profile_readers`, `test_assets_names_d17`, `test_shot_intent`, `test_v31_dp8_world_map`, `test_v31_m25_write_guard` — 218 passed, 6 subtests; `git diff --check` sạch. Ca giữ `approved` đỏ ở cả hai setter trước khi sửa; ca trạng thái `_p.REVIEW_REQUIRED` cũng đỏ trước khi bổ sung guard `pending_review`, rồi cả hai xanh. Kiểm kê AST SQL cập nhật theo writer CAS dùng chung. Rà độc lập phát hiện 3 lỗi P2 ở cảnh báo biến thể, revision snapshot và giữ `approved` khi chỉ sửa metadata; đã sửa cả ba, lượt rà cuối không còn finding. Rà lại cờ TẮT cũng giữ nguyên lỗi cấu trúc cũ.
- Chưa làm `assets.standard_set`: Codex 1 đã commit/push phần P34 trong nhánh riêng, chưa GỘP; không cherry-pick, chờ tích hợp.
- Chưa làm `stage_auto.set_family`: `core/stage_auto.py` đang thuộc vùng CX24-N9-REAPPROVE; không sửa chồng.
- `stage_shape` chưa có schema; phiên chính trả lời 23:24 không thêm schema, không đổi hình học. Giữ nội dung câu hỏi đã được chốt.
- Chưa làm UI `proposals`; M23B đã tạm dừng theo ưu tiên EP, giữ nhánh.
- Không migration/backfill, không ghi dữ liệu thật, không gọi API hay dịch vụ trả phí.
- Đã đọc `docs/THIET_KE_GOI_M6B_2026-10-24.md`, `core/crew.py`, `core/handoff.py` để chuẩn bị M6.10.
- Bước kế: CX24-M610 được giao cho Codex 3 nhưng chỉ nhận sau khi CX23-M62 và CX23-M64 đều GỘP. M62 đã GỘP; tin đính chính 23:28 xác nhận M64 chưa vào main và phiên chính sẽ gộp lượt kế. Chờ tin GỘP, không nhận task khác.
