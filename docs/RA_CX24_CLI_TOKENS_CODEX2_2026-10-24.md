# CX24-CLI-TOKENS — báo cáo Codex 2

**Nhánh:** `codex/v31-cli-tokens`  
**Phạm vi:** `core/llm_runner.py`, cờ `cli_token_budget`, test CLI giả và đăng ký khu vực. Không gọi Claude thật, không mở CSDL/dữ liệu dự án thật, không dùng API trả phí.

## Kết quả

- Thêm cờ `cli_token_budget`, mặc định **TẮT**, chưa xác minh chất lượng thật. Khi TẮT, danh sách tham số lệnh giữ nguyên hoàn toàn như trước. Khi BẬT, chỉ các khâu có hồ sơ đo (`chat_prompt`, `qc`, `video`, `change_review`, `director_rewrite`) nhận `--safe-mode`, `--max-turns` và danh sách công cụ giới hạn; khâu chưa đo giữ nguyên hành vi cũ.
- Một bảng `CLI_TOKEN_STAGE_POLICY` là nguồn chung cho số lượt, công cụ, model kế thừa và mức token trung bình theo khâu. Có ảnh thì chỉ cho phép công cụ `Read` để mở ảnh. Chưa đổi model theo khâu: số liệu hiện có không chứng minh chất lượng khi đổi model, nên giữ nguyên model đã cấu hình cho đến khi có đối chiếu chất lượng thật được duyệt.
- Parser CLI ghi riêng `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens` vào `llm_calls`. Ngưỡng cảnh báo mặc định là 200.000 token đầu vào, chỉnh bằng `CLAUDE_CLI_TOKEN_WARN_INPUT`; token đầu vào tính cả raw input và hai loại cache. Chỉ thêm cảnh báo `diag_events`, không chặn lời gọi.
- Ước tính trước khi chạy dùng cùng bảng trung bình theo khâu cộng ước lượng prompt nhìn thấy theo heuristic hiện có; không giả vờ đếm chính xác system prompt, cấu hình ẩn hay token ảnh.
- Đăng ký cờ ở 12 khu vực có chứa runner hoặc caller liên quan trong `devsys/areas.json`; `version` giữ nguyên **92**.

## Gốc vấn đề

Số đo 24/10 #34 được bàn giao trong đề bài: 27 lời gọi, tổng xấp xỉ **4,738 triệu** token vào; `chat_prompt` 2,51 triệu/8 lượt, QC 1,12 triệu/3, video 0,56 triệu/5, `change_review` 0,46 triệu/10, `director_rewrite` 88 nghìn. Hai lời gọi lớn nhất được nêu là 1,62 triệu và 920 nghìn token, chiếm khoảng **53,6%** tổng số đo.

Rà code cho thấy `ClaudeCliClient` chạy từ thư mục tạm và đã loại dấu hiệu phiên Claude cha cùng biến khóa API trả phí; tuy nhiên lệnh cũ không tắt tùy biến CLI của tài khoản như plugin, hook, MCP, skill, bộ nhớ hoặc cấu hình CLAUDE.md được CLI tự nạp. Đây là nguồn nền lặp lại **có thể có**, không phải nguyên nhân đã chứng minh. Lời gọi nhiều lượt cũng có thể lặp ngữ cảnh/kết quả công cụ. Không đọc payload/prompt hoặc CSDL thật nên chưa thể quy chính xác 1,62 triệu và 920 nghìn token cho nguồn nào.

Một lỗi đo đã xác nhận trong code: parser trước đây cộng cache read/write vào `input_tokens` rồi bỏ trống cột cache của ledger. Vì vậy `cache_read/cache_write NULL` trong bảng cũ không chứng minh CLI không dùng cache; nó chỉ cho thấy ứng dụng chưa tách và lưu các trường đó. Bản sửa lưu đúng bốn trường độc lập.

## Ước lượng và giới hạn

Từ mức trung bình quan sát được, nếu trung bình `chat_prompt` và QC cùng giảm về ngưỡng cảnh báo 200 nghìn/lượt thì phần giảm **lý thuyết** khoảng 1,43 triệu token, tương đương **30,2%** tổng mẫu. Nếu chỉ quy mục tiêu 200 nghìn cho hai lượt ngoại lệ 1,62 triệu và 920 nghìn, mức giảm lý thuyết là 2,14 triệu, khoảng **45,2%**. Đây là kịch bản mục tiêu để so sánh, không phải dự báo đã kiểm chứng: cờ không đặt trần token đầu vào, còn `--max-turns` chỉ giới hạn số lượt agentic. Mức giảm thực tế hiện **chưa đo**; cần một lời gọi thật được phiên chính duyệt rồi so trước/sau.

Không bật `CLAUDE_CODE_SIMPLE=1`: tài liệu Claude Code nói chế độ này không đọc OAuth/keychain và cần `ANTHROPIC_API_KEY` hoặc `apiKeyHelper`, trái yêu cầu dùng đăng nhập CLI, không API trả phí. `--safe-mode` được chọn cho thử nghiệm có cờ vì tắt tùy biến nhưng giữ xác thực CLI bình thường. Tài liệu cũng phân biệt `--tools` (giới hạn công cụ hiện có) với `--allowedTools` (chỉ bỏ hỏi quyền); ảnh cần cả `--tools Read` và `--allowedTools Read` để vẫn đọc được ảnh mà không mở thêm công cụ.

## Rà caller và kiểm thử

Đã đối chiếu stage tags của `core/chat_prompt.py`, `core/change_review.py`, `core/prompt_rewrite.py` và các khâu `qc`/`video` trong `core/claude_tasks.py`; thay đổi nằm tại adapter chung, không sửa caller. Stage chưa có hồ sơ giữ nguyên argv ngay cả khi cờ bật. Các phép thử chỉ dùng fake CLI, ảnh giả và SQLite tạm.

- Test đỏ trước sửa: 6 kiểm thử mới cùng thất bại như kỳ vọng.
- Test xanh sau sửa: `tests/test_llm_runner.py` + `tests/test_llm_ledger.py` + `tests/test_feature_settings.py` + `tests/test_fix_flags.py` + `tests/test_devsys_pipeline_maps.py`: **146 passed**.
- `py tools/related_areas.py core/llm_runner.py` đã chạy để liệt kê caller/khu vực liên quan; rà lại thủ công các stage nêu trên và consumer cache ở `core/cost.py`.
- `git diff --check` không báo lỗi nội dung (chỉ nhắc quy tắc CRLF của Git trên `devsys/areas.json`).

## Bước cần phiên chính

Sau khi nhận nhánh, phiên chính xem xét một lời gọi có kiểm soát và duyệt trước khi bật cờ hoặc đánh giá đổi model. Không chạy ca thật trong task Codex 2 này.
