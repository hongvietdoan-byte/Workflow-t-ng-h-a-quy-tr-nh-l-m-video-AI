# CX21-GOLDEN7 — BLOCKED: catalog/baseline đã đổi

Ngày 22/10/2026, Asia/Saigon. **BLOCKED, chưa nghiệm thu A/B.** Negative control native xanh; dừng trước snapshot/lượt thật vì catalog không còn khớp cấu hình 155 cờ + 30 experimental được giao. Không tự đặt false, loại cờ, đổi SHA hay retry.

## Nguồn đã pin lúc fetch

- A: `origin/main` **`a117497d306024c026804247e0f9f9f67ffdaaf7`**.
- B: `origin/cloud/v31-m2-tichhop` **`9746a6ea38d874baf226765cfd378db01eca988d`**.
- Công cụ: **`621661a8`**, `cloud/v31-golden5`, có sửa C-GOLDEN7.
- Đã đọc spec CX21-GOLDEN7 và hai thư `20261022-025830` / `20261022-025903` của cloud-claude: chạy thẳng công cụ, A/B mới nhất, giữ baseline 155 + 30 experimental TẮT, không loại `gen_auth_shadow`; catalog khác phải báo.

## Negative control chạy trước — XANH

Đúng một test `tests/test_golden5.py::test_real_worker_two_code_trees_same_and_one_line_changed`, native Python 3.14: **1 passed trong 20,00 giây**. Không chạy broad suite hoặc chạy lại test. Test kiểm có ca SAME thật, sửa dòng builder `call` của cây B phải tạo DIFF, module nạp đúng cây.

Native spawn dùng `Environment.Clear()` + whitelist HOME/USERPROFILE/TEMP ngoài repo; thay OBJECT `os.environ` qua `patch.object` trước import pytest/core, `--tb=no`; CSDL/ảnh/credentials của test đều giả. Trần owned test 300 giây, kết thúc bình thường.

## Lý do dừng trước lượt thật

Tại thời điểm chuẩn bị baseline, AST catalog cho thấy:

| Nguồn | Số cờ |
|---|---:|
| Mã live máy chính | 146 |
| A đã pin | 150 |
| B đã pin | 153 |
| Công cụ | 153 |
| Hợp A ∪ B | **159** |

Danh sách experimental theo metadata V3.1 hiện có **32 tên**, khác 30 được giao; `gen_auth_shadow` vẫn được khai. Có hai cờ trong A/B không có nguồn trạng thái production ở catalog live và không được metadata hiện tại phân loại vào experimental V3.1: **`director_rewrite_respect_lock`**, **`stage_view_ui`**.

Collector ghi `preflight-blocker.json` rồi dừng với thông báo `STOP: missing production flags; names in preflight-blocker.json`. Đây là **cổng chuẩn bị baseline của orchestration**, không phải mã 2 từ `main_ab` hay lỗi validator C-GOLDEN7. Không tự dùng default/fallback false hoặc tái dùng file cờ của GOLDEN6.

## Những phần chưa chạy

- **Chưa tạo `flags.json` hay `manifest.sqlite`**, chưa backup CSDL thật cho lượt này.
- **Chưa gọi `main_ab`**, chưa chọn/đếm ca thật và chưa spawn worker A/B. Không có bảng SAME/DIFF/ONE_FAIL/BOTH_FAIL hoặc loaded evidence; không được diễn giải thành “0 DIFF”.
- Không sửa công cụ/tests/pipeline, không ghi dữ liệu thật, không API/gen: **0 USD**.

## Bàn giao cần quyết định

Root đã yêu cầu chốt BLOCKED, không retry: phiên điều phối cần chốt **nguồn baseline cho hai cờ thiếu và catalog/experimental mới**, hoặc chốt **SHA A khác** có cấu hình được duyệt. Sau khi có đề rõ mới mở lượt nghiệm thu; giữ negative control xanh và trạng thái chưa chạy thật riêng biệt.

JUnit, cấu hình helper và `preflight-blocker.json` ở `D:/AI-Video-Output/golden-snapshot-7/` ngoài Git; thư mục này mới là nơi chuẩn bị, không có snapshot production. Không commit prompt/payload/ảnh/CSDL/log raw hay đọc/in môi trường/headers/token/credentials thật.

Đã kiểm tra sạch và gỡ ba worktree công cụ `golden-a7`, `golden-b7`, `golden-tool7` bằng `git worktree remove` không force. Test và helper đã thoát, không còn process sở hữu của lượt này; giữ nguyên thư mục chuẩn bị ngoài Git.
