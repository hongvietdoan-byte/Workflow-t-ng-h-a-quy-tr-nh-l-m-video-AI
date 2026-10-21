# C-M83-TOOL — công cụ đo tải 10 người cho M8.3 (cloud-C, 22/10; chuyển từ cloud-E)

- Nhánh: `cloud/v31-m83-tool`, tách từ `origin/main`.
- 0 USD: mọi nhà cung cấp GIẢ. Không đổi cờ, không migration, không sửa `dashboard/` hay `core/`.
- **Lượt đo THẬT phải chạy trên máy chính.** Số liệu dưới đây đo trên Linux cloud 4 lõi, trình duyệt đo chạy chung máy với server, nên ≠ máy chính.

## Công cụ: `tools/load_test_ui.py`

**1. Dữ liệu**
- Mặc định: CSDL giả dựng bằng API Pipeline thật (`ui_snapshot.build_sample_data`, tham số mới `rich_others`), gồm `--projects` (3) dự án × `--shots` (30) shot, đủ trạng thái ảnh / prompt / clip, ảnh giả nhỏ.
- `--db <CSDL thật> [--data <thư mục dự án>]`:
  - mở `mode=ro` (URI `as_uri`), backup sang thư mục tạm;
  - **làm trơ bản sao**: bỏ ảnh Kho `removed`, vì dọn rác hằng giờ sẽ xóa FILE theo đường dẫn lưu, có thể là đường tuyệt đối tới file thật; tắt nguồn Kho ảnh / âm thanh `auto`; `projects.llm_provider` → NULL, `jobs.llm_provider` → mock;
  - chỉ chép thư mục `<id>/images`.
- Mỗi mức N có một bản chép riêng ở `<tmp>/data/manifest.sqlite`, kèm `ASSET_DIR` / `SOUND_MODEL_DIR` trong thư mục đo. Nhờ vậy `assets.resolve` không giải đường tương đối về repo.

**2. Server đo**
- `streamlit run dashboard/app.py` trên cổng riêng (mặc định 8541). Từ chối 8501 / 8502 và cổng bận.
- Kiểm tiến trình nghe cổng đúng là Streamlit đo (`psutil`). Health "ok" mà không phải tiến trình đo thì dừng, không bấm gì.
- `IMAGE/VIDEO/AUDIO/LLM/SUBJECT_PROVIDER=mock`.
- Bỏ mọi khóa trong môi trường, theo danh sách và theo mẫu `*_KEY` / `*_TOKEN` / `*_SECRET` / `*PASSCODE` / `ANTHROPIC_*` / `CLAUDE_CODE_*`.
- Cờ đọc từ tệp tạm, không theo baseline sản xuất. Đồng bộ đầu phiên chạy nền như sản xuất.

**3. Phiên trình duyệt**
- N phiên Chromium (Playwright async, mỗi phiên một context) chạy song song.
- Luồng: Trang chủ → `Mở →` dự án (i mod số dự án; vào thẳng Storyboard) → (Storyboard) → `✔ Duyệt` 1 ảnh → Video → `▶ Gen video` (giả).
- Mỗi bước đo tới khi màn **ổn định sau lượt chạy lại MỚI của chính nó**. Bộ đếm `MutationObserver` theo `data-test-script-state` ∈ {running, rerunRequested, stopRequested}, sau đó cần 3 nhịp yên × 0,1 s.
- Các trường hợp đặc biệt được ghi riêng:
  - bấm mà không có lượt chạy lại trong 10 s → "không rerun";
  - màn đã hiện sẵn → "đã hiện sẵn";
  - bước lỗi → tính là chậm, kèm ảnh màn `loi_n<N>/loi_s<i>_<bước>.png`, và mã thoát 1.

**4. Phía server**
- Mỗi 0,5 s đo CPU / RAM / số luồng của tiến trình Streamlit và CPU cả máy (`psutil`).
- Đầu dò `sitecustomize` (PYTHONPATH riêng của tiến trình đo; nạp tiếp sitecustomize gốc):
  - bọc `sqlite3.connect` → đo thời gian từng lệnh GHI / commit. Lệnh ≥ 0,05 s được tính là "chờ khóa" (gồm cả chờ GIL);
  - đếm lỗi `locked`;
  - đếm luồng theo tên;
  - thêm độ trễ giả `--latency` cho `submit` / `status` của bộ giả.

**5. Đầu ra**
- `load_ui.md` + `load_ui.json` gồm p50 / p95 từng bước theo N, CPU / RAM đỉnh, khóa SQLite, ngưỡng "chậm" (màn chính p95 > 2 s) xuất hiện ở N nào, và khâu nghẽn.
- Khâu nghẽn xét theo thứ tự: CPU cả máy → CPU Streamlit → SQLite.

**Không đo được ở đây:** khóa Blender, hàng đợi Claude CLI (bộ giả không xếp hàng), giới hạn Deepix / Clip AI.

## Lệnh cho máy chính (lượt thật)
```
py -m pip install playwright psutil          # KHÔNG chạy "playwright install"
set PYTHONUTF8=1
py tools/load_test_ui.py --out data\load_test_ui\may_chinh                        # dữ liệu giả 3×30, N = 1,2,5,10
py tools/load_test_ui.py --db data\manifest.sqlite --data data\projects --levels 1,5,10 --out data\load_test_ui\may_chinh_that
```
- Trình duyệt: tự tìm Chromium của Playwright (`%LOCALAPPDATA%\ms-playwright`, bản số lớn nhất) rồi đến Chrome / Edge của máy. Truyền `--chrome "C:\Program Files\Google\Chrome\Application\chrome.exe"` nếu cần.
- **Cần kiểm trước:** Playwright / greenlet đã có bản cho Python 3.14 Windows chưa.
- Nên tắt Dashboard thật trong lúc đo, vì hai tiến trình tranh CPU. Công cụ không bao giờ đụng cổng 8501 / 8502.
- Để số đo sát thực tế hơn: chạy trình duyệt đo từ MÁY KHÁC là việc của phiên sau (cần `--url`); hiện trình duyệt chạy chung máy.

