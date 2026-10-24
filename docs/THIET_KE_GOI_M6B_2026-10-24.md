# Thiết kế Gói M6-B — bốn vai chuyên trách, ba hạng M6.5/M6.6/M6.8

> **CX23-M6B-DESIGN · Codex 1 · 24/10/2026 · Cấp 1: tài liệu, 0 USD.**
> Bản để phiên chính trình EP duyệt phạm vi Cấp 2. Không triển khai code/cờ/schema, không bật production, không cấp quyền gửi API, không chạy thử trả phí.

## 1. Căn cứ và trạng thái tại lúc đối chiếu

Đối chiếu source của nhánh `codex/v31-m6b-design`, nền `c5ca0cdc`, lúc **15:28 ngày 24/10/2026, Asia/Saigon**. Các tên hàm dưới đây được đọc từ source, chưa gọi hàm hay chạy test. Chỉ thay tài liệu này.

Nguồn: `docs/CODEX_TASKS.md` mục CX23-M6B-DESIGN; `docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md` mục 1c, 3, 7–9; `docs/DANH_GIA_M6_DIEU_PHOI_VAI_2026-10-22.md` (mẫu M6-A, đặc biệt P6/P7/P9/P11); kế hoạch chính `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md`, dòng M6.5/M6.6/M6.8. Đánh giá 22/10 là mốc cũ, không chứng minh code ngày 24/10 đã có đủ các lớp mô tả trên giấy. Kế hoạch vai cũ xếp M6.8 vào gói M6-C; đề CX23-M6B-DESIGN hiện tại yêu cầu đưa thiết kế M6.8 vào tài liệu này, không tự đổi thứ tự hay đánh dấu việc triển khai đã được duyệt.

| Phần | Đã xác minh trên nền này | Giới hạn/dependency |
|---|---|---|
| M2.1/M1.9/M2.7/M2.9/M4.4 | Đề giao ghi các phụ thuộc code đã ✅; có BYĐ, replay, kiểm ảnh, âm thanh, kiểm bản dựng để tái dùng | ✅ code không đồng nghĩa cổng production đã qua; giữ yêu cầu bằng chứng của kế hoạch chính |
| M6.1 | `core/crew.py:owner_of`, `can_write`, `role_of_write` tra vai/trường | `can_write` là tra cứu, docstring ghi guard theo vai thuộc M6.4; không lấy kết quả tra cứu làm quyền ghi đã enforce |
| M6.2/M6.4 | **Codex 3 đang phụ trách, chưa được xác nhận XONG tại 15:28 24/10**; nền đọc này không có `core/handoff.py` | Chờ nhánh owner gộp + đối chiếu API/schema/guard. Mọi giao diện bàn giao bên dưới là yêu cầu, chưa phải hàm hiện hữu |
| Nguồn sân khấu A | Có `stage_desk`, `stage_auto`, `stage_facts`, `stage_crew`; `stage_auto.fingerprint(inputs)`, `stage_auto.apply(... expected_revs=...)`; `write_guard.rev(data)` | Không có `docs/STAGE_REGISTRY_A_PROTOCOL.md` hoặc module `stage_registry` trên nền này. Không dựng store/registry A mới; thiếu pin/revision thích hợp là OPEN |
| M2.10 | `lean_package.build`, `shadow`, `shadow_job`; runner có `_lean_shadow` | Là gợi ý shadow cạnh gói đã gửi, không tự quyết bộ ref và không phải builder gửi thứ hai |

**Hai chốt đã có, không hỏi lại:**

- Q-B, sổ `ep-2210-qb-motion-prompt-auto-2026-10-22`: VPA tự viết; Director tự chấp nhận motion prompt khi kiểm đạt, không đổi BYĐ/dữ liệu khóa. **Chấp nhận prompt không cấp quyền gửi API, duyệt take hay cấp lượt gen.**
- E1, sổ `ep-2210-e1-ref-set-owner-2026-10-22`: vai chuyên trách đề xuất reference; code kiểm hợp lệ/giới hạn model và đóng gói. Lưu đúng ref thực gửi. Hai mục này ghi `APPROVED_IN_PRINCIPLE`, không phải lệnh triển khai Cấp 2 hoặc bật/tốn phí Cấp 3.

## 2. Ranh giới chung và hợp đồng đề xuất

