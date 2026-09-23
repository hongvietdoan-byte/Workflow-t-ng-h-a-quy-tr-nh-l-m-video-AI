# Nghiên cứu phong cách dựng video Free Fire (kế hoạch v3, GĐ1)

Cập nhật 2026-09-24. Dữ liệu chữ ở `research/ff_styles/<STYLE>/*.json` (mốc cắt + nhãn từng shot, **không lưu hình**); công cụ `core/reference_analysis.py`, `tools/reference_video.py`; file kiến thức sinh bằng `py tools/ff_style_knowledge.py` → `knowledge/ff_styles/<STYLE>.md` + phần chung `knowledge/ff_directing.md`.

## Tổng hợp theo phong cách

| Phong cách | Video | Shot | Shot/phút | Độ dài shot trung vị | Đặc trưng | Độ tin cậy |
|---|---|---|---|---|---|---|
| `ANIME_CGI` Anime / hoạt hình CGI | 3 | 107 | 38 | 1,2s | nhanh nhất; phản ứng xen sau mỗi nhịp hành động; đổi nhiệt màu theo hồi | trung bình |
| `SHORT_FILM` Phim ngắn | 3 | 161 | 28 | 1,5s | kể theo hồi, mỗi hồi mở bằng toàn cảnh; montage cao trào 0,5–1,5s | trung bình |
| `REAL_CGI_VFX` CGI tả thực / kỹ xảo | 4 | 89 | 20 | 2,5s | cú máy vòng/bay dài + chuỗi cận đặc tả chất liệu; money shot cuối | trung bình |
| `KELLY_SHOW` Kelly Show | 1 | 80 | 19 | 2,8s | người dẫn nói thẳng vào máy quay; thẻ chương lặp 4–5 lần | **thấp (1 video)** |
| `INGAME` Gameplay trong game | 8 | 82 | 17 | 3,0s | 79% camera game sau lưng, 90% có giao diện game, chữ chương vàng | cao |
| `FAN_3D` 3D fan làm (viral) | 0 | 0 | — | — | chưa phân tích | **chưa có** |
| **Tất cả** | **19** | **519** | **24** | **2,0s** | mở bằng hook 13/19, kết bằng shot kết 19/19 | |

So với bản dựng thử v2 của kịch bản Kenta: **3 shot trong 56 giây** (≈ 3 shot/phút, shot 15–26s) — chậm hơn video Free Fire thật 6–12 lần.

## Nguồn

**ANIME_CGI:** Kenta's Obsession (https://www.youtube.com/watch?v=cUQ1PhwvfAE) · Oscar – The Toxic Tanker (https://www.youtube.com/watch?v=9XDYAtUUpzo) · Chiến Binh Thỏ tập 2 (nội bộ).
**REAL_CGI_VFX:** Thánh Nữ Tái Sinh – phim kỹ xảo (https://www.youtube.com/watch?v=VKAAKZ9wiiM) · Thẻ Vô Cực 11 (https://www.youtube.com/watch?v=r-muFciQCko) · Phi Vụ Cuối Cùng (https://www.youtube.com/watch?v=KNngDqkfEHk) · Bí Ẩn Biển Sâu CGI trailer (https://www.youtube.com/watch?v=D3ltkwGqY6M).
**INGAME:** 8 video nội bộ OB55 (Tình huống Kenta, Combo Kenta, Combo ném lựu lửa, Túi cứu thương, Lựu đạn dò, Điều chỉnh vũ khí, Top 3 mở trạm, Tối ưu ngựa).
**KELLY_SHOW:** Nine-Tails Attacks Bermuda OB55 (https://www.youtube.com/watch?v=ylsjBLzKzco).
**SHORT_FILM:** Pitch Party (https://www.youtube.com/watch?v=STvs0Q9HEuU) · The Last Hero (https://www.youtube.com/watch?v=d-GLVj-SZS8) · Free Fire x Blue Lock (https://www.youtube.com/watch?v=p0cl6p_Hrmo).

Video kênh chính thức chỉ dùng để phân tích nội bộ (người dùng đồng ý 2026-09-23); repo chỉ giữ dữ liệu chữ.

## Việc để sau — phân tích thêm video (tạm dừng theo quyết định 2026-09-24)
Mục tiêu ≥ 6 video mỗi phong cách. Danh sách đã chọn sẵn (quét theo cách ở mục "Tiến độ thực hiện" của `docs/KE_HOACH_V3_CHINH_THUC.md`):
- `ANIME_CGI` +3: Free Fire Daybreak `c8Ms_7dvSec`, Eclipse Rises `tOvd-m1ZPNY`, Hành Trình Truy Tìm Kho Báu `da4K66mkVtw` (hoặc Jujutsu Kaisen CGI `3Xd3zdyN-NI`)
- `REAL_CGI_VFX` +2: 9 Years VFX Masterpiece `QX2XSNo3VLs`, Fury Battle `7vURb1A0XRo` (hoặc Arena of Fire `EqAm3hEcyqQ`)
- `KELLY_SHOW` +5: OB54 `TiinJ2XfY_0`, OB53 `kprw35F7AG4`, Music Festival `lhvBqf0mOXA`, OB51 `50lzLEBOWms`, Booyah with Kelly `7ZiwYDisOnM`
- `SHORT_FILM` +3: Free Fire x Gintama `JNNfVi3Nq20`, Fire & Ice Festival `1-3OZJ__HcQ`, Đảo Mặt Trời `i0t5Tq_tgpM`
- `FAN_3D` +6: tìm trên YouTube theo lượt xem ("free fire 3d animation", "free fire animation")
- Khối "Phân tích video tham khảo" trong ⚙ Kho kiến thức (chạy `reference_analysis.analyze_file` cho MP4 trên máy).
Sau khi thêm dữ liệu: `py tools/ff_style_knowledge.py` để cập nhật phần số liệu các file phong cách, rồi sửa bảng trên.
