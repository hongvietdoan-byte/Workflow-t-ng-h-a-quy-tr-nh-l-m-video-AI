# Thiết kế M8.1 — Chế độ Đơn giản cho Dashboard

> **Bản trình EP duyệt · 23/10/2026 · Cấp 1, 0 USD.** Đây là thiết kế và mockup tĩnh, chưa thay đổi giao diện đang chạy. M8.2 chỉ bắt đầu sau khi EP duyệt bản này.
>
> Phạm vi số liệu: đọc mã Dashboard, `devsys/pipeline_maps.json` và các tài liệu kế hoạch/quyết định trong `docs/`. Không mở CSDL, nhật ký thao tác hay dữ liệu dự án thật. Vì vậy báo cáo **không kết luận tần suất bấm, thời gian hoàn thành thực tế hoặc mức dễ dùng của người dùng**.

## Mục tiêu

Giúp người mới tạo được video AI qua một luồng ngắn, câu chữ thông thường và các lựa chọn có giải thích. Dashboard tự xử lý việc kỹ thuật đã được cho phép; người dùng duyệt nội dung và kết quả. Mọi khoản chi đều hiện giá và cần xác nhận đúng quyền. Chế độ Đơn giản chỉ đổi cách trình bày và luồng thao tác; không đổi quyền của tài khoản.

## Căn cứ và giới hạn số đo

| Nguồn | Bằng chứng dùng trong thiết kế | Giới hạn |
|---|---|---|
| `docs/KIEM_KE_NUT_DASHBOARD_2026-10-21.md` | Kiểm kê tĩnh tại mốc code 3b58812: 853 điều khiển, gồm 439 nút và 414 ô nhập/chọn; 529 điều khiển trên 5 màn sản xuất; luồng tay ước tính khoảng 33 thao tác và 19 quyết định. | Là mốc kiểm kê theo mã ngày 21/10, không phải tổng hiện tại sau các thay đổi M8.0a/b; số thao tác là ước tính, không phải nhật ký người dùng. |
| `devsys/pipeline_maps.json` | Có 4 màn dây chuyền chính và 28 ô chức năng; 19 hành động được gắn tên trong sơ đồ. | Đây là bản đồ chức năng, không phải đếm widget hoặc lượt bấm. |
| `core/ui_step.py`, `core/ui_log.py`, `dashboard/common.py`, `devsys/pipeline_maps.py` | Có cơ chế quan sát `ui_step`/`ui_actions`; cờ `ui_step_log` mặc định tắt. `pipeline_maps` có thể đọc sự kiện theo dự án ở chế độ chỉ đọc. | Không đọc CSDL hoặc nhật ký thật theo giới hạn của nhiệm vụ; chưa có số đo phân bố bước, thời gian, lỗi hay người dùng. |
| `docs/KE_HOACH_DASHBOARD_DON_GIAN_2026-10-21.md`, mục 11; `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md`, mục M8 | Bốn bước, mục tiêu ≤8 thao tác và ≤6 quyết định; các câu Q-A…Q-F và E2 được phản ánh theo trạng thái đã ghi trong kế hoạch. | Mục tiêu thiết kế, chưa qua thử nghiệm với người mới. |

Không suy ra “nút được dùng nhiều” từ số lần xuất hiện trong mã. Để có tần suất thực tế, sau khi được phép cần xuất một snapshot đã lọc định danh, chỉ gồm `project_id` giả, tên bước, kết quả và thời lượng; tổng hợp nhóm theo ngày và bước rồi bỏ snapshot tạm. Nếu không có chấp thuận cho snapshot an toàn, dùng buổi kiểm thử có người tham gia và ghi nhận đồng ý riêng.

## Quyết định EP đã đưa vào

