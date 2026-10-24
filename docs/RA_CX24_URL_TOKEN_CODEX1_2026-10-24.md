# CX24-URL-TOKEN-RA — Codex 1, 24/10/2026

XONG rà source và sửa nhỏ bộ che log. Nhánh `codex/v31-url-token-ra`, nền main274bc335. Không đọc token/log/DB thật, không thêm cookie hoặc lưu phiên mới, không thay TTL/quyền, không restart/deploy. P34 đã báo XONG8d1412ad trước nhận việc này.

## Kết luận và phạm vi

`s` là bearer: người có URL còn hạn có thể thử phục hồi phiên theo cơ chế hiện hành. DB chỉ giữ hash, phiên hết hạn sau12giờ; `auth.identity` đọc lại active/quyền từ DB mỗi action. Guard Owner từ xa và máy thành viên vẫn áp dụng. Không coi các guard này là thay thế cho việc giữ kín URL. Chưa có bằng chứng rò thực tế; đây là rà tĩnh và tái hiện với giá trị giả.

| Đường | Rủi ro / bằng chứng | Xử lý trong nhánh / còn lại |
|---|---|---|
| Chia sẻ link | CAO: `dashboard/header.py` sign_in/require_login giữ và nhận s. Copy thanh địa chỉ có thể chia sẻ phiên. Helper LAN ở admin dùng origin, không tự gắn s. | Giữ cơ chế theo EP. Khi chia sẻ dùng địa chỉ gốc, không sao chép URL đăng nhập; không tự thay auth/cookie. |
| Lịch sử, bookmark, ảnh màn hình | CAO: s nằm trên địa chỉ; TTL và logout không xóa bản sao lịch sử/ảnh. | Ghi giới hạn; không tự thao tác/xóa lịch sử trình duyệt người dùng. |
| Referer | TRUNG BÌNH–CAO tùy origin/chính sách: repo chưa đặt Referrer-Policy. | Đề xuất header no-referrer ở tầng phục vụ/proxy, chưa kích hoạt. Không chèn meta trong iframe rồi tuyên bố bảo vệ trang cha. |
| Log ứng dụng | LỖ HỔNG CHE LOG đã tái hiện: `diag.redact` generic che chuỗi dài chuẩn nhưng query percent-encoded hoặc ngắn có thể lọt. `_keep_lost` còn nối ngoại lệ sau bộ che. | Đã che query s/%73 (kể cả HTML ampersand, tham số lặp) trước generic; fallback che cả thông báo+ngoại lệ trước stderr/file. Không decode hay thay query khác. |
| Log Streamlit/proxy | CHƯA XÁC MINH deployment. Launcher chuyển stdout/stderr vào file trực tiếp, không qua diag. Source Streamlit1.64.0 hiện access_log=False, chưa thấy app chủ động log full URL. | Không kết luận runtime/proxy đã ghi token. Bộ che diag không bảo đảm che mọi log runtime/proxy; cần kiểm cấu hình triển khai riêng bằng URL giả. |
| Cache | TRUNG BÌNH: source runtime HTML dùng no-cache, không phải no-store; bundle có hash được cache lâu. | Đề xuất no-store cho HTML/route xác thực; không cần vô hiệu cache bundle tĩnh. Chưa đổi server/cache thật. |
| Logout/revocation | `core/auth.py logout` xóa token_hash phiên hiện tại; header xóa session_state và s. Có revoke_sessions riêng, không tự thu hồi mọi người. | Test SQLite giả xác nhận token cũ không còn identity sau logout; giữ contract12giờ. Không gọi logout phiên người dùng thật. |
| HTTP trong LAN | CAO khi đi qua mạng không tin cậy: launcher/LAN URL mặc định http. | Đề xuất HTTPS tại tầng triển khai; không đọc/đổi chứng chỉ, proxy hoặc môi trường User. |

Theo [W3C Referrer Policy](https://w3c.github.io/webappsec-referrer-policy/), no-referrer bỏ Referer; strict-origin-when-cross-origin vẫn cho gửi URL đầy đủ với yêu cầu cùng origin. Không suy ra mọi trình duyệt/deployment đang có cùng cấu hình. Theo [RFC9111 §5.2.2.4–5](https://httpwg.org/specs/rfc9111.html#cache-response-directive.no-store), no-cache yêu cầu xác minh lại trước tái dùng; no-store yêu cầu không lưu request/response, nhưng không phải bảo đảm tuyệt đối riêng tư hay xóa lịch sử.

## Thay đổi và kiểm thử

- `core/diag.py`: thêm quy tắc query s trước generic secrets, giữ pid/step và tên query/path khác. `_keep_lost` dùng chung text đã redact cho stderr/file. `record` che trước cắt400ký tự; `report` và `ui_log._clean_detail` tái dùng cùng hàm.
- Không cờ mới: sửa lỗi trong hợp đồng che bí mật có sẵn, không thêm luồng gen/ghi profile/quyền/đăng nhập hoặc đổi gói gửi. Không đặt bộ lọc global của framework, không monkeypatch HTTP server.
- RED **9 failed,2 passed/0,56s** → GREEN **14 passed/2,80s** (11ca mới và3RecordTests cũ), pytest serial --tb=no. Mọi import/call trong OBJECTenv/HOME/TEMP giả, keyring/registry giả; SQLite memory và token literal giả, không provider/process/mạng thật.
- Bao phủ query chuẩn/percent-value/percent-name, lặp, fragment, không đổi query khác, record trước ghi, fallback stderr chứa URI trong ngoại lệ và logout. Chưa test expiry boundary, header/browser/history thực hoặc file fallback; nhánh file dùng cùng biến đã che được rà source.
- Rà độc lập hai lượt log/data/callers/fixture: **0 P1/P2 còn lại trong diff**; root đọc sửa hai lượt. Khai test vào diag, giữ areas.version92. Không chạy cả bộ trong nhánh task; phiên gộp chạy theo quy trình.

## Đề xuất triển khai còn lại — chưa áp dụng

Ở tầng phục vụ được phê duyệt: HTTPS; Referrer-Policy no-referrer; Cache-Control no-store cho HTML/route xác thực; access log chỉ method/path/status, bỏ query/Referer thô. Không áp no-store vô điều kiện lên bundle tĩnh có hash. Cần thử bằng URL giả và kiểm response/log thật trong lượt triển khai riêng; không đọc lại token thật để chứng minh. Cấu hình [Streamlit hiện hành](https://docs.streamlit.io/develop/api-reference/configuration/config.toml) và source runtime đã rà không thấy option public customHeaders để chỉ thêm vào config.toml; không bịa option hoặc vá dependency cài trên máy.

Giải quyết triệt để bearer trong thanh địa chỉ cần thay cơ chế phiên, nằm ngoài quyết định EP hiện tại. Không tuyên bố redaction đã giải quyết history, chia sẻ URL, Referer hoặc proxy.


## Đồng bộ sau thư GỘP 231006-kphf

URL-TOKEN-RA đồng bộ main5d72cf7d sau thư231006-kphf; giữ diag redaction và fallbacklog, hợp danh mục areas hai bên/version92. Root14 passed/1,92s trên nền mới; rà tích hợp độc lập0P1/P2, rootđọc2lượt. Không đổi auth/cookie/token thật, không rewrite/force/mainmerge/CU/data thật.
