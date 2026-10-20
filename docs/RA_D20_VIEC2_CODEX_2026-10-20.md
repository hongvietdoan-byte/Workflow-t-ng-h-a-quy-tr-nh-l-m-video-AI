# Đ20 việc 2 — tranche chụp fixture (M1.9a còn OPEN)

- Nhánh `codex/d20-viec2-golden`, gốc `c0ab784a`; commit xem `git log -1` của nhánh.
- Thêm `tools/golden_capture.py`: bắt buộc DB rõ ràng, SQLite URI `mode=ro`, transaction đọc; không import app/provider/registry, không gọi mạng/API.
- `--shot` là **khóa chính `scenes.id`**, tương ứng `jobs.scene_id`; không phải `scenes.idx`. Mọi job ảnh/video của khóa này được giữ theo id, không tự chọn bản mới nhất.
- Bản chụp: HEAD code hiện tại (không suy diễn là HEAD lúc gửi), PRAGMA user/schema version, model/provider/tier, JSON gốc của `sent_package`, prompt, refs giữ thứ tự và hash đọc lại dưới `--ref-root`.
- `--flags-file`: file JSON **phẳng** `{ "ten_co_thu_nghiem": false }`, người chụp xuất riêng và kiểm chứng. Không đưa nguyên file settings dạng `{preset,flags,modes}`. Không đọc môi trường; không chứng nhận cờ lúc job được gửi. COMPAT yêu cầu các cờ trong file đều tắt.
- Hash thiếu file, ngoài root, remote, thiếu hash cũ, mismatch được ghi status + warning; không fetch URL, không bịa hash. Tier NULL ghi rõ. Job đang chạy cảnh báo dùng snapshot nhất quán DB + refs. Không sao chép dữ liệu thật tự động.
- Trường có tên nhạy cảm / URL query bị từ chối cả fixture; không in raw package. Người chụp cần rà dữ liệu tự do trước khi chia sẻ; đây không phải máy phát hiện mọi bí mật trong prompt.
- Đỏ: 12 lỗi thiếu module. Lượt xanh đầu bắt lỗi SQLite thiếu `uri=True`; sửa → 12 xanh. Sau góp ý rà schema, dùng nguyên `SCHEMA` AST từ `core/db.py` + 3 cột migration tối thiểu → 12 xanh (6,54s). Môi trường giả qua `patch.object(os,'environ',...)` trước import/call; interpreter native Python 3.14 rõ ràng. Không full suite, không dữ liệu thật.
- Tự rà 2b.5/caller: module độc lập, chỉ CLI/test gọi; không đổi runner/autopilot/cờ mặc định/đường trả phí. Đăng ký areas, giữ version 87.
- **OPEN:** chưa dựng lại payload bằng current production builder từ đầu vào trước lắp gói; chưa end-to-end replay. `compare_compat(bytes,bytes)` chỉ là comparator và test lệch một byte; không lấy payload lưu sẵn so chính nó để tuyên bố replay. CORRECTNESS là trạng thái OPEN riêng, không suy ra từ COMPAT.

## Lệnh dành cho phiên Claude trên máy chính (chưa chạy)

Trước tiên chuẩn bị bản sao CSDL + ref nhất quán ở thư mục snapshot được phép; chọn `scenes.id` thực của từng shot. Ví dụ PowerShell dưới dùng biến `$sceneId` do Claude xác định, không thay bằng số thứ tự shot. File cờ phải xuất riêng, không chứa credential. Output chưa tồn tại; tool không ghi đè.

```powershell
py tools/golden_capture.py --db D:/AI-Video-Output/golden-snapshot/manifest.sqlite --project 24 --shot $sceneId --flags-file D:/AI-Video-Output/golden-snapshot/compat-flags.json --ref-root D:/AI-Video-Pipeline --purpose compat --output D:/AI-Video-Output/golden-snapshot/p24-scene.json
py tools/golden_capture.py --db D:/AI-Video-Output/golden-snapshot/manifest.sqlite --project 27 --shot $sceneId --flags-file D:/AI-Video-Output/golden-snapshot/compat-flags.json --ref-root D:/AI-Video-Pipeline --purpose compat --output D:/AI-Video-Output/golden-snapshot/p27-scene.json
py tools/golden_capture.py --db D:/AI-Video-Output/golden-snapshot/manifest.sqlite --project 31 --shot $sceneId --flags-file D:/AI-Video-Output/golden-snapshot/correctness-flags.json --ref-root D:/AI-Video-Pipeline --purpose correctness --output D:/AI-Video-Output/golden-snapshot/p31-scene.json
py tools/golden_capture.py --db D:/AI-Video-Output/golden-snapshot/manifest.sqlite --project 33 --shot $sceneId --flags-file D:/AI-Video-Output/golden-snapshot/correctness-flags.json --ref-root D:/AI-Video-Pipeline --purpose correctness --output D:/AI-Video-Output/golden-snapshot/p33-scene.json
```

`--ref-root` là phạm vi đọc local được cho phép, không phải tự động remap root cũ. Với ref tuyệt đối còn trỏ máy chính, muốn chụp hoàn toàn từ snapshot cần xuất bản DB đã remap có kiểm chứng trước; tool hiện ghi `outside_scope` thay vì tự sửa path. Job ảnh/video không tồn tại hoặc sent_package thiếu → báo lỗi rõ. Fixture chưa đủ để đóng M1.9a.

## Rà độc lập phạm vi nhỏ (Codex, 20/10)

- 2 lỗi P2 đã sửa: JSON nhận NaN/Infinity khiến capture nhận gói không chuẩn (và ref có số này có thể làm output ghi dở); URL chứa userinfo credential không query vẫn lọt bộ lọc. Chặn số không hữu hạn đệ quy trước tạo output và từ chối URL có userinfo, kể cả scheme viết hoa.
- Thêm 5 ca: NaN/+Infinity/-Infinity phải lỗi trước tạo output; URL credential giả bị chặn; output trùng DB không đổi byte CSDL.
- Đỏ: 4 failed, 13 passed; xanh: **17 passed (7,77s)** với native Python 3.14, `--tb=no`, môi trường fake bằng `patch.object` trước pytest import/call. Không chạy lại cả bộ, không đọc môi trường/secret/dữ liệu thật, không API trả phí.
- Rà scope: SQLite chỉ đọc, ref ngoài root/URL không fetch, output exclusive không ghi đè DB, schema jobs dùng AST thật; caller chỉ CLI/test. Không còn P1/P2 trong phạm vi đọc. Replay/current builder/CORRECTNESS vẫn **OPEN**.
