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
  - âm thanh: đánh dấu `sounds.tags` / `heard` đã xử lý (mỗi phiên trình duyệt phân tích / nghe 150 tệp THẬT → CPU phồng N lần);
  - chỉ chép thư mục `<id>/images`; Kho ảnh (`data/assets`) KHÔNG chép → ảnh Kho báo thiếu, trang nhẹ hơn thực tế một chút.
- Mỗi mức N có một bản chép riêng ở `<tmp>/data/manifest.sqlite`, kèm `ASSET_DIR` / `SOUND_MODEL_DIR` trong thư mục đo. Nhờ vậy `assets.resolve` không giải đường tương đối về repo.

**2. Server đo**
- `streamlit run dashboard/app.py` trên cổng riêng (mặc định 8541). Từ chối 8501 / 8502 (kiểm trước) và cổng bận (psutil LISTEN mọi địa chỉ; bind với `SO_EXCLUSIVEADDRUSE` trên Windows, `SO_REUSEADDR` nơi khác, IPv4 + IPv6).
- Kiểm tiến trình nghe cổng đúng là Streamlit đo (`psutil`). Health "ok" mà không phải tiến trình đo thì dừng, không bấm gì.
- `IMAGE/VIDEO/AUDIO/LLM/SUBJECT_PROVIDER=mock`.
- Bỏ mọi khóa trong môi trường, theo danh sách và theo mẫu `*_KEY` / `*_TOKEN` / `*_SECRET` / `*PASSCODE` / `ANTHROPIC_*` / `CLAUDE_CODE_*`.
- Cờ đọc từ tệp tạm, không theo baseline sản xuất. Đồng bộ đầu phiên chạy nền như sản xuất.
- `FF_SITE_AUTO=0` (không kéo website), khóa Blender riêng (`PLATES3D_LOCK` trong thư mục đo — không giữ lượt Blender của máy thật), `BLENDER_PATH` trỏ tệp không có (render nền 3D báo lỗi ngay).
- Meshy đọc khóa cả từ registry Windows (`core/meshy.api_key`) nên lọc môi trường không chặn được; chỉ chạy khi người bấm trong trang quản trị — luồng đo không đi qua.

**3. Phiên trình duyệt**
- N phiên Chromium (Playwright async, mỗi phiên một context) chạy song song.
- Luồng: Trang chủ → `Mở →` dự án (i mod số dự án; vào thẳng Storyboard) → (Storyboard) → `✔ Duyệt` 1 ảnh → Video → `▶ Gen video` (giả).
- Mỗi bước đo tới khi màn **ổn định sau lượt chạy lại MỚI của chính nó** VÀ điều kiện hậu của bước đúng:
  - bộ đếm `MutationObserver` (cả cây, có mốc trang tải lại) theo `data-test-script-state` ∈ {running, rerunRequested, stopRequested}, sau đó cần 3 nhịp yên × 0,1 s;
  - điều kiện hậu: màn đích được chọn trên thanh bước / đã rời Trang chủ / số nút "✔ Duyệt" hoặc nhãn "Duyệt tất cả" đổi / chữ nút Gen đổi. Lượt chạy lại của fragment `run_every` (ô hỏi job đang chạy) không làm bước trả sớm.
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

Lệnh: `py tools/load_test_ui.py --levels 1,2,5,10 --shots 30` (dữ liệu giả 3 dự án × 30 shot, độ trễ giả 0,2 s). Mã thoát 1, vì có bước lỗi (xem phát hiện bên dưới).

### Thời gian tới khi màn ổn định (giây, p50 / p95)

| Bước | N=1 | N=2 | N=5 | N=10 |
|---|---|---|---|---|
| Trang chủ | 3.426 / 3.426 🐢 | 4.537 / 4.605 🐢 | 9.194 / 16.564 ⚠1 lỗi 🐢 | 22.154 / 22.452 ⚠3 lỗi 🐢 |
| Mở dự án (vào thẳng Storyboard) | 3.876 / 3.876 🐢 | 5.411 / 5.488 🐢 | 5.742 / 5.901 ⚠1 lỗi 🐢 | 17.182 / 17.678 ⚠3 lỗi ·1 không rerun 🐢 |
| Storyboard (Bước 2) | đã hiện sẵn sau bước trước | đã hiện sẵn sau bước trước | — / — ·4 đã hiện sẵn ⚠1 lỗi 🐢 | 6.573 / 6.573 ·6 đã hiện sẵn ⚠3 lỗi 🐢 |
| Duyệt 1 ảnh | 3.439 / 3.439 | 5.056 / 5.109 | 5.971 / 7.168 ⚠1 lỗi | 11.83 / 13.008 ⚠3 lỗi |
| Video (Bước 4) | 0.957 / 0.957 | 1.321 / 1.434 | 1.416 / 1.489 ⚠1 lỗi 🐢 | 2.812 / 4.322 ⚠3 lỗi 🐢 |
| Bấm Gen video (giả) | 2.999 / 2.999 | 3.317 / 3.567 | 2.516 / 3.082 ⚠1 lỗi | 3.936 / 9.644 ⚠3 lỗi ·1 không rerun |

