# Thiết kế Tiểu Nhị + Lão Đại — Đợt 7 việc 1

11/10/2026 · base `229f812` · chỉ nghiên cứu/thiết kế, chưa triển khai hoặc thử sản xuất. Các chốt ở [nghiên cứu chính](NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md); kiểm kê code ở [D5](D5_KIEM_KE_HIEN_TRANG.md). Không mở dữ liệu thật, không API/Blender.

## 1. Hai cấp, bốn lớp và luồng phiếu

Lớp 1 Dashboard cung cấp bằng chứng, gói đã gửi/gói gửi kèm và nút sửa; lớp 2 dịch vụ thao tác dùng chung + Tiểu Nhị khung phải dự án; lớp 3 phiếu admin + Lão Đại pet; lớp 4 `experience_cases`/lessons dùng chung. Lão Đại không phải đường ghi dữ liệu thứ hai. Tiểu Nhị chỉ đề xuất, người bấm duyệt sửa dữ liệu; gen duyệt tiền riêng. ID nội bộ shot bất biến, `scenes.idx` chỉ thứ tự.

Đồng nghiệp nhìn **lỗi + nút sửa ngay**: “ảnh nền rộng thừa — bỏ nền rộng rồi vẽ lại”; nhấn mở bản diff gói và giá. Không thấy mã nguồn, branch, phiếu hay trạng thái bảo trì. Ngầm: Tiểu Nhị lập phiếu với bằng chứng và “đã gỡ tạm bằng…” → Lão Đại báo admin → admin duyệt xử lý → hiện admin giao phiên Claude; tương lai thợ cách ly → admin duyệt gộp → kiểm triển khai/ca thật → nếu cần Tiểu Nhị báo kết quả. Chỉ lỗi chặn hẳn mới hiện “đã báo admin, dự án tạm dừng ở shot này”; không tự pause cả dự án nếu chỉ một shot bị giữ.

Owner duy nhất publish Kho/map/Bible; chủ dự án sửa bản sao dự án. Trần Tiểu Nhị dùng thật 2 USD/dự án, tách gen, cảnh báo 80%, hết trần tự lập phiếu nâng; đề xuất hiện tại 0,15 USD/phiên. Kiểm code/đọc pet không gọi LLM. Phiếu hạn 3 ngày; lô thường~22:00, chặn sản xuất chạy ngay khi admin cho phép. Bảo trì tự động Đợt 8+ vẫn **đề xuất chờ xác nhận**, cần cách ly và bộ 42 ca đạt.

## 2. Phiếu admin và nơi lưu (đề xuất)

Đã mở `devsys/answers.py:72–84` load, `:103–128` answer, `:135–143` mark_applied: file `devsys/data/user_answers.json`, format/version, key mã việc, history câu trước, status answered/applied. `answer()` ghi thay bằng atomic replace, nhưng không transaction đa người, không ticket assignment/SLA/kiểm chứng triển khai. `devsys/app.py:825–831` ghi who từ `getpass.getuser()` là username OS, **không chứng minh admin ứng dụng**. `devsys/app.py:975–976` đọc answers; `:1161–1197` đọc taxonomy `devsys/error_types.json`, có cờ thật nhưng không vòng đời phiếu.

| Cách | Trùng dữ liệu / giao dịch | Quyền, ai đọc/đóng | Lão Đại đọc | Kết luận |
| --- | --- | --- | --- | --- |
| AI Dev System: phân hệ phiếu admin mới, bảng cùng manifest | link diag/finding/job/usage; một nguồn bằng chứng, CAS/transaction với dự án | server kiểm Owner/admin; admin phân loại/duyệt/đóng, Owner publish; đồng nghiệp chỉ projection triệu chứng | snapshot chỉ đọc từ broker có danh tính | **chọn đề xuất**: tận dụng 8502/taxonomy; không nhét vào answers |
| Hệ ticket riêng DB/web mới | sao chép quyền/dự án/ledger, sync lỗi/mất link; giao dịch chéo | phải xây login/quản trị/backup/retention riêng | adapter hệ riêng + liên kết job | chưa đáng công; chỉ xét nếu cần nhiều máy/multi-tenant sau |

