# Codex 1 — CX23-M60-AUDIT đang làm

Nhánh `codex/v31-m60-audit`, worktree `D:/AI-Video-Pipeline/.codex-wt/v31-m60-audit`, nền `67a1fc23`. Đã nhận qua hộp thư sự kiện `20261024-153731-codex-lmkr.json` theo hàng dự phòng; kiểm trước nhận không có nhánh/worktree m60 đang hoạt động.

## Đã làm ở checkpoint này

- Đọc docs/CODEX_TASKS.md mục CX23-M60-AUDIT và kế hoạch M6.0. Chưa có kết quả audit hoàn chỉnh hoặc đo hiệu năng; không báo XONG.
- Đã xem mã nguồn `tools/audit_run.py`, `core/perf.py`, `tools/load_test_ui.py` để tái dùng, không gọi chúng. audit_run đọc DB nhưng mặc định ghi báo cáo dưới data/: KHÔNG chạy nguyên lệnh mặc định. load_test_ui có đường sao DB/khởi server riêng/provider giả nhưng mô tả lọc vài khóa môi trường chưa đủ tiêu chuẩn fake-object/whitelist hiện tại: phải audit trước khi tái dùng.
- Không chạm file core/dashboard/areas, không đọc CSDL/asset production, không khởi server hoặc chạy provider/LLM/GUI. Checkpoint chỉ tài liệu bàn giao.

## Làm tiếp

1. Git fetch/pull an toàn ở hộp thư, đọc tin mới và xác minh owner; M82B/UI M47B còn chờ core/gộp ở lần kiểm cuối, nếu mail mới đổi ưu tiên thì theo mail.
2. Kiểm kê source mọi caller tạo job/provider/LLM/TTS/nhạc: file:dòng, vai người/Director/công cụ, sổ chi/ước tính/xác nhận, write guard. Phân biệt tạo queued job với submit trả phí; alias/dynamic chưa chứng minh phải UNKNOWN, không coi rg là bằng chứng toàn bộ caller.
3. Thiết kế phép đo đủ màn/khối/query/lineage trên bản SAO tạm, provider/flags/asset/env giả; SQL nguồn mode=ro, không core.db bootstrap nguồn, không ghi dữ liệu thật. Không dùng Computer Use. Chỉ AppTest/headless trên cổng phụ nếu an toàn; không pull/checkout/restart live tùy tiện.
4. Nếu thêm công cụ: targeted đỏ→xanh, không nới; một reviewer độc lập tiền/dữ liệu/quyền và caller, root đọc fixdiff. Đăng ký code/tests/flags, giữ areas.version. Báo cáo cuối docs/M6_0_AUDIT_2026-10-24.md (đổi ngày đúng khi làm), đề xuất check M6 chỉ là đề xuất, không sửa data/decisions.json.
5. Chốt report/RA/TODO, xóa HANDOFF ở commit cuối, push từng commit, helper xong rồi nhận việc kế.

## An toàn test bắt buộc

Thay OBJECT os.environ bằng dict giả qua patch.object trước imports/calls/spawns, không patch.dict(clear=True). Mock registry/keyring/credential/provider/model; native env whitelist + HOME/TEMP giả. Pytest --tb=no; không showlocals/dump env, không đọc/in/repr token/header/credential/payload thật. Không API trả phí, migration, dữ liệu sản xuất hoặc xóa asset.

## Bàn giao việc đã xong trước đó

M82B `ed687e9f`, REPORT `7e786025` (Markdown/JSON/PDF7trang), thiết kế M6-B `70a9a6ae`: đã push nhánh riêng và báo XONG qua hộp thư, chờ Claude nghiệm thu/gộp. Không làm lại. Không nhận CX24-KIEM-CONG-GOP vì thư 15:17 giao Codex 3. Không tự tạo lịch trùng hoặc chat mới.
