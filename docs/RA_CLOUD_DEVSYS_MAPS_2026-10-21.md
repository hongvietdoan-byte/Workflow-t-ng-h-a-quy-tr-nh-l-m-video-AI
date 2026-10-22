# C-DEVSYS-MAPS — 3 sơ đồ dây chuyền SỐNG trên AI Dev System + tab Thay đổi + tô theo dự án thật (cloud-C, 21/10)

- Nhánh: `cloud/v31-devsys-maps`, tạo từ origin/main.
- 0 USD. Không migration. CSDL thật chỉ đọc (mode=ro) ở phía devsys.
- Cờ mới `ui_step_log`:
  - mặc định TẮT, `verified: False`;
  - nằm trong `OPT_IN_ONLY`, nên preset Thử nghiệm không tự bật;
  - golden đặt `false`.

## Ảnh xuất (21/10, trên main hiện tại)
`docs/so_do/song_2026-10-21/` gồm `so_do_dashboard`, `so_do_hien_trang_khau`, `so_do_truong_cau_truc` (.svg + .png). Xuất lại bằng: `py -m devsys.pipeline_maps <thư mục>`.

| Sơ đồ | xanh | vàng | đỏ | tím | khác mốc 17/10 |
|---|---|---|---|---|---|
| Làm phim qua Dashboard (28 ô + 4 việc ngoài) | 12 | 11 | 2 | 3 | 5 |
| Hiện trạng khâu (16 hàng) | 2 | 2 | 8 | 4 | 6 |
| Trường cấu trúc (21 nút) | 6 | 6 | 7 | 2 | 5 |

- Ô "Xem GÓI trước khi gửi": mốc đỏ → nay **vàng**. Đã có `dashboard/send_preview_ui.py` nhưng cờ `send_preview_panel` TẮT.
- Các nút trường đọc BYĐ (dạng, vật, mốc nền…) vẫn **đỏ**: M2.1 / M2.2 chưa gộp main. Nhánh tích hợp M2 gộp xong thì tự đổi màu.

## Đã làm
1. **Dữ liệu tách khỏi code** — `devsys/pipeline_maps.json`:
   - giữ nguyên chữ + màu 17/10 làm `moc`;
   - mỗi ô / nút có: khâu (L…), việc kế hoạch (`plan`), cờ, `evidence` (tệp glob + chữ phải có), khóa nút `ui` (= tên thao tác `log_ui`), công cụ CLI liên quan.
   - Test dựng lại đủ số ô của 3 SVG cũ: đọc AST của `gen_dashboard.py` (28 ô + 4 việc ngoài) và `gen_hien_trang_khau.py` (16 hàng); mỗi nhãn nút trường có trong SVG mốc.
2. **Màu TÍNH** — `devsys/pipeline_maps.py`, thứ tự ưu tiên:
   - thiếu bằng chứng → đỏ;
   - việc kế hoạch 🔄 → tím;
   - cờ hiệu lực tắt / ô "lỏng" (chỉ người, theo nút) / việc chưa ✅ → vàng;
   - còn lại → xanh.
   - Hàng khâu: theo `stages.effective` (cờ thật) như sơ đồ 17/10, cộng tím theo `plan_map.json`, cộng lỗi mở theo `errors.json`.
   - Cờ hay mã việc không tồn tại → cảnh báo, không im lặng (vd `stage_view_ui` chưa có trên main).
3. **Theo dõi thay đổi:**
   - mỗi lần mở trang, nếu có ô đổi thì ghi ảnh chụp (màu + đầu vào) vào `devsys/data/pipeline_maps_history.jsonl` (đã gitignore);
   - tab **Thay đổi** liệt kê:
     - ô đổi màu so với lần ghi trước, kèm lý do: việc ⬜→✅, cờ off→on, bằng chứng có / mất, lỗi mở;
     - ô khác mốc 17/10;
   - lọc được theo khâu; có công tắc kèm commit cuối của tệp bằng chứng (`git log`, chỉ chạy khi bật).
4. **Trang 8502 "🧭 Sơ đồ dây chuyền"** (`devsys/app.py`): 4 tab (Làm phim qua Dashboard · Hiện trạng khâu · Trường cấu trúc · Thay đổi), chọn dự án, khung cảnh báo các ô đỏ / vàng của dự án. Có test AppTest.
5. **Ghi từng bước bấm** (`core/ui_step.py`, cờ `ui_step_log`):
   - Dashboard: hàm chung `C.log_ui` (nhật ký thao tác có sẵn ở ~31 nút) ghi thêm sự kiện `ui_step` trên CÙNG kết nối riêng của nó, nên không commit giữa giao dịch của trang;
   - nút Gen ảnh báo `hold` (ảnh chờ điều kiện) / `skip` (vẫn gen dù cổng chặn);
   - nút Viết motion dùng `C.log_step` (chỉ `ui_step`; cờ tắt thì không mở kết nối);
   - CLI ghi sự kiện `cli_step`:
     - `tools/stage_auto.py` — bỏ qua các chế độ chỉ đọc `--beats`, `--score`, `--prompt-out`, `--dry`;
     - `tools/stage_previs.py` — chỉ ghi sau khi lượt chạy hợp lệ;
     - `tools/replay_payload.py` — ghi MỘT dòng vào CSDL thật sau sandbox, chỉ khi cờ BẬT ở chính máy `--main`; docstring đã ghi rõ ngoại lệ này.
   - Lỗi ghi không bao giờ làm hỏng nút hay lệnh.
