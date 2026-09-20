# Runbook vận hành — Auto Pipeline Video AI

Dành cho người **vận hành hằng ngày** (không cần đọc code). Kế hoạch tổng thể ở `PLAN.md`, tiến độ ở `TODO.md`, ghi chú API ở `docs/api_notes.md`.

## 1. Cài đặt một lần
1. **Python 3** (lệnh `py` chạy được) và **FFmpeg** (`winget install --id Gyan.FFmpeg -e`). Launcher tự tìm ffmpeg; nếu không thấy, đặt `FFMPEG_PATH` trong `dashboard.env`.
2. `git pull` thư mục dự án.
3. Chạy `powershell -File tools/make_shortcut.ps1` → có 2 shortcut trên Desktop: **AI Video Pipeline** (mở) và **Tat AI Video Pipeline** (tắt). Lần mở đầu tiên tự cài thư viện.
4. Chép `dashboard.env.example` → `dashboard.env` và sửa (không chứa token):
   ```
   IMAGE_PROVIDER=deepix
   VIDEO_PROVIDER=clipai
   ```
   Dùng `mock` cho cả ba (`IMAGE_PROVIDER`, `VIDEO_PROVIDER`, `AUDIO_PROVIDER`) để tập dùng **không tốn credit**.
5. Đặt token vào **biến môi trường Windows của người dùng** (không ghi vào file, không gửi chat): `CLIPAI_TOKEN`, `DEEPIX_TOKEN`, và khi có: `ANTHROPIC_API_KEY`. Dán token **một lần** (dán nhiều dòng/ký tự lạ làm token hỏng — Dashboard sẽ báo "token looks corrupted"). Kiểm tra kết nối (chỉ đọc, không tốn credit): `py -m core.adapters.check`.
6. Điền giá thật vào `data/pricing.json` (xem mục 6).

## 2. Biến môi trường (tra cứu)
| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `IMAGE_PROVIDER` | `deepix` \| `mock` | chưa đặt = nhập ảnh tay |
| `VIDEO_PROVIDER` | `clipai` \| `mock` | chưa đặt = chỉ theo dõi job |
| `AUDIO_PROVIDER` | `clipai` \| `mock` | theo `VIDEO_PROVIDER=clipai` |
| `LLM_PROVIDER` | `anthropic` \| `mock` | `anthropic` nếu có `ANTHROPIC_API_KEY` |
| `CLIPAI_TOKEN`, `DEEPIX_TOKEN`, `ANTHROPIC_API_KEY` | khóa API (bí mật) | — |
| `ANTHROPIC_MODEL` | model Claude (cần đọc ảnh) | `claude-sonnet-5` |
| `CLIPAI_RESOLUTION` | Seedance `480p`/`720p`/`1080p` | `720p` |
| `CLIPAI_KLING_MODE` | Kling `std`/`pro`/`4k` | `pro` |
| `CLIPAI_ASPECT_RATIO` | tỉ lệ khung | `16:9` |
| `CLIPAI_NEGATIVE` | `append` = nối "Avoid: …" vào prompt | bỏ qua |
| `DEEPIX_MODEL`, `DEEPIX_SIZE` | model/kích thước ảnh | Seedream 5.0 Pro, `2048x1152` |
| `HEARTBEAT_SEC` | chu kỳ hỏi trạng thái tác vụ | `90` |
| `PIPELINE_DB`, `PIPELINE_DATA`, `PIPELINE_PRICING` | vị trí DB / thư mục dự án / bảng giá | `data/…` |
| `DASHBOARD_PORT` | cổng Dashboard | `8501` |
| `TRASH_DAYS` | số ngày giữ file trong thùng rác | `30` |
| `SUBJECT_PROVIDER` | `clipai` \| `mock` (kho chủ thể Seedance) | theo `VIDEO_PROVIDER` |

## 3. Quy trình một video (Dashboard, 7 tab theo thứ tự)
| Bước | Việc bạn làm | Kiểm tra trước khi qua bước |
|---|---|---|
| **1 Kịch bản** | Tạo dự án → upload `.docx` → *Chạy phân tích* → *Chạy Director* (hoặc dán JSON) → sửa Character Bible nếu cần → **Duyệt & khóa** | Không còn cảnh báo **IP rủi ro** (sửa mô tả nhân vật trước khi khóa) |
| **2 Gen ảnh + QC** | *Tạo job gen ảnh* → *Chạy heartbeat* → *QC bằng Claude* → duyệt/từ chối (ghi chú reject sẽ vào prompt gen lại) | Mọi cảnh có ảnh **Đã duyệt** |
| **3 Video Prompt** | *Sinh motion prompt* (hoặc dán JSON) → sửa → **Duyệt** | Mọi cảnh có prompt đã duyệt |
| **4 Gen video** | Chọn model (Kling/Seedance) → xem **ước tính chi phí** → *Tạo job* → *Chạy heartbeat* | Job `succeeded` cho mọi cảnh (xem thử từng clip) |
| **5a Nhạc/âm thanh** | Sửa prompt nhạc → *Tạo bản nháp* → nghe, **Chọn**; tùy chọn SFX/giọng đọc + thời điểm | Đã chọn nhạc (hoặc "không dùng") |
| **5b Ghép & Render** | Chọn clip, transition, âm lượng → *Render Final* → xem và tải | Tổng thời lượng đúng dự kiến |

