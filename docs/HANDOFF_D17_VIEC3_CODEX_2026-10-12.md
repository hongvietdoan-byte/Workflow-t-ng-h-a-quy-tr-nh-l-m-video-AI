# Bàn giao Đ17 việc 3

- Worktree `D:\AI-Video-Pipeline\.codex-wt\d17-viec3-ten-kho`, nhánh `codex/d17-viec3-ten-kho`, base `3fa1a61c`.
- Chưa commit/push; không cherry-pick Đ17v1/v2. Root điều phối rà độc lập + GUI trước commit.
- Đã thêm cờ OFF/OPT_IN_ONLY `asset_english_names`; dùng aliases cũ, không migration/backfill/new API.
- Tạo Kho tay hai form: gợi ý tên riêng/thuật ngữ cục bộ + trường Anh sửa được; core.create dùng chung kiểm thiếu đầu vào.
- Matcher chặn gấp dấu tên Việt bởi từ Anh thường; alias Anh khai rõ vẫn khớp; Việt không dấu nguyên cụm còn hoạt động.
- `reference_gaps` warning khi từ mô tả cụ thể của vật đã gắn chưa khớp tên và khi style được nhắc; không đổi selector.
- Đánh giá style không HUD: chưa gửi ref, chờ người chốt + nghiệm thu riêng, tránh chép HUD/góc máy.
- DONE chung ở save_rewrite để scripts/direct retry cũng dọn fallback cũ; Plan.apply không ghi trùng, panel giữ nguyên.
- Caller tự động: ff_site ghi từng tên/lý do skip ra diag + summary; import folder đã báo skip chi tiết.
- Caller trả tiền: costume guard trước spend_gate, alias bộ riêng từ identifier có sẵn; số thứ tự vẫn tính sau tải ảnh ở vị trí cũ.
- Tests đỏ 5 → tự rà đỏ 2 → **149 passed, 4 subtests / 27,55 s**, 7 file; sau đó chỉ dời COUNT về vị trí cũ, compileall/diff check xanh.
- Lệnh pytest: `py -m pytest -q -p no:cacheprovider tests/test_assets_names_d17.py tests/test_assets.py tests/test_assets_match_p24.py tests/test_prompt_rewrite.py tests/test_ff_site.py tests/test_costume.py tests/test_feature_settings.py`.
- `PYTHONUTF8=1`; các test bộ nhớ/temp/fake provider, không đọc real data/API.
- Related areas: assets/core_infra/step1/step2/budget + callers; root đã được báo hai caller thêm scope. areas chỉ đăng ký test/cờ, version giữ nguyên.
- Tự rà: không nới test, không fold VN để tạo alias, OFF giữ matcher/create/gaps cũ; warning không dựa màu/chất liệu, thoại không kích hoạt.
- Còn mở: danh từ cảnh báo cục bộ hữu hạn; không chứng minh mọi tên Anh, không dịch tự động bằng tiền; chưa GUI/rà độc lập/cả bộ/gộp/live restart.
- Bước kế: root giao reviewer đọc diff + related callers, QA form mới/cờ OFF và style warning; chỉ commit/push khi review cho phép.

## Sau rà độc lập
- Đã sửa 2 finding: costume trùng alias sau trả tiền; matcher mất nguyên cụm Việt không dấu có `do`.
- Costume kiểm tên/alias trước spend, giữ COUNT cuối; create vẫn kiểm duplicate; race retry lưu với số mới tối đa 3 lần, tái dùng 2 ảnh đã tải, không gọi provider lại.
- Test mới: alias cùng identifier khác tên Việt, trùng tên chính có khoảng trống số, race cả hai, `cong do`/`den do`; đỏ 3 → xanh 3, không nới assert.
- Nhóm 7 file cuối **154 passed, 4 subtests / 53,14 s**; compileall/diff check xanh; fake provider/spend, 0 USD.
- Chưa commit/push/fullsuite/main; root rà diff cuối rồi tiếp tục quy trình.
