# Việc chạy trên Claude Code cloud (tài khoản credit $100) — 06/10/2026

Người dùng có một tài khoản **Cloud session credits $100** (hết hạn 05/11/2026, 14:59 GMT+7). File này chứa prompt tự đủ để dán vào phiên cloud ở **claude.ai/code** (repo `hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI`). Phiên chính ở máy `D:\AI-Video-Pipeline` rà + chạy cả bộ test (Windows) rồi mới gộp vào `main`.

## Cloud làm được / không làm được
- **Được:** code + test thuần trong git, tài liệu, chạy test liên quan trên Linux, commit + push nhánh riêng.
- **Không:** `data/`, `data/manifest.sqlite`, `dashboard.env`, khóa ClipAI / Claude API, Blender, PowerShell, Dashboard thật, dữ liệu `devsys/data` của máy chính. Không chạy gì tốn tiền API.
- Test chỉ chạy trên Windows (đường dẫn `D:\`, PowerShell) có thể bỏ qua/đỏ trên Linux → ghi rõ trong báo cáo, KHÔNG sửa test cho xanh trên Linux nếu làm hỏng trên Windows.

## Ngân sách credit — dừng cứng $90, không vượt 95 $ (hết credit = không commit/push được → mất việc)
| Credit đã dùng (của $100) | Làm gì | Hỏi người dùng số credit |
|---|---|---|
| < $60 | chạy bình thường, 1 việc/phiên | trước mỗi việc + mỗi ~30 lượt gọi |
| $60–80 | chỉ việc nhỏ hoặc tiếp việc đang dở; commit + push sau MỖI bước | mỗi ~20 lượt gọi |
| $80–85 | không mở bước mới lớn; làm bước nhỏ đang dở | **mỗi ~10–15 lượt gọi** |
| $85–90 | chỉ hoàn tất bước đang dở → commit, push, cập nhật `HANDOFF.md`, báo cáo | **mỗi ~5–10 lượt gọi** |
| **≥ $90** | **dừng cứng** (người dùng chọn 06/10 để luyện kiểm soát chặt) — không chạy thêm gì; TUYỆT ĐỐI không vượt 95 $ | — |

- Phiên cloud **không tự đọc được số credit** → người dùng xem ở trang credit và báo trong chat ("đã dùng $X"); phiên cloud hỏi người dùng số credit **trước khi bắt đầu mỗi việc** và **sau mỗi ~30 lượt gọi công cụ**.
- Ước chi mỗi việc (Opus, ước theo token, có thể lệch): việc vừa ≈ $8–15, việc lớn ≈ $15–25. Chưa chắc đủ → làm phần nhỏ trước.
- **Commit + `git push` sau MỖI commit** (không gom cuối phiên), `HANDOFF.md` ở gốc nhánh luôn ghi: đã xong / đang dở / bước kế. Hết credit giữa chừng vẫn còn việc trên GitHub để làm tiếp.
- Một phiên cloud = một việc. Không mở phiên con (Agent) trong cloud — tốn gấp đôi.

## Luật chung (dán kèm mọi prompt)
```
Luật dự án (bắt buộc):
- Trả lời/ghi chú tiếng Việt. Đọc CLAUDE.md + docs/CHUAN_XAY_DUNG.md trước (không im lặng khi thiếu đầu vào; "đã sửa" kèm bằng chứng chạy thật).
- Làm trên nhánh mới `cloud/<mã-việc>` tách từ main. KHÔNG push lên main, KHÔNG sửa TODO.md / trạng thái kế hoạch, KHÔNG tăng devsys/areas.json "version" (file mã mới vẫn phải khai vào areas.json).
- KHÔNG gọi API tốn tiền (Claude/ClipAI/TTS…) — chỉ mock. Không có data/ máy chính: dùng fixture trong tests/.
- Test ĐỎ TRƯỚC, XANH SAU cho từng mục; chỉ chạy test liên quan: `python -m pytest -q -p no:cacheprovider tests/<file>.py` (Linux dùng python3; PYTHONUTF8=1).
- Commit nhỏ, dòng cuối: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; `git push -u origin <nhánh>` NGAY sau mỗi commit; cập nhật HANDOFF.md (đã xong / đang dở / bước kế) mỗi commit; xóa HANDOFF.md ở commit cuối khi xong hẳn.
- Credit (dừng cứng $90): hỏi người dùng "đã dùng bao nhiêu $" trước khi bắt đầu, rồi mỗi ~30 lượt gọi (< $60) / ~20 ($60–80) / ~10–15 ($80–85) / ~5–10 ($85–90); từ $85 chỉ hoàn tất bước đang dở rồi commit + push + HANDOFF; ≥ $90 dừng hẳn, không vượt 95 $. Ghi số credit vào HANDOFF.md mỗi lần hỏi. Không mở phiên con (Agent).
- Tự kiểm trước bàn giao: test bị nới để che lỗi; đường dẫn tương đối / phụ thuộc thư mục đang chạy; chặn mới làm vỡ luồng tự động/hàng loạt; bật mặc định đổi hành vi; so chữ bỏ dấu khớp nhầm từ ngắn; tiêu đề/nhãn đọc nhầm thành nội dung; lời gọi tốn tiền chạy khi chưa có đồng ý.
- Kết thúc: báo cáo ≤ 25 dòng: nhánh, commit cuối, file sửa, test đỏ→xanh (tên), test bỏ qua vì Linux, rủi ro/việc mở.
```

---

## Việc 1 — S14.45 Bảng chấm hiệu quả quy trình (AI Dev System) · ≈ $10–15
```
Việc S14.45 của dự án (đọc dòng "S14.45 ·" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md và mục 2b của .claude/skills/vong-lam-viec-theo-plan/SKILL.md).
Mục tiêu: AI Dev System (devsys/ + tools/devsys_*.py + trang web devsys) ghi và hiển thị hiệu quả token của quy trình nhiều phiên.
1. Dữ liệu trong git: file `devsys/workflow_runs.json` (hoặc .jsonl) — mỗi dòng: mã việc (S14.x), ngày, chế độ tài khoản (goi | usd | cloud), mức rà (ky | nhe), token làm / rà / sửa (nghìn), số vòng sửa, số lỗi rà bắt (tổng + nặng), ghi chú. Lệnh `python -m devsys.workflow add …` để ghi (skill sẽ gọi sau mỗi nhánh gộp) + `list`.
2. Nhập lại từ kế hoạch: đọc các dòng "Số đo: …" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md (dạng "làm ≈ 233k + sửa ≈ 257k token, rà ≈ 138k (≈ 28 %), rà bắt 5 lỗi", "làm ≈ 252 nghìn token, rà ≈ 123 nghìn", "rà 0"…) → parser chịu được các biến thể (k / nghìn, có/không "sửa"); dòng không đọc được → liệt kê, KHÔNG im lặng bỏ.
3. Trang web devsys "Hiệu quả quy trình": bảng từng nhánh + tổng theo ngày/chế độ; so với 2 mốc ghi sẵn: mốc A 04–05/10 (7 nhánh, làm ≈ 2,0 triệu, rà ≈ 1,1 triệu ≈ 35 %, ≈ 443k/nhánh, rà bắt 1–3 lỗi/nhánh); mốc B 05–06/10 (rà kỹ ≈ 653k/nhánh, rà ≈ 20 %, sửa ≈ 48 %, 5,2 lỗi/nhánh; rà nhẹ ≈ 124k/nhánh). Chỉ số: token/nhánh (rà kỹ vs nhẹ), % rà, % sửa, token rà / lỗi bắt, số vòng sửa. Làm theo cách các trang devsys hiện có dựng (tìm trang "Hiệu quả vận hành" Đợt 6b làm mẫu).
4. Test: parser trên các dòng "Số đo" thật (chép vài dòng làm fixture), add/list, trang hiển thị (theo cách test trang devsys hiện có).
```

## Việc 2 — S14.24 Agent chấm bài học (CHẾ ĐỘ BÓNG) · ≈ $15–25
```
Việc S14.24 của dự án: Đợt 5 "Agent chấm bài học" — đọc mục "## Đợt 5 — Agent chấm bài học (ý 2)" trong docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md (≈ dòng 344–440: core/lesson_judge.py ~260 dòng, facts(), build_prompt(), normalize(), judge(), judge_all(), estimate(), MockJudge, rubric 6 tiêu chí, 8 van về người, chống trôi knowledge) và dòng "S14.24 ·" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md.
Làm ĐÚNG CHẾ ĐỘ BÓNG: chấm nhưng KHÔNG đổi bài học/knowledge nào, chỉ ghi kết quả để người xem; sau cờ mới TẮT mặc định (theo mẫu core/features.py). Lời gọi Claude thật phải đi qua sổ chi + ước tính trước (tìm llm_runner / spend_cap / STAGE_SETTINGS — khâu Claude mới cần max_tokens riêng trong STAGE_SETTINGS); trên cloud chỉ chạy MockJudge.
Lưu ý S14.46 (đang làm ở máy chính): bài học về tính năng đã bỏ (phông xanh / location_plates, layout_to_model, chain_previous_auto, setcheck_autofix, seedance_sample_mode) sẽ bị cất — van "chủ đề đã bỏ" để agent chấm coi là KHÔNG dùng; không đụng code lọc của S14.46 (core/lessons.py phần lọc) — chỉ đọc qua hàm công khai.
Test đỏ→xanh: normalize (enum, thiếu trường → báo), 8 van về người, estimate, MockJudge end-to-end, cờ tắt = không chạy.
```

## Việc 3 — S14.25 Đợt 6a Góp ý → mistakes · ≈ $8–15
```
Việc S14.25 phần Đợt 6a (Đợt 6b đã làm ở S14.10 — KHÔNG làm lại): đọc mục "### 6a. Feedback chảy vào `mistakes`" trong docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md (≈ dòng 443+) và dòng "S14.25 ·" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md.
Mục tiêu: góp ý người dùng (chấm ≤ 2/5, ghi chú từ chối…) chảy vào bảng `mistakes` qua cờ mới `feedback_to_mistakes` (TẮT mặc định), có khử trùng, có nguồn (source/ref_id/stage), không ghi khi cờ tắt. Không đụng code lọc chủ đề đã bỏ của S14.46.
Test đỏ→xanh: góp ý thấp → 1 dòng mistakes đúng stage; trùng → không ghi lại; cờ tắt → không ghi; góp ý tốt → không ghi.
```

---

## Sau khi phiên cloud xong (phiên chính ở máy chính)
1. `git fetch` → đọc báo cáo + `git diff main...cloud/<mã>`.
2. Rà theo mức (skill mục 2): S14.24 RÀ KỸ (đụng lời gọi Claude tốn tiền + knowledge); S14.45, S14.25 rà nhẹ trừ khi đụng tiền/dữ liệu.
3. Cả bộ test trên Windows → gộp `main` → tăng `devsys/areas.json` version một lần → push → pull ở `D:\AI-Video-Pipeline` → khởi động lại Dashboard / devsys.
4. Ghi số đo vào dòng việc (chế độ `cloud`, credit đã dùng) + `py -m devsys.workflow add …` (khi S14.45 đã gộp).
