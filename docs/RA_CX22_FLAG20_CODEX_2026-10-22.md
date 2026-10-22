# CX22-FLAG20 — đo tác động verified của 20 cờ trên Windows

Ngày 22/10/2026, Asia/Saigon. Nhánh `codex/v31-flag20`; nền cố định `85f08963`. **Chỉ đo và tài liệu, 0 USD.** Không sửa `core/`, `dashboard/`, test/assertion hoặc cờ production; không gọi API thật, không truy cập `data/` live.

## Câu hỏi và phạm vi kết luận

20 cờ được trích bằng AST từ diff `9998b46b^..9998b46b` (13/10); không merge nhánh cũ. Con số **362 test đỏ** là số lịch sử được đề bài ghi, không phải số vừa đo lại. Không có danh sách 362 node trong nguồn đã đọc. Sau đó main đã thay đổi đáng kể, đặc biệt `tests._flags.pin_off`, `_TEST_BYPASS` và các cổng M7.

Phép đo hiện tại mô phỏng `verified=True` kiểu **soft** đúng `tools/testing/flagforce.py`: chỉ đổi metadata trong bộ nhớ của subprocess test; các lựa chọn TẮT tường minh của từng test vẫn thắng qua `_TEST_BYPASS`. Không ép `features.on/state` trả ON bất chấp fixture. `music_story_arc` đã verified True ở nền nên bật riêng là đối chứng không thay đổi.

Đây là **matrix hồi quy có chọn mẫu**, không phải cả bộ `-m not slow` cho từng cờ. Không được diễn giải một hàng 0 thành “cờ an toàn trên toàn bộ hệ thống” hoặc dùng test giả để cho phép khóa production.

## Phương pháp / an toàn / kiểm soát nhiễu

1. Cohort K8: 158 node từ `docs/flagmatrix/k8_failed_2026-10-21.txt` (artifact 8 cờ ngày 21/10, không phải danh sách 362 gốc).
2. Cohort bổ sung: 68 ca contract/backend từ package overrides, outfit, motion, send claim, sample quality, music, review frames, shot intent, voice, continuity, ambient, prop lock. Hai cohort không trùng node.
3. Mốc không đổi verified và bật cả 20 trên mỗi cohort. Những node xanh ở mốc nhưng đỏ khi bật 20 tạo cohort attribution chung **107 node**. Bật riêng từng cờ trên cùng 107 node, mỗi lần là subprocess mới, không kế thừa trạng thái cờ/test của lần trước.
4. Chạy Windows native Python3.14 tuần tự trong mỗi subprocess, không xdist. Hai subprocess phép đo độc lập có HOME/TEMP/feature settings/DB giả riêng. Trần sở hữu 600 s mỗi lượt; không chạy 20 cả bộ.
5. Native khởi động bằng whitelist môi trường; thay **OBJECT** `os.environ` bằng dict giả qua `patch.object` trước import pytest/project. Không `patch.dict(clear=True)`, không nạp dashboard.env/khóa/UserEnv; registry được mock trả không tìm thấy trong đối chứng cuối; loader dashboard.env bị mock trước gọi; provider/transport do fixture giả cung cấp. Mạng ngoài bị audit hook chặn; chỉ loopback IPC cho asyncio Windows, cấm cổng live 8501/8502. Đọc dashboard.env và đường dữ liệu production bị chặn. `--tb=no`, không showlocals/dump env; chẩn đoán chỉ fixture đã cách ly.
6. Lượt đầu audit hook chặn cả socketpair loopback khiến 36 UI đỏ do harness. Probe stack không locals chỉ ra `asyncio._make_self_pipe → socket._fallback_socketpair`. Đã sửa harness NGOÀI repo chỉ để cho phép IPC, đo lại đúng 36 UI: mốc 36 xanh; all20 34 xanh / 2 đỏ. Không sửa assertion/core để che lỗi. Các số hợp lệ dưới đã loại nhiễu này; giữ kết quả thô ngoài Git.

## Mốc hợp lệ trước attribution

| Cohort | Mốc | Bật 20 | Cách đọc |
|---|---|---|---|
| K8 158 node (backend + UI đo độc lập sau sửa IPC) | 144 qua / 1 đỏ / 13 bỏ qua | 51 qua / 94 đỏ / 13 bỏ qua | 93 node đỏ mới |
| Contract/backend 68 | 68 qua | 54 qua / 14 đỏ | 14 node đỏ mới |
| Hợp 226 node | 212 qua / 1 đỏ / 13 bỏ qua | 105 qua / 108 đỏ / 13 bỏ qua | **107 node mới đỏ** |

