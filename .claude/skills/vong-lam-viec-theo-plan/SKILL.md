---
name: vong-lam-viec-theo-plan
description: Vòng làm việc theo kế hoạch dài của dự án AI Video Pipeline qua nhiều phiên — đầu phiên đọc TODO/đợt ưu tiên, phiên chính chỉ điều phối các phiên con, đo context + hạn mức gói, dừng ở điểm nghỉ (commit, ghi TODO, push, báo người dùng). Dùng khi người dùng nói "tiếp tục", "làm tiếp S14", "đọc TODO làm tiếp theo plan", hoặc bắt đầu build một đợt nhiều nhánh.
---

# Vòng làm việc theo plan (nhiều phiên, nhiều tài khoản)

Mục tiêu: làm hết một đợt dài mà không để phiên chính đầy context (tự nén làm mất chi tiết, lệch lối tư duy) và không bị cắt giữa chừng vì hạn mức gói. Trạng thái thật luôn nằm trong file trên `main`, không nằm trong trí nhớ phiên. Trả lời người dùng bằng **tiếng Việt**.

## 1. Đầu phiên
1. `git pull` (worktree: `git fetch origin && git merge --ff-only origin/main`).
2. Đọc `CLAUDE.md` và `TODO.md`: khối mới nhất ở đầu và mục "Việc phải làm lại MỖI LẦN".
3. Đọc câu trả lời người dùng cho việc ⏸: `PYTHONUTF8=1 py -m devsys.answers list --pending` (người dùng trả lời trên web 8502 trang 📋, lưu ở `devsys/data/user_answers.json` của bản chính, không vào git). Mỗi câu: áp dụng (đổi trạng thái việc trong kế hoạch, ghi chú/commit) rồi `py -m devsys.answers applied <mã> "ghi chú · mã commit"`; câu chưa rõ thì hỏi lại người dùng. File hỏng → lệnh báo lỗi, báo người dùng, không tự xóa.
4. Tìm đợt đang làm: dòng `> Đợt ưu tiên: Sxx` trong `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`, hoặc chạy `PYTHONUTF8=1 py tools/plan_progress.py`. Việc kế là việc ⬜ đầu tiên. Bỏ qua việc ⏸ chưa có câu trả lời.
5. Đọc file kế hoạch chi tiết của đợt mà tiêu đề đợt trỏ tới. Chỉ đọc đoạn liên quan (`grep` hoặc đọc theo khoảng dòng), không đọc cả file lớn. **Mở lại code và đối chiếu số dòng** trước khi sửa, vì số dòng ghi trong kế hoạch có thể đã lệch.
6. Đo ngưỡng lần đầu (mục 3).

## 2. Làm việc
- **Phiên chính chỉ điều phối.** Không tự sửa code của nhánh (ngoại lệ: lỗi nhỏ 1–3 dòng, mục 2b.4). Test chỉ lấy dòng cuối (`-q`, `tail`).
- **Mỗi nhánh giao một phiên con** (`Agent`, `isolation: worktree`, chạy nền). Chạy **tối đa 2** cùng lúc. Prompt phải tự đủ:
  - việc cần làm + file:dòng + hàm nên tái dùng;
  - test cần **đỏ trước, xanh sau**;
  - luật `docs/CHUAN_XAY_DUNG.md` + nguyên tắc của kế hoạch;
  - **không sửa `TODO.md`, không push**; file mã mới phải khai vào `devsys/areas.json` nhưng **không tăng `version`**;
  - **commit nhỏ thường xuyên** trên nhánh của mình và ghi `HANDOFF.md` ở gốc worktree (đã xong / đang dở / bước kế), để nếu bị cắt thì phiên con mới làm tiếp từ commit cuối;
  - trong nhánh chỉ chạy test liên quan;
  - **báo cáo ≤ 30 dòng**: tên nhánh, file đã sửa, test đỏ→xanh (tên), mã commit, rủi ro/việc mở. Không dán diff hay log.
