# Bổ sung vai Quay phim — bài học dự án #22 Khủng Long Đỏ (cờ `kld_lessons_prompts`)

> Bổ sung cho `dp.md` Q5 mục "Model làm tốt / làm hỏng". **Độ tin: 1 dự án (#22)** — dữ liệu, không phải bảng tra; chuyển động vẫn
> **không có nghĩa mặc định** (Q5). Nguồn: `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md` mục 4.4.

## Q5 bổ sung — dữ liệu #22
- #22 (Seedance 2.0 Fast / 2.5, clip 11,5 s ở nơi có render 3D): ✘ đẩy vào (push-in) hay vòng cung khi nền chỉ có ảnh mô tả → kiến trúc
  trôi dần. ✔ gần tĩnh + ảnh render PLACE → nền giữ đủ 11,5 s. ✘ lùi + nâng máy ở clip cuối → giây cuối nửa khung là sân trống.
- **Cách nghĩ:** clip càng dài và nền càng có mốc dễ nhận (tháp, cổng), chuyển động càng nên nhỏ và **có điểm cuối được đóng khung** (ghi
  rõ khung ở giây cuối là gì). Người dùng vẫn muốn máy có chuyển động — chọn biên độ nhỏ có động cơ, không bỏ hẳn chuyển động. Có ảnh
  render PLACE thì nền đứng vững hơn; chỉ có ảnh mô tả thì biên độ càng nhỏ.