Mốc có 1 đỏ riêng `tests/test_lipsync.py::RunnerTests::test_a_marked_close_up_goes_to_seedance_with_its_voice`: reference_audio rỗng so với fixture mong có một file. Đã tái kiểm trong fixture fake; không gán lỗi này cho 20 cờ. Chưa điều tra hết gốc vì ngoài phạm vi attribution.

Các số K8 là phép ghép kết quả backend và 36 UI chạy độc lập, không gọi là một lượt cả bộ 158 sau chỉnh harness. Selection bias: 107 node chọn từ lỗi khi bật đồng thời; cờ riêng có thể bộc lộ lỗi khác ở node mà all20 đã che. Muốn số toàn cục cần mở rộng matrix trên toàn bộ not-slow ở bước tích hợp.

## Kết quả từng cờ

**Đã đo đủ 20 × 107 = 2.140 lượt test riêng theo cờ.** Đối chứng không đổi verified trên cùng 107 node: **107 qua**. 13 cờ không phát sinh đỏ trong mẫu, 7 cờ có đỏ. Hợp node đỏ của từng cờ = **107**; tổng số đỏ các hàng = 113 (có trùng nguyên nhân, không cộng thành số ca độc lập). Không còn node delta nào nằm ngoài hợp lỗi của các lần bật riêng; điều này chưa chứng minh quan hệ nhân quả cho từng exception hay loại trừ tương tác giữa các cờ. Không có timeout trong 20 hàng.

| Cờ | Đỏ / 107 | Xanh | Gốc / đề xuất | Tối đa 3 test tiêu biểu |
|---|---:|---:|---|---|
| `package_overrides` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `layout_drift_review` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `short_lock_outfit` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `back_view_guard` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `send_claim` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `seedance_sample_mode` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `music_story_arc` | 0 | 107 | Đã verified True ở nền; phép bật là no-op | — |
| `end_frames` | 1 | 106 | Test hợp đồng mặc định OFF | `tests/test_end_frames.py::EndFrameFlowTests::test_off_by_default_nothing_waits` |
| `director_rewrite` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `change_review_frames` | 1 | 106 | Test hợp đồng mặc định OFF | `tests/test_change_review_frames.py::test_flag_default_off` |
| `change_review` | 102 | 5 | Workflow đổi khi bật / fixture chưa xử lý pending review | `tests/test_adapters.py::FactoryAndRunnerTests::test_end_to_end_success_writes_ordered_file`<br>`tests/test_camera_setups.py::CameraSetupTests::test_one_continuous_clip_is_sent_for_the_set_up`<br>`tests/test_code_motion_p27.py::CodeMotionHoldsWhatIsWrong::test_a_yellow_formula_check_is_not_approved_silently` |
| `stage_camera` | 1 | 106 | Test hợp đồng mặc định OFF | `tests/test_plate_camera_stage.py::test_flag_declared_off_by_default` |
| `shot_intent` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `video_pregen` | 1 | 106 | Test hợp đồng mặc định OFF | `tests/test_video_pregen.py::Registry::test_flag_default_off_and_declared` |
| `auto_voice_cast` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `p24_lessons` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `continuity_layout` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `ambient_motion` | 1 | 106 | Test hợp đồng mặc định OFF | `tests/test_ambient_motion.py::test_default_off` |
| `project_prop_lock` | 0 | 107 | Không đỏ trong cohort; không chứng minh an toàn toàn bộ | — |
| `two_tier_quality` | 6 | 101 | Model/tier, fingerprint gen lại và nhãn UI đổi; cần fixture ON phù hợp | `tests/test_runner.py::RunnerTests::test_project_video_model_is_passed_to_provider`<br>`tests/test_scene_regen.py::RegenerateVideoTests::test_can_regenerate_more_times_than_max_retry`<br>`tests/test_seedance_refs.py::SeedanceRefTests::test_runner_follower_cost_provenance` |

Bảng/node đầy đủ: `docs/flagmatrix/flag20_windows_2026-10-22.json`. Thời gian từng hàng ở JSON chỉ là thời gian test trong lúc hai phép đo đồng thời, không phải benchmark hiệu năng production.

## Gốc đã được xác nhận và đề xuất