Bốn vai là **VPA, SBA, Sound Designer, Editor/VFX**; M6.8 chứa hai vai riêng, không gộp thành một chủ sở hữu trường. Registry vai hiện có và nguồn sân khấu A hiện có là nguồn duy nhất; tài liệu này không thêm registry, quyền hoặc hàng đợi cạnh tranh.

Luồng dự kiến: snapshot đầu vào → kiểm mâu thuẫn 0 USD → đề xuất của vai → kiểm tất định → Director phân xử/chấp nhận trong quyền đã chốt → giữ đề xuất shadow. Apply production/gửi API nằm ở luồng riêng, chỉ được nối sau Cấp 2/3 và các dependency đạt cổng. Trong gói shadow, trạng thái “Director chấp nhận” cũng chỉ là kết quả quan sát, không tự sửa motion đã dùng.

### 2.1. Đầu vào chung

Một snapshot bất biến gồm project/shot/group ID; loại job/model/route; BYĐ và provenance; camera/blocking/plate đọc từ nguồn A qua các lớp hiện có; các asset/take được duyệt; ID và hash file ref; mã ảnh theo đúng thứ tự của builder; trạng thái USER_LOCKED; revision đọc hiện tại; dấu vết nguồn và fingerprint đầy đủ.

- `shot_intent.read`, `validate` đọc/kiểm BYĐ; `stage_facts.stage_of`, `stage_auto.inputs_for`, `fingerprint` là các điểm dữ kiện sân khấu hiện có. Không gọi `run_segment` hoặc `stage_desk.approve` để lấy dữ liệu vì chúng là đường tác động.
- `write_guard.rev(data)` hiện là revision của dữ liệu scene, **không giả định đã có revision từng trường hoặc CAS nhiều aggregate**. Hash ảnh/take/model/BYĐ/nguồn A cần pin cùng snapshot; thiếu revision/provenance → `INCOMPLETE_INPUT`/HOLD ứng viên, không tự tạo `_rev` hay suy camera.
- `send_preview.video_package` là đường preview video có bọc provider, `_preview`, giữ ghi chú ngoài DB. Tái dùng kết quả của nó và gói canonical runner; không dựng danh sách ref bằng công thức riêng. Ảnh chưa xác minh có API preview thuần tương đương: Cấp 2 phải tách adapter **tái dùng** `ImageRunner` và chứng minh không I/O phụ, không viết lại builder.
- Ref đề xuất của vai là một diff trên danh sách candidate có nguồn, không được dùng URI lạ, thêm ảnh từ project khác, đổi thứ tự âm thầm hoặc biến bản đề xuất thành ref thực gửi.

### 2.2. Đầu ra chung — schema khái niệm, chưa tạo store

| Trường đề xuất | Ý nghĩa |
|---|---|
| `role`, `project_id`, `scene_ids`, `handoff_id` | Vai thật và phạm vi; ID bàn giao chỉ gán bởi M6.2 khi API đã gộp |
| `source_fingerprint`, `source_revisions`, `dependencies` | Pin nguồn đọc; phụ thuộc thiếu là OPEN, không ghi giả revision 0 |
| `proposal`, `diff`, `coverage`, `findings` | Nội dung ứng viên, trường định thay và từng nhịp/dữ kiện được phủ |
| `model_target`, `refs_proposed`, `refs_actual_snapshot` | Phân biệt bộ ref đề xuất với gói canonical đã dựng/đã gửi; không gọi proposal là actual |
| `status`, `cause_code`, `return_count`, `needs_ep` | `SHADOW_ONLY`, `RETURNED`, `REVIEW_REQUIRED`, `INCOMPLETE_INPUT`; trạng thái này không là lệnh tạo job |
| `validator_version`, `evidence_ids`, `cost_status` | Có nguồn kiểm, so cùng phiên bản; chưa đo phí ghi UNKNOWN, không ghi 0 thay cho thiếu giá |

M6.2 quyết định lưu/đọc các phiếu; M6-B chỉ yêu cầu adapter tương thích sau gộp. Không tự đặt JSONL, bảng CSDL hoặc hộp thư production thứ hai. Hộp thư `tools/hop_thu.py` là phối hợp phát triển, không phải hàng đợi vai làm phim. Bản so offline/test có thể lưu trong thư mục nghiệm thu giả; chưa ghi `data/projects` thật.

