# 📨 Hộp thư sự kiện

Các phiên (phien-chinh, cloud-B/C/D, codex, nguoi-dung, phien-con-*) phối hợp qua git bằng `tools/hop_thu.py`.
Mỗi sự kiện là một file JSON trong `hop_thu/su_kien/`; trạng thái việc tính lại từ toàn bộ sự kiện.
Windows dùng `py`, Linux dùng `python3`; nên đặt `PYTHONUTF8=1`.

## Luật

1. **Nội dung sự kiện bất biến.** Muốn đổi thì ghi sự kiện mới (giao lại, bo…). Chỉ được chuyển file lẻ vào archive theo lệnh `luu-tru --apply` sau khi kiểm bản sao và receipt; ID/reply_to giữ nguyên.
2. **Đồng bộ metadata trước khi nhận việc.** `nhan`, `ke --nhan`, `da-doc`, `luu-tru` tự fetch hộp thư vào cache riêng; không rebase/autostash/checkout/index thật. Lỗi đồng bộ thì dừng, không nhận/ack/archive trên state cũ. `--khong-pull` là lựa chọn tường minh tương thích. Kéo code/đề bài bằng `git pull --ff-only` vẫn thuộc quy trình ngoài sau kiểm cây sạch.
3. **Mọi làn có thể đẩy metadata hộp thư bằng `--push`**, nhưng commit chỉ chứa manifest whitelist `hop_thu/{su_kien,luu_tru,da_doc}`. Cả main và nhánh riêng đều dùng index tạm/commit-tree từ ref origin/main pin riêng; không đẩy code HEAD/staged của checkout. Không force, retry dựng lại union tối đa 3 lần; chỉ bỏ queue sau xác minh remote đã chứa lô.
4. Nhận trùng: sự kiện `nhan` có `ts` sớm nhất thắng, các lần nhận sau ghi "nhận trùng — bỏ".
5. Việc có `depends` chỉ nhận được khi mọi việc trong đó đã **GỘP**.
6. File JSON hỏng được báo rõ tên (không bỏ qua im lặng); thay nó bằng một sự kiện mới.

Trạng thái: CHỜ (hoặc CHỜ ĐIỀU KIỆN) → ĐANG LÀM → XONG (chờ gộp) → GỘP; hoặc BỎ.

## Lệnh (bốn loại sự kiện khẩn tự đẩy lô trong repo Git)

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

## Đọc theo phiên, lịch sử và bảng gọn

- `bang` mặc định chỉ hiện việc active, mỗi mã một dòng có trạng thái, người giữ, nhánh/commit và tin gần nhất. `bang --tat-ca` thêm GỘP/BỎ; `lich-su <mã>` luôn đọc đầy đủ cả sự kiện đã archive.
- `chua-doc --lane codex --reader codex1` (hoặc codex2/codex3) hiển thị exact ID và lưu snapshot cục bộ sau khi in thành công. Ba phiên đọc độc lập; lane khác mặc định reader bằng lane.
- `da-doc --lane codex --reader codex1 [--den <id>] [--push]` chỉ xác nhận phần snapshot đã hiển thị, không xác nhận tin mới đến muộn/backdated. Codex thiếu reader bị từ chối. `bang` chỉ đếm, không tạo/ghi đè snapshot hay tự xác nhận.
- Receipt bất biến trong `hop_thu/da_doc/<reader>/`: event ID + hash + người đọc + ngày đọc; hai phiên cùng đọc được hợp bằng receipt riêng, không ghi đè ngày cũ. Nhãn người giữ Codex chỉ hiện phiên khi `nhan/ke --nhan --reader` có khai; thiếu thì báo chưa xác minh phiên, không đoán theo văn bản.
- Broadcast mới `to=all` lưu danh sách reader lúc tạo sự kiện; lane xuất hiện về sau, kể cả timestamp backdated, không được gán hồi tố. Broadcast legacy thiếu snapshot là **UNKNOWN**: hiện unread bảo thủ cho người đọc, luôn giữ raw khi archive; không sửa nội dung sự kiện cũ để đoán người nhận.

## Queue và đẩy lô