- `change_review`: một probe độc lập `test_adapters::FactoryAndRunnerTests::test_end_to_end_success_writes_ordered_file` trả lý do giữ “Tổ rà soát tác động đang rà thay đổi #1” trước provider. `core/change_review.py:blocking/_blocking` giữ thay đổi pending/mục ĐỎ; `core/runner.py` giữ queued và ghi diag. Các E2E cũ mong gửi ngay nhưng chưa chạy rà giả/giải quyết change_event. Đây là hành vi cổng thật đổi khi bật, không bằng chứng provider hỏng. Nếu test chỉ mô tả đường cờ OFF: đặt OFF tường minh; nếu mô tả đường ON: chuẩn bị artifact, chạy review giả/kiểm giữ và duyệt/giải quyết đúng quy trình. Không xóa cổng production hay nới expected queued thành succeeded tùy tiện.
- Các test khẳng định default OFF / verified False: phải thay đổi cùng quyết định khóa từng cờ sau nghiệm thu; giữ nguyên trong nhiệm vụ chỉ đo này. Kiểm cả OFF byte và ON khi thiếu đầu vào giữ rõ lý do.
- Các exception dây chuyền cũng xuất phát từ fixture chưa vượt cổng: `tests/test_seedance_refs.py:real_png/_ready` gọi Pillow với approved_image_path rỗng sau ảnh bị giữ; `tests/test_end_frames.py:ManualSendTests` gọi private `_end_frame` bằng self.job=None. Vì vậy ValueError/TypeError/IndexError/KeyError không tự chứng minh crash đường gửi production. Sửa fixture xử lý rà soát giả hoặc pin OFF đúng phạm vi; giữ test ON cho cổng và dữ liệu thiếu. Không gọi dịch vụ thật để làm test xanh.
- `change_review_frames` có REQUIRES `change_review`; `ambient_motion` có `prompt_formula`; back_view cần luồng seedance_ref_groups/per_shot thực sự; end frame/ref-end-frame có dependency riêng. Không khóa cờ con khi chưa kiểm cha và từng luồng.
- Theo `docs/KE_HOACH_SUA_20_CO_2026-10-21.md` mục 6, các dòng Gói C vẫn là đề xuất riêng, không quyền nối/bỏ hàng loạt. `continuity_layout` dự kiến đối chiếu với continuity_state/shadow/validator trước khi bỏ; không lấy 0 test đỏ làm lý do khóa.
- Theo M7.7 trong kế hoạch master: K1 send_claim/back_view cần 2 worker/crash/reconcile/bằng chứng thật; K2 video_pregen/stage_camera… cần nghiệm thu; QC cần truth. Báo cáo này không thay phép nghiệm thu đó.

- `two_tier_quality` (6 đỏ): `quality_tier.e1_choice` đổi model Seedance mặc định sang 2.5 theo đường 480p/720p, vì vậy test model/cheap-mode cũ lệch. Hai test gen lại y nguyên bị cổng fingerprint chặn; không nới luật gen lại phải đổi đầu vào. Test follower-cost đỏ tại dòng 59 **sau poll**, không phải assertion “paid running task” trước poll; cần nghiệm thu riêng provenance/final của clip nhóm trong đường hai bậc, chưa kết luận lỗi tiền từ phép đo này. `dashboard/steps/step4.py` cố ý đổi thẻ “Clip dùng được” thành “Bản cao xong” khi ON; test hero cũ chỉ pin chat_first OFF nên assertion nhãn lệch. Pin OFF nếu test nhánh legacy, hoặc thêm ca ON với tiến độ/nhãn hai bậc, không đổi UI production để chiều test. Dự toán ±5% và chất lượng video thật theo M7.4 vẫn chưa được chứng minh ở đây.

## Dữ liệu đo và phần còn mở

Raw logs, helper, trace và kết quả JSON ở `D:/AI-Video-Output/flag20-20261022/`, không chứa trong Git. Báo cáo/JSON tổng hợp chỉ chứa tên cờ, node test, số đếm và thông tin baseline; không prompt/payload/CSDL/credentials.

Không có sửa triển khai nên không có vòng sửa code ĐỎ → XANH. Mốc và các negative-control mặc định là bằng chứng thực nghiệm về đổi hành vi; giữ mọi lỗi đỏ để chủ khâu xử lý. Chưa có đo cả bộ 20 lượt, chưa đo chất lượng clip/truth / chi phí nhà cung cấp; chưa đủ quyền bật/khóa bất kỳ cờ production nào.

Kiểm đối chứng cuối dùng cùng 107 node: **107 passed / 225,35 s**, với wrapper đã gia cố môi trường native giả và registry giả. Tất cả subprocess sở hữu đã kết thúc; không để worker đo chạy nền. Không bổ sung file mã nên không đổi `devsys/areas.json` hoặc `areas.version`.