Dưới mỗi ảnh/clip có mũi tên **📖 nội dung kịch bản**: bấm để đọc lại đoạn kịch bản của cảnh đó (kèm bối cảnh, nhân vật, mood, prompt) và so với kết quả. Video xem ngay trong Dashboard (chọn Nhỏ/Vừa/Lớn; ⛶ để toàn màn hình); chưa ưng thì bấm **↻ Gen lại video** (bản cũ vào thùng rác). Ở Bước 5a, nút **🎬 Xem thử với video** ghép nhanh clip + nhạc để nghe có khớp hình không. **Kho chủ thể (Free Fire):** Bước 1 → "🧩 Kho chủ thể Seedance": chọn nhân vật, tải ảnh lên kho (chờ 1–3 phút tới khi *active*), rồi ở Bước 4 bật "🧩 Gắn ảnh chủ thể nhân vật vào video" (chỉ Seedance). FF đã ký bản quyền nên chủ thể active dùng được; game khác vẫn có thể bị chặn bản quyền. Góc trên có **⚠ Rủi ro (N)** ghi lại cảnh báo IP và các lần bị chặn. Dấu **✓** trên thanh bước = bước đã hoàn tất. Nút **Pause** dừng việc bắt đầu job mới; **Cancel** hủy job đang chạy/xếp hàng của dự án.

## 4. Hai chế độ QC
- **Duyệt tất cả** (Bước 2 và 3) hỏi Có/Không một lần trước khi duyệt; duyệt từng ảnh thì bấm ngay tại ảnh. **Ảnh điểm quá thấp** (mặc định dưới 0,50, chỉnh được) bị tự loại ở cả hai chế độ và xếp hàng gen ảnh mới (gen khi bạn bấm chạy).
- `human_qc` (mặc định V0): mọi ảnh chờ bạn duyệt; điểm QC chỉ là gợi ý.
- `auto`: QC Agent tự duyệt nếu điểm ≥ **threshold**, tự loại nếu thấp hơn. Có thể bật **Vùng chờ review**: điểm nằm giữa *mức sàn* và threshold sẽ chờ bạn duyệt thay vì tự loại.

**Chỉnh threshold an toàn:** đừng hạ threshold để "cho qua nhanh". Chỉ đổi sau khi so sánh ít nhất 20 ảnh giữa QC Agent và người duyệt (tỉ lệ đồng thuận). Nghi ngờ thì nâng threshold hoặc bật vùng chờ review. Mỗi kết quả QC lưu lại `threshold_at_time`, nên đổi threshold không làm sai lịch sử.

## 5. Xử lý sự cố job
Lưu ý chung: nút **↺ Làm lại từ đầu** xuất hiện ở job đã hết số lần thử (⚠ escalated); **↩ Bỏ duyệt & gen lại ảnh** ở ảnh đã duyệt (panel chi tiết); **↻ Gen lại video** ở clip đã xong. Giới hạn và lỗi đã biết: `docs/WORKFLOW_REVIEW.md`.

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Job **failed** (ảnh/video) | Lỗi mạng tạm thời, tác vụ lỗi | *Retry* (tự retry tối đa `max_retry_count`, mặc định 3). Mỗi lần gửi API có thể tốn credit |
| Thẻ **⚠ Risk control** (video) | Nội dung bị bộ lọc của model chặn (thường do IP/nhân vật nổi tiếng, cảnh nhạy cảm) | **Không retry mù** (tốn credit). Sửa mô tả nhân vật/motion prompt để bớt IP, hoặc đổi model (bộ lọc mỗi model khác nhau) |
| **⚠ escalated**, cảnh `needs_attention` | Hết số lần retry | Xem lịch sử (tab **Lịch sử**), sửa nguyên nhân gốc (prompt/nhân vật), rồi tạo job mới |
| Job kẹt `running` rất lâu | Nền tảng chậm; job không tìm thấy trong danh sách gần nhất | *Submit + Poll 1 lần*; nếu vẫn không thấy sau ~12 lần hỏi, job tự đánh `failed` (`not_found`) → kiểm tra trên web Clip AI/Deepix |
| Nhạc/SFX **failed** | Lỗi nhà cung cấp | Đọc thông điệp lỗi, sửa prompt, tạo lại thủ công (không tự gửi lại) |
| Ảnh hiện "Không đọc được ảnh" | File tải về hỏng | Retry job ảnh |