Nơi hiển thị: AI Dev System 8502 phân hệ admin mới, link tới trang duyệt Dashboard 8501 đã đăng nhập. Không coi 8502 hiện có ACL an toàn; trước thêm thao tác admin phải gắn session login/role server. Lưu `support_tickets`, `ticket_events` **đề xuất** cùng manifest, migration về sau theo quy trình backup. Khi 8501 sập, broker tiếp nhận phải độc lập tiến trình 8501 nhưng kiểm session/role như nhau; khi DB không đọc được hiện unavailable, không tạo phiếu giả thành công hoặc tự sửa DB. `answers` chỉ tiếp tục câu trả lời kế hoạch, có thể link mã phiếu trong note; không đồng bộ hai vòng đời.

### Đối chiếu năm bảng cũ

| Cũ | Bỏ/gộp/giữ | Vì sao so nguồn thật |
| --- | --- | --- |
| service_proposals | giữ tối thiểu | diag_events (`core/db.py:295`) là lỗi, change_findings (:531) là kết luận rà, thiếu snapshot diff/hash/expiry/approval; proposal cần immutable hash, actor, scope, revision, estimate/version, TTL/state |
| service_operations | giữ tối thiểu | jobs/job_events quản gen, không claim sửa dữ liệu/editor; cần proposal UNIQUE, idempotency UNIQUE, expected_revision, pending/claimed/applied/failed/unknown, external/job ID |
| service_audit | **bỏ**, dùng audit_log | `core/db.py:153–159`: at/email/action/detail; detail JSON thêm operation/ticket/capability/before_after_hash, lọc secrets; enforce append-only tại adapter |
| support_tickets + ticket_events | giữ mới | findings thiếu owner/due/branch/deploy; answers chỉ answered/applied; ticket links giữ bằng chứng ở diag/change/experience thay chép log |
| service_budget_reservations | giữ chỉ phần trợ lý | `project_reserves` (:330–352) trích mức thử dự án, không reservation từng chat/concurrent unknown; dùng `usage_events` (:83–94), `llm_calls` (:95), `core/cost.py:756`, `core/llm_runner.py:615–623` đối soát, không tạo usage_ledger thứ hai |

Giữ reservations theo project/service với operation UNIQUE, reserved/spent/unknown, pricing_version và expiry; TTL không giải phóng unknown submit. Claim operation+reservation nguyên tử trước call. Cấp trần mới không tự sửa jobs/gen caps; request nâng trần cần admin duyệt giá/trần/phạm vi/thời hạn.

### Lược đồ phiếu và vòng đời

`support_tickets`: id UUID; title chữ thường; kind code/budget/shared_asset/operation/unknown; error_type nullable + taxonomy_revision; severity; project_id/scene_id/job_id nullable; fingerprint UNIQUE theo kind/project/root-cause/revision; source_actor; created_at UTC; due_at=created_at+72 h; owner_actor; state; impact={blocked_projects,blocked_shots,money_usd,money_unknown}; cause={confidence:guess|confirmed,summary,evidence_refs}; requested_action; assigned_to; workaround={text,at,actor,verified}; evidence_refs={diag_ids,finding_ids,experience_ids,sent_job_ids,filtered_artifact_hashes}; technical={files,tests,branch,base_commit,fix_commit,deploy_commit}; verification; resolution; closed_by/at; revision.

`ticket_events`: ticket_id,event_id,at,actor,transition,before/after_hash,reason,evidence_refs; append-only. Trường cause “đã xác nhận” cần link bằng chứng; chi chưa rõ ghi unknown, không 0. Lão Đại chỉ đọc summary projection admin. Không nhúng base 64/đường dẫn máy/token vào payload.

Trạng thái: new→triaged→waiting_admin→assigned→investigating→fixing→verifying→waiting_merge→deployed→resolved→closed. Nhánh budget/shared_asset dùng waiting_admin→approved/rejected→applied→verified→closed; không ép test code vào phiếu nâng trần. blocked/waiting_info/reopened có lý do, giữ lịch sử. Admin mới chuyển/đóng; code deployed cần commit+health+kiểm ca, không chỉ test giả; Owner duyệt publish chung. Nút duyệt chỉ Dashboard session thật, POST/CAS/hash, không GET/URL duyệt. Pet không giữ capability write.

