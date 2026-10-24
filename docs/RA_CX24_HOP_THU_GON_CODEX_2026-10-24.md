# CX24-HOP-THU-GON — hộp thư gọn, không bỏ sót tin

Nhánh `codex/v31-hop-thu-gon`; nền `origin/main` 2d8958cb + dependency G3 90639aeb được cherry-pick có chủ ý thành 61e0d61f. Không làm lại G3 hoặc tự kéo main mới vào WIP. Chi phí API 0 USD; chỉ fixture/repo bare tạm, không archive/ack thư thật, không đọc data dự án/dashboard.env/credential, không Computer Use hay restart live.

## Phạm vi đã triển khai

| Mục spec | Hành vi |
|---|---|
| Bảng gọn | `bang` giữ bộ lọc active mặc định, mỗi mã một dòng, có người giữ/reader đã khai, nhánh/commit và tin gần nhất. `--tat-ca` thêm GỘP/BỎ; `lich-su <mã>` đọc toàn bộ active + archive + metadata remote. Thiếu reader Codex ghi chưa xác minh phiên. |
| Không sót tin | Codex có ba reader tường minh codex1/2/3; lane khác reader mặc định bằng lane. `chua-doc` chỉ lưu snapshot exact IDs/hash sau khi in/flush thành công. `da-doc [--den id]` chỉ ack snapshot đó, không ack tin mới/đến muộn/backdated. `bang` chỉ đếm, không ghi đè snapshot. |
| Receipt | `hop_thu/da_doc/<reader>/event--nonce.json` bất biến: ID/hash/lane/reader/read_at. Receipt riêng không ghi đè ngày cũ; hai tiến trình hợp receipt theo file riêng. Broadcast mới đóng băng recipients lúc writer tạo; broadcast legacy UNKNOWN luôn hiện unread bảo thủ và không được archive. |
| Archive | `luu-tru` mặc định dry-run, `--apply` mới chuyển. Đủ ba ngày + tất cả receipt đủ tuổi, việc đã GỘP/BỎ đủ tuổi; hỏi chưa trả lời, unread/pool/UNKNOWN giữ raw. JSONL `{id,event}` giữ filename ID/reply_to, dedupe cùng ID/nội dung; khác nội dung/JSONL hỏng báo lỗi rõ và chặn ghi. |
| Copy trước xóa | Kiểm containment và mọi ancestor symlink/junction trước metadata read/write/unlink; ghi + flush/fsync, đọc lại/hash bản sao và kiểm nguồn chưa đổi trước unlink. Ngắt giữa copy/unlink chạy lại được; source-only trong remote cache cũng có thể chuyển an toàn. |
| Queue/đẩy lô | Tin thường không `--push` nằm queue local. Trong Git, hoi/xong/gop/giao tự flush cả lô dù không `--push`; `--khong-day` opt-out local loại trừ `--push`. Nongit chỉ local và in rõ. `day-lo` hoặc mọi `--push` vẫn flush cả lô. Push lỗi trả lỗi, giữ queue, không báo đã gửi. Manifest chỉ whitelist su_kien/luu_tru/da_doc. Mọi nhánh, kể cả main, dùng temp index/commit-tree từ ref fetch UUID riêng, không HEAD/index/staged code thật, không force. Retry hợp remote archive/events/receipts; giữ queue đến khi xác minh remote chứa commit. |
| Đồng bộ đọc | API `git_pull` cũ giờ fetch + cache metadata nguyên tử theo ref pin riêng; không rebase/autostash/checkout hay kéo code. Lỗi sync làm nhận/ack/archive dừng rõ; `--khong-pull` giữ lựa chọn tường minh. Cache blob theo OID được kiểm Git blob hash; SHA không đổi không gọi lại cat-file từng blob. |

`tools/hop_thu_store.py` là module standard-library riêng; `tools/hop_thu.py` giữ API/lệnh legacy. Không tạo ACL hoặc suy reader từ tiêu đề/văn bản. Mỗi broadcast mới lưu danh sách reader ở thời điểm tạo; thêm lane tương lai hoặc backdated không đổi recipients cũ. Legacy UNKNOWN không được coi đã xác minh đủ người nhận chỉ vì những lane đang có đã đọc.