### Server (tiến trình Streamlit)

| N | CPU đỉnh % | CPU cả máy đỉnh % | RAM đỉnh MB | Luồng gốc → đỉnh | Luồng thêm / phiên | Lệnh ghi SQLite | Chờ khóa (≥ 0.05 s) | Chờ lâu nhất s | Lỗi locked |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 121.9 | 84.5 | 130.8 | 7 → 29 | 22.0 | 181 | 0 (0.0 s) | 0.0 | 0 |
| 2 | 129.9 | 95.5 | 145.4 | 7 → 37 | 15.0 | 275 | 0 (0.0 s) | 0.0 | 0 |
| 5 | 141.9 | 99.5 | 165.6 | 7 → 51 | 8.8 | 784 | 0 (0.0 s) | 0.0 | 0 |
| 10 | 151.9 | 100.0 | 269.1 | 7 → 59 | 5.2 | 887 | 1 (0.051 s) | 0.051 | 0 |


**Đọc số:**
- CPU cả máy chạm 95–100 % ngay từ N=2. Ở đây trình duyệt đo và Streamlit chạy chung 4 lõi, nên từ N=5 số đo chủ yếu phản ánh máy đo bị bão hòa.
- Trang chủ ở N=1 đã mất 3,4 s, Mở dự án 3,9 s. Ngưỡng 2 s đã vượt từ N=1 trên máy cloud. Hai màn này là ứng viên tối ưu đầu tiên.
- Khóa SQLite: chỉ 1 lần chờ ≥ 0,05 s (0,051 s, ở N=10), 0 lỗi `locked`. Tranh chấp ghi không phải nút thắt khi có ≤ 10 phiên. Cần đo lại khi `DASHBOARD_AUTH` bật vì khi đó mỗi lần chạy lại có thêm lệnh ghi.
- Mỗi phiên thêm khoảng 5 luồng (N=10). RAM tiến trình 131 → 269 MB.
- "Storyboard: đã hiện sẵn": nút "Mở →" vào thẳng màn đang chờ (Storyboard), nên thời gian vẽ Storyboard nằm ở bước Mở dự án.

## ⚠️ PHÁT HIỆN — lỗi thật của sản phẩm (đề xuất cho phiên chính, CHƯA sửa vì đề bài chỉ cho đo)
- **Triệu chứng.** Khi nhiều người mở Dashboard cùng lúc, một số trang hiện màn lỗi đỏ: `sqlite3.OperationalError: trigger trg_scene_noi_chon_new already exists`.
  - Gặp ở 1/5 phiên khi N=5 và 3/10 phiên khi N=10 trong lượt đo trên.
  - Ảnh màn lỗi: `loi_n10/loi_s0_home.png`.
- **Gốc.** Mỗi lần mở kết nối, `core/db.py` `connect()` → `_migrate()` → `conn.executescript(CHANGE_TRIGGERS)` (dòng ~883).
  - Script này gồm các cặp `DROP TRIGGER IF EXISTS x; CREATE TRIGGER x …`.
  - `executescript` chạy từng lệnh ở chế độ autocommit. Hai kết nối chạy song song có thể xen nhau theo thứ tự DROP(A), DROP(B), CREATE(A), CREATE(B), và CREATE(B) lỗi.
  - Các phiên Streamlit mở kết nối đồng thời nên gặp đúng trường hợp này.
- **Tái hiện ngoài trình duyệt** (8 kết nối, barrier, 100 vòng, chạy `executescript(CHANGE_TRIGGERS)` cùng lúc): **208 / 800 lần lỗi** "already exists".
- **Đề xuất sửa** (đã thử trên cùng kịch bản → **0 / 800 lỗi**): bọc script trong giao dịch giữ khóa ghi:
  `conn.executescript("BEGIN IMMEDIATE;\n" + CHANGE_TRIGGERS + "\nCOMMIT;")`.
  Có thể làm thêm: chỉ DROP / CREATE khi `sqlite_master.sql` của trigger khác bản mới, để mỗi lần mở trang khỏi phải ghi.
