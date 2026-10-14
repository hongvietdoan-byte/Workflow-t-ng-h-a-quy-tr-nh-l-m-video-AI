# UI QA điều phối Bàn đạo diễn — 14/10/2026

Kiểm trên fixture Streamlit riêng tại port loopback được hệ điều hành cấp, không dùng 8501/8502.
Node/Playwright bundled + Edge headless, profile mới. Python server/Node/browser nhận env whitelist;
app thay os.environ OBJECT bằng dict giả trước imports, model/data/home trong thư mục temp mới.
Renderer giả bằng PIL, worker chờ tín hiệu file do bộ chụp phát; không API/Blender/SQLite sản xuất.
Server chỉ dừng qua Popen của PID tự tạo; browser đóng trong finally; thư mục temp fixture được dọn.
Không bootstrap bị policy từ chối, không cài hay đổi runtime/BLENDER_PATH.

6 ảnh cuối ở `docs/images/bdd_performance/`:
- pending_1440.png, pending_1280.png: DOM thông báo đang chạy có mặt, result chưa có; worker còn bị giữ.
- done_1440.png, done_1280.png: result đã có, không còn pending; thấy hai ảnh PIL fixture và nút đưa Kho.
- revision2_pending_1280.png: lần bấm submit kế, result cũ đã gỡ, thông báo pending/running mới có mặt.
- off_1280.png: queue tắt, sync renderer giả giữ kết quả/các key widget cũ.

`metrics.json`: cả 6 ảnh scrollWidth đúng viewport 1440/1280, horizontal overflow=false, console/page errors=0.
Render button x=97, width=263.25 nằm trong bề rộng1280; y=1045.75 là đo sau rerun/scroll,
không dùng số đó để tuyên bố mọi điều khiển luôn trong viewport. Trang vẫn cần scroll dọc.
Soi trực tiếp pending1440 và done1280: status đọc được, không che nút, ảnh/nhãn/cột vừa bề rộng;
ở1280 các chip góc máy xuống dòng đúng. Không kiểm breakpoint mobile ở pha này.

Ảnh pending đầu đã bị chụp muộn do chờ caption ngoài fragment; đã thay toàn bộ bằng bộ cuối có DOM asserts.
Caption “Revision fixture” ở ngoài fragment chỉ là số ở lần full refresh gần nhất (pending có thể vẫn 0/1),
không phải revision ticket đang chạy; bằng chứng lần submit mới dựa vào chuỗi action + status/result DOM.
Hai lượt giữ worker đầu lỗi bộ chụp, không dùng chúng làm PASS. Bộ chụp cuối qua, worker chỉ release SAU hai ảnh pending.

Giới hạn: UI fake executor chứng minh hiển thị submit/poll/result snapshot, không native Store safety/Blender performance.
Không claim 4–5 pipeline/autopilot hay một Blender toàn máy từ các ảnh này. Fresh reviewer đang sửa lifecycle/cache;
Store background phải chặn tới khi có runtime/vòng đời an toàn; Portable chưa cài/chưa thay default.
Không rerun pytest trong pha UI QA; số58 passed/1 skipped là trước vòng sửa reviewer, root phải kiểm bản sửa cuối riêng.
