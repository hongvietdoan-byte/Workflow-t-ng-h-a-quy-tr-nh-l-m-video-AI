# CX24-N9-REAPPROVE — Codex 1, 24/10/2026

## Kết quả xác minh và phạm vi

N9 trước sửa gọi `stage_auto.rerender`, đo vào thư mục kết quả cũ, ghi camera ngay và giữ `crew/state.json` ở `xong` cùng dấu duyệt cũ. Vì vậy sản phẩm đã duyệt có thể đổi mà không quay lại chờ EP.

Thêm cờ `stage_rerender_reapprove`, mặc định **TẮT**, chưa VERIFIED, không gọi API trả phí. Khi bật cho lượt chia vai đã được người dùng duyệt:

- Đo vào thư mục mới; giữ nguyên final/result/camera cũ trước EP. Thiếu shot, lỗi đo, trạng thái duyệt hỏng hoặc tắt cơ chế người duyệt thì từ chối, có câu lỗi.
- Lưu đề xuất `duyet`, bỏ dấu duyệt/accepted/waiver cũ khỏi lựa chọn hiện tại; giữ bằng chứng cũ trong history. Dùng chính crew state hiện có, không thêm registry.
- Pending đã lưu vẫn có hiệu lực khi tắt cờ. Chặn tự chạy/cache một vai hoặc chia vai, nạp câu trả lời ngoại tuyến một vai và reset; driver không gỡ camera đã duyệt khi nhận waiting.
- EP có thể duyệt hoặc trả lại để Quay phim sửa; các lượt đo sửa và final mới không ghi đè thư mục đo/final cũ. N6 vẫn kiểm quyền EP chuẩn; N9 vẫn giữ quyền SỬA và xác nhận ảnh đã vẽ như trước.
- Chỉ sau bước EP ghi máy thành công mới công bố result mới và bỏ pending. Shot EP đã đánh dấu plate bắt buộc tiếp tục được paid gate giữ khi phase chưa xong; chính sách ngoại lệ EP hiện có giữ nguyên.

Cờ OFF và không có pending giữ hành vi cũ; không tự bật cờ hoặc sửa cài đặt thật.

## Kiểm chứng

- RED ban đầu: 3 lỗi hành vi N9; test N6/đăng ký cờ: 2 lỗi; nhóm caller bổ sung: 4 lỗi; reset N8: 1 lỗi hành vi sau khi hoàn thiện fixture. Không tính lỗi chuẩn bị fixture là bằng chứng RED.
- Các ca kiểm gồm bất biến byte final/result, không apply trước EP, đo mới đầy đủ, lỗi đo/thiếu shot, cờ OFF, state hỏng, pending sau tắt cờ, EP duyệt thành công/lỗi apply, lựa chọn số đo mới, khe số m1/m3, guard offline/reset/driver và quyền EP N6.
- Test chỉ dùng thư mục tạm, môi trường giả thay OBJECT `os.environ`, renderer/camera/DB ghi bằng mock, credential/registry/native bị cô lập; không Blender, API, dữ liệu thật hoặc Computer Use.
- Root gom hai file N9 và hồi quy chọn lọc `test_stage_auto.py`/`test_stage_crew.py`: **39 passed, 127 deselected / 2,59 s**, serial, `--tb=no -p no:cacheprovider`. Sau đó chỉ sửa fixture khôi phục riêng entry keyring để tránh làm lệch module cache; file N9 chạy riêng **23 passed / 0,96 s**. Hồi quy OFF trước đó **10 passed / 2,93 s**; không cộng các lượt trùng.
- Rà CLAUDE §7 bằng `tools/related_areas.py`; reviewer độc lập phát hiện caller offline và vòng trả lại→prompt, đã sửa; rà cuối **0 P1/P2 còn mở trong phạm vi N9**, root đọc lại phần sửa và caller hai lượt.

## Giới hạn và bàn giao tích hợp

Chưa nghiệm thu GUI/Blender/dự án thật. Test EP đi qua `crew_user_verdict` → finalize nhưng `apply` dùng mock; không chứng minh giao dịch CSDL thật hoặc quyền bị thu hồi đồng thời.

`apply` kế thừa chưa nguyên tử xuyên nhiều shot và tệp. Lỗi DB/ghi log/công bố tệp sau một phần ghi có thể để DB và result lệch, dù pending chưa được bỏ. Nhánh này không tạo API giao dịch mới và **không tuyên bố rollback nguyên tử**. Lỗi đo có thể để thư mục đề xuất dở, không xóa asset. Khi tích hợp cần giữ các guard/cổng quyền từ main mới, chạy hồi quy/cả bộ theo quy trình phiên chính trước gộp và giữ cờ OFF đến nghiệm thu được phép.

Nhánh: `codex/v31-n9-reapprove`. Không sửa vùng profile/revision của M23B, không gộp main, không khởi động lại máy live.


## Đồng bộ sau thư GỘP 231006-kphf

N9 đồng bộ main5d72cf7d sau thư231006-kphf; giữ guard pending/G1 EP/BEATS assemble, hợp danh mục areas hai bên/version92. Root39 passed,127deselected/3,11s trên nền mới; rà tích hợp độc lập0P1/P2 và rootđọc2lượt. Không rewrite/force, không cả bộ/mainmerge/dữ liệu thật/CU; cờ vẫn OFF.