Nhắc hạn: vàng tại 48 h (còn 24 h), đỏ ≥ 72 h; overdue không auto-close, escalation admin. Gia hạn phải có người/lý do/new_due trong event, giữ due gốc; không dừng đồng hồ khi waiting_info. Fingerprint gộp chứng cứ nhiều dự án nhưng projection đồng nghiệp không tiết lộ dự án khác. Cần sửa kỹ thuật đủ 3 ngày hay không là trách nhiệm admin; nếu chưa thể sửa phải ghi hướng giải quyết và gia hạn, không đổi thành “đã sửa”.

## 3. Gói gửi kèm theo shot (đầu vào Đợt 8)

**Lưu chọn:** khóa `scenes.data.package_overrides` (không bảng mới): schema_version, revision, base_package_hash, base_scene_revision, edits, updated_by/at/reason. `edits` gồm exclude/add/pin theo asset_image_id hoặc plate_key, content_sha, role, look, source_kind kho|shot_3d, project_id/scene_id cho nền. Không lưu đường dẫn tùy người nhập. Bản lịch sử before/after hash vào audit_log; proposal duyệt giữ snapshot. Phiên đầu chỉ ảnh; video route cần hợp đồng riêng, không áp overrides ảnh vô điều kiện vào video.

`jobs.sent_package` bất biến: xem lần trước theo job thật, không dựng lại request hôm nay. Editor tạo **gói ứng viên lần tới** từ gói tự chọn hiện hành+override, hiển thị gói trước/candidate/diff/giá. base hash lệch → stale, chọn lại hoặc duyệt diff, không áp sửa cũ mù. Không thay sent_package hoặc job cũ khi undo.

Điểm nối tương lai (KHÔNG sửa ở Đợt 7/Đợt 8 file cấm): `core/runner.py:2462` assets.scene_references; `:2518` shared_references, `core/scene_storyboard.py:131–169` cast ưu tiên shot. Áp override trên **danh sách cuối** sau thêm anchor/wide/nền và trước đánh số ảnh/name_render/final provider args; kiểm lại sau giới hạn nhà cung cấp cắt ref. Không áp trước rồi để builder chèn lại ảnh bị bỏ. `core/runner.py:2379–2385` gọi `place_refs.package_problem`, phải tiếp tục bảo vệ gói thực gửi, không thay bằng editor check. `:2587–2593` cast_missing hiện chỉ VÀNG; editor mới có ĐỎ cần sửa/duyệt trước gen, không tuyên bố runner đã chặn cast.

| Phép | Quy tắc/UI | Kiểm dùng lại / oracle |
| --- | --- | --- |
| Bỏ | đánh dấu ref bị loại cho lần sau, lý do bắt buộc; không xóa Kho | ảnh lịch sử còn nguyên; ref bắt buộc thiếu báo ngay |
| Thêm | chọn ảnh Kho đã được phép trong dự án, đúng look; hoặc nền 3D đúng shot hiện hành | tệp/hash/role/ACL/camera_key, không path/URL chat tùy ý |
| Ghim | ưu tiên giữ slot khi trim theo giới hạn, không bất chấp limit; pins vượt limit thì báo không thể dựng | không im lặng bỏ pin; outfit và identity theo ảnh chuẩn |
| Hai nền khác góc | “2 nền khác góc” + bỏ nền rộng/đổi về render shot | `core/place_refs.py:280–314` package_problem với record camera đúng; camera khóa chỉ nền chính, không wide/scene_establish; ca 649 |
| Người thiếu mẫu | “người trong khung thiếu ảnh mẫu” + thêm ảnh Kho phù hợp | `core/scene_storyboard.py:162–169` cast_missing (vai character/outfit/STANDARD_ROLES), cộng assets.reference_gaps cho asset không có ảnh; ca 645–651/Kho 419 |
| Chốt gen | gói candidate hash + scene revision + ACL + price_version/TTL | người duyệt dữ liệu rồi duyệt gen; worker kiểm lại, không quote gói khác |
| Hoàn tác | revert revision override từ audit với CAS | restoring input không gửi job, không trả tiền lại; candidate kiểm lại guard hiện hành |