USER_LOCKED ở prompt/ref/BYĐ/giọng/cut giữ nguyên: chỉ proposal diff `REVIEW_REQUIRED`; Director tự chấp nhận theo Q-B không được ghi đè trường khóa. Mọi recheck khi apply tương lai phải dùng `current_user`/ACL và guard hiện hành, kiểm revision mới; role string không phải người đăng nhập, không cho actor giả `user` né tiền. M6.4 chưa gộp → giữ shadow, chưa nối writer. Mỗi callback/job observer dùng ngữ cảnh riêng, lấy identity qua current_user/ACL hiện hành; không gán p.user/p.actor/p.origin lên Pipeline cache dùng chung. Candidate được Director chấp nhận hoặc role label hợp lệ vẫn không tạo ACL mới hay mở quyền gửi.

## 3. M6.5 — Video Prompt Artist

### Đầu vào/đầu ra

Đọc snapshot chung, các nhịp BYĐ/âm thanh và end-state đã chốt, ảnh đầu/cuối đã duyệt nếu có, camera và số đo plate, hướng dẫn model và giới hạn ký tự. Trước khi viết, kiểm BYĐ ↔ ảnh ↔ camera ↔ ref; mâu thuẫn trả đúng vai chủ dữ liệu, không “chữa” BYĐ bằng prompt.

Đầu ra: prompt ứng viên + coverage từng nhịp BYĐ trích đoạn chữ tương ứng; refs đề xuất có lý do; model target; các lint tìm thấy; fingerprint và diff. Model/route mới chỉ đề xuất, không đổi job/model đã được duyệt. Một lượt viết và tối đa một lượt sửa theo phát hiện là **đề xuất trần thiết kế**; mọi lượt cần engine LLM thật vẫn phải có duyệt phí riêng.

### Điểm bọc/thay đã xác minh

| File:hàm hiện có | Vai trò hiện tại | Cấp 2 dự kiến, không làm ở bản này |
|---|---|---|
| `core/runner.py:chat_rewrite` | D6 video/ảnh; sau rewrite còn `kept_after_rewrite` của side_truth/skill_objects/travel_truth | Tách observer lấy assembled/ref đã pin; shadow không thay return value hoặc ghép câu ứng viên vào prompt đang gửi |
| `core/chat_prompt.py:build_text`, `fingerprint`, `rewrite`, `check`, `no_added_features` | Engine D6, cache/app_settings, gọi LLM và có bước đổi chữ | Tái dùng khuôn/khóa cache; **không gọi rewrite như hàm thuần**. Adapter role cần client/cache/sink kiểm soát. Những bước đổi chữ trở thành finding cho ứng viên trong thiết kế apply sau này, không âm thầm đổi prompt |
| `core/lean_package.py:classify`, `select`, `build`, `shadow` | Chọn/gợi ý bộ ref và prompt tối giản từ gói thật | Xuất proposal cho VPA; code chỉ validate khả thi, không nâng gợi ý select thành quyết định sáng tạo được gửi |
| `core/send_preview.py:video_package`; `core/runner.py:VideoRunner._build_package` | Preview và canonical package của đường gửi | Cùng một nguồn ref/order/payload. `_build_package` có metadata/điều kiện theo job, không được giả định pure hoặc dựng lần hai làm lệch gói |
| `core/seedance_refs.py:shot_motion`, `write_by_code`, `code_motion`; `core/llm_runner.py:run_motion` | Các đường nội dung motion hiện có; run_motion có LLM, các writer có tác động | Audit/tái dùng khuôn, không gọi tự động trong shadow. Chỉ sửa cách viết khi có gói apply riêng, không đổi API ngầm |
| `core/video_pregen.py:check`, `plan_of` | Kiểm/đọc kế hoạch gửi video hiện có | Giữ tách khỏi quyết định Director chấp nhận prompt; xác minh side effect trước gọi ở observer |
| `core/motion_prompt_lint.py:end_frame_problem`; `core/speaker_lint.py:problems`; `core/video_rules.py:problems` | Kiểm end-frame/người nói/model | Tái dùng kiểm; **không gọi `speaker_lint.apply` để tự thêm câu** vào ứng viên |
| `core/skill_objects.py:standing_text`; `core/prompt_formula.py:red_issues` | Có đường biến đổi chữ và kiểm công thức | So diff/giữ cảnh báo; không thay ý đồ hoặc biến vật mọc thành vật đứng sẵn bằng code khi vai là chủ nội dung |

Lưu ý: `chat_prompt.no_added_features` hiện trả prompt đã thay chữ cùng phát hiện; `chat_rewrite` có ghép câu trở lại. Đây là **điểm cần thiết kế adapter/validator riêng**, không thể tuyên bố chỉ đổi tên D6 là đã đáp ứng “code chỉ kiểm”. OFF giữ các đường legacy này nguyên trạng; shadow ON không sửa chúng.

