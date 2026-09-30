# Lệnh tốn tiền chờ người dùng chạy (session chính)

> Người dùng 30/09: các việc tốn tiền đã duyệt, **người dùng tự chạy ở session chính**. Session phụ không ghi CSDL thật
> (quyền Claude Code chặn), chỉ chuẩn bị công cụ + ước tính. Chạy từ `D:\AI-Video-Pipeline` sau `git pull`.
> Mỗi lệnh có trần riêng trong công cụ; trần đợt thử chung: 74,50 USD (còn ≈ 12,58 ngày 30/09), Claude 9,80 (còn ≈ 1,70).
> Chạy xong: ghi kết quả vào `TODO.md` + dòng việc trong `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`, đánh dấu dòng dưới đây là ✅.

| # | Việc | Lệnh | Ước tính | Điều kiện |
|---|---|---|---|---|
| 1 | S5.5' vẽ lại 5 khung #13 theo render 3D (lần vẽ lại 1/2) | `py tools/experiments/place_refs_trial.py --project 13 redraw` rồi `... --project 13 measure` (0 USD) | ≈ 0,26 USD (trần riêng 1 USD, đã chi 0,31) | ✅ 30/09 17:28 — chi thật 0,26 (tổng 0,572); kết quả ở docs/THU_PLACE_RENDER_REFS_2026-09-30.md mục 7 |
| 2 | S7.1 nghiệm thu agent QC (cảnh 1–2 #8) | `py tools/experiments/qc_agent_eval.py --project 8 --scenes 1 2 --yes --max-usd 0.45` | ≈ 0,45 USD Claude (khóa cứng) | sau 07:00 01/10 (khóa API Anthropic mở lại) |
| 3 | S4.2 chạy thật 1 cảnh thoại khớp môi (c) | _chờ soạn_ | ≈ 2,5 USD | sau khi nhánh C3 (khung đầu chỉ gửi ảnh người có trong shot) lên main |
| 4 | S4.6 A/B cận (`closeup_start_frame`) | _chờ soạn_ (cần viết công cụ thử, miễn phí) | ≈ 1–2 USD | — |
| 5 | S4.7 / S4.10 / S4.11 / S4.12 / S2.6 / S1.15 | _chờ soạn từng việc_ (phần miễn phí làm trước: kiểm API, công cụ thử) | S4.10 ≈ 3–4, S4.12 ≈ 0,5, còn lại ước tính khi soạn | — |
| 6 | S0.14 T4 cờ `hero_takes` | bật `FEATURE_HERO_TAKES=1` trong `dashboard.env` cho lần chạy kế (không có lệnh riêng) | thêm ≈ 1 USD mỗi shot ⭐ Seedance 2.5 4–5 s | người dùng quyết khi bật |
