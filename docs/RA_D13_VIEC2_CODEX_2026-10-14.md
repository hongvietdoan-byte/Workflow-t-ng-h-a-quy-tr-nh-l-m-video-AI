# Tự rà Đ13 việc 2 — 14/10/2026
- Nhánh `codex/d13-viec2-goi-blockout`, nền `2c43a28f`; chưa commit/push.
- `related_areas`: plates3d; cờ chung assets/knowledge/step1/step2, không đổi cờ; không có test chậm bắt buộc.
- Đối chiếu caller: không có caller production đọc/ghi pack ngoài module; tests dùng API roundtrip; `blockout_clay.projection` và render_sheet dùng `_font`/render_top_view.
- Schema 2 phân biệt SHA mới/ngày timezone; schema 1 chỉ SHA JSON raw, không fallback qua lại, không sửa/migrate gói gốc.
- Canonical chỉ trường hình học: int/float cùng giá trị exact dùng ratio; bool/chữ/nhãn/mã Kho/thứ tự list giữ ý nghĩa; NaN/Inf chặn, int lớn không ép float.
- Ngày schema 1 naive: giữ nguyên ngày, cảnh báo thiếu múi giờ + can_duyet_lai; luật thay đổi/redflag/history vẫn giữ độc lập.
- Ngày schema 2 tạo UTC và đọc offset ISO aware; naive bị từ chối.
- Font: fallback chỉ TypeError từ load_default(size), giữ dependency; PNG thật xác nhận khi giả lập Pillow không nhận size.
- Đỏ 5 failed/88 passed; xanh 93 passed; thêm test allgeometry bắt thiếu huong_sang (1 failed/94 passed) → sửa → 95 passed.
- Có thêm một proof security cuối (tổng 5 lượt).
- Nhóm 5 file: test_blockout_sheet, test_blockout, test_blockout_facts, test_d11_clay, test_d11_clay_review; 4 lượt tổng do test bổ sung bắt lỗi.
- Proof cuối sửa theo root: patch.object(os, "environ", fake_dict) trước import pytest/test, teardown stop; 95 passed/3.29s; không sao chép/đọc object môi trường thật.
- Các lượt cũ dùng patch.dict clear=True không đáp ứng security object, đã thay bằng proof patch.object; chưa có proof object riêng với credentials giả.
- Test mới chỉ PIL/geometry/hash; caller tests có mock model/client/ước tính; không API, không đọc keys hay dữ liệu thật.
- `git diff --check` qua; không nới test cũ; chỉ thêm vào file test đã đăng ký areas, version 74 giữ nguyên; widget keys không đổi.
- Không sửa PLAN/TODO/runner/delivery/step5/admin_auth/feature production.
- Tự rà 2b.5: không phụ thuộc cwd/data; không đổi luồng auto/bulk/cờ; không chuẩn hóa bỏ dấu; không đường mạng hay lời gọi tốn tiền mới.
- Chưa thử trên Pillow cũ cài thật; fallback fake signature + PNG thật trên Pillow hiện hành.
- Chờ phiên chính RÀ KỸ sạch về data format, cả bộ Windows trước gộp.

## Rà độc lập — 14/10/2026

- READ ONLY code; chỉ bổ sung báo cáo. Đọc diff, schema blockout và caller clay/render; không API/model/data thật/live/commit/push.
- **P2 — `_font` fallback bitmap không render được tiếng Việt** (`core/blockout_sheet.py:89–94`). Repro ép `truetype` báo OSError, `load_default()` chữ ký cũ trả `ImageFont.load_default_imagefont()` (bitmap Latin-1): `render_top_view(plan(), [], temporary_png)` báo **UnicodeEncodeError** ngay tiêu đề. Test hiện dùng `load_default()` của Pillow mới trước patch nên nhận font Unicode hiện đại, chưa chứng minh trường hợp cũ. Đề xuất dùng font TrueType Unicode đóng gói/đường dẫn local đáng tin; thiếu font Unicode thì báo lỗi rõ trước render. Hồi quy dùng bitmap thật, không thay bằng default mới.
- **P2 — SHA chuẩn hóa nhầm metadata ngoài hình học** (`core/blockout_sheet.py:71–73`). `encode` giữ section `khoi` qua dict lồng: plan hợp lệ có `khoi[0].metadata={"z":3}` đổi thành `3.0` vẫn cùng SHA. Repro tạo schema 2 rồi sửa metadata này: `read_location_pack` nhận gói và `can_duyet_lai=False`. Đề xuất nhận diện đường dẫn chính xác của trường geometry, không truyền section xuyên mọi dict con. Hồi quy metadata lồng có `z`/`tam`/`huong` phải giữ kiểu số; geometry chính thức vẫn đồng nhất int/float.
- Kiểm liên quan **29 passed / 0,89 s** (`test_blockout_sheet.py`, `--tb=no`, không showlocals). Trước import module/pytest, dùng `patch.object(os, "environ", dict_gia)`; dict chỉ chứa PYTHONUTF8/PYTEST_DISABLE_PLUGIN_AUTOLOAD/PIPELINE_TEST_KEEP_TEMP. Không đọc/in/assert môi trường thật; không provider/model gọi trong nhóm này. Teardown patch khôi phục object gốc.
- Schema 1 raw SHA nghiêm; schema 2 không fallback raw; timezone aware/naive cũ và history chưa thấy lỗi khác trong phạm vi diff. Chưa chạy lại 95 test hoặc cả bộ.

## Vòng sửa gom sau rà — 14/10/2026

- Root giao cùng phiên rà sửa cả 2 P2; hai test mới chạy **2 failed / 29 deselected** trước sửa, không nới test cũ.
- SHA giờ nhận diện đường dẫn chính xác `huong_sang`, `san.<geometry>`, `khoi[index].<geometry>`, `loi_mo[index].<geometry>`; metadata lồng giữ kiểu số và đổi sẽ bị từ chối SHA.
- Font giữ Arial/DejaVu cũ, thử thêm Tahoma/Segoe UI local. Khi chỉ còn bitmap Latin-1, kiểm nhãn tiếng Việt và báo **ValueError thiếu font Unicode + cách bổ sung font** trước tạo PNG; không bỏ dấu/thay nhãn/PNG giả, không nâng dependency. Root đã chốt cách báo thiếu đầu vào này.
- Nhóm 5 file cũ + 2 hồi quy: **97 passed / 3,43 s**; `git diff --check` sạch. `patch.object(os, "environ", dict_gia)` trước imports/calls, context manager teardown; không patch.dict môi trường thật, không subprocess/API/model thật. Các caller test tự mock client/model/ước tính trước gọi.
- Giữ version 74, widget keys và schema 1; chưa cả bộ Windows/commit/push. Root đọc diff vòng sửa trước gộp.