- **Mức rà (người dùng duyệt 05/10):** RÀ KỸ (phiên con rà độc lập riêng) cho việc đụng TIỀN, DỮ LIỆU, QUYỀN, vòng đời job, migration CSDL. RÀ NHẸ (không mở phiên rà; phiên chính đọc `git diff --stat` + đoạn đổi chính + test xanh) cho tài liệu, nhãn, prompt/knowledge sau cờ TẮT, CSS/giao diện không đổi luồng. Gom việc nhỏ cùng vùng file vào MỘT phiên con. Phiên rà chỉ đọc phần thay đổi + chỗ gọi tới, không đọc lại cả kế hoạch. **Ghi số đo mỗi nhánh** vào dòng việc S14.x: token phiên làm / phiên rà (từ thông báo hoàn tất) + số lỗi phiên rà bắt được — để báo người dùng hiệu quả quy trình (mốc trước khi tối ưu: 7 nhánh S14 ngày 04–05/10, làm ≈ 2,0 triệu token, rà ≈ 1,1 triệu ≈ 35 %, rà bắt 1–3 lỗi/nhánh, có lỗi tiền).
- **Rà độc lập trước khi gộp:** một phiên con mới (context sạch, chỉ đọc) đọc `git diff main...<nhánh>`, đối chiếu kế hoạch, tìm lỗi. Còn lỗi thì giao sửa, xong mới gộp.
- **Gộp:** theo bảng xung đột file chung của kế hoạch; tăng `devsys/areas.json` `version` **một lần** ở nhánh tích hợp; chạy **cả bộ test** (`py -m pytest -q -p no:cacheprovider`, ≈ 12 phút, chạy nền) → `git push origin HEAD:main` → `git pull --ff-only` ở `D:\AI-Video-Pipeline` → khởi động lại Dashboard nếu đổi code `dashboard/` hoặc `core/` (`tools/stop_dashboard.ps1` + `tools/launch_dashboard.ps1`).
- **Ghi trạng thái ra file sau MỖI nhánh gộp xong:** đổi trạng thái việc trong `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` (✅ + mã commit + bằng chứng) → `PYTHONUTF8=1 py tools/plan_progress.py --write` → cập nhật `TODO.md` → commit (dòng `Co-Authored-By` theo cấu hình session) → push.
- **Tiền:** việc tốn tiền (ClipAI, Deepix, Kling, Claude API, TTS…) **không tự chạy**. Liệt kê trần từng việc và hỏi người dùng trước. Mọi lời gọi tốn tiền phải qua sổ chi và có ước tính trước.

## 2b. Hạn chế phiên con (người dùng duyệt 06/10)
Số đo 05–06/10 (5 nhánh rà kỹ): rà chỉ còn ≈ 20 % tổng và bắt ≈ 5 lỗi/nhánh, nhưng **vòng sửa ≈ 48 % tổng**: đánh thức lại phiên làm cũ phải nạp lại TOÀN BỘ context của nó mỗi lượt gọi (vd 8 lượt gọi tốn 287k vì context ≈ 280k), còn phiên mới phạm vi hẹp chỉ ≈ 80–100k (U5: 14 lượt 86k). Mốc so: 04–05/10 ≈ 443k/nhánh; 05–06/10 ≈ 653k/nhánh rà kỹ, ≈ 124k/nhánh rà nhẹ.
1. **Mỗi nhánh tối đa 3 phiên:** 1 làm, 1 rà (chỉ khi RÀ KỸ), 1 vòng sửa. **Gom mọi việc sửa vào MỘT vòng**: chờ phiên rà xong mới giao, không giao lắt nhắt (lỗi test cả bộ tìm thấy trong lúc chờ → gom vào cùng vòng).
2. **Chọn ai sửa theo context đang có** (xem `subagent_tokens` ở thông báo hoàn tất):
   - Ưu tiên **đánh thức chính phiên RÀ** để sửa trong worktree của nhánh (context thường 110–150k, đã đọc đúng diff + chỗ gọi). Phiên chính đọc `git diff` phần sửa trước khi gộp (thay cho rà độc lập phần sửa).
   - Phiên LÀM còn nhỏ (< ~150k) thì đánh thức nó.
   - Cả hai lớn → **phiên sửa MỚI**, chỉ đưa danh sách lỗi kèm `file:dòng` + cách sửa phiên rà ghi; dặn "chỉ đọc các chỗ này".
3. **Phiên rà ghi luôn cách sửa cụ thể** cho từng lỗi (`file:dòng` + thay đổi đề xuất + test chứng minh) để bên sửa không phải dò lại.
4. **Lỗi nhỏ (1–3 dòng) phiên chính tự sửa** (ngoại lệ của "phiên chính chỉ điều phối"), chỉ khi context phiên chính < ~50 %; vẫn có test + cả bộ test trước khi gộp.
5. **Gom việc nhỏ cùng vùng file vào một phiên**, và **phiên làm TỰ KIỂM trước khi bàn giao** theo các loại lỗi phiên rà hay bắt (đưa danh sách này vào prompt phiên làm): test bị nới để che lỗi; đường dẫn tương đối / phụ thuộc thư mục đang chạy (`data/…` từ worktree); chặn/kiểm mới làm vỡ luồng tự động hoặc hàng loạt (tải lô, tự đồng bộ, autopilot); bật mặc định đổi hành vi người không dùng tính năng; so chữ BỎ DẤU khớp nhầm từ ngắn; vùng cách ly (sandbox) chưa chặn mạng; tiêu đề/nhãn bị đọc nhầm là nội dung; lời gọi tốn tiền chạy khi người dùng chưa bấm đồng ý.
6. Xếp RÀ NHẸ khi thay đổi nằm sau cờ đang TẮT và có so prompt/kết quả trước–sau giống hệt (như S14.9).