| Mục | Cách áp dụng trong thiết kế |
|---|---|
| Q-A — chọn hướng kịch bản | Máy chọn hướng đề xuất trong ba hướng; người dùng vẫn mở “Phương án khác”. Ghi nhận lựa chọn để có thể giải thích hoặc đổi lại. |
| Q-B — motion | Theo M6.5: VPA tạo prompt, kiểm tra theo vai; không đưa prompt tiếng Anh thành việc bắt buộc cho người mới. Quyền chấp nhận prompt tách khỏi quyền gửi API có phí. |
| Q-C — bản 1080p | Có thể tự nâng clip đã duyệt từ nháp 480p lên 1080p trong ngân sách và không ghi đè bản nháp, nhưng quyết định đang **PENDING_VERIFICATION**. Mockup chỉ hiển thị trạng thái “đang chờ xác minh”; chưa thiết kế như hành vi đã được bật. |
| Q-D — ngân sách | Ngân sách phim được duyệt một lần; báo trước ở ngưỡng 80%. Theo giải thích ngày 22/10: hard stop chỉ chặn luồng tự động; thao tác tay được cảnh báo và vẫn qua xác nhận giá/quyền hiện hành. |
| Q-E — mặc định | Tài khoản mới vào Đơn giản; tài khoản hiện hữu giữ Chuyên gia. Đổi chế độ không cấp hay thu quyền. |
| Q-F — thứ tự an toàn tiền | M8.0 được làm trước luồng tự động trả phí. M8.0/M8.0b đã có trên main theo kế hoạch; M8.0c còn phần nút thử lại/từ chối/mở lại/giọng/nhạc chưa được xác nhận. Đơn giản không đưa các thao tác chưa có xác nhận an toàn thành lối tắt. |
| E2 — “Duyệt hết” | Trước khi áp dụng hàng loạt, hiện danh sách mục sẽ duyệt và kiểm tra quyền; mục không đủ điều kiện phải giữ ở trạng thái chờ, kèm lý do. Nút chung không tự khóa Bible, duyệt motion hoặc duyệt sân khấu 3D thay EP. Các duyệt chỉ-EP cần thẻ/cổng riêng có tên người duyệt. |

## Luồng đề xuất

```text
⌂ Ý tưởng → ① Kịch bản → ② Ảnh → ③ Video → ④ Tải bản giao
  gõ một câu    xem/sửa lời    duyệt ảnh     xem/duyệt clip       tải
```

1. **Ý tưởng và ngân sách:** người dùng nhập ý tưởng. Hệ thống hỏi tối đa các chi tiết còn thiếu bằng câu ngắn, có đáp án gợi ý. Trước tác vụ trả phí, hiện tổng dự toán, mức xấu nhất và phạm vi; người có quyền xác nhận bấm “Đồng ý ngân sách ≈ X USD”. Tại 80% hiện cảnh báo. Khi luồng tự động chạm hard stop, dừng và giải thích; không tự xin thêm tiền.
2. **Kịch bản:** hiển thị hướng được chọn và nhãn “Phương án khác”; người dùng đọc từng cảnh, góp ý bằng lời hoặc bấm “Được, làm tiếp”. Việc lập kế hoạch/chuẩn bị kỹ thuật chạy theo đúng quyền và phạm vi ngân sách đã duyệt. Không gộp nút này thành chấp thuận mọi khâu phía sau.
3. **Ảnh:** hiện lưới theo cảnh, ưu tiên cảnh đang cần người xem. “Duyệt hết” mở bước xem trước n mục: chỉ các mục người đó được duyệt mới được chấp nhận; mục cần EP hoặc còn lỗi được giữ lại và nêu rõ nguyên nhân. Giữ “Vẽ lại ảnh” với ô góp ý và giá trước khi gửi.
4. **Video:** hiện clip theo cảnh, trạng thái dễ hiểu. Người dùng có thể duyệt hoặc “Làm lại cảnh này”, nhập góp ý và xem giá trước xác nhận. Tự nâng 1080p chỉ sau khi xác minh Q-C; bản 480p gốc được giữ nguyên. Khi toàn bộ clip đủ điều kiện, tự dựng theo cổng đã duyệt; người dùng bấm tải.

Luồng bình thường được **ước tính** 6 hành động chính (gõ ý tưởng, duyệt ngân sách, duyệt kịch bản, xem trước/duyệt ảnh, xem trước/duyệt video, tải) và tối đa 8 nếu phải trả lời câu hỏi. Số quyết định mục tiêu ≤6. Đây là phép đếm thiết kế, chưa phải kết quả đo.

