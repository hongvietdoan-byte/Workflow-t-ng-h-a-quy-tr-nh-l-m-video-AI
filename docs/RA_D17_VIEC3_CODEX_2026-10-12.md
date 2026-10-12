# Rà Đ17 việc 3 — tên Kho

Root đọc diff sửa trước commit: matcher giới hạn chặn từ Anh ở tên một token, costume kiểm tên/alias trước spend và kiểm lại sau download; race chỉ đổi số lưu lại ảnh đã có, không submit mới/nới duplicate. DONE chung giữ panel/caller cũ, ff_site nói rõ skip. UI không đổi trong vòng sửa; dùng 4 PNG đã kiểm, không lặp QA/tests khi không có thay đổi cần kiểm mới.

Root GUI: component thật `admin.lib_new_item_box` và `step1_prep.assets_panel`, CSDL/ảnh/quyền giả, Streamlit riêng 8519. Chrome1440/1280: 0 pageerror/0 tràn ngang, 4 PNG `docs/images/d17/english_*.png` đã mở xem; ô tiếng Anh/gợi ý hiện rõ. Không bấm lưu; chưa toàn Dashboard/thử sản xuất. Helper thumbnail đã tạo 4 cache giả trong `data/assets/_thumbs` của chính worktree mới; root xác nhận vị trí, dọn đúng 4 tệp fake, chuyển ASSET_DIR harness sang temp. Không dùng dữ liệu thật, đã dừng đúng server QA, không ảnh hưởng8501/8502.

| Phần | Tần suất / lợi ích | Công / tiền | Rủi ro / quyết định |
|---|---|---|---|
| Tên Anh khi tạo | Ca #27 nhiều vật thiếu ref; tránh vẽ sai | aliases hiện có, 0 USD | Cờ OFF riêng; tên chưa biết yêu cầu nhập; không tự dịch/backfill |
| No ↔ Nỏ | Mọi kịch bản/prompt Anh; tránh gắn nhầm | So từ tại matcher, 0 USD | Chặn gấp dấu với từ Anh thường; giữ alias Anh và Việt không dấu |
| Vật đã gắn / style | Ca torii/style; nói rõ thiếu ảnh | reference_gaps + readiness/diag sẵn, 0 USD | Chỉ cảnh báo; không đổi selector hay tự gắn ảnh |
| Style không HUD | Có thể giúp hiệu ứng nhưng dễ chép HUD/góc máy | Chưa có thử thật; không trả tiền | Chưa bật gửi style; cần người chốt + nghiệm thu riêng |
| Fallback cũ | Đã sửa panel + Plan.apply trên main | Chỉ tái hiện đường còn thiếu | Không viết lại panel/runner; giữ stage image/video |

- Không có paid creation response/schema tạo Kho trong repo để tái dùng; Claude/scripts dùng chung `assets.create` và trường aliases.
- Gợi ý cục bộ là tên có sẵn / thuật ngữ rõ trong mô tả; không xác minh ngôn ngữ bằng API, không coi bỏ dấu tiếng Việt là bản dịch.
- Nhánh `codex/d17-viec3-ten-kho`, base `3fa1a61c`; chưa commit/push/gộp.
- ĐỎ lần 1: 5 hỏng / 40 qua; lần 2: 2 hỏng / 147 qua (ff_site nuốt lý do, costume thiếu kiểm trước cổng tiền).
- XANH lần 3: **149 passed, 4 subtests / 27,55 s**, 7 file tests liên quan; giữ nguyên assert cũ.
- Ca costume đúng Character Bible tái hiện ngoại tuyến trước sửa: `RuntimeError ENTERED_PAID_GATE`; fake gate, không API.
- Tự rà sau test: giữ COUNT số bộ trang phục ở vị trí cũ sau tải ảnh (tránh chọn số quá sớm); compileall + diff check xanh, chưa lặp pytest.
- `asset_english_names` OFF + OPT_IN_ONLY; khai test/cờ vào areas, giữ version. Tên riêng ASCII và alias người nhập được tin theo ngữ cảnh, không xác minh dịch.
- Cảnh báo mô tả chỉ dùng danh từ cụ thể torii/pagoda/archway/shrine/crossbow/katana/gloowall; không đoán theo màu/chất liệu/từ chung, không tự chọn ảnh.
- `reference_gaps` nói cả shot không nhân vật; runner/readiness sẵn có nhận warning; selector ref và panel latest FALLBACK/DONE giữ nguyên.
- Gốc d: `rewrite_for_retry` gọi `save_rewrite` không ghi DONE; dời DONE chung vào save, không ghi trùng ở Plan.apply, xóa trạng thái fallback cũ trên caller.
- Caller phát sinh: costume kiểm tên trước tiền, alias riêng từ tên/alias có sẵn; ff_site giữ lô chạy tiếp + diag và summary tên/lý do mục từ chối. Import folder có skipped(name,lý do) sẵn.
- `related_areas.py` đã chạy cho 7 file code: assets/core_infra/step1/step2/budget + callers; root giao rà độc lập trước commit theo CLAUDE §7.
- Không sửa runner/TODO/PLAN/DB/env/main; không paid call; chưa GUI, cả bộ Windows, rà độc lập, commit/push.

## Rà độc lập và sửa gom
- P1 `costume.py`: tái hiện fake provider 2 submit rồi trùng alias `KELLY outfit 1`; chọn số duy nhất theo cả tên/alias cùng scope trước spend, giữ COUNT cuối + create guard. Race chỉ đổi số/lưu ảnh đã tải, tối đa 3 lần, không submit lại/allow_duplicate.
- P2 `assets.py`: `Cổng đỏ`/`cong do`, `Đèn đỏ`/`den do` bị chặn bởi token `do`; giới hạn common-English guard vào tên một token, giữ nguyên cụm Việt không dấu và alias tường minh.
- Focused ĐỎ **3 failed** → XANH **3 passed**; thêm cover tên chính có khoảng trống số, alias khác tên Việt và race cả hai; không nới assert.
- Nhóm cuối 7 file theo lệnh trên: **154 passed, 4 subtests / 53,14 s**; compileall + diff check xanh. Fake spend/provider, DB bộ nhớ/temp; 0 USD, không dữ liệu thật.
- Root cần đọc diff sửa cuối trước commit; chưa cả bộ Windows/gộp.
