# Cách phân tích và mô tả kỹ năng chủ động (rút từ hồ sơ KENTA và ORION)

Nguồn: `data/skills/KENTA/skill.json`, `data/skills/ORION/skill.json` (30/09/2026), bài học sửa sau các lần thử #11/#12. Dùng cho
`core/video_analysis.py` (bản nháp từ video) và `tools/skill_dossier_build.py` (dựng hồ sơ). Mọi hồ sơ mới theo đúng khuôn dưới đây.

## 1. Nguồn và thứ tự bằng chứng
1. **Mô tả chính thức trong game / ff.garena.com** cho CƠ CHẾ (số liệu, điều kiện, thời lượng). Video không thay được: Orion "miễn nhiễm 3 s,
   không thể tấn công, hút 10 HP trong 5 m" là chữ chính thức; video chỉ cho HÌNH.
2. **Video chính thức của đúng phiên bản hiện hành** cho HÌNH (hình dạng, màu, độ đục, nhịp, neo vào đâu). Ghi rõ bản video (độ phân giải,
   khung/giây, độ dài) vì mọi mốc giây theo bản đó. Kiểm tra là *rework vĩnh viễn* hay *Skill Boost tạm thời* (xem `ff_character_skills_visual.md`);
   tên kỹ năng giữ nguyên chưa chắc cơ chế còn giữ (A124).
3. Khung cắt: xem thưa 1 khung/giây để tìm đoạn kỹ năng, rồi xem **từng khung** của đoạn đó (và phóng to quanh nhân vật) — hiệu ứng nhanh
   chỉ kéo dài 2–5 khung (vung tay Kenta ≈ 0,07 s) nên lấy mẫu đều thưa sẽ bỏ lỡ.
4. Mỗi câu gắn nhãn `[OBSERVED] / [EXPLICIT] / [INFERRED] / [UNKNOWN]`. Không bịa sát thương, thời gian hồi, tầm.

## 2. Khuôn hồ sơ (`skill.json`)
- `skill_vi / skill_en / version / active / source (url|file, bản, ngày xem)`.
- `mechanism_vi`: cơ chế chính thức, một đoạn.
- `phases[]`: mỗi giai đoạn `id`, `t` [từ, đến] (giây), `vi` (điều thấy), `image_en` (câu cho model vẽ ẢNH TĨNH), `video_en` (câu cho
  model làm VIDEO — chỉ chuyển động liên tục), khung `frame`/`frame_full`. Tên giai đoạn ngắn, nối tiếp: Kenta = chuẩn bị → vung → vòng gió
  trên đất → gió bay tới → xuyên Bom Keo / lướt; Orion = kích hoạt → chớp → hút máu → bùng dây cuối → hết.
- `sequences`: các chuỗi giai đoạn hay dùng (vd `release`, `cast`, `full`) + `default_phase`.
- `timing_vi`: tổng thời lượng và độ dài từng giai đoạn.
- `interactions[]`: CHỈ điều đã thấy (`with`, `vi`, `seen` = mốc giây). Chưa thấy → không ghi, và đưa vào `unconfirmed_vi`.
- `never_vi / never_en / script_contradictions`: danh sách KHÔNG vẽ + từ khóa để code bắt kịch bản mâu thuẫn.
- `script_rules_vi`: luật cho người viết kịch bản (Orion: trong 3 s KHÔNG tấn công; dây đỏ chỉ khi có địch trong 5 m).
- `unconfirmed_vi`: điều video chưa cho thấy rõ — người đọc sau không được coi là đã biết.
- `video_ref` + `video_ref_phases`: clip cắt từ video chính thức (≥ 3 s, 700–4553 px, SAR 1:1), `skill_sheet` + `skill_sheet_phases`.
- `model_errors_vi`: model đã vẽ sai gì khi thử và đã sửa thế nào (để lần sau không lặp).

## 3. Sáu bài học bắt buộc
1. **Tách giao diện khỏi hiệu ứng.** Vệt đỏ lưỡi liềm quanh người trúng đòn = chỉ báo hướng sát thương; tấm sọc ngang trong suốt xanh ngọc
   cạnh Kenta = thanh định hướng kỹ năng; thanh máu, số sát thương, banner, nút = giao diện. Cả bốn là "không vẽ". Chưa chắc → `[UNKNOWN]`,
   hỏi người dùng, không tự quyết.
2. **Tả trạng thái tay và vũ khí từng giai đoạn.** Kenta vung TAY KHÔNG, katana nằm trong vỏ ngang sau thắt lưng suốt kỹ năng; model từng
   vẽ rút kiếm vì hồ sơ cũ tả "lưỡi cầm tay".
3. **Tả hiệu ứng bằng hình dạng + màu + độ đục + kích thước theo người + nhịp**, không bằng từ gợi cảm ("cuồng nộ"). Màng gió "rất mờ, xanh nhạt,
   cao gấp đôi người, nhìn xuyên thấy cảnh sau" khác hẳn "cột lốc đặc".
4. **Phân biệt thấy được và chỉ là cơ chế.** Orion vẫn di chuyển được (chữ chính thức) nhưng video cho thấy cầu gần như đứng yên → ghi cả hai,
   nói rõ cái nào là nguồn nào.
5. **Mỗi giai đoạn có hai câu:** `image_en` cho ảnh tĩnh (trạng thái tại khoảnh khắc) và `video_en` (chuyển động). Không tả lại ngoại hình nhân
   vật trong câu hiệu ứng — ngoại hình lấy từ hồ sơ chuẩn + ảnh.
6. **Hồ sơ phải kiểm bằng thử thật.** Thử 1 cảnh (Seedance 2.5 tham chiếu: khung đầu + ảnh chính diện + `video_ref` chỉ cho hiệu ứng), xem lỗi,
   ghi vào `model_errors_vi`, sửa hồ sơ; chỉ coi là xong khi thử lại không còn lỗi đó.

## 4. Quy trình khi người dùng gửi video mới
1. `py tools/skill_dossier_build.py sparse <video> <thư mục>` → tìm đoạn kỹ năng; `dense` → mọi khung của đoạn đó.
2. Lấy mô tả chính thức (ff.garena.com / bảng `assets`) cho `mechanism_vi`; hỏi người dùng nếu video và chữ chính thức lệch nhau.
3. Soạn nháp bằng ⚙ → Kho → 📹 Phân tích video (nay đã hỏi đủ giai đoạn, giao diện, tương tác, danh sách không vẽ) hoặc đọc khung thủ công.
4. Viết `skill.json` theo mục 2; `py tools/skill_dossier_build.py build data/skills/<TÊN>` dựng khung cắt, storyboard, video_ref.
5. Cho người dùng xem storyboard + danh sách "không vẽ" + `unconfirmed_vi` để xác nhận trước khi bật.