## Bảng giữ, gộp, ẩn và tự động

| Khu vực / điều khiển hiện tại | Đơn giản | Lý do và thay thế |
|---|---|---|
| Ô “Bắt đầu dự án mới”, danh sách dự án, tải bản hoàn tất | **GIỮ** | Điểm vào quen thuộc; dùng câu gợi ý dễ hiểu. |
| 12 ô thiết lập, JSON tay, phân tích, biểu mẫu kỹ thuật | **GỘP / ẨN** | Câu hỏi hội thoại với mặc định cho dữ liệu thiết yếu; thiết lập nâng cao ở Chuyên gia. |
| Bốn lượt Biên kịch, radio ba hướng | **GỘP** | Một nút “Viết kịch bản” trong ngân sách; máy đề xuất một hướng, vẫn có “Phương án khác”. |
| “Dùng kịch bản”, “Lập kế hoạch”, “Duyệt & khóa” | **GỘP có xem phạm vi** | Một nút “Được, làm tiếp” cho phần kịch bản/khâu được phép; không biến thành duyệt thay EP ở bước khác. |
| Các trường blocking, end_state, BYĐ, model, cờ và tên provider | **ẨN** | Người mới góp ý bằng lời. Thêm chú giải một dòng khi bắt buộc nêu khái niệm. |
| “Gen ảnh”, nút riêng motion/giọng, mức QC, sửa prompt tiếng Anh | **TỰ ĐỘNG trong phạm vi duyệt** | Hệ thống thực hiện công việc kỹ thuật sau bước duyệt; báo trạng thái và yêu cầu người dùng khi có ngoại lệ. |
| Duyệt từng ảnh / “Duyệt tất cả” | **GIỮ / GỘP có preview** | Một nút chính, mở danh sách ảnh, trạng thái và số mục; mục thiếu quyền/không đạt bị HOLD. |
| “Vẽ lại”, chọn ảnh tham chiếu, bản cũ | **GIỮ phần cốt lõi** | Thẻ “Sửa bằng lời” và “Đổi ảnh”; hiện giá trước xác nhận. “Khác” chứa bản cũ/bỏ cảnh; chỉ báo cũ các đầu ra phụ thuộc đúng cảnh. |
| Model, độ phân giải, gói gửi, cổng kỹ thuật | **ẨN** | Chỉ chuyên gia; ngoại lệ an toàn hiển thị thành thẻ “Cần bạn” với nguyên nhân dễ hiểu. |
| Duyệt clip, làm lại, nâng bản cao | **GIỮ / TỰ ĐỘNG có điều kiện** | Giữ duyệt và làm lại cảnh với giá. Nâng 1080p tự động chỉ sau khi xác minh Q-C, trong ngân sách, không thay bản nháp. |
| Nhạc, SFX, TTS, phụ đề và 117 điều khiển hậu kỳ | **GỘP / ẨN** | Giữ lựa chọn đơn giản “Có/không phụ đề” và một số lựa chọn nhạc có sẵn; bảng kỹ thuật trong Chuyên gia. |
| Thanh trên: mức tự động, tính năng thử, kho, cờ, sổ chi | **ẨN / GIỮ** | Ẩn công cụ chuyên gia; giữ tên phim, mức đã dùng/trần, tạm dừng và công tắc chế độ. |
| “Duyệt hết” mọi bước | **GỘP có preview và quyền** | Xem trước các mục cụ thể; HOLD mục không đủ điều kiện. Duyệt sân khấu 3D/Bible/motion cần đúng vai, không có quyền thì không thực hiện. |

### Lỗi và thay đổi đầu vào

Thẻ lỗi luôn dùng cấu trúc **“Chuyện gì — Máy đã thử gì — Bạn chọn”**. Câu chữ không lộ exception/mã kỹ thuật. Khi hết lượt tự sửa, không tự chi thêm; gợi ý 2–3 lựa chọn phù hợp loại lỗi: thử lại sau góp ý (có giá), giữ bản tốt hiện có, hoặc gửi yêu cầu kỹ thuật. Từ chối của nhà cung cấp được giải thích ngắn, không hiển thị nguyên văn nội bộ.