Director chỉ có thể đánh dấu ứng viên đạt Q-B khi coverage đầy đủ, lint/model/ref/order đúng, revision còn khớp, không diff vào BYĐ/khóa và không mâu thuẫn đầu vào. Kết quả shadow thiếu check → giữ/return, không fallback “được duyệt” từ việc legacy vẫn gửi được. Send vẫn qua cơ chế xác nhận/giá/lượt/paused/claim/unknown hiện có khi được phép ở gói khác.

## 4. M6.6 — Storyboard Artist

### Đầu vào/đầu ra

Đọc snapshot BYĐ/camera/plate và trạng thái nhân vật/đạo cụ từ Kho; shot grouping/anchor/own_camera và ref thứ tự canonical. Khác VPA: sản phẩm là **đề xuất image_prompt/layout/end-frame và ref ảnh**, không phải motion hay quyền duyệt sân khấu.

Đầu ra: prompt ảnh ứng viên, layout diff, mô tả end-frame nếu nguồn đã có, coverage BYĐ + Kho (ai ở/không ở khung, view/form, vũ khí), ref proposal, phát hiện sai plate/anchor, fingerprint. Thiếu ảnh sau/mặt sau không suy nhận dạng từ một mặt; thiếu số đo ghi VÀNG/UNKNOWN theo policy sẵn có. Xung đột hoặc dữ liệu khóa trả phiếu đúng chủ, không tự đổi shot grouping hay sân khấu để dễ gen.

| File:hàm hiện có | Điểm sử dụng/bọc Cấp 2 |
|---|---|
| `core/assets.py:scene_references`; `core/scene_storyboard.py:group_of`, `anchor_picture`, `shared_references`, `cast_missing`, `job_fields` | Dùng grouping/anchor/cast/ref đúng nguồn hiện có; không mở cờ anchor_by_spot hoặc bỏ own_camera để dùng chung ảnh |
| `core/storyboard_frames.py:mapping_text`, `run` | Mapping nhãn ref để kiểm. **run gọi provider và chờ/tải ảnh**, không gọi trong shadow; không chạy nó để “xem trước” |
| `core/runner.py:ImageRunner._submit_args`, `_submit_kwargs`; `core/runner.py:chat_rewrite` | Adapter ảnh tái dùng builder canonical, chụp dữ liệu trước engine; phải chứng minh preview không upload/gen/ghi DB trước khi nối |
| `core/chat_prompt.py:build_text`, `fingerprint`, `check` | Chung engine/khuôn với VPA, cache tách kind/model/fingerprint/role và phiên bản kiểm, không dùng ứng viên video làm ảnh |
| `core/shot_intent.py:read`, `validate`; `core/batch.py:image_gates` | Kiểm BYĐ/cổng ảnh đúng phạm vi shot; findings không đồng nghĩa đã sửa dữ liệu hoặc đã gen lại |

SBA chỉ chủ prompt/layout/ref ảnh thuộc registry. Các trường đã đối chiếu là `image_prompt`, `layout`, `layout_people`, `end_frames.prompt`; layout chỉ diễn đạt dữ kiện blocking/camera đã pin, không được ghi ngược trường Cinematographer/3D hoặc nguồn A. `end_frames.prompt` không cấp quyền đổi BYĐ/end_state. Cinematographer/3D Artist/Director vẫn giữ camera, sân khấu, ý đồ; duyệt take ảnh không được suy ra từ “prompt hợp lệ”. Cần kiểm owner/field thực với M6.1/M6.4 sau gộp, không tự thêm field quyền vào registry trong task thiết kế.

## 5. M6.8a — Sound Designer

Đầu vào: thoại/lời dẫn và ý đồ âm thanh đã chốt, vai người nói/voice-only, profile giọng có nguồn, clip duration/timeline hiện hành, Kho âm thanh đã có license/nhận dạng, ref audio explicit nguồn/đoạn/tốc độ nếu có. Đầu ra là proposal theo cue/shot: chọn giọng, chữ đọc diff, nhạc/SFX/ambience, gain/duck và khớp môi, khoảng thời gian, nguồn asset/license, coverage sound_intent, cảnh báo vượt shot; không sinh file TTS/nhạc/lipsync tự động.

