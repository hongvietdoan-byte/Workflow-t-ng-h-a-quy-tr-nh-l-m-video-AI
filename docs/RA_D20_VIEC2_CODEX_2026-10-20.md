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

## Bổ sung replay biên lắp gói hiện tại (20/10)

- Frozen input `tests/golden/package_inputs.json` ảnh/video: args/kwargs/sent_kwargs/meta/job, ref manifest SHA256 + bytes synthetic, timestamp/external id, model/tier/provider, legacy ON/experimental OFF; baseline UTF-8 viết độc lập, không rebuild trong test.
- Gọi thật `ImageRunner._build_package` (kế thừa `_Runner`) và `VideoRunner._build_package`; không lấy raw gói làm args. Provider stub whitelist tên fake/clipai/deepix, không client/registry/credential; env object fake trước import/call; socket/subprocess bị chặn; ref chỉ đọc sau kiểm hash/root. Current runner không cần feature setting ở biên này; on/active vẫn đóng băng từ snapshot, không đọc ambient config.
- COMPAT so từng byte + đổi 1 ký tự input phải lệch; CORRECTNESS kiểm prompt/ordered ref roles độc lập, ca sai vẫn đỏ dù COMPAT xanh. Đây là correctness cấu trúc synthetic, **không** bằng chứng chất lượng ảnh/video.
- Capture thêm sidecar explicit `--input-snapshots-file`: map job id → snapshot trước lắp gói; không suy từ sent_package. Sidecar chưa đủ trường vẫn lưu như input chưa xác minh, replay từ chối rõ trường thiếu; không tự tuyên bố có replay thành công.
- ĐỎ **3 failed / 17 passed** trước helper → XANH **20 passed** → cuối **25 passed / 9,47s**, targeted một file `--tb=no`, Python3.14 native. Hai lượt xanh chạy process với explicit whitelist SYSTEMROOT/TEMP/TMP/PYTHONUTF8; lượt đỏ ban đầu launcher kế thừa env, nhưng mọi fixture/test dùng patch.object env fake trước import/call, không đọc/in env/key. Không lặp cả bộ.
- Tự rà 2b.5: không đổi production runner/cờ/default/autopilot; ref tương đối neo cwd tạm có finally restore; tuyệt đối/escape/URL không vào manifest local; positional video refs vị trí7/8 cũng phải manifest. Hàm replay dùng cwd/patch toàn tiến trình: chạy tuần tự, chưa API thread-safe. `_from_sample` từ chối rõ vì thiếu snapshot CSDL nguồn.
- `related_areas.py tools/golden_capture.py tests/test_golden_replay.py`: step2; shared flags assets/autopilot/core_infra/plates3d/step1, không caller production dùng tool, không test chậm bắt buộc. Đăng ký fixture mới, giữ areas.version nền. Rà độc lập do root thực hiện, không spawn con.
- **M1.9a OPEN**: mới chứng minh biên lắp sổ gửi từ frozen pre-send inputs, chưa replay `_submit_args/_submit_kwargs` từ DB/physical production snapshot, chưa capture #24/#27/#31/#33, chưa chất lượng thật/cả bộ Windows/gộp. Các lệnh chụp trên vẫn dành Claude; thêm sidecar chỉ khi đã có snapshot input độc lập, không dùng roundtrip để đóng việc.
- Tự rà cuối bắt lỗi mapping JSON fingerprint có key string trong khi VideoRunner lookup job id int: đổi snapshot field đơn `pregen_fingerprint`, gán vào job id thực; case video baseline có field này để chứng minh override chạy. Lượt xác nhận thêm vì finding mới: **25 passed /9,60s**, native explicit whitelist như trên. Rà độc lập đang do phiên `d20_golden_final_review` thực hiện, chưa coi kết quả tự rà là thay rà độc lập.

## RÀ KỸ độc lập bổ sung biên replay (Codex, 20/10)

- Phạm vi: diff `d28f6213`, builder ảnh/video hiện tại, `sent_package` bind/hash/meta, sidecar CLI, fixture và caller `related_areas` (step2; shared flags assets/autopilot/core_infra/plates3d/step1). Không có caller production của helper, không thay cờ.
- Bắt và sửa **1 P2**: sidecar mới chưa qua bộ redact của sổ gửi; `_safe` bỏ lọt tên credential `passwd`, `access_key`, `auth_*` (và private_key). Capture có thể lưu chúng vào fixture. Bổ sung bộ chặn tên thống nhất các dạng này trước mở output; không đọc credential thật.
- 3 hồi quy synthetic `test_sidecar_rejects_credential_fields_before_output`: ĐỎ **3 failed / 25 passed (8,06s)** → XANH **28 passed (8,60s)**, đúng 2 lượt targeted `--tb=no`. Một lỗi quoting launcher trước lượt đỏ chưa chạy pytest đã được sửa.
- Native Python3.14 spawn bằng môi trường whitelist SYSTEMROOT/TEMP/TMP/PYTHONUTF8; pytest import/call dưới `patch.object(os, "environ", {})`; không đọc/in/assert môi trường thật/header/token, không provider client/registry/API/dữ liệu thật. `git diff --check` xanh.
- Baseline không làm input builder, đổi prompt làm COMPAT đỏ; correctness có kỳ vọng riêng. Video fingerprint dùng khóa job thực + snapshot singular đã được builder sửa trước review. Ref có manifest hash/root, timestamp/cờ/provider stub đóng băng; hiện tại builder không đọc registry/config.
- Không còn P1/P2 trong phạm vi đã rà. Stub tên provider không chứng nhận adapter submit signature/mạng hay chất lượng; thread-safety toàn tiến trình chưa hỗ trợ. M1.9a và capture sản xuất / `_submit_args` / cả bộ Windows / gộp vẫn OPEN; không push/main/TODO/plan/version.
