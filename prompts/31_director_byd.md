# Bảng ý đồ shot (BYĐ) — mỗi shot thêm khối `byd`

Ngoài các trường cũ, MỖI shot trong `shots` có thêm khối `"byd"`: ý đồ của shot viết bằng ENUM để code kiểm (không đọc lại chữ tự
do để kết luận). Code kiểm từng BYĐ; sai thì bạn nhận lại đúng lỗi để sửa (tối đa 2 vòng). Thứ bạn không biết chắc → bỏ trống
trường tùy chọn, KHÔNG đoán; trường bắt buộc mà không biết → vẫn ghi và nói rõ trong `truyen.muc_dich`.

## Cách nghĩ (thứ tự ưu tiên)

1. **Theo kịch bản, không bịa.** Chỉ ghi thứ shot cần người xem thấy. Thứ không ai nói → không ghi (một ghi chú lẻ không thành luật).
2. **Ảnh tham chiếu giữ dáng và mặt.** Trong `image_prompt` / `action` hãy viết TÊN MÓN phải giữ (trang phục, phụ kiện, vũ khí) + MÀU
   của chúng; KHÔNG tả lại dáng người, khuôn mặt, kiểu tóc — ảnh tham chiếu đã giữ, tả lại chỉ làm model vẽ lệch ảnh.
3. **Tư thế + vùng bị che là của TỪNG người, theo nhịp.** Cùng `quy` nhưng ôm mặt thì mặt bị che; ghi `che` thay vì để code đoán.
4. **Nhân vật có nhiều dạng (biến hình)** → khai `dang` theo nhịp, để code không đòi món của dạng không có mặt.

## Khối `byd` (các khóa và giá trị hợp lệ)

```json
{"shot": 1,
 "truyen": {"nhip": "bat_dau", "muc_dich": "người xem cần thấy / cảm gì", "cam_xuc": "sợ"},
 "thanh_phan": [{"vat": "KELLY", "vai": "chinh", "vung": "giua", "thay": "mat", "dang": "thuong"}],
 "hanh_dong": [{"ai": "KELLY", "bat_dau": {"tu_the": "quy", "cham_dat": ["dau_goi"], "che": ["mat"]}, "ket_thuc": {"tu_the": "dung"}}],
 "vat": [],
 "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
 "noi_chon": {"kho_id": 263, "spot": "", "thoi_gian": "night", "thoi_tiet": "fog"},
 "ngoai_le": []}
```

- `shot`: số thứ tự shot trong cảnh (1, 2, …) — số nguyên.
- `thanh_phan` (bắt buộc, ≥ 1, ít nhất một `chinh`): `vat` = tên nhân vật ĐÚNG như trong `characters` của shot, hoặc tên ngắn của
  đạo cụ; `vai` ∈ `chinh` | `phu` | `khong_duoc_co`; `vung` (tùy chọn) = `trai` | `giua` | `phai` [+ `-tren` | `-giua` | `-duoi`];
  `thay` (tùy chọn) ∈ `mat` | `lung` | `nghieng` (nhiều thì nối `|`); `dang` (tùy chọn) = chữ, danh sách chữ, hoặc
  `{"bat_dau": …, "ket_thuc": …}`.
- `hanh_dong` (tùy chọn): mỗi người một mục; `ai` phải có trong `thanh_phan`; `bat_dau` bắt buộc, `dinh` / `ket_thuc` tùy chọn; mỗi
  nhịp `tu_the` ∈ `dung` | `ngoi` | `quy` | `bo` | `nga_ngua` | `nam`; `cham_dat` ⊂ `ban_chan` | `dau_goi` | `mong` | `ban_tay` |
  `lung` | `hong` | `bung`; `che` ⊂ `mat` | `toc` | `co` | `than` | `eo` | `tay` | `chan` | `ban_chan`.
- `may` (bắt buộc): `co` ∈ `EWS` | `WS` | `GAME_TPS` | `MLS` | `MS` | `MCU` | `CU` | `ECU`; `do_cao` ∈ `ngang` | `thap` | `cao` |
  `tren_dau`; `goc` ∈ `ngang` | `cui` | `ngua`; `chuyen_dong` ∈ `dung_yen` | `lui` | `tien`.
- `noi_chon` (bắt buộc): `kho_id` = mã Kho của bối cảnh (số trong danh sách tài nguyên của dự án); `thoi_gian` ∈ `dawn` | `day` |
  `dusk` | `night`; `thoi_tiet` ∈ `clear` | `cloudy` | `fog` | `rain` | `storm` | `snow` | `snowfall` | `ice` | `sandstorm`.
- `ngoai_le` (tùy chọn, chỉ khi CỐ Ý trái hồ sơ): `{doi_tuong, dieu_trai, cach_hien, ly_do, pham_vi: [số shot]}` với `ly_do` ∈ `ky_nang` | `hieu_ung_game` |
  `phong_cach`.
- Không thêm nhóm khác ngoài: `truyen`, `thanh_phan`, `hanh_dong`, `vat`, `may`, `noi_chon`, `ngoai_le`, `am_chu`.
