# Rà soát: Claude API dùng model và kỹ năng thế nào — dữ liệu thật (2026-09-27)

Người dùng hỏi: Claude API dùng model hợp lý chưa, QC có dùng kỹ năng chuẩn chưa, các kỹ năng đã thêm có thật sự được dùng và hiệu quả
không. Mọi số dưới đây đo từ dữ liệu thật: sổ chi `usage_events` (kind llm), bảng `qc_results` / `review_log` của dự án #8, và prompt dựng
lại đúng như lúc gửi với cờ của dashboard (công cụ chạy khô: gắn bộ ghi vào hàm đọc tệp, không gọi Claude).

## 1. Model và token
| Khâu | Model | Số lượt | Token vào (mới / đọc cache) | Token ra | Ghi chú |
|---|---|---|---|---|---|
| Director (#6, #7, #8) | claude-sonnet-5 | 16 | 251k / 305k | **229k** | #8: 9 lượt (Tầng A + 6 Tầng B + hỏi lại + kiểm Bible) |
| QC ảnh (#7, #8) | claude-sonnet-5 | 59 | 300k / 266k | 28k | ~5,1k mới + 4,8k cache mỗi lượt, ~470 ra; cache đọc 55/59 lượt ✅ |
| Motion prompt | claude-sonnet-5 | 2 | 50k / 0 | 5k | không cache |
| QC video | claude-sonnet-5 | 2 | 16k / 2k | 0,2k | |
Tổng sổ chi Claude từ 24/09: **4,14 USD** (Director 2,98 · QC 0,97 · motion 0,15 · video 0,04).

**Nhận xét:** một model cho mọi việc — không phân tầng. Director (lập kế hoạch dài, nhiều luật) hợp với Sonnet 5 (hoặc mạnh hơn); QC từng
ảnh là việc lặp nhiều lần, có thể thử model rẻ hơn (Haiku 4.5 có đọc ảnh) — **nhưng chỉ đổi sau khi đo trên bộ ảnh có nhãn** (mục 3), vì
QC hiện đã yếu. Cache: QC tốt; Director Tầng B đọc cache phần chung ✅; motion chưa cache.

## 2. Kỹ năng nào thật sự được nạp (prompt dựng lại cho #8)
| Lời gọi | Độ dài | Tệp kỹ năng nạp vào |
|---|---|---|
| Director Tầng A (Đạo diễn) | ~62k ký tự (~18k token) | `roles/director.md` (32,7k), `prompts/19`, `ff_gameplay_visual`, `research_notes`, `genre_guides`, `character_lock` |
| Director Tầng B (Quay phim, mỗi cảnh) | ~93k ký tự (~27k token) | `roles/dp.md` (24,2k), `prompts/17` + `20`, `ff_directing`, `ff_styles/SHORT_FILM`, `ff_gameplay_visual` |
| QC ảnh (mỗi ảnh) | ~14k ký tự (~4k token) | `prompts/02_qc_agent`, `ai_image_failure_modes`, `character_lock` + `qc_checklist.json`; **không** có sách Quay phim / Đạo diễn, không `set_consistency_qa`, không vùng an toàn; `knowledge_user/qc` **rỗng** |
| Motion prompt | ~72k ký tự | `prompts/03`, `video_motion_vocab`, `research_notes`, `t2v_prompt_structure`, `seedance_prompting`, `seedance_director_workflow` |
| Sách Dựng (`editor/editing.md`, `safe_zones.md`) | — | dùng **bằng code** (phụ đề, màu, âm thanh, vùng an toàn), không gửi Claude — đúng thiết kế |

**Kết luận:** kỹ năng **có được nạp** (cờ `film_crew` bật → sách vai thay tài liệu rời). Nhưng **nạp ≠ làm theo**: Director #8 bỏ qua
`hook_mid`, `money_shot`, mẫu `lighting`, trái/phải khung, đặt ý đồ nhạc sai (phát hiện 4), xin cảnh đêm "chìm trong bóng tối". Nguyên
nhân khả dĩ: prompt rất dài (62–93k ký tự), sách viết theo lối "cách nghĩ" chứ không có danh sách kiểm cuối, và chỉ một phần luật có
code kiểm + hỏi lại. Tệp chỉ đọc theo tên động (thể loại / phong cách khác của dự án) không dùng là **đúng thiết kế**; `roles/README.md`
chỉ là tài liệu.

## 3. QC ảnh có hiệu quả không — đối chiếu 54 ảnh #8 có nhãn bằng mắt
16 ảnh lỗi rõ (khung chữ nhật dán, nền sàn, thân lơ lửng, đè cột, vẽ cả cảnh thay phông xanh) · 38 ảnh không lỗi ghép.

| | QC tự duyệt | QC để người xem (dưới sàn 0,82) | QC tự loại |
|---|---|---|---|
| 16 ảnh lỗi | **6** (268, 271, 275, 279, 297, 302) | 10 (người loại) | **0** |
| 38 ảnh không lỗi | 15 | ~19 | 4 (mặt mờ, thiếu người, hướng nhìn…) |

- **Điểm trung bình gần như không phân biệt**: ảnh lỗi 0,67 · ảnh không lỗi 0,69.
- Tiêu chí `grounding` (đứng trên nền) trung bình **0,94** — kể cả ảnh thân lơ lửng / nền là sàn → tiêu chí này **mù** với lỗi ghép.
  `set_match` thấp nhất (0,51) nhưng không đủ để loại.
- Ngưỡng tự duyệt 0,82 cao so với phân bố điểm → phần lớn ảnh đẩy sang người xem (19/38 ảnh tốt) — tốn công người mà vẫn lọt lỗi.
- QC tự loại 4 ảnh có lý do đúng (nội dung / diễn xuất) → **QC hữu ích cho nội dung, vô dụng với lỗi kỹ thuật ghép**.
- Kiểm Bible với ảnh (prompt 18) **báo sai** hướng mũ MAXIM (phát hiện 21).

## 4. Đề xuất (theo thứ tự đáng làm)
1. **54 ảnh có nhãn của #8 → bộ đo QC** (`eval/golden.json` đã có khung): mọi thay đổi QC / model / ngưỡng phải chạy lại trên bộ này
   trước khi tin. Miễn phí dựng; đo lại tốn Claude (~0,02 USD/ảnh).
2. **Lỗi kỹ thuật bắt bằng code, không trông vào QC** — đã làm cho ghép (đo phông xanh, mép cắt, vật che); với cách vẽ mới: kiểm cỡ cảnh
   bằng dò mặt (CU/MCU/MS), kiểm khuôn mặt đủ số người.
3. **QC nhận ảnh toàn cảnh của cảnh làm tham chiếu nơi chốn** (cách vẽ mới) để `set_match` có căn cứ; sửa `grounding` thành câu hỏi cụ
   thể (bóng dưới chân? chân chạm sàn?) — nhỏ, miễn phí code.
4. **Ghi "prompt đã nạp những tệp nào" vào sổ chi** mỗi lời gọi (hiện không lưu) → lần sau đo được kỹ năng có dùng không mà không phải
   dựng lại.
5. **Phân tầng model** (Haiku 4.5 cho QC lặp / kiểm nhỏ; Sonnet 5 cho Director) — chỉ sau khi (1) có số đo.
6. **Director làm theo luật**: thêm bảng kiểm cuối ngắn ở cuối prompt + code kiểm + hỏi lại cho các trường bị bỏ (hook_mid, money_shot,
   lighting, trái/phải) — thuộc đợt sửa kỹ năng gộp sau lần chạy.