| File:hàm hiện có | Ranh giới bọc/thay Cấp 2 |
|---|---|
| `core/sound_intent.py:clean`, `of`, `music_plan`, `unmet` | Đọc/kiểm ý đồ và đo phần cue còn thiếu; không tự thêm cue production |
| `core/voice_casting.py:clean_traits`, `persona`, `apply`; `core/voice.py:planned_lines`, `generate`, `preview` | Trait/persona là đầu vào. **apply ghi profile, generate/preview có thể trả phí**: shadow không gọi các writer/generator này |
| `core/sfx_plan.py:timeline`, `catalog`, `build_prompt`, `propose`, `apply` | Timeline/catalog/khuôn tái dùng; propose có LLM, apply ghi cue: không gọi như preview thuần. Dùng ứng viên đã có/fixture ở shadow 0 USD |
| `core/dialogue_take.py:segments`, `billed_seconds`, `lip_directive`; `core/lipsync.py:plan`, `post_tick` | Tính kế hoạch/kiểm lời và phạm vi; post_tick có gửi dịch vụ/ghi trạng thái, không chạy trong observer |
| `core/music.py:default_brief`, `submit_drafts`; `core/ambience.py:choose`, `beds`; `core/ref_audio.py:tempo`, `propose`, `fit` | Brief/chọn asset/kiểm tỉ lệ dùng làm dữ kiện. submit_drafts trả phí; beds/fit sinh file; ref_audio.propose có dọn/trích file: không cho shadow tự gọi |

Âm thanh thiếu metadata/giọng/license/đoạn gốc → proposal incomplete, không đoán tempo, không lấy file không rõ quyền. Mẫu số thời gian theo clip đang dùng; thay take/tốc độ làm cue stale, không tự kéo shot hoặc thay lời thoại của Scriptwriter. Muốn dùng model nghe âm thanh phải xét sẵn có; không tự download model qua `sound_ai`.

## 6. M6.8b — Editor / VFX

Đầu vào: đúng take đã chọn, lineage/revision, timeline/clip durations, cue Sound đã được chấp nhận ở đúng phạm vi, ý đồ dựng và bản rough-cut/QC hiện có. Đầu ra: edit decision list/cut/transition/post-FX/caption proposal, diff thời gian/coverage, rủi ro mất thoại/âm thanh, fingerprint rough-cut; không render, replace bản giao hay duyệt phim trong shadow.

| File:hàm hiện có | Ranh giới bọc/thay Cấp 2 |
|---|---|
| `core/final_cut.py:collect_clips`, `collect_clips_for_render`, `render_problems` | Dùng đúng take và kiểm thời lượng, không tự chọn take chỉ vì mới nhất; dữ kiện thiếu HOLD ứng viên |
| `core/rough_cut.py:fingerprint`, `build` | Tái dùng định danh bản dựng. **build tạo bản thô/ảnh sheet**, shadow đọc artifact đã có, không gọi build để đo đối chứng miễn phí giả |
| `core/editor_review.py:fingerprint`, `editor_prompt`, `vet`, `reconcile`, `run` | Tái dùng khuôn và kiểm finding/đối chiếu Director. **run gọi Claude và lưu kết quả**, shadow không gọi tự động |
| `core/editor_apply.py:plan`, `qc_worse`, `apply`, `revert` | plan là đề xuất, cần kiểm read-only trước bọc; apply/revert thay bản dựng/ghi dữ liệu, không dùng trong shadow. Revert hiện hữu không phải giấy phép rollback dữ liệu thật |
| `core/ffmpeg_studio.py:build_crossfade_cmd`, `build_mux_music_cmd`, `build_extras_mix_cmd`; `core/delivery.py:render` | Tái dùng cách đóng lệnh ở kế hoạch sau, không chạy command/render để “so shadow”; tránh tạo hai bộ dựng production |
| `core/post_fx.py:validate`, `fingerprint`, `apply` | Kiểm thông số/fingerprint; apply tạo đầu ra, không tự chạy. Final QC/duyệt giao vẫn độc lập |

Khi cần preview/render ở gói sau, FFmpeg dù 0 USD vẫn tốn CPU/I/O: gửi tác vụ có owner sang worker/queue local đã được xác minh trên main, trả job/status để Streamlit chỉ poll nhẹ; không render trong rerun. Adapter/queue/cancel theo owned process chưa đủ thì ghi dependency OPEN trước khi nối, không tạo worker chạy nền ngoài kiểm soát. Không lấy benchmark fixture “5 dự án” hay nhánh hiệu năng ngoài main làm cam kết công suất production. Shadow của thiết kế này không tự render.

