# Tự rà Đ10 việc 6 — 12/10/2026

Nhánh codex/d10-viec6-chuyen-dong-nen, nền 167fb37. RÀ NHẸ: cờ ambient_motion mặc định TẮT; chưa commit/push.
- Luật vào Director một lượt, DP hai lượt và motion bundle; action làm nguồn dịch motion_en.action, không sửa dịch trung thành.
- OFF snapshot lấy từ code gốc trước sửa, so UTF-8 từng byte Director/motion/DP xanh; fixture JSON giữ newline trong chuỗi, không lệ thuộc CRLF checkout.
- ON motion payload truyền đủ BYĐ/location/weather/time + gợi ý có điều kiện; BYĐ dùng noi_chon.thoi_tiet/thoi_gian.
- Chỉ nhận chủ thể nền + động từ, không nhận danh từ đơn, phủ định/đứng yên; từ tiếng Việt có biên từ, không bỏ dấu.
- Thiếu nền VÀNG trong lint_motion kể cả máy tĩnh; review_shot.red vẫn False, red_issues/group_red_issues chỉ lấy level red, không chặn gen.
- Root phát hiện dependency: on_prompt_saved/after_director theo prompt_formula; đã khai REQUIRES ambient_motion→prompt_formula + test cấu hình cờ.
- Caller llm_runner dùng chung bundle ở từng shot/lô/only_missing; director_two_pass dùng dp_common cache; OFF lọc chuỗi rỗng, ON luật đặt phần cache chung.
- Caller llm_io.store_motion_prompts + prompt_rewrite gọi on_prompt_saved, người sửa tay/viết lại vẫn nhận VÀNG nếu mất nền.
- Đề chuyên biệt viết lại prompt_rewrite chưa thêm luật ambient; kiểm sau lưu vẫn báo VÀNG, không tự sửa prompt. Đây là giới hạn, không mở rộng phạm vi.
- related_areas: step1/core_infra và callers step3/step4/autopilot/UI/knowledge; slow bắt buộc ở gộp. Không đổi đường gửi runner/gen hay API.
- §2b.5: không nới test/ngưỡng; path fixture theo __file__; OFF không đổi hành vi; không so bỏ dấu/nhãn thành nội dung; không sandbox/mạng;
  không gọi tốn tiền/chạm data sản xuất. areas khai fixture/test/knowledge/cờ, giữ version. Không đổi widget key/UI.

Bằng chứng: lượt đỏ 8 failed/46 passed (6 thiếu tính năng; 2 lỗi setup fixture/DP đã sửa trước code). Xanh 54 passed;
chốt cuối 62 passed cùng 3 file tests/test_ambient_motion.py tests/test_prompt_formula.py tests/test_prompts.py, tổng đúng 3 lượt pytest.
62 ca gồm dependency hai cờ, payload BYĐ/weather/time, không đỏ/chặn, phủ định/danh từ/biên từ, progressive fog, trời lặng/trong nhà.
git diff --check xanh. Widget smoke chạy tools.ui_v2_acceptance.measure_keys trên demo temp cho ui_v2 0/1; kết quả ở HANDOFF.
Chưa thử Claude/video thật; test chữ không chứng minh chất lượng nền. Cờ chưa bật. Chưa chạy cả bộ; root phải rà trước commit và test Windows trước gộp.

Rà caller trước commit phát hiện P2: phủ định cả câu làm VÀNG sai khi máy/người tĩnh nhưng nền chuyển động.
Hai regression `Static camera while fog drifts gently` / `She remains still as leaves sway` đỏ trước: 2 failed, 21 deselected.
Đã giới hạn phủ định vào cụm nền sau ranh giới mệnh đề; giữ `No fog drifts` và nền đứng yên là VÀNG.
Sau sửa: cùng 3 file trên xanh 64 passed (1,15 s). Vòng sửa thêm 2 lượt pytest; tổng phiên 5 lượt.
