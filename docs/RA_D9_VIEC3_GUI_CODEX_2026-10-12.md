# Đ9 việc 3 · GUI Lão Đại — tự kiểm trước RÀ KỸ

Nhánh `codex/d9-viec3-lao-dai`, nền `5bffa89`; chưa commit/push. Backend `broker.py`/`logic.py` đã main, không viết lại.

## Phần triển khai

- `gui.py`: Tk transparent/topmost, cú vẽ canvas native từ mockup; idle/tickets/disconnected, bong bóng chỉ waiting_admin + đỏ/vàng; không duyệt. Click mở đúng phiếu qua URL allowlist; drag, WM_MOUSEACTIVATE/WS_EX_NOACTIVATE, queue từ poller/tray về Tk.
- `native.py`: Shell_NotifyIcon khay thật (hiện/ẩn/thoát), named mutex tránh chạy đôi. Toast WinRT desktop thật qua PowerShell, shortcut AUMID riêng; XML chỉ mã/trạng thái/hạn, click protocol URL allowlist. Thông báo Windows tắt/lỗi được báo trên pet, không thay bằng balloon rồi gọi là toast.
- `channel.py`: Windows Credential Manager, read-only token TTL≤300, endpoint ephemeral 127.0.0.1; không proxy/redirect. Client challenge HMAC bằng token RAM server trước Bearer, cùng socket HTTP1.1, `auto_open=0`. Server chỉ GET, reject Origin/Host khác. Sai token caller không thu hồi grant hợp lệ; Owner/role/session/TTL/OFF kiểm lại phía broker, watchdog xóa credential/dừng service.
- `devsys/lao_dai_channel.py` + 2 dòng `devsys/app.py`: module server RAM tồn tại qua rerun, explicit Owner local bấm cấp/thu hồi. Không endpoint mạng cấp quyền, không session/token trên trình duyệt/URL/CLI/env/log/file. Hết hạn cần bấm cấp lại 8502, không renewal âm thầm.
- Launcher dựa `$PSScriptRoot`, Hidden, không nạp dashboard.env/tự cài dependency. `demo.py` dùng dữ liệu tổng hợp, credential/shortcut/mutex QA riêng; không CSDL hay auth thật.
- `areas.json`: khai module/launcher/test, giữ nguyên version.

## Bằng chứng hiện có

