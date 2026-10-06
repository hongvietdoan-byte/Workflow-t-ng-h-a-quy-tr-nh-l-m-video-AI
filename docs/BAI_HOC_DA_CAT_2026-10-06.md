# Bài học / kinh nghiệm đã cất — 2026-10-06 (S14.46)

Người dùng 06/10: "bài học nào không dùng đến cũng nên loại bỏ, tránh gây nhầm lẫn cho Đạo diễn". Các dòng dưới đây thuộc tính năng đã bỏ nên KHÔNG còn đưa vào prompt. Không xóa: dòng vẫn ở bảng của nó, có `retired_at` / `retired_why`.

- Lúc cất: 2026-10-06 13:55:41 · số dòng: 57
- CSDL: `manifest.sqlite` · bản sao lưu trước khi cất: `manifest.before_lessons_retire_2026-10-06.sqlite` (thư mục `data/backup/`)
- Khôi phục một dòng: `py tools/lessons_retire.py --restore mistakes:<id>` (nhiều dòng cách nhau dấu phẩy; tất cả: `--restore all`). Dòng khôi phục mà vẫn khớp chủ đề đã bỏ thì bộ lọc lúc đọc (core/retired_topics.py) vẫn chặn — muốn dùng lại phải bỏ chủ đề đó (data/retired_topics.json: `{"<chủ đề>": null}`).

## Theo chủ đề

- **location_plates** (57): Ghép phông xanh lên nền 3D: tạm ngưng từ 27/09 (#8), thay bằng place_render_refs / scene_establishing

## Từng dòng

| Bảng:id | Ngữ cảnh | Chủ đề | Nội dung |
|---|---|---|---|
| mistakes:96 | review:227 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:97 | review:228 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:98 | review:229 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:99 | review:230 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:100 | review:231 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:101 | review:232 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:102 | review:233 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:103 | review:234 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:104 | review:235 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:105 | review:236 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:106 | review:237 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| mistakes:107 | review:238 · dự án 8 · image | location_plates | Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền #D (sửa #/#: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:143 | review:227 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:144 | review:228 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:145 | review:229 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:146 | review:230 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:147 | review:231 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:148 | review:232 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:149 | review:233 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:150 | review:234 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:151 | review:235 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:152 | review:236 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:153 | review:237 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:154 | review:238 · dự án 8 · image · failure | location_plates |  — Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D (sửa 27/09: lọc chữ nơi chốn, ảnh neo phông xanh) |
| experience_cases:155 | review:241 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:156 | review:242 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:157 | review:243 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:158 | review:244 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:159 | review:245 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:160 | review:246 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:161 | review:247 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:162 | review:248 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:163 | review:249 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:164 | review:250 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:165 | review:251 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:166 | review:252 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:167 | review:253 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:168 | review:254 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:169 | review:255 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:170 | review:256 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:171 | review:257 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:172 | review:258 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:173 | review:259 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:174 | review:260 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:175 | review:261 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:176 | review:262 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:177 | review:263 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:178 | review:264 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:179 | review:265 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:180 | review:266 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:181 | review:267 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:182 | review:268 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:183 | review:269 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:184 | review:270 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:185 | review:271 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:186 | review:272 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
| experience_cases:187 | review:273 · dự án 8 · image · failure | location_plates |  — Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh (người dùng chốt 27/09) |
