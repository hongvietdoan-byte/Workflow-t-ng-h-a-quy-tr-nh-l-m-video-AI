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

## Thêm 01/10 (sau 4 nhánh song song) — chờ người dùng duyệt từng dòng
| # | Việc | Lệnh | Ước tính | Điều kiện |
|---|---|---|---|---|
| 7 | ✖ bỏ (người dùng 01/10) — S4.11 bản cuối 1080p từ bản mẫu `cgt-20260930185359-bkbcr` | `py tools/experiments/s411_s412_test.py --project 16 final` (nâng `CAP_USD` trong script lên ≈ 3,1) | ≈ 2,1 USD | bản mẫu hết hạn ~07/10 |
| 8 | S4.7 thử `seedance_subjects` trên 1 nhóm 3 người (Kelly/Kenta/Maxim đủ ảnh) | _chờ soạn_ (mở rộng `tools/experiments/s47_s410_test.py`) | ≈ 1 USD | sau khi người dùng xem 3 clip `D:/AI-Video-Output/2026-10-01_s4-7_s4-10/*_co-giong.mp4` |
| 9 | ✖ bỏ (người dùng 01/10) — S2.6 Seed Audio chạy lại (1 lượt còn trong trần) | `py tools/experiments/audio_s26_s115.py seed --variant 1 --why ...` rồi `check` | vài xu | sau khi người dùng tạo 1 lần trên web để đối chiếu |