- ĐỎ: collection thiếu `tools.lao_dai.channel`.
- Lượt xanh đầu: 27 qua/1 đỏ (test dựng TTL301 lúc collection bị thời gian chạy giảm dưới300); sửa test dựng grant ngay trong test, không nới điều kiện code.
- Lượt liên quan: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_lao_dai_gui.py tests/test_lao_dai.py tests/test_devsys_admin_auth.py` → 44 qua /13,61s.
- Native Windows Credential Manager QA thật bắt lỗi bytes→Unicode của pywin32; sửa write JSON Unicode/read UTF16LE và fake hợp đồng đúng native. Sau sửa native write/read/delete credential riêng `AI.VideoPipeline.LaoDai.QA.native20261012` OK, không để lại credential.
- AUMID shortcut native riêng `AI.VideoPipeline.LaoDai.QA.shortcut20261012` tạo/xóa OK.
- Test hồi quy có broker thật/CSDL tạm, file byte không đổi sau snapshot, Owner đổi role bị từ chối/xóa credential; GUI controller fake, dedupe/toast privacy, URL, OFF/remote Owner, giả cổng không nhận Bearer, socket EOF không reconnect, GET-only/Origin/query.
- Lượt bổ sung sau lỗi native mới: 44 qua /13,72s (cùng 3 file). Bốn lượt pytest do một lỗi native mới xuất hiện sau lượt3; không mở rộng bộ kiểm.

## Tự kiểm 2b.5 / phạm vi chưa chứng minh

- Không sửa/nới test để che lỗi; thời gian TTL test sửa cách dựng fixture. Đường root/DB dựa cấu hình tuyệt đối, pet không import broker/CSDL; demo tách credential production. Cờ OFF không tạo service/kho credential/UI cũ. Không lời gọi tốn tiền, không dữ liệu thật, không dashboard.env.
- Không can thiệp pipeline/autopilot/gửi hàng loạt; không auth role từ client, không approve trên pet. Hạn token cố ý cần thao tác Owner lại, không lưu phiên Owner trong credential.
- `related_areas.py` chỉ vùng diag/devsys, cả bộ Windows (kể cả slow access/devsys/devsys_v2) bắt buộc ở bước gộp; chưa chạy ở phiên làm.
- CHƯA QA GUI desktop/ảnh/DPI100–150%/hai màn/sleep-resume/toast hiển thị thật bằng computer-use. Root thực hiện; smoke credential/shortcut và test fake không chứng minh chất lượng GUI hay toast thực sự hiện.
- CHƯA RÀ KỸ độc lập, chưa pilot sản xuất, chưa bật cờ, chưa main/restart. Không ghi hoàn tất Đ9 trước QA/rà/toàn bộ.
- Root thử GUI trước khi native credential được sửa gặp dialog khởi chạy lỗi, lần2 dialog chạy đôi. Computer-use @sky không activate/click được cửa sổ đã capture, báo `failed to activate captured window` sau refresh/recovery; root dừng thao tác theo skill và hỏi trạng thái desktop. QA GUI/toast còn chặn ở công cụ, KHÔNG dùng API native để tự động click/chụp thay thế. Code sửa credential đã được smoke native độc lập; chưa được thấy GUI thật sau sửa.

## QA native tổng hợp cho root

Từ worktree này chạy `powershell -NoProfile -File tools/launch_lao_dai.ps1 -Demo -QaName d9root20261012 -DemoState idle`.
Thoát bằng khay rồi đổi `idle` → `tickets` → `disconnected` cùng QaName. Không đổi credential production.

- Idle: cú không bubble, margin magenta phải trong suốt, topmost trên cửa sổ khác.
- Tickets: chính xác 2 waiting_admin (1 đỏ,1 vàng), thêm waiting_merge chỉ toast/click. Toast WinRT gửi 3 sự kiện; Notification Center cần xem nếu Windows không hiện banner. Bấm chỉ mở `http://127.0.0.1:8502/?ticket=QA-RED`, không login thật/approve.
- Drag không focus: đặt Notepad/browser foreground rồi kéo pet; gõ vẫn ở cửa sổ cũ. Poll/show không tự foreground. Tray menu là thao tác chủ ý có thể foreground menu riêng.
- Khay: hide/show/exit; chạy lại cùng QaName lúc đang chạy phải báo đã chạy. Exit dọn icon/QA shortcut/credential/service.
- Disconnected: không credential, bubble Mất kết nối; không mở stale ticket. Grant hết 5 phút cũng về mất kết nối, xóa credential.
- Poll counter tổng hợp `qa_reads` trong demo snapshot: dùng `py -c "from tools.lao_dai.channel import CredentialStore,PetClient; print(PetClient(CredentialStore('AI.VideoPipeline.LaoDai.QA.d9root20261012')).snapshot()['qa_reads'])"` khi demo chạy. Không in token; snapshot mỗi15s, watchdog kiểm quyền2s (2 bước challenge+snapshot mỗipoll), không chi phí API. Counter chỉ trong demo, không đổi snapshot sản xuất.

