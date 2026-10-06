# Phân tích tài liệu "Prompt Spider / AI Film Production Blueprint" (06/10)

Nguồn: `AI_Film_Production_Blueprint__Architecture.pdf` người dùng gửi 06/10 (2 trang, tiêu đề "Phân Tích Kiến Trúc Prompt Spider & Ứng Dụng
Trong Làm Phim AI"). Tài liệu mô tả một giao diện mẫu phân luồng từng phần của prompt cho Code (p ≥ 0,95) / LLM / Người, rút ra 5 nguyên lý
và lộ trình 3 giai đoạn. Không có code, không có số đo thật (65 % / 12 % / 5 % là số minh họa trên ảnh giao diện), không có nguồn.

## Kết luận
Phần lớn **đã có trong dự án, và chặt hơn**; lộ trình 3 giai đoạn **không theo** (ngược quyết định đã chốt). Lấy 2 ý nhỏ, 0 USD.

| Nguyên lý | Dự án đã có | Đánh giá |
|---|---|---|
| 1. Phân việc code / AI / người | QC lớp 0 bằng code (`core/qc_scene.py`, `core/qc_measure.py`), linter (`shot_normalize`, `speaker_lint`), ffmpeg; Claude chỉ ở khâu suy luận; người ở cổng storyboard / ngân sách / bài học | Đã có — thiếu **bảng đo** ai quyết (→ S14.47) |
| 2. Prompt theo vai | Biên kịch → Đạo diễn 2 lượt → Quay phim → Dựng (`film_crew`, `director_two_pass`) | Đã có, chi tiết hơn |
| 3. Luật cứng gắn prompt | Character Lock `must_keep` / `forbidden` (`knowledge/character_lock.md`), hồ sơ kỹ năng "không được vẽ", `docs/CHUAN_XAY_DUNG.md` | Đã có — mã màu hex dùng để **đo bằng code**, không để nhét prompt (→ S14.48) |
| 4. Ngưỡng tin cậy tự cho qua | `qc_auto_pass_threshold` 0,85, vùng xám, `storyboard_auto_trust` (≥ 50 ảnh, ≥ 90 % khớp người), `lesson_judge` (bóng) | Đã có và thận trọng hơn: tài liệu đề xuất tự đẩy khi ≥ 0,90, nhưng nghiệm thu 27/09 QC Claude báo nhầm 12/21 ảnh tốt — tự cho qua phải đo đồng thuận với người trước |
| 5. Cây tài nguyên | `core/lineage.py`, `jobs.source_job_id` (video biết từ ảnh nào; ảnh đổi → video cũ) | Đã có |

**Lộ trình không theo:** GĐ1 (Streamlit + Claude + nút duyệt) dự án đã vượt; GĐ2 n8n/Langflow + ComfyUI/Midjourney/Runway trái quyết định
"Không làm: video cục bộ ComfyUI/Wan…; nhúng n8n/LangGraph…" (`docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md` mục 4) và sẽ đi vòng qua
sổ chi / cổng tiền; GĐ3 React/D3 không cần (UI v2 trên Streamlit). "Quét từng từ của prompt, chấm p" không áp được: độ tin cậy video AI đo
trên ẢNH/CLIP tạo ra, không trên chữ.

## Hai việc lấy từ tài liệu (dòng đề xuất cho `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` — phiên chính thêm khi gộp)
```
- [ ] S14.47 · Bản đồ "Ai quyết" (ý 1 tài liệu Prompt Spider 06/10): devsys/decisions.json (76 điểm: code / claude / người, file:hàm, khâu, gợi ý chuyển sang code) + devsys/decisions.py (kiểm khớp code: khâu Claude thiếu, hàm không còn) + trang devsys 'Ai quyết' · nặng:1 · ✅ (cloud 06/10)
- [ ] S14.48 · Màu chính nhân vật đo bằng code (ý 2 tài liệu Prompt Spider 06/10): bảng màu hex trích từ ảnh tham chiếu đã duyệt (cột characters.palette, người sửa tay được), đo lệch màu vùng thân trên khung Tổ QC soi (0 USD, ghi chú), sau cờ TẮT — ngưỡng hiệu chỉnh trên ảnh thật ở máy chính · nặng:2 · 🔄 (cloud: code + test; còn hiệu chỉnh)
```

## Kết quả S14.47 lần đầu (06/10)
76 điểm quyết định: code 27 (36 %), Claude 38 (50 %), người 11 (14 %) — đếm theo LOẠI quyết định, chưa theo số lượt chạy (bước sau: nhân
với số lượt thật theo khâu từ sổ chi `usage_events.stage` ở máy chính). Gợi ý chuyển sang code / bỏ đã ghi trên bản đồ: `cast_voices` →
luật `voice_casting` (khi cờ `auto_voice_cast` đã thử thật); `lint_motion` → phần từ cấm / thiếu trường đo bằng code trước; QC lớp 1 và
`qc_agent` → S14.13 quyết bỏ nếu `qc_team` đạt.

## Kết quả S14.48 (06/10, cloud)
`core/palette.py` + cột `characters.palette` + cờ `palette_check` (TẮT): trích bảng màu vùng thân (ngay dưới mặt) từ ảnh tham chiếu đã duyệt
(một lần theo sha ảnh; người đặt tay thì thắng), so với khung Tổ QC soi (`core/qc_team.review_frame` → `code["_palette"]`), chỉ khung MỘT
người. Luôn 'uncertain' (ghi chú cho người), không tự từ chối. Test trên ảnh tổng hợp (`tests/test_s1448_palette.py`). **Còn ở máy chính:**
hiệu chỉnh MATCH_DE / KEEP_RATIO trên ~20 khung #8 có / không lệch màu; xem vùng thân ước theo hộp mặt có sai ở dáng nghiêng / cận mặt.