Editor/VFX không đổi nội dung giọng/chữ đọc thuộc Sound/Scriptwriter; Sound không sửa cut thuộc Editor. Mâu thuẫn timing → phiếu có source và N/D; không âm thầm kéo clip cho đủ cue hoặc cắt mất câu. “Dựng kiểu #27” ở đây là tập yêu cầu kiểm trong replay giả, chưa có thử thực tế hay cam kết chất lượng đầu ra.

## 7. Chế độ shadow, phí và so builder cũ

### 7.1. Cờ đề xuất, **chưa thêm vào features**

| Hạng | Cờ đề xuất, default OFF | OFF | ON trong giai đoạn 0 USD |
|---|---|---|---|
| M6.5 | `crew_vpa_shadow` | Không gọi observer/engine/cache/sink mới | Đọc snapshot + ứng viên fixture/cache đã có nguồn; chỉ phân tích/so sánh |
| M6.6 | `crew_sba_shadow` | Như cũ byte-for-byte | Như trên, loại image tách video |
| M6.8 | `crew_sound_shadow`, `crew_editor_shadow` | Như cũ byte-for-byte | Hai observer độc lập; không gọi TTS/nhạc/LLM/render |

Cờ ON **không tự cấp chi phí**. Phiên đề xuất thủ công dùng LLM thật chỉ được có sau duyệt Cấp 3 riêng (ước tính trước + trần + sổ chi); phải nêu ai bấm, model, số lượt, snapshot, hạn mức và đường dừng. Thiết kế/lập trình/replay giả ở gói này có **trần 0 USD cho cả bốn vai**; số liệu phí thật chưa có là UNKNOWN. Cờ không nối `_submit_pending`, `provider.submit`, `batch.queue_*`, các writer production, Duyệt hết hoặc autopilot để sinh tác dụng mới.

Không dùng `chat_prompt.rewrite`, `sfx_plan.propose` hay `editor_review.run` như pure helpers: các hàm này có LLM/cache/ghi. Lựa chọn mặc định: observer chỉ đọc artifact có sẵn; thiếu ứng viên thì ghi `NO_SHADOW_SAMPLE`, không tự gọi API để đủ mẫu. Sink đề xuất phải qua M6.2 sau gộp, chỉ vùng shadow được duyệt, không lưu secrets/payload/đường dẫn riêng tư vào tài liệu so mù.

### 7.2. Số đo và ngưỡng đề xuất để EP chốt Cấp 2

`coverage` do vai tự khai chỉ là claim cần đối chiếu, không phải bằng chứng độc lập hay quyền tự chấm sản phẩm của mình. Tái dùng `core/continuity_validator.py:read_evidence`, `build` và `core/qc_evidence.py:validate` để gom/kiểm hợp đồng bằng chứng, chỉ sau xác minh đường đọc không có side effect; validate schema không chứng minh hình/âm thanh/video đúng. Các đường `run`/`record` có thể gọi kiểm hoặc ghi bằng chứng, không gọi trong observer 0 USD khi chưa rà/duyệt. Thiếu chứng cứ độc lập cho một tiêu chí → UNKNOWN/so mù EP, không đổi claim thành đạt. Q-B vẫn cho Director tự chấp nhận prompt khi **thực sự đủ kiểm tra**, không suy prompt hợp lệ thành duyệt chất lượng clip/sản phẩm.

| Vai | Đối chứng builder legacy cùng snapshot | Thước đo shadow, có tử/mẫu và thiếu dữ liệu |
|---|---|---|
| VPA | Prompt/ref/order/payload canonical, model, BYĐ, lock và warnings hiện có | Coverage nhịp 100%; 0 diff trái khóa/ý đồ; lint đạt ≥98% số ứng viên đủ đầu vào; 100% nhãn ref khớp gói; EP chọn VPA ≥2/3 trên ≥15 shot so mù đủ mẫu |
| SBA | ImageRunner + nhóm/anchor/plate/cast hiện tại | Coverage BYĐ+Kho 100%; 0 sai scope/view/form/own_camera; 0 tự thêm/chuyển ref ngoài proposal; cùng ngưỡng lint/so mù như VPA, báo riêng phần thiếu plate |
| Sound | Brief/cue/timeline/profile hiện có, không gen audio đối chứng | 100% cue trace được về sound_intent/nguồn license; 0 cue ngoài shot hoặc diff trái khóa; số cue chưa đáp ứng/không có dữ liệu báo riêng; tỷ lệ so mù chỉ đo khi đã có audio, không suy từ JSON |
| Editor/VFX | Take đang dùng + rough-cut fingerprint + bộ dựng cũ | 0 thay take/BYĐ/cue trái chủ; 0 cắt mất thoại bắt buộc; EDL timing hợp lệ 100%; số finding hợp lệ/rejected và chi phí/thời gian render chỉ là UNKNOWN khi chưa thực hiện |

