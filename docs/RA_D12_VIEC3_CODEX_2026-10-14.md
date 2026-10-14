# Rà tự kiểm Đ12v3 âm ref — 14/10/2026

- Root chốt polish: đọc diff sửa lần hai, 22 test xanh/3,40s; browser CUA actual component 1440/1280 warning rõ/không overflow/0 console error, readonly nút disabled. 2 JPEG docs/images/d12/ref_audio_polish_*.jpg, root đã xem1280. Owned QA PID118464 đã dừng/cổng18636 đóng; chưa toàn Step5/production/cả bộ Windows.

## Phạm vi
Nguồn gốc + đoạn + tốc độ đã duyệt; cờ `ref_audio_sync` TẮT. Không làm lại mix_bus trên main.

## Đã tự rà (skill2b.5)
- Không đọc `data/`, dashboard.env, credential thật; test mới thay OBJECT `os.environ` trước import; native subprocess whitelist; pytest --tb=no.
- ON thiếu metadata báo VÀNG qua failed, không đoán từ tên motion_ref hay fallback file silent.
- OFF không đọc cột metadata và giữ extract/fit cũ, uploader/nút/key cũ; bổ sung metadata không tự bật use.
- Metadata đổi tham gia fingerprint đề xuất; người dùng đã tích tiếng cũ vẫn giữ với ref_stale, không xóa quyết định.
- Rà caller: chat_intake không đoán nguồn gốc và setter clear metadata khi gắn mới; UI là đường nhập explicit; sfx_plan vẫn fit khi đặt timeline.
- Root bắt trước review: đường path tùy ý, metadata legacy không sửa được, ghi đè trước validation, thiếu giới hạn/timeout. Đã gom sửa: nguồn upload riêng + phạm vi project, nút lưu legacy không reupload, UUID/rollback, giới hạn600s/.01..100 và timeout.

## Bằng chứng
ĐỎ2 → XANH27; nhóm chốt49/13,57s; proof ffmpeg nguồn880Hz khác đoạn đầu440Hz, speed.5 ra~2s từ đoạn1s, fit2.5s pad. Cả bộ chỉ bước gộp; chưa sản xuất.

## Còn chờ
Reviewer độc lập + QA giao diện1440/1280; chưa commit/push. Thông số UI chưa có tự nạp metadata đã lưu để sửa tiện hơn; có thể tải gốc và khai lại metadata explicit. File fixture QA tạm cần xóa trước commit.

## Rà độc lập — cần sửa gom trước gộp
- **P1 · core/pipeline.py:244:** phạm vi nguồn GỐC lấy từ chính `path` người gọi truyền vào, không lấy dự án của `scene_id`. Người có quyền sửa dự án A có thể truyền motion ref trong dự án B và metadata nguồn B; setter probe nguồn B rồi lưu metadata vào cảnh A mà không kiểm quyền B. `propose` kiểm lại thư mục A chỉ khiến bản ghi không dùng được, không bảo vệ lần đọc ở setter. Sửa: xác định project_id từ scene, lấy data root tin cậy (tham số tường minh hoặc cấu hình được neo), kiểm cả ref/source thuộc project đó trước probe. RED: hai dự án A/B, actor chỉ edit A, setter nhận hai path của B phải từ chối trước `_source_duration`, CSDL không đổi; path hợp lệ A vẫn lưu.
- **P2 · core/ref_audio.py:146–148,165:** fingerprint chỉ chứa path/giây/tốc độ, không chứa dấu vết tệp GỐC. Ghi đè nguồn cùng đường dẫn bằng âm khác nhưng cùng duration khiến lượt sau báo `already`, giữ tiếng cũ và không đánh dấu `ref_stale` cho tiếng đã tích. Sửa: thêm dấu vết nội dung nguồn vào identity (hash nội dung hoặc cơ chế version nguồn đáng tin), dùng chung cho prune/cache; kiểm lại khi nguồn bị đổi hoặc mất. RED: propose lần một → ghi đè nguồn cùng path và duration → propose lần hai phải tạo đề xuất mới, xóa đề xuất chưa tích cũ; nếu đã tích phải giữ và đánh dấu stale.
- Chưa sửa code; hai RED trên là đề xuất, chưa chạy. Đã chạy related_areas bằng environ OBJECT giả trước runpy, xác nhận step5/core_infra/step3 và test chậm bắt buộc khi gộp; đọc caller chat_intake, sfx_plan, audio_lib và UI Bước5. Không chạy API/cả bộ, không truy cập dữ liệu/env thật.

