# Giao việc: tổng hợp, thống kê và rút kinh nghiệm từ 3 lượt làm Khủng Long Đỏ (#22)

Người dùng yêu cầu 08/10/2026 và muốn **làm ở tài khoản khác**, không làm trong phiên này. Phiên Claude hết hạn mức ($, ≈ 91 %) nên chỉ làm phần việc rẻ, cần ngay: **chụp trạng thái dữ liệu** (xem mục 3) và soạn bản giao việc này. Mọi con số dưới đây là số đã có, chưa phân tích sâu.

## 1. Mục tiêu (nguyên văn ý người dùng)
Một bản **thống kê + so sánh** để biết:
1. Đã làm những gì ở từng lượt: **2 lượt gen thử** (rẻ) và **1 lượt chất lượng cao**.
2. So sánh nội dung giữa các lượt: **khâu nào làm tốt, khâu nào sai**.
3. Rút kinh nghiệm từ chỗ làm tốt và chỗ làm sai.
4. **Học được gì và cập nhật được gì cho TỪNG VAI trong Dashboard.**

## 2. Ba lượt là gì (xác nhận lại trước khi làm)
| Lượt | Nhãn | Video | Ghi chú |
|---|---|---|---|
| 1 — thử | `ban_thu_1` | `D:\AI-Video-Output\2026-10-07_du-an-22\KhungLongDo_ban_thu_re_2026-10-07.mp4` (51,6 s) | Seedream 5 Pro, Seedance 2.0 Fast 720p (Thử rẻ), thoại Seedance 2.5 |
| 2 — thử | `ban_thu_2` | `...\KhungLongDo_ban_thu_re_v2.mp4` (52,6 s) | GPT Image 2.5 Sunburst, vẫn Fast |
| 3 — "chất lượng cao" | `chat_luong_cao` | `...\FINAL_VIDEO_khung_long_do_2026-10-07.mp4` (52,6 s), người dùng 08/10 xác nhận **đạt** | GPT Image 2.5; **chỉ 3 cảnh nhảy (254–256) làm bằng Seedance 2.5 720p**, các cảnh 1, 2, 4, 6 vẫn Fast, cảnh 3, 5 là 2.5 từ lượt trước. Nên ghi rõ "lượt cao" = **một phần**, đừng so như thể cả phim đều chất lượng cao. |

Bảng so sánh đã dựng sẵn ở `docs/kld_runs/README.md` (cột "Chất lượng cao" còn trống). Mốc đầu lượt 3 ≈ CSDL `data/backup/manifest.before_kld_round3_2026-10-07.sqlite`.

