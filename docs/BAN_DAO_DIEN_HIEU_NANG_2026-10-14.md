# Điều phối render nền Bàn đạo diễn — cấu hình máy chính

## Cập nhật sau portable và phép thử native thật
Portable5.0.1 riêng đã xác minh checksum và chạy qua guard Job một process; Store giữ nguyên. Root đọc vòng sửa3findings, nhóm129qua/1skip. Native16/16job ở mức1/5/10 dự án hoàn tất7,283/24,801/53,488s, không fallback2D;17ownedroot kết thúc,3queue dừng. Chi tiết và giới hạn trong `BENCH_BLENDER_PORTABLE_2026-10-14.md`. Cờ vẫn OFF, chưa cả bộ Windows/production. Các trạng thái chưa tải/chưa thử native trong phần lịch sử phía dưới được thay bằng cập nhật này. Đề xuất5 active/một heavyrenderer; chưa hardCPU/RSScap/ngân sách chungFFmpeg.


Ngày 14/10/2026 · nhánh `codex/ban-dao-dien-hieu-nang` · nền `c18b5e6f`.
Đây là BUILD backend + điểm nối render 3D admin sau cờ **TẮT**, chưa phải nghiệm thu Bàn đạo diễn production.

## Kết quả Codex — worker portable đã được duyệt
- Tải bản Windows x64 **Blender 5.0.1** chính thức, cùng phiên bản Store; ZIP và checksum riêng từ
  https://download.blender.org/release/Blender5.0/ (web fetch 402; HTTP shell official thành công).
- ZIP: `blender-5.0.1-windows-x64.zip`; checksum: `blender-5.0.1.sha256`; SHA256 đã so khớp
  `921d77f6c505a35b2c2f6e67d4ad1c10b72418338ba0e0d3ea7f582a5e5fe46e`.
- Runtime riêng: `D:/AI-Video-Pipeline/.codex-runtime/blender-worker-5.0.1-x64/unpacked/blender-5.0.1-windows-x64/blender.exe`.
  Tạo thư mục mới, không ghi đè Store/install khác; ZIP/checksum/runtime ngoài Git, không sửa data/env/UserEnv.
- Native `--version` qua whitelist giả và Job Object trả rc=0: **Blender 5.0.1**, build **a3db93c5b259**.
- `get_service()` không tham số của admin tự nhận profile private này nếu tệp tồn tại; cả `submit_plates` và
  `submit_preview` ưu tiên runtime service. Máy khác dùng `get_service(worker_blender=<absolute blender.exe>)`
  hoặc `configure_worker_runtime()` trước service đầu. Không đổi `plates3d.find_blender`/Store legacy; OFF trả disabled trước lookup.
- Admin ON chọn runtime service trước caption/nút và submit không truyền locator legacy; Store/None legacy không ghi đè portable.
  OFF giữ locator/sync cũ. Worker tạo suspended → gán Job không kế thừa handle → resume đúng owned process.
- Contract supervisor sau rà: **một process Blender, nhiều threads**. Job đặt `JOB_OBJECT_LIMIT_ACTIVE_PROCESS=1`
  và `KILL_ON_JOB_CLOSE`, không breakaway, trước worker chạy. [Microsoft mô tả guard](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information).
  Process mới vượt giới hạn bị terminate và associate thất bại. Không hỗ trợ importer/plugin cần helper process.
- Timeout/nonzero/success đều terminate Job → đợi handle root đã giữ từ trước resume signaled → xác minh zero-active
  trước trả/nhả khóa renderer. Bỏ snapshot/OpenProcess/IsProcessInJob để loại khoảng hở child spawn/membership error.
  Không taskkill, registry, global process scan. Query/terminate/wait lỗi giữ khóa, báo `supervisor_failed` qua status/reason/log.
- Queue close hiện join 5 s, **không hủy job đang render**; worker/cache root còn giữ tới khi chạy xong. Lỗi OS vĩnh viễn giữ lock,
  cần người vận hành kiểm supervisor. Chưa kiểm sự cố OS thật/RSS hard cap/benchmark5/full pipeline.
- Rà độc lập bắt 3 findings (runtime admin, snapshot race, membership query silent); sửa gom theo contract single-process.
  Native fixture chứng minh child attempt bị từ chối trước chạy, timeout root chết, success root signaled, nonzero/assignfailure/queryretry.