## Vòng sửa gom sau rà
- P1 đã sửa: `Pipeline.data_dir` cấu hình tin cậy tùy chọn; `dashboard.common.scoped` gán root cấu hình DATA. Setter metadata lấy project_id từ scene, kiểm motion ref/source thuộc root đó trước probe; thiếu cấu hình từ chối. Setter không metadata giữ legacy.
- P2 đã sửa: identity thêm SHA256 nội dung nguồn; đọc theo chunk1MiB, trần512MiB, nguồn mất/không đọc/overflow báo VÀNG và không tách. Không cache hash theo mtime/size nên thay bytes cùng kích thước vẫn phát hiện. Giữ luật prune đề xuất chưa tích và stale tiếng đã tích.
- RED setter trên bản chưa sửa; RED source ban đầu có lỗi regex fixture, đã sửa thành Stream #0:0. Xác nhận riêng hồi quy source với mô phỏng fingerprint legacy cố định: 2fail đúng lượt đề xuất thứ hai. XANH cuối nhóm ref_audio_sync/f5b_backlog/chat_intake: **47 qua,6 bỏ qua /6,47s**; bỏ qua test cần ffmpeg trên PATH môi trường giả (proof thật có trong lượt triển khai trước).
- Test thêm: actor A/path B từ chối trước probe và CSDL nguyên; path A lưu được; thay bytes nguồn cùng path/size cho use=False/True; giới hạn đọc ở biên10bytes. Environ OBJECT giả trước imports, home fixture tạm cho Streamlit; không API/env/dữ liệu thật/cả bộ. Chưa commit/push; root đọc diff vòng sửa trước quyết gộp.

## Sửa hẹp vòng 2 theo root
- RED3 thật: source đổi trong extractor vẫn added; fit1e300 vẫn spawn; timeout ghi đè `_sync.wav` cũ. Đã sửa pre/post SHA nguồn trước add_local (mất/overflow/đổi → VÀNG, finally dọn tmp), shot fit trần600s trước spawn, fit ghi WAV tạm cùng directory rồi os.replace chỉ sau ffmpeg thành công.
- XANH focused cuối: **13 qua** trong `tests/test_ref_audio_sync.py`; thêm biến thể source mất/overflow trong extraction đều không added, tmp sạch. Atomic fit timeout giữ bytes/cache cũ và dọn temp. Không chạy lại nhóm rộng/cả bộ/API; environ OBJECT giả trước imports, subprocess native whitelist.
- Root đã QA1440/1280: 0pageerror/overflow, PNG trong docs/images/d12/ref_audio*.png; root còn ảnh height1450 để xem hết fields. Chưa xóa fixture QA; chưa commit/push, root đọc diff vòng2.
- QA cuối root: chính component `_motion_ref_editor`, ảnh1280/1440 height1500 hiển thị đủ fields, 0pageerror/overflow; root đã xem ảnh1280. Ảnh cuối thay ảnh expander đang animation. Đây là fake pipeline trên server QA riêng, chưa sản xuất/không8501; không khẳng định consoleerror. Root đã dừng PID sở hữu, reviewer xóa đúng tệp `_qa_ref_audio_ui.py` theo ủy quyền sau xác minh absolute path (không recursive).
- Root chốt fixdiff vòng2. Finding flag cuối: preset experimental tự bật ref_audio_sync dù verifiedFalse → thêm OPT_IN_ONLY. Test settings experimental/flags{} với environ OBJECT giả: RED1→GREEN1/0,16s. Không chạy lại nhóm rộng. Tổng file mới14test đã xanh theo các lượt13+1; sẵn sàng commit/push nhánh, chưa cả bộ/gộp/sản xuất.