## 3. Dữ liệu đã chụp / nơi lấy dữ liệu
- **Ảnh chụp trạng thái 3 lượt** (spec từng shot, prompt ảnh, motion prompt, model, số lượt gen, thiết lập dựng): `docs/kld_runs/ban_thu_1`, `ban_thu_2`, **`chat_luong_cao`** (`.json` + `.md`, chụp 08/10 bằng `py tools/project_snapshot.py <db> 22 <nhãn> docs/kld_runs --git <commit>` từ bản sao `data/backup/manifest.snapshot_chat_luong_cao_20261008.sqlite`; commit chụp `5839f37`).
- **CSDL thật (máy chính `D:\AI-Video-Pipeline`, ngoài git)**: bảng `jobs`, `job_events`, `qc_results`, `review_log`, `diag_events`, `usage_events` (cột `stage`, `model`, `tier`, `quantity`, `at`, `job_id`, `project_id`), `lessons`, `lesson_reviews`, `experience_cases`, `kho_review_log`. Chia lượt theo `created_at` / `at` và theo các bản backup `data/backup/manifest.before_kld_*` (liệt kê trong `docs/BAN_GIAO_2026-10-07_KHUNG_LONG_DO_PHIEN_CLAUDE.md` mục 4).
- **Tài liệu**: `docs/DU_AN_KHUNG_LONG_DO_2026-10-06.md`, `docs/RA_KLD_PLACE_REFS_CODEX_2026-10-07.md`, `docs/RA_KLD_QUALITY_CODEX_2026-10-07.md`, `docs/BAN_GIAO_2026-10-07_KHUNG_LONG_DO_PHIEN_CLAUDE.md`, `.claude-memory/projects/ai-video-pipeline.md` (bài học bản thử 1/2 và bài học 07/10), memory cá nhân `feedback_kld_preview_review_0710`, `feedback_scene_location_change_checklist`, `feedback_confirm_before_paid_and_dont_assume`.
- **Tệp xem**: `D:\AI-Video-Output\2026-10-07_du-an-22\` và `...\kiem_thu_phong_AI\` (khung hình, góc render, lưới 3 giây).
- **Số tổng đã biết (dự án #22, lúc 08/10):** ảnh: 9 duyệt / 29 loại / 11 hủy; video: 9 duyệt / 25 loại / 11 hủy. Theo ngày: 06/10 ảnh 28, video 13; 07/10 ảnh 21, video 32. `usage_events`: 139 (06/10) và 212 (07/10). Ngân sách đợt thử đã chi 55,82 / 74,50 USD; Claude API ≈ 4,54 USD.

## 4. Nội dung báo cáo cần làm
**A. Thống kê từng lượt (chỉ đọc dữ liệu, 0 USD)**: số ảnh/clip gen, số bị loại, số gen lại, lý do loại (QC / người dùng / lỗi nhà cung cấp / gửi nhầm), tiền theo khâu và theo model (tính từ `usage_events`, đối chiếu sổ chi), thời gian từ bắt đầu đến video giao, số cảnh báo `diag_events` theo loại, điểm QC trung bình theo khâu. Tách **tiền lãng phí** (ảnh/clip không dùng) theo lý do.

**B. So sánh theo khâu (bảng: lượt 1 / lượt 2 / lượt 3 + nhận xét + bằng chứng job/tệp + nguyên nhân gốc)**:
1. Ý tưởng, kịch bản, Biên kịch (thoại: cứng → tự nhiên, tên thật FF).
2. Bible / hồ sơ nhân vật / Kho tài nguyên (trang phục trên giường, tóc Kelly lẫn bạc từ ảnh trang phục, khẩu trang).
3. Đạo diễn / kế hoạch shot, `director_rewrite`.
4. Nền 3D (plates) và chỗ đứng: nền phòng tầng 2 (cửa ngoài trời sai), tháp đoạn nhảy đổi dần, chân cầu thang, khóa nền, ảnh toàn cảnh cùng hướng.
5. Ảnh khung đầu (Deepix; Seedream vs GPT Image), QC ảnh, `place_match`.
6. Motion prompt và Quay phim (push-in, vòng cung, START LOCK, camera tĩnh).
7. Gen video (Fast 720p vs 2.5 720p; chế độ chỉ-ảnh-tham-chiếu; chuỗi nối cảnh `start_from_prev_clip`; tự gen lại).
8. Thoại, TTS, khớp môi (tương quan 0,14/0,45 → 0,03/0,44).
9. Nhạc, âm thanh, SFX, hậu kỳ (chớp trắng, rung, nhún theo nhịp).
10. Dựng (Editor): nối clip, cắt/hold, lỗi lặp cảnh do tệp phụ trong `videos/`, đề xuất `trim_start`.
11. QC video, `clip_measure`, QC tự loại/tự gen lại tốn tiền.
12. Tiền, ngân sách, giao diện (nút gen chung, Thử rẻ, hiển thị tiến độ, model thật).

**C. Rút kinh nghiệm → cập nhật cho TỪNG VAI.** Vai lấy từ `core/llm_runner.STAGE_SETTINGS` và tổ làm phim (`decision_film_crew_and_capped_pilot`): Biên kịch (`screenwriter`), Đạo diễn (`director`, `director_rewrite`), Quay phim, Editor (`editor`), Tổ QC (`qc`, `video`), Motion (`motion`), Dịch (`translate`), Nhạc / SFX / Phụ đề (`music`, `sfx`, `subtitles`), Bảng kê tài nguyên (`asset_checklist`), Bài học (`lessons`, `lesson_judge`). Với mỗi vai: (i) học được gì từ chỗ làm tốt; (ii) học được gì từ chỗ sai; (iii) **thay đổi đề xuất cụ thể** — prompt/knowledge, luật kiểm bằng code, giá trị mặc định, UI; (iv) bằng chứng.

**D. Đầu ra mong đợi:**
- `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md` (báo cáo) + điền cột "Chất lượng cao" trong `docs/kld_runs/README.md`.
- Danh sách thay đổi theo vai **chờ người dùng duyệt** (không tự bật).
- Bài học đưa vào đường chuẩn (bảng `lessons` qua công cụ của devsys, `.claude-memory`, và prompt/luật sau cờ TẮT theo `feedback_lessons_into_director`), không sửa tay CSDL.

## 5. Chỗ làm tốt / sai đã biết (hạt giống, để kiểm chứng bằng số liệu)
- **Tốt:** GPT Image 2.5 đẹp hơn Seedream cùng giá; gửi ảnh Kho cho shot không người → đúng bộ đồ; prompt thoại tự nhiên; khẩu trang đeo kín khi có luật; nối clip nhảy từ khung cuối clip trước; nền 3D đồng trục + câu khóa nền + loại ảnh toàn cảnh ngoài tường → nền đúng suốt 11,5 s; chế độ Seedance 2.5 không còn "chuyển cảnh" ở giây 3 như bản 2.0 lỡ gửi.
- **Sai / tốn tiền:** ảnh toàn cảnh vẽ từ ngoài tường kéo ảnh sai; đổi chỗ đứng không dựng lại nền 3D ở đường vẽ thủ công; prompt cũ ("sân phẳng, nhà mái đỏ thấp") thắng render 3D; Thử rẻ ép model người dùng chọn riêng (đã sửa `fa21c76`); alias `seedance` = 2.0 gây báo nhầm 2.5; nút "Gen video" chung gửi nhầm cảnh cũ; tự gen lại của QC tốn thêm (clip 255); tệp phụ trong `videos/` làm lặp cảnh; nháp 480p lấy quyền bản cuối chưa cần; ước giá sai (công thức repo cao hơn giá web ≈ 33 % ở 2.0@1080p); khung cuối clip 256 nhiều sân trống; Kelly đứng yên ở lượt 2.
- Chi tiết lỗi phiên Claude: `docs/BAN_GIAO_2026-10-07_KHUNG_LONG_DO_PHIEN_CLAUDE.md` mục 5.

## 6. Quy tắc làm
- Phân tích **chỉ đọc**: không gọi API tốn tiền, không sửa dữ liệu thật; chạy lệnh cần dữ liệu ở máy chính `D:\AI-Video-Pipeline` (CSDL, `data/` không có trong worktree). Dùng bản sao RAM hoặc bản backup khi đọc.
- Trả lời người dùng bằng **tiếng Việt**. Theo `docs/CHUAN_XAY_DUNG.md` (không im lặng khi thiếu đầu vào; "đã sửa" kèm bằng chứng chạy thật).
- Thay đổi prompt/knowledge cho vai: để sau cờ TẮT, rà nhẹ; thay đổi động tiền/dữ liệu/quyền: rà kỹ. Mỗi nhánh tối đa 3 phiên con (xem skill `vong-lam-viec-theo-plan`).
- Commit + push `main`, cập nhật `TODO.md`; nếu đổi code `dashboard/` hoặc `core/` thì khởi động lại Dashboard, đổi `devsys/` thì khởi động lại cả cổng 8502.
- Đề xuất mở đầu: chia việc theo mục 4A (thống kê, 1 phiên), 4B (so sánh theo khâu, 1–2 phiên), 4C–D (theo vai + bài học, 1 phiên).