Báo giá dùng cost/pricing hiện có; cộng ảnh tham chiếu/route theo model thật, missing price tính dư theo CHUAN và nêu lý do. Hiện tổng lần tới và “đã gen bản trước”; sửa sau gen giữ lịch sử, gen lần 2 tốn thêm. Không nói undo hoàn tiền. Bản sửa khác gói phải đổi hash; retry trùng input không được tự gen lại. Sửa override sau có job queued phải khiến approval cũ stale, không đổi payload của job running. Chặn hẳn thì phiếu ngầm + câu báo ở mục 1; gỡ tạm thành công không đóng phiếu root cause.

### Hợp đồng cho ĐỢT 8 việc 1 (bổ sung khi rà 11/10 — Codex code theo đúng mục này)
1. **API** (module mới `core/package_overrides.py`, cờ `package_overrides` TẮT trong `core/features.py`; cờ tắt → mọi đường cũ giống từng byte):
   `load(conn, scene_id) -> dict|None`; `save(conn, scene_id, edits, who, reason, expected_revision) -> revision` (CAS: revision lệch → lỗi rõ, không ghi đè);
   `apply(refs, overrides) -> (refs_moi, canh_bao)` (hàm THUẦN, không đọc CSDL); `check(conn, data_dir, pid, scene_id, refs) -> list[lỗi ĐỎ/VÀNG]`
   (gọi `place_refs.package_problem` + kiểm người trong khung thiếu ảnh mẫu, không sửa hai hàm đó); `undo(conn, scene_id, to_revision, who)`.
2. **Khớp ảnh:** ref từ `assets.scene_references` (`core/assets.py:1609`) chỉ có `{path, label, role}` (+ `plate_key` cho nền). Chỉnh lưu theo
   `asset_images.id` + `sha256` (`core/db.py:179–186`, `core/sent_package.sha256_of` `:82`), KHÔNG theo path; `apply` đổi path → id/sha để so; ảnh
   không đổi được (mất file, sha lệch) → cảnh báo VÀNG, không lặng lẽ bỏ.
3. **Sống qua replan:** `shots.store_plan` / replan xóa và chèn lại cảnh (`core/shots.py:333`, `:382`), chỉ giữ khóa trong `_user_locked`
   (`:325–327`, `:376–378`) → hoặc giữ `package_overrides` qua replan (như khóa người dùng), hoặc phát hiện "chỉnh mồ côi" bằng `base_scene_revision`
   và báo VÀNG. Chọn một, có test replan.
4. **Đường ghi:** chọn một và ghi rõ — qua đường sửa cảnh thường (`core/llm_io.py:553–555`, tự thêm khóa vào `_user_locked`) hay UPDATE riêng; test
   khẳng định khóa còn sau replan.
5. **Tương tác sẵn có:** trigger `trg_change_scene` (`core/db.py:608`) sinh `change_events` mỗi lần chỉnh — `change_review.WATCH` (`core/change_review.py:26`)
   không theo dõi khóa mới nên không tốn lời gọi Claude (giữ thế, có test). `lineage.IMAGE_KEYS` (`core/lineage.py:14`) không gồm khóa mới → ảnh đã
   duyệt KHÔNG bị đánh cũ khi chỉnh gói (chủ ý: vẽ lại phải bấm rõ).