- **Phạm vi.** Đây là thay đổi `core/db.py`, đụng mọi lần mở CSDL. Phiên chính quyết định và giao việc riêng, kèm test barrier như trên.

## Rà soát (quy tắc 7) — 2 lượt agent, đã sửa hết CAO / VỪA
| Lượt | Mức | Vấn đề | Sửa |
|---|---|---|---|
| 1 | CAO | `--db`: dọn rác Kho (`purge_removed`) xóa FILE thật qua `assets.resolve` (CSDL sao không nằm dưới thư mục `data`) | Bản sao ở `<work>/data/`, `ASSET_DIR` riêng, bỏ hàng ảnh `removed` |
| 1 | CAO | `--db`: `projects/jobs.llm_provider` đè `LLM_PROVIDER=mock` → `claude -p` thật (tốn hạn mức gói) | Làm trơ: NULL / mock |
| 1 | CAO | `settle` trả sớm: chưa tính `rerunRequested` | Bộ đếm lượt chạy lại + trạng thái bận đủ |
| 1 | VỪA | Cổng: health "ok" có thể đến từ Dashboard thật | Từ chối 8501 / 8502, cổng bận; kiểm pid nghe cổng |
| 1 | VỪA | Thiếu khóa: SYNC_API_KEY, MESHY_API_KEY, ANTHROPIC_AUTH_TOKEN… | Bỏ theo mẫu tên |
| 1 | VỪA | Lỗi / timeout bị che trong bảng; luôn trả 0 | Lỗi = chậm, đếm lỗi, mã thoát 1 |
| 1 | VỪA | `DASHBOARD_SYNC_BACKGROUND=0` phồng số; mô hình âm thanh ghi `data/models` của repo | Đồng bộ nền như sản xuất; `SOUND_MODEL_DIR` riêng |
| 1 | VỪA | Đổ oan SQLite (đo gồm chờ GIL) | Xét CPU trước; SQLite theo tổng `wait_s` |
| 1 | VỪA | UTF-8 / tìm Chromium trên Windows | `PYTHONUTF8`; tìm `ms-playwright`, so số bản, rồi Chrome / Edge |
| 1 | THẤP | Đầu dò che sitecustomize gốc; tiến trình con ghi đè probe.json; thiếu `functools.wraps`; URI ro | Nối sitecustomize gốc; xóa biến khỏi môi trường; wraps; `as_uri()` |
| 2 | VỪA | `SO_REUSEADDR` trên Windows bind trùng cổng đang nghe | psutil LISTEN là điều kiện chính; `SO_EXCLUSIVEADDRUSE`; IPv6 |
| 2 | VỪA | Lượt chạy lại của fragment `run_every` làm `settle` trả sớm | Điều kiện hậu từng bước |
| 2 | VỪA | `.stApp` bị thay / trang tải lại | Theo dõi cả cây + mốc `timeOrigin` |
| 2 | VỪA | `--db`: phân tích âm thanh thật N lần, kéo website, khóa Blender chung máy | Làm trơ `sounds`; `FF_SITE_AUTO=0`; `PLATES3D_LOCK` / `BLENDER_PATH` riêng |
| 2 | THẤP | SKIP ở home vẫn chờ 10 s; SKIP một phần không đếm; nút "Mở →" trùng chữ; đầu dò nối đệ quy; cổng thật kiểm sau 15 s | Sửa hết |

**Ghi nhận, không sửa:**
- Meshy đọc khóa từ registry Windows; luồng đo không đi qua.
- Kho ảnh không được chép.
- "Luồng thêm / phiên" tính cả các luồng khởi một lần mỗi tiến trình.
- Mỗi số đo gồm ~0,3 s cửa sổ yên.
- Trình duyệt đo chạy cùng máy với server: chạy từ máy khác (`--url`) là việc của phiên sau.

## Test
- `tests/test_load_test_ui.py`: 23 test nhanh + 1 test chạy Chromium thật (N=1, đánh dấu `slow`) → **24 xanh**.
- Các test nhanh gồm: dữ liệu giả 3×20, sao CSDL `mode=ro` (đường dẫn có `#%?`), làm trơ, môi trường chỉ có provider giả và bỏ khóa theo mẫu, đầu dò (đo chờ khóa thật ~0,3 s, không làm gì khi thiếu biến, ẩn biến khỏi tiến trình con, nối sitecustomize gốc đúng một lần, giữ chữ ký hàm), `settle` (rerunRequested, fragment, tải lại trang, không rerun), cổng (bận / 8501 / psutil), tổng hợp (ngưỡng chậm, lỗi = chậm, CPU / SQLite, đã hiện sẵn), `find_chrome` so số bản.
- `tests/test_ui_snapshot.py` xanh, vì tham số mới `rich_others` mặc định None giữ hành vi cũ.
- Đã đăng ký `tools/load_test_ui.py` và test vào khu vực `diag` (`devsys/areas.json`).
- Full suite (cloud 3.13, `-m "not slow" -n auto`): **7111 passed**. 25 đỏ đều là golden cần native Python 3.14 (nền).