## 3. Đo ngưỡng
Đo **trước MỌI lần cho phiên con chạy** — mở phiên mới HOẶC đánh thức phiên cũ (SendMessage) — và sau mỗi nhánh gộp. Bài học 05/10: chỉ đo khi phiên con báo về là quá thưa; một phiên con sửa + chạy cả bộ test tiêu 15–25 % hạn mức 5 giờ, hai phiên đánh thức liên tiếp không đo đã đẩy từ ~65 % lên 100 % và bị cắt giữa chừng. Phiên rà KHÔNG chạy cả bộ test khi phiên làm đã chạy, trừ khi phải thử bản gộp với nhánh khác.
- **Desktop (tab Code):** `mcp__ccd_session_mgmt__get_usage` (session `self`). Tool bị hoãn thì nạp bằng `ToolSearch select:mcp__ccd_session_mgmt__get_usage`. Xem `context.percentUsed` và `plan.windows` (5 giờ, tuần).
- **Dự phòng khi không có tool đó** (Claude Code dòng lệnh, môi trường khác): nhờ người dùng gõ `/context` (và `/usage` nếu có) rồi đọc số họ dán. Không có số thì coi như đã gần ngưỡng sau khoảng 3 nhánh lớn và dừng ở điểm nghỉ.

**Hai chế độ tài khoản (người dùng dùng 2 tài khoản, 06/10).** Đầu phiên gọi `get_usage` rồi chọn chế độ, ghi chế độ vào khối bàn giao TODO:
- **Chế độ GÓI** — `plan.windows` có "5-hour limit" / "Weekly": áp bảng ngưỡng gói bên dưới.
- **Chế độ $** — `plan.windows` rỗng / `status` not_applicable, chỉ có `extraUsage` (spent / monthlyLimit, USD): bỏ qua ngưỡng 5 giờ/tuần, áp bảng ngưỡng $ bên dưới; **trước khi mở mỗi phiên con báo người dùng số USD còn lại**; mỗi phiên con ≈ 1–6 USD (ước theo token: làm ≈ 150–300k, rà ≈ 100–150k, sửa mới ≈ 80–120k). Ở chế độ $ mọi token là tiền thật → áp mục 2b chặt hơn: ưu tiên RÀ NHẸ khi đủ điều kiện, phiên chính tự sửa lỗi nhỏ, không mở phiên rà cho việc chỉ có tài liệu.
- Không đọc được cả hai → dự phòng ở trên (nhờ người dùng `/usage`).
- **Chế độ CLOUD** (phiên ở claude.ai/code dùng *Cloud session credits*, vd tài khoản $100 hết hạn 05/11): không đọc được credit bằng công cụ → hỏi người dùng "đã dùng $X" trước mỗi việc và sau mỗi ~30 lượt gọi; < $60 bình thường (hỏi mỗi ~30 lượt), $60–80 chỉ việc nhỏ (~20 lượt), $80–85 không mở bước lớn (~10–15 lượt), $85–90 chỉ hoàn tất bước dở rồi commit + push + HANDOFF (~5–10 lượt), **≥ $90 dừng cứng (người dùng chọn 06/10 để luyện kiểm soát chặt) — không vượt 95 $ vì hết credit thì không commit/push được**; push ngay sau MỖI commit; không mở phiên con trong cloud; chỉ việc thuần code/test (không có `data/`, khóa API, Windows). Prompt sẵn + luật: `docs/CLOUD_TASKS.md`.

**Ngưỡng chế độ $** (`extraUsage.percentUsed`):

| Chỉ số | Hành động |
|---|---|
| Context phiên chính **65–75 %** | điểm nghỉ |
| $ **≥ 80 %** | chỉ cho **1** phiên con chạy cùng lúc; báo USD còn lại mỗi lần |
| $ **≥ 85 %** | điểm nghỉ (trần cứng) — TUYỆT ĐỐI tránh vượt 90–95 % (người dùng: đoạn này % tăng rất nhanh) |