Mỗi thẻ cảnh có bốn lối nhất quán: “Được”, “Sửa bằng lời”, “Đổi ảnh tham chiếu”, “Khác”. Đổi ảnh kèm vai trò và một câu chỉ dẫn; trước khi chạy lại, hiện đầu ra nào sẽ cũ và giá dự kiến. Đổi thứ tự, chọn bản cũ, cắt clip và đổi nhạc cục bộ giữ dưới “Khác” khi không tốn tiền. Việc đổi dữ liệu không được âm thầm ghi đè bản đã duyệt.

## Ngôn ngữ trên màn

| Thuật ngữ hiện tại | Chữ đề xuất trong Đơn giản |
|---|---|
| BYĐ | Ý đồ của cảnh |
| plate / nền 3D | Ảnh bối cảnh |
| ref / reference | Ảnh tham chiếu |
| motion prompt | Chỉ dẫn chuyển động |
| storyboard | Bộ ảnh theo cảnh |
| multi-shot | Clip nhiều cảnh nhỏ |
| QC | Kiểm tra chất lượng |
| Lock / Bible | Hồ sơ nhân vật đã duyệt |
| Seedance / Kling / tên model | Ẩn; chỉ báo tên dịch vụ nếu cần xử lý sự cố |
| Mã cờ / exception | Ẩn; thay bằng mô tả và bước tiếp theo |

## Kiểm chứng sau khi EP duyệt

1. M8.2 dựng đúng khung màn theo bản này, cờ `simple_mode` giữ TẮT cho đến nghiệm thu; chế độ Chuyên gia hoạt động như hiện tại.
2. M8.0c hoàn tất trước khi luồng Đơn giản đưa thêm nút tốn tiền chưa được bảo vệ vào sản xuất.
3. Thử với người chưa có kinh nghiệm trên dự án giả; ghi số bước, số lần cần hỏi lại, thời gian, số lần mở “Khác”, lỗi thao tác và mức hiểu giá. Không lấy số ước tính trong thiết kế làm kết quả thử.
4. Kiểm tra quyền/actor cho từng thao tác duyệt; E2 phải giữ mục thiếu quyền ở HOLD. Kiểm tra mọi đường gửi tiền có giá và xác nhận. Chế độ Đơn giản không đổi quyền truy cập và không cho luồng tự động vượt trần.
5. So sánh với mốc code 21/10 (≈33 thao tác, ≈19 quyết định) sau khi đo cùng một bài thử. Mục tiêu: ≤8 hành động tới video đầu tiên, ≤6 quyết định, 0 đường gửi tiền không báo giá/xác nhận. Đo thời gian riêng; chưa đặt ngưỡng vì chưa có baseline nhật ký an toàn.

## Bản vẽ

Mockup HTML tĩnh: [`mockup/che_do_don_gian_m81.html`](../mockup/che_do_don_gian_m81.html). Các nút chỉ minh họa cấu trúc; không kết nối Dashboard, provider, ngân sách hay dữ liệu dự án.

## Nguồn

- `docs/KE_HOACH_DASHBOARD_DON_GIAN_2026-10-21.md` — nguyên tắc, số đo mã nguồn, luồng và câu hỏi EP.
- `docs/KIEM_KE_NUT_DASHBOARD_2026-10-21.md` — kiểm kê điều khiển ngày 21/10.
- `devsys/pipeline_maps.json`, `devsys/pipeline_maps.py`, `core/ui_step.py`, `core/ui_log.py`, `dashboard/common.py` — bản đồ và cơ chế ghi/đọc bước bấm.
- `docs/DANH_SACH_CAN_DUYET_2026-10-22.md` và quyết định được ghi trong dòng M8.1 của `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md`.
- `docs/CODEX_TASKS.md` — CX23-M81 và đề bài bổ sung C-M81B trong `docs/CLOUD_TASKS.md`.