Ngưỡng ≤1,5 lượt LLM/shot từ kế hoạch gốc là tiêu chí **đo khi có lượt đã được duyệt**, không chạy thêm để làm đẹp số. Độ đúng hình/chất lượng âm thanh/video không được chứng minh bằng lint hoặc fixture. Shadow đạt số đo không tự chuyển default ON hay thành production.

Golden OFF: trên fixtures đóng băng và pin time/ID, so **raw bytes** prompt, serialized provider args/kwargs, ref/order, sent_package/warnings và trace lời gọi legacy trước/sau; hash DB/asset trước/sau cùng mock/clock. OFF không thêm gọi cache/LLM/provider, upload, job, diag hoặc file shadow. Với ON, trace tăng chỉ observer/sink shadow được phép; phần production vẫn bằng baseline (không cộng side effect do shadow). Không normalize mất nội dung khác biệt để làm test xanh; baseline có nguồn commit, không so hai lời gọi cùng code mới. Tái dùng `tools/replay_payload.py:replay`, `compare` khi triển khai fixture, không tự đổi tiêu chí so payload. `gen_auth.authorize`/`shadow` hiện là các điểm quyết định/quan sát cần đối chiếu trạng thái cờ; không tuyên bố M6-A shadow đã là cổng enforce chung cho mọi đường gửi.

## 8. Kế hoạch triển khai sau duyệt và test đỏ → xanh

1. **M6B-0 — chốt contract/adapter:** đối chiếu M6.2/M6.4 sau Codex 3 gộp; pin provenance nguồn A qua code hiện có; xác định adapter preview ảnh. Chưa đủ thì chỉ fixture/hợp đồng, không nối production.
2. **M6B-1 — VPA/SBA observers:** mỗi vai một nhánh, chung khuôn/schema/test helper có owner rõ. Không sao chép builder/registry. Ưu tiên cùng bộ snapshot để so song song 0 USD; tránh vòng phụ thuộc VPA đợi SBA mới làm được mọi việc.
3. **M6B-2 — Sound và Editor:** hai vai theo timeline/cue contract; có thể song song khi không đụng delivery/ffmpeg chung. Gom các sửa chung schema/test fixture; không nhận file còn owner.
4. **M6B-3 — nghiệm thu shadow offline:** một file manifest bộ mẫu giả có thể chứa replay cấu trúc #24/#27/#31, không đọc data thật trong test. Mẫu thật/ảnh/sổ chi do phiên chính thực hiện chỉ sau cho phép và rà riêng. Không coi tên fixture #31 là đã kiểm dự án #31 thật.
5. **M6B-4 — trình tiếp:** chỉ sau bằng chứng hợp đồng, OFF golden và so mù đủ mẫu mới trình riêng việc apply/sản xuất. Pilot trả phí cần đề/trần Cấp 3; giữ M6.12 là nghiệm thu riêng.

| Nhóm test đề xuất | Ca đỏ cần bắt trước sửa | Xanh phải chứng minh |
|---|---|---|
| OFF golden | Nhánh observer bị gọi khi OFF; prompt/refs/payload đổi; diag/file tăng | Byte-for-byte với baseline trước thay đổi, 0 side effect mới; không cần GUI |
| Phí/side effects ON | Rewrite/LLM/provider/TTS/render/writer bất ngờ được gọi | Mock ném lỗi mọi điểm tiền/ghi production; ON vẫn không gọi, thiếu mẫu có báo |
| Snapshot/ownership | Thay revision giữa đọc/kiểm, khác project, USER_LOCKED, ref file đổi hash, role không sở hữu | Proposal incomplete/review-required, không ghi; sau M6.4 thật phải có test cổng ghi riêng, không giả bằng can_write |
| VPA/SBA | BYĐ↔ảnh mâu thuẫn; Image N sai order; 3 người/ref thiếu; vật đứng sẵn bị đổi thành mọc; camera own bị dùng chung anchor | Trả đúng vai/cause, coverage N/D; giữ nguyên cả locked prompt/ref; không thêm câu “sửa hộ” |
| Sound | Thiếu license/nguồn audio; cue vượt shot; thoại offscreen bị biến thành khớp môi; giọng khóa | Finding/proposal, không gọi generate/preview/post_tick; không cắt/kéo tự động |
| Editor | Take stale, duration đổi, mất thoại, proposal đổi cue của vai khác; rough-cut missing | Không apply/render; source fingerprint và diff đầy đủ, phát hiện trả đúng chủ |
| Handoff/rollback | Đề xuất trùng snapshot, phiếu trả lặp, lỗi sink, M6.2 chưa có | Dedup theo role+snapshot+validator; giữ return_count theo M6.2, không queue mới. Return cap chưa có → OPEN/escalate, không vòng tự sửa vô hạn |