## 6. Chi phí
- Trước mỗi lô gen, Dashboard hiện **ước tính** (min và max nếu mọi mục retry đủ lần). Lô ≥ `confirm_batch_at` (mặc định 10) phải tick xác nhận.
- Muốn có số tiền: mở **💲 Bảng giá** ở đầu Dashboard và chép giá mà web Clip AI hiện **trước khi bấm gen** cho từng thiết lập. Khóa `model:mức:Ns` (vd `kling-v3-omni:pro:5s`) = giá đúng của clip đó; `model:mức` = giá mỗi clip; `per_video_second` = giá mỗi giây. Có thể sửa trực tiếp `data/pricing.json`. Deepix không biết giá thì để trống. Khi cần đối chiếu: so số tổng đã dùng trên web trước/sau một lần chạy.
- Thanh trên cùng hiện "đã ghi nhận (gửi API thật)": số ảnh, clip (giây), âm thanh. Đây là ước tính từ sổ của app; **số dư trên web mới là nguồn chính xác**. Provider `mock` không tính tiền.
- Chưa ghi nhận: token của Claude API. Gói Claude doanh nghiệp có hạn mức cứng 400$/tháng cho Chat + Code của tài khoản (tới ngưỡng tự dừng; dùng chung với các phiên làm việc khác). Đây không phải ngân sách API: LLM runner cần API key riêng do admin cấp; chưa có thì dán JSON từ Claude Desktop.

## 7. Dữ liệu và sao lưu
- Cơ sở dữ liệu: `data/manifest.sqlite`. Ảnh/clip/nhạc/output: `data/projects/<id>/` (`images`, `videos`, `music`, `music_drafts`, `audio_assets`, `output`). Cả hai **không nằm trong git**: sao lưu thư mục `data/` định kỳ (copy sang ổ khác/ổ mạng), đặc biệt trước khi cập nhật phần mềm.
- **Thùng rác:** ảnh bị loại, ảnh/clip bạn xóa (nút 🗑) và clip bị thay bằng bản gen lại được chuyển vào `data/projects/<id>/trash/images` và `trash/videos` (không xóa ngay). Xem/khôi phục ở tab **Lịch sử → 🗑 Thùng rác**; tự xóa vĩnh viễn sau 30 ngày.
- Xóa dự án hoặc làm lại: dùng *Reset* ở Bước 1 (chỉ xóa cảnh/nhân vật chưa có job, chưa khóa). Muốn xóa hẳn dữ liệu thì đóng Dashboard rồi xóa `data/projects/<id>/`.
- DB cũ tự được nâng cấp khi mở (không mất dữ liệu).

## 8. Cập nhật phần mềm
1. Tắt Dashboard (shortcut **Tat**), sao lưu `data/`.
2. `git pull`.
3. Mở lại. Thư viện mới (nếu có) tự cài. Nếu giao diện không đổi: tắt hẳn rồi mở lại (Streamlit không nạp lại file giao diện phụ).
4. Chạy kiểm tra: `py -m unittest discover -s tests -t .` (kỳ vọng: OK).

## 9. Khi Dashboard không mở
| Triệu chứng | Cách xử lý |
|---|---|
| Không thấy cửa sổ | Xem `data/dashboard.log` (lỗi in ở đây) |
| "port 8501 đang dùng" | Bấm shortcut **Tat** rồi mở lại; hoặc đổi `DASHBOARD_PORT` |
| "ffmpeg not found" khi render | Đặt `FFMPEG_PATH=<đường dẫn ffmpeg.exe>` trong `dashboard.env` |
| "token looks corrupted" | Lấy lại token từ web, dán **một lần** vào biến môi trường (`Read-Host`/`NetworkCredential`, không dán nhiều dòng) |
| HTTP 401 | Token sai/hết hạn |
| HTTP 403 (Deepix, không có JSON) | Mạng bị whitelist chặn — dùng mạng công ty/VPN đúng |
| Shortcut không chạy sau khi dời thư mục | Chạy lại `tools/make_shortcut.ps1` |

## 10. Bàn giao Prompt Templates & kiến thức
- Prompt: `prompts/01…04_*.md` (Director, QC, motion, music brief). Kiến thức: `knowledge/` (điện ảnh, thể loại, lỗi ảnh AI, từ vựng motion, Seedance). QC: `data/qc_checklist.json`. Blocklist IP: `data/ip_blocklist.json`.
- Sửa prompt/kiến thức → chạy bộ đánh giá `eval/` (xem `eval/README.md`) trước khi dùng cho dự án thật, rồi commit và ghi version.

## 11. Bảo mật
- Không commit token, không dán token vào chat/log. `dashboard.env`, `data/`, `deepix-*` nằm ngoài git.
- Repo GitHub đã private. Ảnh nhân vật gửi Claude API (QC) là dữ liệu của dự án — kiểm tra chính sách dữ liệu công ty trước khi dùng cho nội dung nhạy cảm.