Network Git giữ whitelist đường dẫn PATH/SystemRoot/HOME/USERPROFILE/APPDATA/LOCALAPPDATA/TEMP/SSH agent cần cho đăng nhập Git chuẩn; không truyền API key/token/toàn bộ môi trường. Git riêng dựng index/commit dùng HOME/config NUL và identity bot tường minh. Không hardcode credential helper hay yêu cầu khóa CLI. QA thay OBJECT os.environ bằng dict giả trước import/call/spawn; native chỉ HOME giả/config global off và remote bare riêng. Log timestamp/control field hỏng chỉ có ID/path và lý do hằng, không echo giá trị payload hỏng.

## Test và đo

- RED builder trước production store: **6 failed / 0,77 s** (exact-ID/hash snapshot, archive/HOLD, collision/JSONL hỏng, fsync trước unlink). GREEN mốc đầu: **8 passed / 1,58 s**, gồm hai acceptance CLI đầu của root.
- Root RED CLI độc lập: **2 failed / 0,88 s** trước CLI; bổ sung broadcast backdated mới RED **1 failed, 2 passed / 1,95 s**; malformed priority không echo RED **1 failed / 0,54 s**. Assertions giữ yêu cầu không mất tin; broadcast mới đi qua writer thật, legacy UNKNOWN có ca riêng.
- Hồi quy builder mốc đầu: **43 passed, 2 skipped / 160,77 s**: storage/CLI, hai native hai-process (batch và archive/receipt), legacy `test_hop_thu` và G3 stale. Lượt này trước các sửa cache OID/control validation cuối, không gọi là chứng nhận cuối toàn bộ.
- Focused sau vòng gom: **37 passed, 2 skipped / 57,01 s**: store, CLI acceptance root, G3 stale, native hai-process archive/receipt union và native same-SHA cache. Native archive có barrier để hai writer cùng pin base cũ: một thành công lượt 1, một retry lượt 2; remote còn đủ ba ID, raw đã chuyển, receipt vẫn làm unread bằng 0.
- Root native acceptance độc lập: **1 passed / 44,65 s**. Hai process thật: A ở feature HEAD có code riêng + staged, B main có staged; 9 sự kiện mới chỉ tạo **2 remote commits**, remote đủ 11 IDs gồm hai seed, không code lọt vào main, HEAD/index cả hai giữ nguyên. Không cộng trùng với native builder: builder cũng đo hai lô 3 sự kiện → 2 commit (thay vì 6 commit từng sự kiện).
- Root focused CLI + G3 stale cuối: **16 passed / 9,89 s**, ghi riêng, không cộng thành số ca duy nhất với nhóm builder. Có priority sentinel không echo, recipient future/backdated, legacy UNKNOWN và snapshot/reader độc lập.
- Hai skip chỉ là tạo symlink thật trên Windows thiếu quyền. Hai ca guard ancestor giả lập không cần quyền vẫn kiểm atomic write không được gọi; không tuyên bố đã chạy physical symlink thật trên máy này.
- Store bổ sung: push lỗi/xác minh remote lỗi giữ manifest; ref fetch riêng không bị FETCH_HEAD lệnh khác đổi; cache OID hỏng fail rõ; stdout gián đoạn không lưu snapshot chưa hiện; repeat ack không sửa receipt; `--den` chỉ prefix đã hiện; auth paths giả giữ nhưng API key giả không truyền subprocess.

## Vòng rà và giới hạn

Đã gom các finding root/reviewer: (1) symlink ghi trước kiểm queue; (2) recipient toall suy hồi tố bằng timestamp; (3) echo timestamp/priority hỏng; (4) thiếu identity khi repo chỉ có global config; (5) FETCH_HEAD dùng chung; thêm giữ auth Git chuẩn và cache OID. Reviewer độc lập đã xác nhận **0 P1/P2** ở hai sửa cuối; root đọc lại fixdiff lần hai và chốt **0 P1/P2**.