- ĐỎ vòng sửa: **4 failed/13 deselected/2.57s**. XANH cuối **129 passed, 1 skipped, 13.10s** nhóm 6 file,
  fake env OBJECT trước imports, native explicit whitelist, --tb=no/no cache. BPY fixture cũ chưa cấu hình.
  Proof version ở trên thuộc BUILD trước guard; cần root chạy Blender portable thật dưới guard, đọc fixdiff, rồi benchmark/cả bộ.
  Chưa commit/gộp/bật cờ; quota/revision/cache/export giữ; cache băm thêm binary/service/supervisor.

Máy đã được phiên chính đo: i7-11700 (8 core/16 thread), RAM 63,7 GiB, GTX 1070 Ti 8192 MiB.
Không suy GPU này chạy được mọi engine/scene. Giữ engine `auto` hiện có (EEVEE nếu có, fallback Cycles hiện có);
`RenderBudget(engine_mode='cpu')` là lựa chọn CPU bảo thủ, không phải profile GTX đã tối ưu/đo thật.

Kế hoạch đã BUILD:
1. Hàng đợi RAM process-local, một worker; mọi Blender qua `plates3d.render` → khóa file xuyên tiến trình hiện có.
2. Ưu tiên interactive; round robin theo project trong từng lane, tối đa 3 interactive rồi dành một lượt batch.
3. Gộp pending theo project/scene, giữ revision mới nhất; đang chạy không bị ngắt, hoàn tất cũ không publish vào revision mới.
4. Submit snapshot JSON nhỏ, trả ticket ngay; worker băm file đầy đủ/kiểm nguồn/render. Status đọc metadata, không render/SQLite.
5. Cache metadata/artifact giới hạn, namespace project/scene/revision; export bản sao trước dùng Kho. Điểm nối admin dùng fragment poll.

| Ngân sách mặc định | Giá trị / hành vi |
|---|---|
| Blender được điều phối | 1 worker/process + khóa `plates3d.blender_turn` chung giữa process |
| CPU | `--threads 6` và `scene.render.threads_mode=FIXED`, threads=6; cũ không có cfg này giữ command cũ |
| RAM | Chừa 16 GiB, ước tính job 8 GiB; cần ít nhất 24 GiB khả dụng mới khởi chạy |
| Deadline | Interactive 110 s; batch 3600 s, giữ thời hạn map cũ; ưu tiên chỉ đổi các lượt chưa chạy |
| Queue | 24 pending, tối đa 4 pending/project; 64 scope, tối đa 12 scope/project |
| Lịch sử | 160 records; pending/running/latest được giữ, terminal cũ bị loại; `forget` giải phóng scope đã đóng |
| Cache | 16 entry, tổng metadata + file ≤256 MiB; metadata/entry ≤64 KiB, ≤64 file/entry |
| Snapshot | JSON ≤1 MiB, không chứa connection/callback/bytes file; file nguồn băm streaming tại worker |
| Nguồn | Tổng file băm ≤2 GiB/job, configurable; GLB/GLTF gồm buffer/texture URI cục bộ, chặn URI mạng |

RAM 8 GiB/job là **ước tính admission**, không phải giới hạn RSS process. Chưa có watchdog áp hard cap RAM/VRAM.
Thread cap giảm tải CPU, không đảm bảo GPU/driver ổn định. Profile cấu hình bằng `RenderBudget` và
`get_service(budget=...)` trước lần submit đầu; dịch vụ đang chạy không im lặng đổi ngân sách.
**Microsoft Store đang bị chặn ở đường render nền**, trước submit và trước kích hoạt process.
Adapter cũ chưa quản lý owned PID/process tree hoặc chứng minh env package; hết hạn đợi rc.txt có thể để Blender chạy tiếp.
Cờ TẮT vẫn giữ render đồng bộ/Store legacy. Chưa đổi/cài runtime; việc hỗ trợ worker máy chính còn chờ quyết định runtime/supervisor.
Whitelist env chỉ áp dụng native Blender thường; không dùng mock để khẳng định Store inheritance đã an toàn.