## Số đo chạy thử trên cloud (Linux 4 lõi, Python 3.13 — KHÔNG phải máy chính)
### Thời gian tới khi màn ổn định (giây, p50 / p95)

| Bước | N=1 | N=2 | N=5 | N=10 |
|---|---|---|---|---|
| Trang chủ | 3.545 / 3.545 🐢 | 5.204 / 5.244 🐢 | 9.801 / 16.749 🐢 | 19.115 / 34.883 🐢 |
| Mở dự án (vào thẳng Storyboard) | 3.848 / 3.848 🐢 | 5.957 / 6.018 🐢 | 12.324 / 12.573 🐢 | 12.642 / 24.969 ·4 không rerun 🐢 |
| Storyboard (Bước 2) | đã hiện sẵn sau bước trước | đã hiện sẵn sau bước trước | đã hiện sẵn sau bước trước | 13.82 / 14.606 🐢 |
| Duyệt 1 ảnh | 1.98 / 1.98 | 3.401 / 3.457 | 8.104 / 8.45 | 9.329 / 16.865 |
| Video (Bước 4) | 0.913 / 0.913 | 1.024 / 1.031 | 1.953 / 2.798 🐢 | 6.877 / 12.037 🐢 |
| Bấm Gen video (giả) | 2.971 / 2.971 | 3.061 / 3.283 | 3.856 / 4.82 | 6.596 / 11.919 |

### Server (tiến trình Streamlit)

| N | CPU đỉnh % | CPU cả máy đỉnh % | RAM đỉnh MB | Luồng gốc → đỉnh | Luồng thêm / phiên | Lệnh ghi SQLite | Chờ khóa (≥ 0.05 s) | Chờ lâu nhất s | Lỗi locked |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 109.0 | 85.6 | 132.8 | 7 → 33 | 26.0 | 181 | 0 (0.0 s) | 0.0 | 0 |
| 2 | 133.8 | 98.5 | 144.7 | 7 → 36 | 14.5 | 277 | 0 (0.0 s) | 0.0 | 0 |
| 5 | 153.9 | 99.5 | 173.4 | 7 → 55 | 9.6 | 424 | 0 (0.0 s) | 0.0 | 0 |
| 10 | 163.3 | 100.0 | 323.2 | 7 → 57 | 5.0 | 483 | 0 (0.0 s) | 0.0 | 0 |

### Kết luận

- Ngưỡng chậm xuất hiện ở: N=1 (Trang chủ, Mở dự án (vào thẳng Storyboard))
- Khâu nghẽn (lỗi rồi p95 lớn nhất ở N=10): Trang chủ 34.883 s — CẢ MÁY đo bão hòa CPU (trình duyệt đo + Streamlit chung máy) — số đo phồng; đo lại với ít phiên hơn / máy mạnh hơn
- Tổng bước lỗi: 0
- Không đo ở đây: khóa Blender, hàng đợi Claude CLI, giới hạn Deepix / Clip AI (bộ giả).
- Khác máy chính: DASHBOARD_AUTH=off (bỏ ghi team.touch / quyền mỗi lần chạy lại), `streamlit run dashboard/app.py` (máy chính: dashboard.serve), trình duyệt đo chạy CÙNG máy với server — tranh chấp SQLite thấp hơn, CPU cao hơn thực tế.
- Mỗi số đo gồm ~0.3 s cửa sổ "yên" của bộ đo; "không rerun" = bấm mà không có lượt chạy lại trong 10 s (số đo gồm thời gian chờ đó). Luồng thêm / phiên tính cả luồng khởi một lần mỗi tiến trình (N=1 phồng).
- Luồng theo tên ở N=10: ThreadPoolExecutor×4, AnyIO worker thread×3, MainThread×1, load-probe-dump×1, Thread×1, bg-poll×1, autoqc-video×1

**Đọc số:**
- CPU cả máy chạm 98–100 % ngay từ N=2. Ở đây 10 phiên Chromium và Streamlit chạy chung 4 lõi, nên từ N=5 số đo chủ yếu phản ánh máy đo bị bão hòa.
- Ở N=10, 4 phiên ghi "không rerun" ở bước Mở dự án. Lúc máy bão hòa, cú bấm không gây chạy lại trong 10 s, nên 4 phiên này chưa vào Storyboard. Vì thế dòng Storyboard ở N=10 có số đo thật (13,8 s). Đây là triệu chứng bão hòa, không phải lỗi công cụ.
- Cả 4 mức: 0 lần chờ khóa SQLite, 0 lỗi locked. Tranh chấp SQLite không phải nút thắt khi có ≤ 10 phiên, nhưng cần đo lại khi `DASHBOARD_AUTH` bật.
- Mỗi phiên thêm khoảng 5 luồng (N=10). RAM tiến trình 133 → 323 MB.
- Trang chủ ngay cả ở N=1 đã 3,5 s, gồm lượt vẽ đầu và bấm "Tất cả dự án". Mở dự án mất 3,8 s. Hai màn này là ứng viên tối ưu đầu tiên. Ngưỡng 2 s đã vượt từ N=1 trên máy cloud.
- Trong các lượt chạy thử có một lượt N=5 với 3 phiên không tải được trang trong 120 s; lượt chạy lại thì 0 lỗi. Từ đó công cụ chụp ảnh màn khi lỗi để chẩn đoán.

## Rà soát (quy tắc 7)