Không benchmark latency trên hộp thư sản xuất hàng nghìn receipt; cache unit/native chứng minh lần sync thứ hai cùng SHA không gọi lại cat-file, lượt lạnh vẫn đọc mỗi blob lần đầu. Cache/snapshot/queue nằm git-dir worktree, không nằm manifest gửi. Nếu process bị kill khi giữ lock local, thao tác sau timeout báo rõ và không xóa nguồn/queue; việc dọn lock mồ côi cần kiểm process sở hữu trước. Chưa xây cơ chế tự lấy lại lock khi process chết để tránh phá writer đang chạy.

Không sửa `hop_thu/LICH_DIEU_PHOI.md` hoặc lịch đang chạy. Không chạy archive/ack/push lô trên hộp thư thật trong QA. Phiên tích hợp còn chạy bộ bắt buộc, xử lý union areas/TODO và gộp main theo quy ước; nhánh này giữ version areas 92. Không thêm HANDOFF WIP vào commit hoàn tất.

## Đề xuất cập nhật LICH_DIEU_PHOI cho phiên chính áp dụng

1. Bước 2, sau fetch code theo quy trình hiện hành: chạy `chua-doc --lane phien-chinh`, đọc đủ tin; chỉ sau đó `da-doc --lane phien-chinh --den <ID cuối thực sự đã đọc>` (có thể để queue rồi đẩy cùng sự kiện khẩn). `bang` chỉ tóm tắt tiến độ/chưa đọc, không thay bước đọc/ack.
2. Với ba phiên Codex, mỗi phiên dùng đúng `--lane codex --reader codex1|codex2|codex3` của mình cho cả chua-doc/da-doc; không ack hộ hoặc lấy reader từ tên task.
3. Gom tin thường không `--push`, dùng `day-lo` khi cần; sự kiện giao/hỏi/xong/gộp tự đẩy cả queue trong Git. Khi soạn offline dùng `--khong-day`. Không lấy việc `git_pull` helper đổi thành metadata sync làm bằng chứng code/đề bài đã mới; code vẫn `git pull --ff-only` khi cây sạch.
4. Chỉ đưa `luu-tru` dry-run vào kiểm kê; người điều phối xem phần held/eligible trước khi chọn `--apply`. UNKNOWN/unread/hỏi chưa trả lời phải còn nguyên. Không tự đổi lịch hoặc chạy archive thật từ nhánh thử.

## Hai điểm gom cuối sau rà độc lập

- `flush_pending` kiểm lại `safe_path(root, rel)` và file thường trước đọc nguồn/Git, chặn cả ancestor symlink/junction được thay sau lúc queue. Guardmock chứng minh chưa đọc source và chưa gọi remote.
- Theo nguyên văn mục 4, bốn loại hoi/xong/gop/giao tự flush trong Git; quyết định cũ chỉ flush khi có `--push` đã được thay. Unit kiểm dispatch từng loại, opt-out/offline/nongit, loại trừ cờ, ordinary `--push`, lỗi auto giữ queue; native bare kiểm một tin thường + một giao không `--push` tạo đúng một remote commit, HEAD checkout giữ nguyên.
- RED bổ sung trước sửa: 6 failed, 14 passed / 3,12 s; ca ancestor được siết mock đọc thực rồi xác nhận RED riêng 1 failed / 3,03 s. GREEN store sau sửa 39 passed, 2 skipped / 2,24 s. Hai skip vẫn do quyền physical symlink Windows; không coi là đã chạy physical symlink.
- Lượt gom trước giới hạn protocol: 57 passed, 2 skipped / 15,35 s. QA native tiếp theo giới hạn `GIT_ALLOW_PROTOCOL=file`; production chỉ giữ constraint an toàn này nếu caller đặt, không hardcode file-only cho người dùng.
- Lượt cuối có giới hạn protocol file-only: **57 passed, 2 skipped / 15,62 s**, gồm store + ca native auto-flush + 5 CLI acceptance + 11 G3 stale. Đây là lượt chạy chồng các nhóm đã ghi, không cộng thành số test duy nhất mới. `git diff --check` sạch; reviewer độc lập và root đã chốt hai sửa cuối **0 P1/P2**.
