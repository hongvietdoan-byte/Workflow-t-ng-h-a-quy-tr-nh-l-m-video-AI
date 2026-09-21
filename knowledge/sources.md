# Nguồn tham khảo đã kiểm chứng (kiểm tra ngày 2026-09-19)

Số liệu lấy từ GitHub API tại thời điểm kiểm tra. **Chỉ dùng ý tưởng và cấu trúc, diễn đạt lại bằng lời của dự án; không sao chép nguyên văn.** Repo không có license = mặc định giữ mọi quyền, chỉ đọc tham khảo. CC-BY-4.0 nếu dùng lại nội dung phải ghi công.

| # | Nguồn | Sao | License | Hoạt động | Độ tin cậy | Dùng để làm gì |
|---|---|---|---|---|---|---|
| 1 | [google-deepmind/dramatron](https://github.com/google-deepmind/dramatron) | 1.1k | Apache-2.0 | push 07/2024 (ổn định) | Cao (DeepMind, có nghiên cứu người dùng) | Cấu trúc phân tầng: logline → nhân vật → cốt truyện → địa điểm → thoại. Mẫu cho Bước 1 |
| 2 | [HITsz-TMG/FilmAgent](https://github.com/HITsz-TMG/FilmAgent) (nay đổi tên VideoClaw) | 1.8k | MIT | push 08/2026 | Cao về ý tưởng (có bài báo); phần sản phẩm hóa mới hơn | Vai trò đạo diễn/biên kịch/quay phim phối hợp, có người kiểm duyệt |
| 3 | [openstory-so/openstory](https://github.com/openstory-so/openstory) | 637 | MIT | push 09/2026 | Trung bình–cao (đang phát triển tích cực) | Quy trình 5 pha script → storyboard: tách cảnh, "bibles", shot list, motion prompt dựa trên ảnh đã render |
| 4 | [jnMetaCode/ai-shortfilm-prompts](https://github.com/jnMetaCode/ai-shortfilm-prompts) | 429 | MIT | push 09/2026 | Trung bình (cộng đồng, có bộ tự kiểm 10 mục) | Khung prompt 5 tầng, mẫu 21 thể loại, cách tự kiểm |
| 5 | [smixs/visual-skills](https://github.com/smixs/visual-skills) | 403 | CC-BY-4.0 | push 09/2026 | Trung bình (cộng đồng; nội dung dựng phim có cơ sở như quy tắc Murch) | Kịch tính học, blocking, montage; cú pháp riêng từng model (Seedance/Kling/Veo) |
| 6 | [showlab/MovieAgent](https://github.com/showlab/MovieAgent) | 363 | không có | push 03/2025 | Cao về học thuật (bài báo arXiv 2503.07314) | Lập kế hoạch phân tầng đạo diễn → cảnh → shot; ngân hàng tham chiếu nhân vật |
| 7 | [neopen/story-shot-agent](https://github.com/neopen/story-shot-agent) (PenShot) | 203 | MIT | push 09/2026 | Trung bình | Chia kịch bản thành shot theo giới hạn thời lượng model; bộ nhớ nhất quán nhân vật; QA agent |
| 8 | [Vchitect/ShotBench](https://github.com/Vchitect/ShotBench) | 106 | không có | push 09/2025 | Cao về học thuật (benchmark, chú thích chuyên gia) | Phân loại 8 chiều điện ảnh dùng làm từ vựng chuẩn cho QC/eval |
| 9 | [geekjourneyx/awesome-ai-video-prompts](https://github.com/geekjourneyx/awesome-ai-video-prompts) | 78 | MIT | push 01/2026 | Thấp–trung bình (danh mục tổng hợp) | Mục lục các hướng dẫn chính thức và mẫu prompt để đối chiếu |
| 10 | [Picrew/awesome-llm-story-generation](https://github.com/Picrew/awesome-llm-story-generation) | 108 | không có | push 06/2026 | Thấp–trung bình (danh mục bài báo) | Mục lục bài báo/dự án tạo truyện–kịch bản để đọc sâu thêm |

## Đã xem nhưng không dùng
- `cliprise/awesome-ai-video-generator-prompts` (18 sao, không license, dạng quảng bá/tổng hợp): giá trị thấp.
- `NAMDIE/SKRIPTON` (0 sao, repo mới, Apache-2.0): ý tưởng "prompt pack tự thực thi" hay nhưng chưa được kiểm chứng.
- `YidanPan/Movie-Agent` (1 sao): chưa đủ độ tin cậy.

## Lưu ý về độ tin cậy
- Phần lớn repo về prompt video AI là dự án cộng đồng mới (2026) với số sao khiêm tốn; giá trị nằm ở nguyên tắc dựng phim chung, không ở cú pháp cụ thể của từng model.
- **Cú pháp/giới hạn từng model (Seedance, Kling, MiniMax) phải lấy từ tài liệu chính thức của model hoặc của Clip AI**, và kiểm tra bằng bộ đánh giá `eval/`, không tin hoàn toàn vào repo cộng đồng.
- Kiểm tra lại số liệu này định kỳ (mỗi quý) vì các model và repo thay đổi nhanh.

## Bộ kỹ năng nội bộ đã chắt lọc (2026-09-21)
- "AI Film Direction & Prompt Workflow Kit" 1.0.0 (film-director, motion-director, narration-writer, style-analyst) → `film_director_method.md`, `t2v_prompt_structure.md`, `motion_complex_shots.md`, tính năng World Bible.
- "Seedance Director — Prompt Optimization Skill" 1.0 → `seedance_director_workflow.md`.
- Đây là tài liệu nội bộ do người dùng cung cấp, chưa được kiểm chứng bằng bộ đánh giá `eval/`.