6. **Điểm nối (để sau #24, KHÔNG sửa ở Đợt 8):** áp chỉnh SAU khi cắt giới hạn số ảnh (`core/runner.py:2461`) và TRƯỚC hai chỗ chụp `self._sent`
   (`:2511–2513` đường thường, `:2577–2579` đường storyboard), để `_pregen` (`:2377–2385`) kiểm đúng gói cuối.
7. Không bao giờ sửa `jobs.sent_package`; mọi chỉnh có ai/lúc/lý do + hoàn tác.

## 4. Lão Đại pet desktop (đầu vào Đợt 9)

Windows app nhỏ transparent/topmost, icon khay để ẩn/mở/thoát; không chiếm focus/ăn phím Dashboard; drag vị trí, scale DPI, click-through ngoài pet. Dáng thường + có phiếu, bong bóng “📨 N phiếu chờ duyệt”, toast có mã/trạng thái không ảnh/tên nhạy cảm; click mở Dashboard đúng trang, admin đăng nhập lại nếu phiên hết hạn. Không có approve/publish/run shell trong pet.

| Cách | Công giả thuyết / ưu | Rủi ro / quyết định |
| --- | --- | --- |
| Python+tkinter | S/M; runtime sẵn, win32 topmost/transparent, một poller | DPI/alpha/animation và toast Windows cần thử; **đề xuất pilot** pet đơn giản, broker tách process |
| Python+pywebview | M; tái dùng HTML mockup, render đẹp | bridge JS quá rộng có thể thành write/shell; packaging/runtime Windows phải kiểm; chỉ bridge read/open allowlist |
| Tauri hoặc Electron | L; packaging/update rõ, HTML animation | toolchain Rust/Tauri hoặc footprint Electron, updater/security surface; để sau khi pilot có giá trị |

Các công S/M/L là dự kiến chưa benchmark/cài runtime. Không giả định endpoint read mới tồn tại. Chọn **broker loopback độc lập chỉ đọc** trên máy chính, có xác thực admin session/token read-only scope + expiry; không expose ra LAN. Dùng session do server cấp kiểm role; `getpass`/JSON who không đủ. Pet giữ token trong kho credential OS, không URL/query string; endpoint allowlist, method GET, origin/CSRF cho đường duyệt riêng ở Dashboard. Nếu cả 8501/8502 hỏng pet báo unavailable, không tự mở DB write.

So đường đọc: HTTP 8501/8502 đã đăng nhập giúp tái dùng ACL nhưng Streamlit hôm nay chưa có API snapshot này, cần broker endpoint và kiểm session; SQLite `mode=ro` không ghi nhưng pet tiếp cận toàn DB nhạy cảm/khó lọc và khóa file, **không chọn pet đọc trực tiếp**. Broker server có connection read-only/SELECT, projection tối thiểu; không migrate/schema init khi đọc, timeout ngắn, snapshot consistency. Token pet không khởi động bảo trì; chỉ mở màn yêu cầu, admin duyệt trên Dashboard rồi controller capability một phiếu/thời hạn/quota khởi động worker cách ly.

Snapshot: counts+summary ticket/due/blocked; usage tổng từ usage_events/llm_calls qua ledger logic, pending/unknown tính riêng tránh bỏ tiền; stuck job từ state+WAIT_REASONS+diag, không tự retry; gen_done dựa mọi job mục tiêu terminal theo revision và còn chờ người duyệt, không nói “phim hoàn tất” chỉ vì gen xong. Poll 15 s, backoff 30/60 s khi lỗi, toast dedupe theo event/revision, chỉ notify thay đổi có hành động, nhắc hạn một lần/mốc 48 h/72 h; không LLM mỗi poll. Cap 80%/100% cùng nguyên tắc. Cần QA desktop thật: DPI 100/150%, hai màn hình, sleep/resume, mất session, đóng Dashboard, toast disabled; chưa làm phiên này.

## 5. Bộ 42 ca: fixture, chấm và pilot tối thiểu

Giữ danh mục C01–C42 nghiên cứu chính. Mới 649/645–651 là variant C05/C13; stale_endframe là variant C04, không tăng mẫu đếm. C09 điện thoại giữ nhưng deferred theo chốt; **không thể tuyên bố đủ 42 đạt khi ca hoãn**, cổng mở pilot nội bộ 41 active riêng, full-release/worker tự động vẫn chờ ca C09 được chốt/thử (hoặc người dùng phê duyệt bộ thay thế máy chính có chứng cứ).

Nơi đề xuất `tests/fixtures/self_service/cases.json`, `golden.json`, `assets/` + README provenance; fixture builder tạo SQLite tạm từ core.db không connection CSDL sản xuất. JSON schema ví dụ (thiết kế, chưa tạo fixture):

```json
{"id":"C04","variant":"stale_endframe","provenance":{"kind":"reconstructed_from_docs","base":"229f812","source":"core/end_frames.py:56-62","production_checked":false},"inputs":{"project_id":24,"scene_id":104,"start_job_id":651,"end_frame":{"state":"ready","start_job_id":645}},"actor":"edit","expected":{"reason":"Khung cuối cũ vì đổi khung đầu","action":"prepare_redo_end_frame","paid_calls_before_approval":0,"old_package_unchanged":true},"oracle":["no_new_jobs","ledger_unchanged","proposal_has_quote","no_pet_approval"]}
```

ID synthetic scene 104 minh họa, không suy là ID thật. Snapshot sanitized tối thiểu: projects/scenes/jobs/refs/diag/findings/users/watchers/ledger cùng ảnh PNG nhỏ tự dựng/hash; không token/user email thật/path absolute/URL ký. Provider fake có counter submit/error/timeout; fixture worker clock cố định. Ảnh hình học synthetic chỉ chứng minh luồng, không chất lượng vision.

| C01–C09 | Nguồn tái dựng không data thật | Oracle/giới hạn |
| --- | --- | --- |
| C01,C02 | mô tả chín ca trong kiểm kê + stage_facts_golden và code shot_lessons | camera 0,60<miệng 0,90; blocking 0,25→1–1,5; fixture không chứng minh gen đẹp |
| C03 | CODEX_TASKS và Pipeline.add_scene_next | complete-shot schema, ID job cũ không đổi, reorder idx |
| C04 | end_frames code + tests endframe của repo | đầu đổi, ready cũ/path thiếu; quote trước enqueue; no duplicate |
| C05 | mô tả 649 + package_problem/test refs hiện có | hai plate keys khác/góc khóa; gửi một nền đúng shot, lịch sử immutable |
| C06 | mô tả thùng dầu và location_pack đọc model 3D | bản sao model synthetic, shared untouched, Owner publish |
| C07 | lock_exceptions code/test phạm vi | ngoại lệ 9–10 không lây shot 8/11 |
| C08 | change_review code/test + UI nút có sẵn | lý do/hash/ACL trước close, queued consequences hiện |
| C09 | ca thiết kế mobile cũ, chưa chứng thực dữ liệu | deferred; pilot thay ca hai tab máy chính chỉ như phụ kiểm C41 |

Dùng lại khuôn `core/evalset.py:26–33` Check, `:151–178` summarize/run_case/run_all và review_sheet(:210), **không nhét fixture trợ lý vào eval/cases.json Director**, không gọi scoring hiện có giả rằng nó đo ACL/ledger. Adapter riêng sau này trả Check với oracle state/DB/files/ledger, hard failures tách khỏi% và review người. Hai người gán đúng/sai độc lập, bất đồng chưa tính đạt. `% đạt=ca active đạt tất cả oracle / tổng ca active chạy`; thêm per-run/per-role, số variant riêng; variant/role không tăng “số ca”. Hoãn/skipped/missing tách mẫu số, không tính là pass. Routing và self-resolve dùng mẫu số đủ điều kiện riêng. USD gồm cả lỗi/retry/API/bảo trì, gen riêng.

**Pilot đầu tối thiểu:** chỉ máy chính/admin + một đồng nghiệp với view/edit, 8 ca C04,C05,C08,C13,C31,C34,C35,C41 (kèm variants thiếu Kho 419/stale endframe). Fake/tool miễn phí trước, 0 API/0 gen; 100% 8 ca/routing/audit và 0 paid unauthorized/duplicate/leak. Khi APIs đã có và admin duyệt ngân sách mới test shadow phân loại/đề xuất, không apply/gen bằng AI. Pilot này không đủ cổng mở tự động/bảo trì/42 ca; tiếp theo 41 active ba vòng,2–3 đồng nghiệp ≥ 50 yêu cầu rồi giải quyết C09/cổng 42.

### Dự toán một lượt (không phải hóa đơn, chưa chạy)

Sonnet 5.5 input 2/output 10 USD/MTok đã đối chiếu [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) ngày 11/10/2026. **Cache hit Sonnet 5.5 = 0,20 USD/MTok** (input 2 × 0,1 — bảng giá Anthropic; rà 11/10 bỏ câu "nguồn ghi 0,10" vì sai). Token ảnh/tool phải nằm trong input tổng dự toán, khi usage vượt dự kiến phải cập nhật trước lượt tiếp; không cộng ảnh thành 0.

| Lượt | Số call × model × token/call | Chưa cache | Prefix cache 5 phút (một call ghi 8 k, các call còn lại hit 8 k, delta 2 k/call) |
| --- | --- | --- | --- |
| Pilot 8 ca active, một lời đề xuất/ca | 8 × Sonnet 5.5 × (10 k input + 1 k output) | 8 × 0,030=0,240 USD | ghi 0,024+output 0,010, rồi 7 × (hit 0,0016+delta 0,004+output 0,010) = 0,1432 USD |
| Bộ 42 danh mục, C09 hoãn→41 active | 41 × Sonnet 5.5 × (10 k+1 k) | 1,230 USD | 0,034 + 40 × 0,0156 = 0,658 USD |
| Đủ 42 sau C09 chốt/thử | 42 × Sonnet 5.5 × (10 k+1 k) | 1,260 USD | 0,034 + 41 × 0,0156 = 0,6736 USD |

Đây là **một call/ca**, chưa tool vòng 2, gen, bảo trì hoặc người gán nhãn; chạy code fixture hoàn toàn 0 USD. Dự phòng × 1,5 trên không cache: pilot 0,36 USD, 41 ca 1,845 USD, 42 ca 1,89 USD; giá chưa xác minh theo CHUAN thêm × 1,25. Nếu 2 call/ca thì × 2; ba vòng 42 ca × 4 role khi phù hợp, upper-bound 504 calls = 15,12 USD không cache, dự phòng 22,68 USD (đây là trần dự toán xin trước, **không quyền chi**). Prefix chỉ public/schema, không cache project/ACL riêng vào prefix dùng chung; nếu không hit/TTL hết dùng dự toán không cache. USD/ca đo output usage và reservations, không dùng con số dự toán để báo thực chi.

## 6. Chấm từng tính năng Dashboard và lộ trình

S = 1–2 ngày (hệ số công 1), M = 3–5 ngày (3), L = 6–10 ngày (6), gồm test/rà chưa tính chờ thật. Tần suất F: 5 = từng job/ngày; 4 = nhiều lần/dự án; 3 = 1–2/dự án; 2 = thỉnh thoảng; 1 = hiếm; **tất cả giả thuyết**, nguồn là ca/code không telemetry. Ma trận hai trục **tần suất × công sức** đặt từng tính năng vào ô F (1–5) và S/M/L; ưu tiên ô tần suất cao/công thấp. Để xếp các ô, dùng chỉ số **điểm = F/công** (công quy đổi S=1, M=3, L=6), chỉ xếp trong cổng/phụ thuộc; tiền/quyền ưu tiên cổng trước điểm. 30 ngày telemetry loại thao tác/request/hit/hoàn tác rồi xếp lại. Mỗi hàng là một tính năng, không chấm chung cả đợt.

| Tính năng | Ca lỗi / nguồn | F giả thuyết | Công | Điểm | Thứ tự / đợt Dashboard |
| --- | --- | --- | --- | --- | --- |
| Identity/ACL adapter | C34,C35; access/auth | 5 mỗi thao tác | M | 1,67 | 0 cổng nền |
| Proposal/hash/revision/duyệt | C39; llm_io | 5 mỗi sửa | M | 1,67 | 0 cổng nền |
| Claim/idempotency/reservation | C32,C41; bg_poll/spend_gate | 5 mỗi gửi | L | 0,83 | 0 trước gen trợ lý |
| Gói đã gửi viewer | C05,C13; sent_package | 5 mỗi job | M | 1,67 | 1 a Đợt 1 |
| Gói gửi kèm bỏ/thêm/ghim/undo | 649/645–651; C05,C13 | 4 nhiều lần/dự án | M | 1,33 | 1 b **Đợt 1 chốt** |
| Kiểm gói nền/cast+quote | C05,C13; package_problem/cast_missing | 5 mỗi lần vẽ | S | 5,00 | 1 c Đợt 1 phụ thuộc 1 b |
| Diagnostics+WAIT_REASONS+cách sửa | C23,C33; diag/runner | 5 mỗi lỗi | S | 5,00 | 1 d Đợt 1 |
| Đóng rà soát có lý do/tác động | C08; change_review_ui | 4 sau nhiều sửa | S | 4,00 | 2 a Đợt 2 |
| Cặp đầu/cuối và stale | C04; end_frames | 3 khi gen video | M | 1,00 | 2 b Đợt 2 |
| Ngoại lệ khóa theo shot | C07; lock_exceptions | 3 1–2/dự án | S | 3,00 | 2 c Đợt 2 |
| Thêm/chèn/reorder shot đủ trường | C03; add_scene_next | 2 thỉnh thoảng | M | 0,67 | 2 d Đợt 2 |
| Blocking/beat editor | C02,C19; shot_lessons | 4 nhiều shot | M | 1,33 | 3 a Đợt 3 |
| Camera/solver preview | C01,C18; stage_solver | 3 1–2/dự án | L | 0,50 | 3 b Đợt 3 |
| Khóa approved/diff/cache provenance | C19,C20; place_refs | 4 mỗi lượt sửa | M | 1,33 | 3 c trước apply 3D |
| Ánh sáng/env + facts inspector | C17,C21; stage_facts | 3 1–2/dự án | M | 1,00 | 3D Đợt 3 |
| Audio/subtitle/timeline preview | C25–29; voice/ffmpeg | 3 1–2/dự án | M | 1,00 | 3 e sau gói ảnh/video |
| Phiếu admin/SLA/projection ngầm | C06,C36,C40; answers/taxonomy | 3 lỗi vượt quyền | M | 1,00 | 4 a Đợt 4, cần trước Tiểu Nhị |
| Trần Tiểu Nhị/80%/xin nâng | C31; ledger | 3 mỗi dự án | M | 1,00 | 4 b Đợt 4 |
| Tiểu Nhị context/tool adapter | C10–42 | 4 nhiều lần/dự án | M | 1,33 | 5 Đợt 5, sau 8 ca→41 ca |
| Shared revision/report Owner | C06,C14; assets | 2 thỉnh thoảng | M | 0,67 | 6 a Đợt 6 |
| Bài học/experience admin duyệt | C40; experience/lessons | 2 lặp độc lập | S | 2,00 | 6 b Đợt 6 |
| HTTPS/mobile compare | C09 | 1 chưa cần theo chốt | M | 0,33 | sau, không đợt gần |

Pet Lão Đại là desktop khác Dashboard: công M, F3 giả thuyết phiếu/ngày theo C31/C36, triển khai sau phân hệ phiếu (ĐỢT 9 Codex). Bảo trì tự động công L, F1 chưa số liệu, chờ xác nhận/cách ly/42 ca (ĐỢT 8+), không đưa vào đường tới pilot 8 ca. “Gói gửi kèm” lõi ĐỢT 8 việc 1 và nối sau #24; phần UI/Dashboard chưa tự coi đã làm. Bộ kiểm đang có tái dùng, chỉ bọc service/projection/editor thiếu.

## 7. Ca khung cuối và bốn tham chiếu sửa

`core/end_frames.py:56–62`: row ready nhưng start_job_id≠start hiện hành → usable_path=None. UI: “Khung cuối cũ vì đổi khung đầu (bản X→Y)” + xem đôi đầu mới/cuối cũ gắn nhãn không dùng + **“Tạo lại khung cuối theo đầu mới”** có báo giá; duyệt trước end_frames.redo(:256) enqueue. Không tự đổi ready thành “dùng được”, không nói gen video đã chắc có lastframe. Route bắt buộc thiếu giữ job; optional chỉ gửi không last frame khi người duyệt hiểu, cảnh báo rõ; cờ học việc không chặn/sửa thật.

Bốn nguồn đã mở: step1.py:292 gọi unlock_scene_fields; lessons.py:217–223 đếm lỗi chưa phân loại và diag, không đề xuất bài học; step1_prep.py:292–295 hướng dẫn đặt người lên background phối cảnh, không “Storyboard 2D” editor sân khấu; L13.md:24–31 movement_gaps/layout_drift chưa nối change_audit. Tham chiếu kế thừaĐợt 5 khác có thể lệch khi code đổi: triển khai phải mở lại base, không coi mọi số dòng cũ được revalidate.
