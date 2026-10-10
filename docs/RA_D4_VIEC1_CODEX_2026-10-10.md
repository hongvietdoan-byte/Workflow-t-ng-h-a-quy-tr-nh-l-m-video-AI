# Rà K3 trước gen — Codex, 10/10/2026

Nhánh `codex/d4-viec1-ra-k3`, tách từ `origin/k3-ra-sua` (`080360a`). Rà diff K3 và các đường gọi runner; chỉ dùng CSDL/tệp tạm, provider giả. Không đọc/ghi dữ liệu sản xuất, không gọi API, không chạy Blender. **Chưa thử thật với nhà cung cấp.**

## Kết quả bốn điểm được giao

1. **Cờ tắt:** tách `_build_package` không làm đổi gói thường hoặc thứ tự ghi sổ: đã rà, không lỗi. Test nạp snapshot hai hàm của main `c78bcfe911935688fa19414b1f5da59ad87e1848`, chạy cùng job giả trước/sau, cố định giờ, so chuỗi JSON **từng byte**, external_id và thứ tự `package → external_id → running → spend`. Snapshot nằm trong `tests/fixtures/k3_flagoff_runner_c78bcfe.txt`; không cần lịch sử Git khi chạy test. Hai lỗi chuyển từ bật sang tắt được sửa riêng bên dưới.
2. **Nhóm nhiều shot:** follower giữ queued cùng nhóm nhưng lý do cũ không chỉ ra K3 của leader. Test đỏ ở câu thông báo; sửa xong follower thấy lỗi khung đầu, sửa ảnh leader thì gửi đúng **một** request, `sent_group` chứa cả hai shot, follower không gửi lẻ.
3. **Lỗi tệp:** video/ảnh tham chiếu mất bị bỏ trước kiểm; ảnh hỏng có SHA vẫn được coi là đọc được; lỗi PIL trong chuẩn bị request hoặc lỗi upload làm ngắt vòng runner. Các ca đỏ được sửa; test xác nhận job lỗi queued, job tốt tiếp theo running, có lý do rõ.
4. **Upload:** `_submit_kwargs` tải Kho chủ thể trước `_pregen`. Test đỏ chứng minh `picture_refs` gọi một lần dù request ĐỎ. Nay chuẩn bị ảnh tại máy, kiểm, kiểm ngân sách, rồi mới hydrate URI; không dựng lại route bản cao. Test đường `_reference_pictures` Seedance thật bằng PNG 32 px ghi thứ tự `check → upload`; request ĐỎ và gen lại cùng đầu vào không upload.

## Lỗi và commit riêng

Số dòng là bản cuối trên nhánh này, không phải số dòng trong kế hoạch cũ.

| Mức | File:dòng | Lỗi / bằng chứng đỏ → xanh | Commit |
|---|---|---|---|
| Trung | `core/runner.py:855` | Tắt cờ sau hold vẫn bị cache giữ 30 s; mong 1 gửi nhưng được 0 → gửi ngay | `d571899` |
| Trung | `core/runner.py:1463` | Follower không hiện lý do K3 leader; assert lý do đỏ → cả nhóm có lý do, release đúng một request | `008621b` |
| Cao | `core/runner.py:1626` | Video ref mất bị bỏ trước plan; cả hai shot gửi thay vì giữ shot lỗi → queued/running | `1754c84` |
| Cao | `core/runner.py:814` / `:833` | Upload trước cổng K3; `picture_refs` phải 0 nhưng được 1 → 0, gửi hợp lệ theo check/upload | `7921f56` |
| Cao | `core/runner.py:347` / `:823` | Lỗi đọc tệp trong blocked/args/kwargs/hydrate ngắt vòng; PIL/OSError đỏ → giữ riêng job, tiếp tục job tốt | `9eb14a8` |
| Cao | `core/video_pregen.py:141` | Khung đầu/cuối hỏng có tệp vẫn gen; 2 request thay vì 1 → 1; PIL verify/load tại máy | `dc7a436` |
| Cao khi đường nhận refs bật | `core/runner.py:1614` | Ảnh tham chiếu mất bị lọc dù provider sẽ nhận; 2 gửi → 1. Guard chỉ giữ khi K3 và `SEEDANCE_REFS_WITH_FIRST_FRAME` bật, không chặn ảnh bị provider bỏ có chủ ý | `9841fe2` |
| Trung, tự rà lượt hai | `core/runner.py:777` | Metadata tạm của K3 lọt vào gói khi gửi tay `only` sau tắt cờ; assert không có metadata đỏ → xanh | `9c79536` |
| Cao, tự rà N10 | `core/runner.py:1245` | Vân tay ảnh gốc khác ảnh sạch resize 1280 thực tải; assert vân tay gói ảnh sạch đỏ → xanh. Chuẩn hóa tại máy trước kiểm, hydrate không resize lần hai | `025b346` |