Tái dùng nhóm test hiện có `test_chat_prompt*.py`, `test_v31_m210_lean_package.py`, `test_storyboard*.py`, `test_editor_review.py`, `test_editor_apply.py`, `test_v31_m63_gen_auth.py`; tạo test role observers khi Cấp 2 được duyệt, khai areas không tăng version ở nhánh task. Test tiền/quyền/dữ liệu cần RÀ KỸ độc lập, root đọc lại diff sửa. Môi trường test: thay **OBJECT** os.environ bằng dict giả trước imports/calls/spawns; mock registry/keyring/credential/provider/model, native env whitelist; pytest `--tb=no`, không showlocals/dump/print token/header/payload.

Tài liệu này không chạy test. Nếu cần kiểm giao diện ở gói triển khai, dùng AppTest cho logic/mock; ảnh UI thật do Claude/phiên chính nghiệm thu theo công cụ được phép. Không Computer Use trong phiên này.

## 9. Rollback và điều kiện dừng

- Tắt đúng cờ observer, hủy chỉ task shadow do mình tạo; không hủy job legacy hay provider request đang chạy. Không kill worker/browser chung.
- Giữ bản baseline legacy và artifact shadow tách biệt. OFF phải được chạy lại golden sau thay đổi Cấp 2; ON trước đó không được để cache/role state làm OFF đổi hành vi.
- Không tự xóa dữ liệu thật/asset, không migration, không sửa sổ quyết định/quyền khi rollback. Ứng viên stale giữ làm bằng chứng với trạng thái vô hiệu, không phục hồi bằng ghi đè snapshot cũ.
- Phát hiện ghi production, gọi API ngoài ý định, bỏ guard hoặc lock/provenance không đủ → dừng observer tương ứng, ghi sự cố đã lọc bí mật, trình owner/EP. Không lấy “cờ shadow” làm lý do thử tiếp tác vụ trả phí.

## 10. Ba câu trình EP — mỗi câu có phương án đề xuất

Đây là câu hỏi của **bản thiết kế mới**, chưa gửi EP bằng công cụ. Q-B/E1 đã chốt nên không hỏi lại.

1. **Duyệt Cấp 2 tới đâu?** Đề xuất duyệt M6B-0…3 observers/fixtures và hợp đồng shadow, bốn cờ OFF, **0 USD**, không apply/gửi production. Phần apply/pilot mặc định giữ cho đề tiếp theo.
2. **Shadow thiếu ứng viên có được gọi LLM không?** Đề xuất **không**: ghi NO_SHADOW_SAMPLE, dùng fixture/cache có nguồn. Nếu cần thu mẫu LLM mới, trình Cấp 3 riêng với trần theo vai/model/số shot và sổ chi, không gộp vào việc bật cờ shadow.
3. **Cổng shadow mới của hai vai Sound/Editor?** Đề xuất coverage/ownership/timing theo mục 7.2, 0 diff trái khóa và không suy chất lượng từ JSON; chưa có media để so thì chưa đủ mẫu. Ngưỡng VPA/SBA từ kế hoạch gốc giữ nguyên, không xin hạ hoặc coi chưa đủ mẫu là đạt. Đây chỉ là cổng observer của gói Cấp 2, chưa duyệt apply/render/gửi production.

**Trạng thái cuối tài liệu:** thiết kế để trình, chưa có duyệt Cấp 2, chưa triển khai M6.5/M6.6/M6.8, chưa đo chất lượng/pilot thật. M6.2/M6.4 và pin nguồn A/preview ảnh còn dependency OPEN như mục 1–2.