6. **Tô theo dự án:**
   - ô nút theo lần bấm MỚI NHẤT: lỗi → đỏ (kèm mã), cảnh báo / giữ → vàng (số lần + câu mới nhất, tooltip), ổn → xanh, chưa ai bấm → xám;
   - `cli_step` → nút ảo nét đứt "THIẾU NÚT: <việc>" ở đúng cột màn, đếm số lần, có đường nối tới làn ngoài Dashboard.

## Test — `tests/test_devsys_pipeline_maps.py` (22 ca, commit đỏ trước rồi xanh)
- Màu ô:
  - bằng chứng + cờ bật + việc ✅ → xanh;
  - tắt cờ → vàng;
  - xóa hàm bằng chứng → đỏ;
  - việc 🔄 → tím.
- Lịch sử: việc ⬜→✅ → ghi đúng 1 dòng thay đổi kèm lý do; không đổi gì → không ghi.
- Mốc 17/10 dựng lại đủ ô của 3 SVG cũ.
- Tô theo dự án:
  - hold ở Gen ảnh → vàng (đếm 2 lần);
  - lỗi → đỏ kèm mã;
  - không ai bấm → xám;
  - `cli_step` stage_auto → nút ảo nét đứt ở cột STORYBOARD.
- Cờ `ui_step_log` TẮT → CSDL không đổi byte; lỗi ghi không làm hỏng nút.
- CSDL mở mode=ro (không tạo tệp).
- Trang 8502 vẽ đủ 4 tab + 3 SVG.
- Đã sửa 2 test có sẵn:
  - `test_tickets_page` (danh sách trang ghim cứng): thêm trang mới;
  - `test_diag` (stage phải biết): cộng `diag.OBSERVE`.

## Rà khâu liên quan (luật 7) — agent báo 13 mục, đã xử lý
- **CAO:**
  - stage `ui_step` / `cli_step` lọt vào panel ⚙ Chẩn đoán ("Khác"), trang Sức khỏe devsys và đề xuất sổ lỗi (`tools/project_error_report`). Đã sửa: thêm `diag.OBSERVE`, rồi lọc ở `stage_table` / `recent` / `repeated`, `devsys/collect.diag_summary` và `project_error_report`;
  - `skip` từng bị ghi mức error. Đã sửa: nay là warn.
- **VỪA:**
  - `replay_payload` đọc cờ của repo đang chạy lệnh thay vì của máy chính. Đã sửa: đọc tệp 🧪 của `--main`;
  - CLI ghi cả khi chạy ở chế độ chỉ đọc hoặc khi lệnh thoát lỗi. Đã sửa;
  - preset Thử nghiệm có thể tự bật cờ. Đã sửa: thêm vào `OPT_IN_ONLY`;
  - ô đã đỏ một lần thì đỏ mãi. Đã sửa: tô theo lần bấm mới nhất;
  - `git log` chạy mỗi lần mở trang. Đã sửa: chỉ chạy khi bật công tắc.
- **THẤP:**
  - nút motion từng ghi `ui_actions` kể cả khi cờ tắt. Đã sửa: dùng `log_step`;
  - `diag.record` thử lại khi CSDL khóa có thể làm nút chậm ~1,2 s trong trường hợp xấu nhất (chỉ khi cờ bật). Chưa sửa, ghi nhận lại;
  - chưa nút nào truyền `error_code`. Đã có tham số, mã sổ lỗi sẽ thêm khi nút biết mã;
  - cờ `stage_view_ui` chưa có trên main nên có cảnh báo. Đúng thực tế: tự hết khi C-STAGE-VIEW được gộp.

## Bộ test đầy đủ (cloud Linux, Python 3.13)
`6869 passed`. 25 đỏ, đều là golden (cần Python 3.14 — máy chính). Không có đỏ mới.

## Phiên chính
1. Gộp nhánh, rồi khởi động lại 8502 trên máy chính. Mở "🧭 Sơ đồ dây chuyền", gửi ảnh cho người dùng.
2. Muốn tô theo dự án thật: bật cờ `ui_step_log` ở 🧪, bấm thử vài nút trên dự án, chọn dự án trên trang.
3. Cập nhật `devsys/pipeline_maps.json` khi một ô đỏ đã có hàm thật. Ví dụ ô BYĐ: đổi `evidence` sang tên hàm thật của M4.7 khi có.