`e2d0c02`: snapshot test được lưu riêng để chạy trên checkout không có commit baseline; khai fixture trong assets khu vực step4, **không tăng areas.version**.

## Test Windows

Đặt `PYTHONUTF8=1`; mọi lệnh dùng `py -m pytest -q -p no:cacheprovider`. Không sửa/nới assert cũ. Fixture ảnh K3 đổi từ chuỗi giả `b'picture'` sang PNG thật 32 px để kiểm đọc ảnh; ca hỏng tự ghi bytes hỏng có chủ ý.

- 15 test mới. Từng lỗi có lượt đỏ thật trước sửa; riêng ca so baseline, đường Seedance hợp lệ và thứ tự upload là bằng chứng tương thích xanh ngay.
- Nhóm: `tests/test_video_pregen.py tests/test_sent_package.py tests/test_v3.py tests/test_subjects.py tests/test_skill_route.py tests/test_quality_tier.py tests/test_cost_route_e1.py`: **162 passed, 2 skipped, 110.30 s**. Hai skip là điều kiện sẵn có; không thêm skip mới.
- Sau rà lượt hai và chuẩn hóa ảnh sạch: `tests/test_video_pregen.py tests/test_sent_package.py`: **64 passed, 6.77 s**.
- Nhóm FlagOff sau chuyển snapshot offline: **3 passed, 0.43 s**.
- `git diff --check`: sạch (Git chỉ nhắc LF/CRLF).
- **Không chạy cả bộ trong việc 1**; bên gộp chạy theo quy trình, việc 3 ĐỢT 4 đo cả bộ riêng.

## Rà tác động và tự kiểm

`py tools/related_areas.py core/runner.py` chỉ ra step2/step4/core_infra và caller assets/autopilot/dashboard/budget; UI acceptance slow bắt buộc ở bước gộp. Phiên chính đã rà độc lập diff/caller trước từng commit và rà lại lần hai: các đường tự động/bấm tay cùng `submit_pending`, WAIT_REASONS giữ lý do, cờ tắt và ImageRunner dùng hook cũ, task đã có external_id không bị giữ như request chưa trả tiền. Không sửa Dashboard.

Theo skill mục 2b.5: không nới test; đường fixture dựa ROOT, tệp thật của dự án không được đọc; không bật cờ mặc định; không bỏ dấu tên; không có lời gọi mạng trong test. Lượt rà hai bắt metadata cache khi `only` gửi tay sau tắt cờ và phụ thuộc lịch sử Git của test, đều đã sửa. Tự rà thêm N10 bắt ảnh sạch khác ảnh gốc, đã sửa và có test.

## Việc mở / giới hạn

- Provider/upload đều giả: chỉ chứng minh thứ tự và trạng thái, chưa chứng minh chất lượng video hay hành vi ClipAI thật; K3 vẫn mặc định tắt.
- K1a hiện không lưu ref chỉ có `uri` như một ref đầy đủ có SHA. Không mở rộng sửa K1a trong đợt rà K3; metadata `pregen_fingerprint` mới giữ vân tay đầu vào tại máy cho các lượt K3 đã kiểm. Gói cũ thiếu thông tin URI không thể khôi phục đầy đủ ảnh đã gửi chỉ bằng sổ hiện có.
- Nếu Kho chủ thể không khả dụng rồi trở lại, đường fallback đánh dấu và đường ảnh sạch có thể khác nhau; vân tay trước upload giữ theo ảnh đã kiểm, có thể giữ thận trọng một lượt cùng nguồn thay vì chứng minh payload khác. Cần thử provider thật có người duyệt khi bật K3.
- Đọc ảnh bị lỗi giữa kiểm và hydrate được giữ riêng job; không có khóa tệp chống người khác sửa đúng lúc provider gửi. Không tuyên bố loại bỏ mọi race với hệ thống tệp.