**Ngưỡng chế độ GÓI:**

| Chỉ số | Hành động |
|---|---|
| Context phiên chính **65–75 %** | điểm nghỉ |
| Hạn mức 5 giờ **90–95 %** hoặc tuần **≥ 95 %** (người dùng 06/10: dùng 5 giờ tới 90–95 %; tuần nâng 05/10) | điểm nghỉ — **TRÁNH VƯỢT 95 %**: đã ≥ 90 % thì không mở/đánh thức phiên con nào nữa, chỉ gộp phần đã xong |
| Hạn mức 5 giờ **≥ 60 %** | chỉ cho **1** phiên con chạy cùng lúc |
| Hạn mức 5 giờ **70–90 %** | chỉ cho chạy **việc NHỎ** (một phiên, phạm vi chặt, ≈ ≤ 30 lượt gọi công cụ / ≈ ≤ 100k token — ước mỗi việc nhỏ tốn ≈ 3–6 % hạn mức 5 giờ); trước khi mở ước xem có vượt 90–95 % không, có nguy cơ thì KHÔNG mở; không mở việc lớn, không đánh thức phiên có context lớn |
| Hạn mức tuần thấp mà còn nhiều việc | làm theo thứ tự giá trị (lỗ tiền, mất dữ liệu trước; giao diện, dọn dẹp sau) |

## 4. Điểm nghỉ
**Hai loại dừng, đừng lẫn:**
- **Dừng vì hạn mức gói** (5 giờ 90–95 % / tuần ≥ 95 %; tránh vượt 95 %), context còn thấp → KHÔNG cần `/clear`. Làm bước 1–4 bên dưới, rồi đặt lịch `CronCreate` một lần (vài phút sau giờ hạn mức đặt lại, lấy từ `resetsAt`) để tự làm tiếp TRONG CÙNG phiên, và báo người dùng giờ chạy lại.
- **Dừng vì context** (65–75 %) → làm bước 1–5: người dùng `/clear` rồi gõ "tiếp tục".

1. Chờ mọi phiên con xong (không bỏ dở giữa chừng).
2. Gộp các nhánh đã xanh và đã rà. Nhánh dở thì để nguyên trên nhánh, kèm `HANDOFF.md`.
3. Cập nhật kế hoạch + `plan_progress --write` + `TODO.md`, ghi rõ **bước kế + file nguồn + nhánh dở (tên, commit cuối)**. Commit, push, pull ở `D:\AI-Video-Pipeline`.
4. Báo người dùng: đã xong gì (mã commit), còn gì, các chỉ số hiện tại, câu để gõ tiếp ("tiếp tục Sxx").
5. **Không tự xóa phiên.** Remote Control đang bật thì ứng dụng từ chối `clear_session`. Người dùng gõ `/clear` rồi "tiếp tục". Chỉ dùng `clear_session("self")` khi người dùng yêu cầu rõ trong chính lượt đó.

## 5. Luôn nhớ
- **Báo về điện thoại khi cần người dùng quyết** (người dùng yêu cầu 04/10): gọi `PushNotification` (nạp bằng `ToolSearch select:PushNotification`, `status: "proactive"`) khi phải chờ người dùng — câu hỏi chặn việc, duyệt việc tốn tiền, đến điểm nghỉ, lỗi không tự xử lý được. Một dòng < 200 ký tự, mở đầu bằng việc cần làm. KHÔNG gửi cho tiến độ thường.
- **Người dùng trả lời một việc ⏸ trong chat** → ghi về cùng chỗ với web: `PYTHONUTF8=1 py -m devsys.answers add <mã> "…" --source chat` (thêm `--choice Duyệt|Không|"Để sau"` nếu rõ). Áp dụng xong → `py -m devsys.answers applied <mã> "ghi chú · mã commit"`. Câu trả lời không tự đổi trạng thái việc: phiên Claude sửa kế hoạch.
- Không im lặng khi thiếu đầu vào; "đã sửa" phải kèm bằng chứng chạy thật (tên test, số liệu).
- Không tự chạy tiếp sang việc người dùng chưa duyệt. Việc nằm trong đợt đã duyệt thì làm theo thứ tự.
- Ở thư mục gốc dùng `py`, không dùng `python`; console cần `PYTHONUTF8=1`.
- `data/`, `dashboard.env`, `data/manifest.sqlite` chỉ có ở máy chính `D:\AI-Video-Pipeline`. Lệnh cần dữ liệu thật chạy ở đó, không chạy trong worktree.