## Bổ sung bảo vệ đầu vào ffmpeg sau commit nhánh 4a52a772
- Root finding: file nằm đúng project nhưng nội dung playlist HLS/concat có thể gọi URL hoặc đọc file khác project. Chỉ source ON `_source_probe`/`_extract_segment` thêm input options trước `-i`: `-protocol_whitelist file,pipe -format_whitelist mov,matroska,webm,wav`; HLS/concat không nằm trong demuxer allowlist. OFF `_extract` giữ nguyên.
- Đối chiếu nguồn chính thức [FFmpeg Formats](https://ffmpeg.org/ffmpeg-formats.html): format_whitelist là input allowlist demuxer; MOV enable_drefs/use_absolute_path mặc định tắt, giữ mặc định này. [FFmpeg Protocols](https://ffmpeg.org/ffmpeg-protocols.html): protocol_whitelist là input allowlist. Tên native demuxer/option xác nhận bằng proof ffmpeg thật MP4+WAV.
- RED2 mock args thiếu allowlists → XANH **16qua/1,40s** focused toàn test_ref_audio_sync; có ffmpeg thật nguồn WAV440/880Hz, speed/fit và generated nativeMP4 probe. Playlist giả.mp4 có URL chỉ chạy mock subprocess, không mở mạng; test kiểm cả allowlists và vị trí trước `-i` cho probe/extract. Không khẳng định đây là sandbox decoder tổng quát; phạm vi chặn playlist/protocol ngoài nguồn native.
- Chưa commit/push bổ sung; root đọc diff rồi quyết. Không API/data/env thật/cả bộ; environ OBJECT giả trước imports/native subprocess env whitelist.

## Bổ sung polish sau thư 14/10 18:26/19:23 (chưa gộp)

Mail origin/main 7340e6b1 xác nhận C5 giải phóng file và Đ12v3 thuộc Codex,
không làm lại backend. Nhánh mới codex/d12-ref-audio-polish từ main này;
cherry-pick backend 4a52a772/2808cfe0 thành ff24a25c/b5207db4. Conflict hai
file FEATURES/areas đã giữ nội dung main mới, thêm ref_audio_sync, version80.

ĐỎ 4 failed/16 passed (1.53s) → XANH 20 passed (1.37s), lệnh chung
`py -m pytest -q tests/test_ref_audio_polish.py tests/test_ref_audio_sync.py --tb=no -p no:cacheprovider`, PYTHONUTF8=1.
Các test mới dùng access thật trên SQLite fake kiểm viewer/denied không IO;
helpers UI được execute cô lập bằng AST để không import credential/provider
Dashboard, kiểm warning qua rerun/scoped project/reset và help ON/OFF.
Existing sync tests tiếp tục kiểm nguồn/đoạn/tốc độ bằng fixture giả.

Tự rà 2b.5:
- Không nới test, không secret env/header/token reads; patch.object object
  os.environ fake trước import/call. Không provider/network/fallback/API.
- Không đổi đường dẫn backend hay đọc dữ liệu thật; code need_edit trước
  tạo thư mục/audio probe/ffmpeg, kế thừa user=None trusted system.
- Cảnh báo no_audio giữ trong session_state riêng pid qua rerun; không claim
  tồn tại sau đóng session/restart, không ghi thêm DB manifest. Lần lấy tiếng
  thành công kế cập nhật/xóa; đổi dự án không hiển thị warning dự án khác.
- Cờ ref_audio_sync vẫn OFF/OPT_IN_ONLY; ON help đúng atrim+atempo theo
  metadata và apad/atrim cuối shot, OFF giữ giới hạn ≤40% cũ.
- Không đổi use=False/consent/checkbox keys/autosend, không paid API.
- Bắt guard caption fit_tempo: sync fit_file không có fit_tempo nên dùng get
  thay truy cập trực tiếp để không KeyError, không đổi backend fit.
- related_areas step5 + core_infra/step3; chưa fullsuite Windows/GUI polish,
  chưa nghiệm thu nghe bản dựng sản xuất. Root cần rà quyền độc lập/gộp.


## RÀ KỸ độc lập polish · sửa gom nhỏ (14/10 tối, chưa commit/gộp)

Phạm vi chỉ uncommitted polish trên baseorigin7340e6b1 + backendcherry-pick
ff24a25c/b5207db4; không rà/làm lại backend đã có. Đọc CLAUDE7/diff/tests và
related_areas: Step5, caller pipeline/Step3 chỉ gọi validate_metadata/setter,
không gọi propose nên server need_edit mới không làm vỡ luồng setter.

Finding P2 tại dashboard/steps/step5.py:297: catch st.error rồi unconditional
rerun làm lỗi/AccessDenied biến mất ngay. Sửa catch return để giữ error trên lượt
hiện tại; readonly disable riêng ax_refaudio theo C.read_only, server need_edit
trong core/ref_audio.py:155 vẫn kiểm trước assets_dir/probe/extract. Không đổi
widget keys, consent use=False, flags/default hoặc background/paid API.

Tests mới gọi **actual extras_section** (AppTest), fake SQLite/users/session/
manifest/providerNone: error probe tồn tại, readonly nút disabled; warning pid1
qua rerun, pid2 không mang warningpid1, quay lại pid1 giữ cảnh báo; ON/OFF và
sync fit_file thiếu fit_tempo không exception. Helpers AST vẫn có tests cũ;
đường source test sửa absolute theo __file__, không phụ thuộc cwd.

Bằng chứng reviewer: lượt1 21pass/1fixturefail+warning (thiếu fake USERPROFILE
trước ScriptRunner config); sửa fakeHOME. Lượt2 **RED actual1fail/1pass** (error
bị rerun xóa). Lượt3 20pass/2fixturefails do readonly dùng C.access_user global
nhưng auth.identity đã forbidden; bổ sung fakeC.access_user=p.user nhất quán.
Root cho thêm1confirm có lý do: **22passed/3.40s**, hai file test_ref_audio_polish
+test_ref_audio_sync, --tb=no, không nới assert. Tổng reviewer4lượt, ghi minh bạch
vượt3 do fixture isolation; không broad/fullsuite.

Fixture tests/fixtures/ref_audio_polish_qa.py khai areas version80 giữ. os.environ
OBJECT fake trước imports/calls; winreg/keyring modulefake trước importcommon,
restore cả missing/present; prepatch providerfactory/model profileloader/voice/
auth identity/ownercheck trước dashboard import. Static sources cho thấy registry
fallback ở meshy.api_key là local import trong function, modelprofiles loader
cũng lazy; fakeguards không đọc registry/credential thật. Fake files=None nên
không đọc media. Native launcher spawn explicit whitelist dict (không inherit
credentials), -I -Xutf8; không env/header/token repr/assert/showlocals.

Root QA browser riêng:
- URL http://127.0.0.1:18636 ; PID118464 ; unifiedexecsession49976.
- Launcher ngoài repo: D:/AI-Video-Pipeline/.codex-wt/_qa_ref_audio_polish_launch.py;
  wrapper D:/AI-Video-Pipeline/.codex-wt/_qa_ref_audio_polish.py dùng runpy tới
  fixturetracked. Root giữ quyền dừng PID sở hữu sau QA.
- Command launcher: py -I -X utf8 D:/AI-Video-Pipeline/.codex-wt/_qa_ref_audio_polish_launch.py;
  lần khởi động thực còn có outerPython patch.object envfake + subprocess.Popen
  env=explicitwhitelist trước childspawn, không nativeenv hostsecret.
- Click lấy tiếng để có VÀNG, rerun/đổi dự án, hover help, ON/OFF, readonly,
  lỗi probe giả; actual extras component, **chưa toàn Step5/production**.
- Root bổ sung ảnh1440/1280/bằng chứng sau; reviewer không claim đã browserQA.

Warning chỉ lưu session riêngpid, không DB/restart; chỉ cập nhật/xóa khi propose
trả kết quả mới, không tự re-probe khi đổi nguồn/flag. Help row theo cùng điều kiện
backend metadata+flag; OFF legacy ≤40%, ON source/segment/speed và trim/pad. Lỗi
manifest fit_tempo kiểu sai không thuộc polish, chưa claim sanitize toàn audio
manifest. Không sửa backend/C5/mix/delivery, TODO/main/live/API/data thật.
