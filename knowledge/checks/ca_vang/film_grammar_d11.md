# Ca vàng Đ11v4 — luật quay và máy sau gen

Ca tái dựng offline, không đọc dự án thật. Cờ `film_grammar_check` và `camera_match_qc` mặc định TẮT, kể cả preset experimental.

- Hai shot A trái/B phải rồi đảo bên: `continuity.axis_warnings` hiện có báo 180°, không viết lại. Test `test_existing_axis_golden_not_reimplemented`.
- Hai máy lệch 0,1 m cùng chủ thể: đổi góc <30° → VÀNG. Ngoại lệ BYĐ phong_cach, phạm vi đúng shot, ghi cắt nhảy có cách hiện thì bỏ riêng luật cắt nhảy; hướng nhìn sai vẫn báo.
- Actor chuyển từ trái sang phải sân: góc tương đối máy trước phải dùng vị trí actor trước, không lấy tọa độ sau cho cả hai máy.
- Actor A quay mặt khỏi B dù BYĐ nhìn B: VÀNG; mặt sát mép nhìn tiếp ra ngoài, đầu quá thấp: lead room/headroom VÀNG.
- Chân trời đo 90%, máy dự kiến 50%: VÀNG. Không model mặt local/không biết danh tính subject: cỡ mặt và mắt không đo được, không giả đạt.
- Clip seek cuối thất bại: không gán frame sai thành khung cuối. URL/UNC bị từ chối trước mở tệp.

Ngưỡng 30° là luật dựng; ngưỡng cỡ mặt/mắt/chân trời 8% và headroom/lead room đều chưa hiệu chỉnh. Cỡ mặt là chỉ báo tạm của cỡ cảnh,
không chứng minh toàn thân khớp. Ca #24 máy thấp nhưng thấy lòng giếng mới là nguồn vấn đề, chưa nghiệm thu ảnh thật/tiền.
Gợi ý gen lại phải đổi đầu vào + giá từ cost đang có, không tự gửi job.