API:
```python
from core import clay_preview_service, blockout_clay
service = clay_preview_service.get_service()
ticket = blockout_clay.submit_preview(service, project_id, scene_id, revision, plan, cho_dung,
                                     camera=camera, people=people, priority='interactive')
info = clay_preview_service.status(service, project_id, ticket)
# Nhận artifact chỉ khi done + đúng project/revision; export vào thư mục MỚI của caller trước chỉnh/ghi Kho.
```
`clay_background_queue` TẮT/opt-in/unverified. OFF submit API trả `disabled`, không tự render/tạo service.
Caller phải kiểm cờ trước gọi `get_service()`; factory được gọi trực tiếp vẫn tạo service/worker, như ví dụ trên.
`blockout_clay_sheet` được snapshot riêng khi submit; worker không đổi ý theo cờ bị sửa giữa lượt.
Đường sync `render_sheet`/admin cũ giữ nguyên khi cờ queue OFF. Không đổi key widget/ACL admin.
Generic scope API là bảo vệ cách ly kết quả, không thay ACL: caller Bàn đạo diễn phải kiểm quyền trước lấy snapshot/gửi ticket.

Cache băm toàn bộ payload, revision, project/scene, budget, source bytes và mã renderer liên quan.
FBX/OBJ/BLEND/USD có thể có dependency ngoài gói không kê khai: **không tái dùng cache** cho định dạng đó.
Projection 2D do lỗi Blender không tái dùng làm cache clay thành công. Thay byte cùng tên/kích thước nguồn làm đổi key;
nguồn đã kê khai thay trong render thì không publish kết quả. Cache file bị sửa được kiểm khi worker hit và trước/sau export.
Caller chỉ nhận metadata sao chép; admin export file ra thư mục riêng trước `to_library`, không sửa cache chung.
Cache eviction chỉ xóa thư mục con do dịch vụ tự tạo trong temp, không xóa dữ liệu nguồn/Kho. Export staging riêng cạnh target,
rename khi copy/hash hoàn tất, dọn staging khi lỗi để retry; không ghi đè thư mục tồn tại. Giới hạn count/byte/timeout là int dương;
GLTF JSON phải trong budget và trần 8 MiB trước cấp phát, đọc có trần kể cả file tăng trong lúc đọc.

Dashboard: công cụ “Bối cảnh 3D” admin gửi batch và fragment poll 1 s, không truyền Pipeline/SQLite cho worker.
Scope private theo phiên admin; import vẫn ở luồng UI/ACL cũ, giữ game/place/look của lần submit.
Khởi động lại mất queue/ticket, UI báo gửi lại; chưa có durable queue, chưa chia hàng đợi ưu tiên giữa nhiều process.
Round robin là trong một service/process. Queue mới với Blender native thường dùng khóa chung; chưa khẳng định một Blender toàn máy
khi các caller Store legacy khác vẫn có khả năng timeout để process chạy tiếp.
Bàn đạo diễn A chưa vào main: API clay sẵn cho snapshot/backend A nhưng chưa có màn Editor production dùng nó.

Bằng chứng tải local **giả**: 5 project x 2 scene cho thứ tự 1,2,3,4,5,1,2,3,4,5; 5 AppTest phiên admin gửi nonblocking,
poll/export PNG fixture; 1 project gửi 9 scene chỉ nhận 4, còn 4 project khác vẫn nhận lượt.
Sau rà độc lập 5 findings: ĐỎ **45 failed, 7 passed**; XANH nhóm 5 file lần đầu **112 passed, 1 skipped, 9.02 s**.
Skip là fixture BPY thật cũ chưa cấu hình; kết quả cuối kèm regression UI Store ghi ở RA/HANDOFF.
Không benchmark Blender thật trong phiên này. Số Store 8,29/7,41/7,40 s từ RA Đ11v2 cũ là baseline riêng,
không dùng làm số đo scheduler mới. Chưa chứng minh 4–5 pipeline/autopilot sản xuất, paid API hay dựng video cùng lúc;
không tăng `core/capacity`/remote concurrency. Đã rà độc lập và sửa 5 findings, root đọc diff vòng hai; vẫn cần QA tải thực,
chốt runtime worker và owner C5 ngân sách chung trước bật cờ.


UI QA fixture riêng: xem `UI_QA_BAN_DAO_DIEN_2026-10-14.md`, 6 PNG ở `docs/images/bdd_performance/`.
Ảnh pending cuối có worker được giữ bằng tín hiệu, DOM pending/running có mặt và result chưa có;
ảnh DONE/OFF có result. Đây là kiểm giao diện fake executor, không thay native lifecycle QA hoặc benchmark thật.
