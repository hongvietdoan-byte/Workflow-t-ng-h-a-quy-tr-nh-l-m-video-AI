# 📨 Hộp thư sự kiện

Các phiên (phien-chinh, cloud-B/C/D, codex, nguoi-dung, phien-con-*) phối hợp qua git bằng `tools/hop_thu.py`.
Mỗi sự kiện là một file JSON trong `hop_thu/su_kien/`; trạng thái việc tính lại từ toàn bộ sự kiện.
Windows dùng `py`, Linux dùng `python3`; nên đặt `PYTHONUTF8=1`.

## Luật

1. **Mỗi sự kiện một file, không bao giờ sửa hay xóa file cũ.** Muốn đổi thì ghi sự kiện mới (giao lại, bo…).
2. **Pull trước khi đọc hoặc nhận việc** (`nhan` tự `git pull`; `ke --nhan` cũng vậy).
3. **Mọi làn được push thẳng `main`** commit `hộp thư: <kind> <mã> (<lane>)` bằng `--push`, nhưng commit đó **chỉ chứa
   file trong `hop_thu/su_kien/`**. Khi đang ở nhánh khác, công cụ dựng commit riêng chỉ có file sự kiện trên đỉnh
   `origin/main`, nên không đẩy code của nhánh lên main. Không bao giờ force; thử lại tối đa 3 lần.
4. Nhận trùng: sự kiện `nhan` có `ts` sớm nhất thắng, các lần nhận sau ghi "nhận trùng — bỏ".
5. Việc có `depends` chỉ nhận được khi mọi việc trong đó đã **GỘP**.
6. File JSON hỏng được báo rõ tên (không bỏ qua im lặng); thay nó bằng một sự kiện mới.

Trạng thái: CHỜ (hoặc CHỜ ĐIỀU KIỆN) → ĐANG LÀM → XONG (chờ gộp) → GỘP; hoặc BỎ.

## Lệnh (thêm `--push` để commit + push; không có thì chỉ ghi file)

- `py tools/hop_thu.py giao C-M42 --to cloud-C|pool --title "…" --spec "docs/CLOUD_TASKS.md#### C-M42" [--depends A,B] [--priority 1] --lane phien-chinh` — giao việc (giao lại cùng mã cho làn khác = đổi chủ).
- `py tools/hop_thu.py nhan C-M42 --lane cloud-C` — nhận việc; từ chối (mã 1) nếu đã có người nhận, giao cho làn khác hoặc depends chưa GỘP.
- `py tools/hop_thu.py xong C-M42 --lane cloud-C --branch claude/x --commit abc123 [--report docs/…] [--text …]` — báo xong, chờ gộp.
- `py tools/hop_thu.py gop C-M42 --lane phien-chinh --commit def456` — phiên chính báo đã gộp.
- `py tools/hop_thu.py bo C-M42 --lane phien-chinh --text "lý do"` — bỏ việc.
- `py tools/hop_thu.py hoi --lane cloud-B --to phien-chinh --text "…" [--task M]` — hỏi.
- `py tools/hop_thu.py tra-loi <file-sự-kiện-hỏi>.json --lane phien-chinh --text "…"` — trả lời.
- `py tools/hop_thu.py tin --lane cloud-D --to all --text "…"` — tin chung.
- `py tools/hop_thu.py het-viec --lane cloud-D` — báo làn hết việc.
- `py tools/hop_thu.py bang [--lane cloud-C]` — bảng markdown: theo làn, pool, câu hỏi chưa trả lời, làn HẾT VIỆC, 10 tin mới nhất.
- `py tools/hop_thu.py ke --lane cloud-C [--nhan]` — việc kế: việc riêng đủ điều kiện (ưu tiên rồi giờ giao) → pool → "HẾT VIỆC".

Test: `py -m pytest tests/test_hop_thu.py`.

## Cảnh báo tiến độ commit (G3)

`bang` chỉ đọc và cảnh báo việc ĐANG LÀM quá 12 giờ chưa có commit riêng mới
trên nhánh ngoài `origin/main`; không tự đưa về CHỜ. Người điều phối phải kiểm
owner và tiến độ trước khi giao lại. Commit đã nằm trong main không tính là
commit riêng của việc đang mở. Chỉ xét refs hiện có: hãy fetch trước khi đọc
nếu cần cập nhật remote, `bang` không tự fetch hoặc sửa refs.

Khi biết nhánh, có thể dùng `nhan <mã> --lane codex --branch codex/<việc>`
hoặc `tin --lane codex --task <mã> --branch codex/<việc> --text "Codex 1: …"`.
`ke --nhan` cũng nhận `--branch`. Tin chỉ cập nhật nhánh khi lane đang giữ việc;
tin tiến độ không đặt lại giờ nhận. Lệnh cũ không có `--branch` vẫn tương thích.
Không suy nhánh hoặc phiên Codex 1/2/3 từ lane/tên việc/văn bản tự do. Thiếu
metadata, ref chưa có, lỗi Git hoặc thời gian commit ở tương lai được báo
**chưa xác minh**, không coi là bằng chứng task không hoạt động.
