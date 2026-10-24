# CX24-P34-D6-REFROLES — giữ vai ảnh trong gói video

Nhánh `codex/v31-p34-d6-refroles`, gốc `be59f311`. Fixture tái hiện **theo mô tả** job 1202 trong `docs/CODEX_TASKS.md`; không trích CSDL thật, không chạy lại job/provider thật. Chi phí API: 0 USD.

## Thay đổi

- `_reference_sources` giữ nguồn chọn ảnh/thứ tự hiện có, bổ sung câu vai từ chính `seedance_refs.prompt` (forms, outfit, object, place và góc máy); thiếu storyboard làm cardinality lệch thì không gán vai nhầm số. Không tạo registry mới.
- D6 video nhận đoạn KHÓA; code khôi phục nguyên câu vai/annotation trước kiểm kết quả, cả đường cache/cap. Cùng số ảnh khai vai khác thì dùng bản ghép. Quá chỗ cho D6 thì dùng bản ghép, không gọi thêm Claude chỉ để chép vai.
- `VideoRunner._guard_reference_roles` kiểm gói args+kwargs trước pregen/sổ chi: ref-only/skill phải có metadata đầy đủ, số ảnh đúng, không khai vai trái, đủ trần prompt (tính Avoid và câu khung cuối) và trần ảnh. Thiếu vai có nguồn → ghép + diag; thiếu nguồn/trái vai/quá trần → job ở QUEUED + HOLD nêu shot/ảnh. Độc lập `video_pregen`; không thêm cờ.
- Preview gọi cùng guard, chỉ ghi notes bản sao, không sửa DB hay WAIT_REASONS. Metadata `_reference_roles` bị lọc trước `provider.submit`.

## Ma trận đường gửi

| Đường | Cách bảo vệ |
|---|---|
| Tay, hàng loạt/autopilot, regen | Cùng `_submit_pending`: args → kwargs → guard → pregen → spend → submit |
| Ref-only đơn/nhóm, hosted/marked/shared place | Cùng sources dùng để tạo ảnh gửi và metadata; thiếu frame giữ chờ |
| Skill front/sheet/skill-sheet | Vai từ `skill_dossier.reference_block`, kiểm cùng guard |
| D6 bật/tắt/cache/cap | Guard cuối luôn có; D6 giữ vai bằng code trước validation |
| Ref-first Seedance | Adapter thêm vai từ actual refs đã lọc/cắt cap sau D6; limit sau ghép |
| First/last frame | Adapter thêm câu đầu/cuối; nhánh có last frame không gửi extra refs |
| Kling multishot | Không gửi ref-only; multi_prompt có đường giới hạn riêng hiện có |
| Nâng từ sample | Không gửi prompt/ảnh mới, guard bỏ qua `_from_sample` |
| Xem trước | Cùng guard, không chi tiền/ghi trạng thái |

`ClipAIVideoProvider.submit_video_edit` không có caller core/dashboard qua VideoRunner; không tuyên bố guard này bảo vệ API direct độc lập. Không crop/xóa banner/dấu trên ảnh. Đề xuất tùy chọn riêng: bản ảnh sạch nhãn cần được EP duyệt bằng mẫu trước khi đổi nguồn gửi.

## Bằng chứng và giới hạn

- RED trước production diff: `tests/test_p34_d6_refroles.py` **4 failed / 1,24 s**. Những ca đầu kiểm vai còn số nhưng mất nghĩa, input khóa, repair/COMPAT, HOLD thiếu nguồn/quá trần. Sau đó bổ sung regression và tách validation video khỏi prompt ảnh cũ.
- Rà độc lập do root điều phối phát hiện 2 P2: fallback vai vượt d6_limit có thể gọi lượt sửa Claude; thêm câu đúng nhưng giữ câu PLACE sai cho cùng ảnh. Đã gom sửa: fallback trước paid fix, kiểm conflict trước nhánh không-thiếu, guard cuối HOLD conflict; test đếm fake calls và fix=0.
- Hồi quy cuối: **158 passed / 136,13 s**: `test_p34_d6_refroles`, `test_chat_prompt`, `test_chat_prompt_image3`, `test_chat_prompt_cap_928`, các lớp `SeedanceRefTests`/`MarkTests`/`PromptLessonsTests` của `test_seedance_refs`, và `test_v31_m47a_send_preview`. Sau khi bổ sung sâu ca actual sources → kwargs → guard có cả OUTFIT, chạy lại riêng **13 passed / 8,38 s**. Không đổi/nới các test cũ.
- Golden frozen-input COMPAT: **6 passed / 4,29 s**, image/video × fake/ClipAI/Deepix; mỗi ca còn kiểm một byte đổi phải lệch. Worker native Python chạy môi trường whitelist + HOME giả, không kế thừa credential.
- Các lượt test thay OBJECT `os.environ` bằng dict giả trước import; chạy `--tb=no`, không dump môi trường/payload. Lượt hồi quy cuối chặn socket connect và native Popen; golden chỉ mở worker có env whitelist/HOME giả.
- `tools/related_areas.py`: step2/step4/core_infra và callers assets/autopilot/diag/lipsync/plates3d/dashboard/step1/budget/step3. **Test chậm bắt buộc khi gộp**: access + ui_v2_acceptance. Phiên builder không gộp/main/live restart; cả bộ Windows do phiên tích hợp chạy.
- Chưa kiểm chất lượng clip thật; chưa retry job 1202, chưa trả phí, chưa đọc/ghi data/projects thật hoặc dashboard.env.
- Root đã đọc diff lần hai sau vòng gom, chốt không còn P1/P2 ở phần mới và cho commit/push nhánh khi suite xanh. Chưa gộp; `devsys/areas.json.version` giữ **92**.
- Đóng gói test độc lập: thêm autouse thay object môi trường mỗi ca theo tmp_path, chặn mạng/Popen/registry/keyring/credential, mock factory provider/model. Rerun cuối **13 passed / 3,89 s**; không cần harness ngoài để bảo vệ khi chạy pytest thường. Harness vẫn thay object trước import pytest/core lúc đo.