## C-FIX5 (22/10) — rà VỪA: bản sao `--db` còn đường tới tệp THẬT
- **Lỗi.** `neutralize` chỉ làm trơ hàng (ảnh Kho đã xóa, nguồn auto, Claude theo dự án). `jobs.result_path`, `sent_package`, ảnh Kho, plates… vẫn trỏ về dữ liệu thật, hoặc tuyệt đối, hoặc tương đối `data/…` giải theo cwd = repo. Luồng duyệt ảnh / Gen video giả / dọn rác có thể thay hoặc dời tệp thật theo các đường đó.
- **Sửa.** `relocate(db, real_homes, new_home)` chạy ở MỖI mức đo, trên bản chép CSDL của mức đó:
  - quét MỌI cột chữ của MỌI bảng, kể cả JSON;
  - tiền tố thư mục data thật → `<work>/data` của mức. Thư mục data thật gồm thư mục chứa CSDL và `--data` cùng thư mục cha của nó; đổi cả dạng dấu xuôi, dấu ngược, và dấu ngược đã thoát trong JSON;
  - `data/…` tương đối (đứng đầu, sau dấu nháy hoặc khoảng trắng) → `<work>/data/…`;
  - đường không thuộc data thật thì giữ nguyên (ví dụ `/khac/data/x`, `metadata/…`).
  - Số hàng đổi được in ra log của mức.
- **Test:**
  - `test_relocate_moves_every_real_path_into_the_copy`: tuyệt đối dấu xuôi + dấu ngược, JSON, tương đối; giữ đường khác.
  - `test_copy_db_names_the_real_homes`.
  - `test_a_measured_run_on_a_real_copy_never_touches_the_real_files` (slow, Chromium thật, `--db` + `--data` với `result_path` TUYỆT ĐỐI tới tệp thật): sau lượt đo, danh sách + mtime tệp thật không đổi, và CSDL của mức không còn đường tới data thật. Tắt `relocate` thì test này ĐỎ (CSDL mức đo còn đường thật).
- **Rà quy tắc 7 (C-FIX5), đã sửa:**

  | Mức | Lỗi | Sửa |
  |---|---|---|
  | VỪA | UPDATE kích trigger sản xuất (`trg_change_scene` → thay đổi chờ rà giả, đồng bộ `noi_chon`) | Gỡ trigger của BẢN SAO trong lúc đổi, tạo lại đúng câu cũ |
  | VỪA | Bảng chỉ-thêm (`ticket_events` ABORT) / lỗi CHECK làm sập lượt đo | Bỏ qua bảng lịch sử ticket; lỗi từng hàng đếm `_skipped` |
  | VỪA | Windows hoa / thường, realpath; thư mục thật chỉ gồm thư mục CSDL | Thay không phân biệt hoa / thường khi `nt`; thêm realpath; luôn thêm `data/` của repo, `PIPELINE_DATA`, `ASSET_DIR`; quét lại và báo `_leaks` |
  | THẤP | `--data` ánh xạ sai; thư mục gốc / rỗng thay mọi chuỗi; không ranh giới (`data2`); "data/ trong câu"; lọc kiểu cột sót | `--data` → `projects/`; bỏ gốc / rỗng; ranh giới đường; `data/` phải theo sau là ký tự tên tệp; mọi giá trị chữ |
  | THẤP (phát hiện khi test) | Bản sao nằm TRONG một thư mục thật → thay nhiều lượt thay lại chính kết quả | Một lượt thay bằng regex gộp |

- **Không đổi bảng thư viện Kho / âm thanh** (`SKIP_TABLES`):
  - Lý do: lúc đo các bảng này chỉ được đọc (dọn rác và đồng bộ đã làm trơ); lineage băm đường ảnh Kho, nên đổi đường sẽ làm mọi ảnh đã duyệt thành "cũ", số đo lệch máy thật.
  - Đường của chúng không tính vào `_leaks`.
- `tests/test_load_test_ui.py`: 30 xanh, gồm 2 test slow chạy Chromium. 4 test mới của lượt rà ĐỎ trên bản trước sửa.
