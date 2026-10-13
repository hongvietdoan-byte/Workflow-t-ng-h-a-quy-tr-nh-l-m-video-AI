# Rà Đ11 việc 4 — 13/10/2026

Nhánh `codex/d11-viec4-luat-quay`, nền `771b96b6`; chưa commit/gộp. Không phụ thuộc nhánh Đ11v2.

| Ý tưởng | Giá trị / công sức / quyết định |
|---|---|
| Mở rộng continuity | Tránh lỗi dựng bằng số, 0 USD; tái dùng luật 180°/bố cục cũ, thêm adapter hình học sau cờ TẮT |
| QC camera local | Phát hiện chân trời lệch trước gen lại, 0 USD; thiếu model/danh tính thì VÀNG, không giả đạt |
| Màn camera mới | Chưa có màn thật; để việc bàn dựng sau, không nhét vào bảng tiến độ hoặc sửa mockup |

## Bằng chứng

- Đỏ đầu: hai module chưa có → 2 lỗi collection, `--tb=no`.
- Test mới ban đầu xanh 15. Root rà bắt hai lỗi: góc 30° dùng vị trí actor sau cho máy trước; seek clip thất bại vẫn đọc frame.
  Hai test hồi quy đỏ (2 failed/15 passed), sửa lưu vector máy→actor từng shot + chỉ đọc khi seek thành công.
- Cuối: **52 passed / 2,27 s**, nhóm film_grammar/camera_match_qc/camera_match_ui/continuity/continuity_layout/before_run/plate_layout_qc.
  Toàn phiên pytest thay `os.environ` bằng dict giả; thử absent/present FACE_MODEL thay dict, detector mock trước đo; teardown giữ object môi trường gốc.
  DB/ảnh/clip/model giả trong thư mục tạm. Không API/mạng/ tải model; `--tb=no`, không showlocals.
- `git diff --check` sạch; `areas.version=68`; file mã/test/cờ mới đăng ký. Widget key cũ giữ nguyên.

## Tự rà 2b.5 + caller

Continuity cũ không đổi. Report gọi adapter; Trước khi chạy chỉ thêm VÀNG vào đầu vào. Hai thẻ ảnh v1/v2 và fragment xem clip gọi QC chỉ đọc.
Cờ `film_grammar_check`/`camera_match_qc` unverified + OPT_IN_ONLY: custom/stable/experimental mặc định TẮT có test dict giả.
Không đổi runner/autopilot/job/prompt gửi, không trả tiền tự động; gen lại chỉ gợi ý đổi đầu vào, giá từ cost có sẵn hoặc báo chưa có giá.
`related_areas.py` đã chạy: vùng chứa step1/plates3d/core_infra/step2/step4/dashboard_ui; caller rộng do features.
Bước gộp yêu cầu test chậm access/editor_apply/editor_review/rough_cut/ui_v2_acceptance hoặc cả bộ; chưa chạy trong nhánh.

## Giới hạn / việc mở

- Máy camera thật chưa có trong Dashboard; backend `continuity.film_warnings(..., objects=...)` sẵn nhận objects của stage_solver ở cùng hệ tọa độ.
  Luồng report/Trước khi chạy chưa lưu blocking đã duyệt, vì vậy báo VÀNG thiếu tọa độ/hướng mặt thay kiểm giả. Cần upstream adapter K2/bàn dựng nối sau.
- Headroom/lead room đo bằng project; hướng nhìn so facing với đích nhìn BYĐ (chưa kiểm chuyển hướng theo mọi nhịp/mắt động hoặc tracking chuyển động).
- `camera_plan.subject` hiện không có tên/ID. UI không gán chỉ vì một nhân vật; mắt/cỡ mặt dự kiến thiếu → VÀNG tới khi upstream có ID.
- Cỡ mặt là chỉ báo tạm cỡ cảnh, chưa đo toàn thân. Nhiều mặt không gán bừa. Chân trời dùng công cụ plate_layout_qc hiện có.
- Clip seek đúng đầu/cuối, local-only. Máy chuyển động thiếu máy cuối → VÀNG; actor chuyển động thiếu vị trí cuối chưa được đo đầy đủ.
- Ngưỡng mắt/cỡ mặt/chân trời 8%, headroom/lead room chưa hiệu chỉnh; chưa dùng ảnh/clip #24, chưa render/GUI 1440/1280, chưa bật cờ.
- Báo cáo chỉ là tự rà + hai lỗi root đã sửa; root cần rà độc lập/cả bộ trước gộp. Không đụng plate_camera, data thật/env/secret/main/live.

## Rà độc lập và sửa 3 P2

- P2 số hình học không hữu hạn (NaN facing ở CU từng im lặng): thêm kiểm finite cho xy/z/H/h/facing của actor và đích nhìn trước chiếu/so hướng; sai → VÀNG số không hợp lệ.
- P2 BYĐ khai A nhưng dàn cảnh chỉ B: so danh sách chủ thể BYĐ với actor sân khấu, báo thiếu đúng A, không bỏ qua.
- P2 khung cuối clip dùng actor đầu: thêm `end_actor` cuối chữ ký, chỉ dùng actor đầu cho khung đầu; thiếu actor cuối thì cỡ/mắt VÀNG, chân trời/máy cuối giữ độc lập.
- Đỏ **7 failed / 17 passed** cho các ca mới (4 actor NaN/Inf, đích NaN, thiếu A, thiếu actor cuối); sửa rồi **59 passed / 1,88 s** trên nhóm 7 file như trên.
  Môi trường thay dict giả trước import pytest; detector/VideoCapture giả trước gọi đo, không API/model/mạng. Chưa commit/gộp.
- Giới hạn UI/adapter upstream và nghiệm thu GUI 1440/1280 vẫn chưa đóng. Không mở thêm phạm vi.