Tin thường không có `--push` chỉ ghi file/queue cục bộ. Trong repo Git, `hoi/xong/gop/giao` tự đẩy toàn bộ queue ngay cả không có `--push`; dùng `--khong-day` để soạn offline/local. Hai cờ `--push` và `--khong-day` loại trừ nhau. Thư mục không phải repo Git chỉ lưu local và in rõ trạng thái này. `day-lo` đẩy mọi metadata pending trong một commit; mọi lệnh cũ có `--push` vẫn đẩy ngay. Queue/snapshot/cache nằm trong git-dir của worktree, không vào commit và không là receipt đã đọc. Nếu đẩy tự động thất bại, lệnh trả lỗi và giữ queue, không báo đã gửi.

Nếu push/fetch/xác minh remote lỗi thì queue còn nguyên để thử lại. Hai writer dùng ref/index/thư mục operation riêng; archive JSONL hợp theo ID, cùng ID cùng nội dung dedupe, khác nội dung hoặc JSONL hỏng báo rõ và chặn ghi. Không stage/code commit của người dùng.

Network Git giữ whitelist đường dẫn hệ thống/HOME/USERPROFILE/APPDATA/LOCALAPPDATA/SSH agent để dùng đăng nhập Git chuẩn đã có; không chuyển API key/token hay toàn bộ môi trường. Index/commit-tree dùng HOME/config riêng và danh tính bot không bí mật. Test chỉ dùng HOME giả/config global vô hiệu và remote bare tạm.

## Archive an toàn, mặc định chỉ xem

`luu-tru` là dry-run; `luu-tru --apply [--push]` mới chuyển metadata. Chỉ việc GỘP/BỎ quá 3 ngày hoặc tin thường đã được đọc quá 3 ngày, với đủ receipt cho mọi reader đã xác minh, mới được chuyển vào `hop_thu/luu_tru/yyyy-mm.jsonl`. Câu hỏi chưa trả lời, tin chưa đọc, pool/recipient UNKNOWN luôn giữ raw. Reader Codex cần đủ ba phiên.

Trước unlink: kiểm đường dẫn/ancestor không symlink/junction, ghi + flush/fsync archive, nạp lại và so hash/ID, kiểm nguồn chưa đổi, rồi mới bỏ file lẻ. Ngắt giữa copy/unlink có thể chạy lại; active + archive + cache remote luôn được đọc hợp, ID/reply_to và bảng/lịch sử/unread giữ nguyên. Không chạy archive/ack trên hộp thư sản xuất trong QA; chỉ fixture.

Cache blob theo OID Git được kiểm hash. Đồng bộ lại cùng SHA dùng cache, không gọi `cat-file` từng blob lần nữa; lượt lạnh vẫn cần đọc mỗi blob lần đầu. Chưa có benchmark latency trên hộp thư sản xuất nhiều nghìn receipt.

## Đẩy lô và phục hồi khóa

`flush` kiểm hợp raw/archive/receipt trong bộ nhớ, chỉ đưa phần metadata thay đổi vào Git index riêng. Cache đọc remote dùng bundle nguyên tử, không dựng lại hàng nghìn file sự kiện để kiểm một lô nhỏ. Event nguồn vẫn bất biến; xác minh remote có commit thành công rồi mới bỏ đúng manifest pending.

Khóa có PID, định danh lần chạy, token và thời điểm gia hạn. Khi chủ đã chết hoặc lease quá 10 phút không gia hạn, helper chuyển khóa cũ vào `_luu_tru` trong cache metadata và báo PID trước khi nhận khóa mới. Khóa còn sống và đang gia hạn được giữ. Không xóa khóa bằng tay hoặc dùng PID làm bằng chứng duy nhất khi PID có thể được tái sử dụng.

Nếu hết thời gian chờ khóa, lệnh `--push` giữ sự kiện trong pending, trả mã 0 và báo **“đã xếp hàng, lô sau sẽ đẩy”**. Mã 0 trong trường hợp này chỉ xác nhận đã xếp hàng, chưa xác nhận có trên remote. Lỗi dữ liệu/whitelist/xung đột ID hoặc lỗi Git thật vẫn báo lỗi và giữ queue; không đổi thành thông báo đã gửi.

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