Tài liệu Microsoft primary đã đối chiếu: [AUMID shortcut](https://learn.microsoft.com/en-us/windows/win32/shell/enable-desktop-toast-with-appusermodelid), [WinRT desktop toast](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/legacy/hh802768(v=vs.85)).

## RÀ KỸ độc lập · 12/10 (chưa gộp)

- Đã rà diff mới + caller app/admin_auth/broker/logic, related_areas diag/devsys; không chạy lại pytest/full suite, không dữ liệu thật/API/GUI native.
- **P1 · channel.py:72–75, CredentialStore.read:60**: read→delete không nguyên tử giữa process pet và 8502. Poll cũ đọc grant A, Owner ghi B, poll gọi CredDelete cùng TARGET sẽ xóa B; nhánh malformed/expired read cũng có race tương tự. Repro tổng hợp ngay với delete_grant: store.read trả A nhưng xen ghi B trước return → `new_grant_deleted=True`.
- Sửa: named mutex liên process theo credential target, khóa mọi write/read/conditional-delete; conditional-delete phải đọc và so token/port dưới cùng khóa, kể cả cleanup invalid. Không dùng chỉ threading.Lock. Test interleaving A→B phải giữ B, test watchdog epoch cũ không xóa quyền mới.
- **P2 · gui.py:47–55 / native.py:_proc,show,move**: scale chỉ GetDpiForSystem lúc mở, không xử lý WM_DPICHANGED; hai màn DPI khác nhau không scale theo màn đích. Drag không giới hạn work area; rút màn phụ rồi tray Show giữ tọa độ ngoài màn, pet không hiện lại được.
- Sửa: DPI theo HWND/màn hiện tại, nhận WM_DPICHANGED qua queue Tk để cập nhật kích thước/font/geometry, clamp trong work area monitor ở move/show và khi layout màn đổi. Test adapter synthetic 96→144 DPI, bounds âm/màn biến mất; QA desktop thật vẫn bắt buộc.
- HMAC proof cùng socket/auto_open=0, Origin/Host/GET-only, unauth không thu hồi, TTL/Owner/feature watchdog, broker ro/absolute, OFF và gate Owner local: không thấy lỗi thêm trong phạm vi. Gate request_source giữ hợp đồng admin_auth hiện có; không sửa module đó.
- Còn mở: hai lỗi trên + QA GUI/toast/DPI/hai màn/sleep-resume đang bị công cụ computer-use chặn + cả bộ Windows trước gộp. Không kết luận Đ9v3 hoàn tất.

## Vòng sửa gom P1/P2 · 12/10

- P1: `credential_mutex` Global theo SID user + SHA256 target, không token trong tên; khóa write/read/delete/delete_if và cleanup malformed/expired. Timeout fail closed, hỗ trợ abandoned mutex, đóng handle. `delete_grant` chỉ gọi conditional delete nguyên tử.
- P2: DPI theo HWND; WM_DPICHANGED copy RECT trong callback, WM_DISPLAYCHANGE gửi queue về Tk. Resize canvas/font/geometry theo DPI; move/show/displaychange clamp work area monitor gần nhất, giữ SWP_NOACTIVATE/SW_SHOWNOACTIVATE và MA_NOACTIVATE.
- Khai `pywin32; sys_platform == "win32"` trong requirements; không cài thư viện hay đổi quyền OS, không tăng areas version.
- ĐỎ nhóm 3 file: 3 hỏng / 44 xanh /13,77s; xanh lần1 47 qua /13,69s. Bổ sung regression expired/malformed + stale watchdog theo đúng phạm vi, xanh cuối **50 qua /14,60s** (3 lượt pytest vòng sửa).
- Lệnh: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_lao_dai_gui.py tests/test_lao_dai.py tests/test_devsys_admin_auth.py`. Interleaving hai store + writer xen cleanup giữ grant B; snapshot/DB/auth test cũ vẫn xanh.
- Named mutex QA thật acquire/release OK; smoke hai Python process: child bị chặn khi parent giữ mutex, vào được sau release (`named_mutex_QA_crossprocess_block_release_OK`). Không dùng credential sản xuất và không GUI native. `git diff --check` sạch.
- QA GUI/toast/DPI/hai màn/sleep-resume vẫn CHƯA thực hiện; test layout synthetic và mutex native không chứng minh pet hiện/focus/toast thật. Không main/commit/push/full suite; root đọc phần sửa trước gộp.

## Root phát hiện muộn · lý do mất kết nối

- `gui.py:138`: bubble trước đây bỏ `PetView.reason`, chỉ hướng dẫn cấp quyền chung; sửa một dòng hiện reason nguyên văn hoặc fallback, wrap width290×scale.
- Regression FakeCanvas hai lý do hết hạn/thu hồi: ĐỎ 2 hỏng /0,26s; xanh nhóm 3 file **52 qua /13,37s**. Không nới test; chưa QA đọc chữ/wrap trong GUI thật do computer-use còn chặn.

Root đọc diff sửa mutex/DPI và lý do mất kết nối trước commit. QA Windows vẫn bị chặn: get_window_state thấy dialog khởi động lỗi (trước sửa CredWrite), rồi dialog chạy trùng; sky.click và sky.activate_window đều failed to activate captured window sau refresh/recovery. Theo Computer Use đã dừng UI, hỏi trạng thái desktop; chưa có ảnh/GUI/toast nghiệm thu. Đã dọn đúng 4 process --demo --qa-name d9root20261012, credential QA và shortcut QA riêng; không đụng production.
