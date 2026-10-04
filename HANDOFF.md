# HANDOFF — S14.16 chính sách tiền mới (nhánh `s14-16-money-policy`)

Nguồn: `docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md` mục 6c. 0 USD, không gọi API thật. Không push, không merge main, không sửa TODO.md.

## Đã xong (cả 8 việc của prompt)
1. Trần → CẢNH BÁO: `core/money_policy.py` (mới: hằng số WARN_AT 1.0 / DANGER_AT 1.5 / SAFETY_FACTOR 1.5, `estimate`, `warning_text`,
   `note` → diag mã `money_warning`, chống ngập 10 phút/khóa). `budget.check_*`/`check_llm` chỉ còn chặn khi hết tiền (halted);
   cảnh báo ở `budget.warn_image/warn_video/warn_audio/warn_llm`. `project_budget.check` luôn None (giữ API), cảnh báo ở
   `project_budget.warning`; thêm `planned`/`set_planned`. `spend_gate`: `slot.over` = chặn thật, `slot.warning(s)` = cảnh báo, `assess()`.
   Runner `_over_budget` dùng `spend_gate.assess`. `llm_runner`: 3 khóa (một lời gọi / spend_cap / Claude+dự án) → cảnh báo;
   chỉ chặn `out_of_credit` và sổ chi không ghi được (mã mới `ledger`). `music.audio_refusal`, `qc_team` → cảnh báo.
2. Còn chặn kèm số liệu: hết tiền (`budget.halted` thêm đã chi/mức dự tính, "⛔ CHẶN … cách mở"), dự án tạm dừng (`spend_gate._paused_text`),
   trần job/ngày (`autopilot._daily_note`: số lượt, trần, đã chi hôm nay).
3. `_stop_if_claude_blocked` bỏ nhánh `budget`; dừng khi auth/config, hết hạn mức gói, out_of_credit, ledger. Các tuple mã ở qc_agent/qc_team/claude_tasks đổi theo.
4. `pipeline.AUTO_REGEN_LIMIT = {"image_gen": 3, "video_gen": 2}` (một nơi, thay AUTO_RETRY_CAP); `retry_count` = số lần MÁY tạo từ lần người
   dùng gần nhất. Người dùng (reject "user", `retry(by_user=True)`, `reopen_approved`, `regenerate_video`) không giới hạn, đặt lại 0.
   Tự động: `retry()` mặc định, reject "ai_agent", `reopen_approved(auto=True)`, `regenerate_video(auto=True)` (plate fallback),
   `redo_from_set_check(auto=True)` (setcheck autofix). Đủ giới hạn → escalate + diag `auto_regen_limit` + 📥 "Cần bạn quyết — đã tự gen lại N lần".
   Mọi nút `p.retry` trong dashboard truyền `by_user=True` (có test quét). autopilot SHOT_SENDS → `_shot_cap(kind)` = 1 + giới hạn.
5. Ước tính dư: `money_policy.estimate` (giá cao nhất cùng model, không có thì cùng loại × 1.5; unverified × 1.25); token Claude thiếu giá cũng vậy.
6. `money_reset.set_planned(conn, owner, "trial"|"claude"|"project", usd, reason, project_id=)` — CHƯA chạy trên CSDL thật.
7. UI v2: `shell_parts.money_meter/money_flag` (vàng/đỏ theo mức dự tính), thẻ 💵 dùng chúng; nhãn giá "(ước tính)"; 📥 một dòng "Cảnh báo tiền".
8. `docs/CHUAN_XAY_DUNG.md` mục 6 + Luật chi phí + bảng kế thừa.

## Test
- Mới: `tests/test_money_policy.py` (31 test, đỏ trước → xanh).
- 630 test liên quan xanh (danh sách lệnh trong báo cáo phiên).

## Bước kế / còn dở
- Không có việc dở trong prompt. Việc sau: UI Gói K gọi `money_reset.set_planned` (reset thật), rà các cảnh báo trên dự án thử 30 s.
- Rủi ro cần rà: trần số job theo dự án của autopilot (`_job_caps`/BUDGET_NOTE) vẫn chặn — không phải tiền, chưa đổi; cổng chờ duyệt
  ngân sách dự án (`gate_reason`) vẫn giữ; `tools/pilot_run.py` SHOT_SENDS=3 chưa đổi.
