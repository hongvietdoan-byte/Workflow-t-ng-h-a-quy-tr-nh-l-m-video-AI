# Thử tải Bàn đạo diễn — 14/10/2026

Đo trên nhánh `codex/ban-dao-dien-hieu-nang`, nền `d6797503`. **Chỉ chứng minh queue/service + render Pillow 2D thật. Chưa xác định tối đa dự án production, native 3D, UI Streamlit hoặc pipeline/autopilot.**

## Cách thử và phạm vi

Baseline NVIDIA do root đo 09:22:07: GPU util0%, VRAM used2975MiB/free5086MiB. Đây là baseline máy, không phải tải GPU của benchmark Pillow CPU.

Máy thực: i7-11700, 8 core/16 thread; RAM 63,73 GiB, GPU GTX1070Ti + UHD750 (không dùng GPU). RAM khả dụng đầu đo: 27.04 GiB. Không dùng giá trị AdapterRAM Win32 làm số VRAM vì trường này không đáng tin trên GPU >4GiB.

Mỗi dự án có một producer đồng thời tại barrier và gửi 2 cảnh riêng. Tăng 1/5/10/20/30 dự án. RenderQueue thật:1 worker,24 pending,4 pending/project,64 scope,cache16 entry/256MiB; RenderBudget mặc định6 CPU thread,8GiB/job và chừa16GiB. Pillow là 2D, không sử dụng cap Blender6 thread. Worker kiểm RAM thật≥24GiB, không mock admission.

Interactive:24 khối hộp synthetic, topview1200×1000 và pinhole projection640×360 PNG thật. Batch: cùng plan, snapshot bổ sung64KiB JSON, projection1280×720 và Pillow resize2400×2000/blur/PNG thật. Một tệp nguồn synthetic1MiB được hash đầy đủ trước/sau render; warm hash nguồn và kiểm artifact thật. Bản warm chỉ probe entry còn resident, cùng revision, không suy warm tất cả20/25 job khi cache chỉ16.

Không gọi API/tốn tiền, không Blender/Store, không đọc data/dashboard.env/khóa; fake object os.environ trước import, module plates3d/features cô lập trước import. Không sửa production, không restart dashboard. Timeout30s từng scenario; tất cả kết thúc worker, cleanup thư mục tạm thuộc phép thử.

## Kết quả cold

| Profile | Dự án | Nhận/từ chối | Tổng s | job/s | Submit p50/p95 ms | Status p50/p95 ms | Chờ p95/max ms | RSS peak MiB | CPU peak % một core | RAM free min GiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| interactive_2D | 1 | 2/0 | 0.33 | 6.053 | 0.254/0.371 | 0.012/0.051 | 173.599/173.599 | 39.16 | 119.01 | 27.033 |
| interactive_2D | 5 | 10/0 | 1.572 | 6.361 | 0.376/1.881 | 0.005/0.036 | 1398.344/1398.344 | 39.66 | 132.49 | 27.029 |
| interactive_2D | 10 | 20/0 | 4.649 | 4.302 | 0.297/0.398 | 0.005/0.026 | 4129.887/4375.789 | 40.62 | 137.74 | 27.024 |
| interactive_2D | 20 | 25/15 | 6.763 | 3.697 | 0.344/0.804 | 0.005/0.024 | 6166.737/6473.439 | 41.1 | 148.14 | 27.006 |
| interactive_2D | 30 | 25/35 | 7.163 | 3.49 | 0.469/1.393 | 0.005/0.023 | 6540.39/6827.607 | 41.29 | 143.62 | 27.054 |
| batch_2D_heavy_64KiB | 1 | 2/0 | 1.35 | 1.481 | 1.647/1.758 | 0.012/0.065 | 644.093/644.093 | 96.03 | 109.64 | 27.017 |
| batch_2D_heavy_64KiB | 5 | 10/0 | 7.165 | 1.396 | 12.106/16.211 | 0.007/0.037 | 6373.305/6373.305 | 97.69 | 129.26 | 27.013 |
| batch_2D_heavy_64KiB | 10 | 20/0 | 13.225 | 1.512 | 13.589/21.418 | 0.006/0.026 | 11832.658/12468.226 | 99.45 | 151.25 | 27.015 |
| batch_2D_heavy_64KiB | 20 | 25/15 | 17.802 | 1.404 | 20.067/45.065 | 0.006/0.026 | 16394.736/17064.153 | 102.02 | 154.77 | 27.062 |
| batch_2D_heavy_64KiB | 30 | 25/35 | 17.518 | 1.427 | 21.381/79.427 | 0.006/0.025 | 16049.805/16731.175 | 104.43 | 150.94 | 27.057 |

CPU100%=một core; để đổi thành phần trăm tổng16 logical CPU chia16. Peak lấy mẫu50ms có nhiễu độ phân giải process_time, không coi là CPU toàn hệ thống. RSS là process Python benchmark, không phải RSS native Blender. RAM khả dụng bao gồm chương trình khác đang chạy. Tổng thời gian tính từ trước tạo producer tới terminal cuối, không gồm warm. Chờ đo từ submit tới renderer bắt đầu, bao gồm hash nguồn đầu; không phải chỉ thời gian pending thuần. p95 dùng nearest-rank; mỗi mức chỉ chạy1 lần trong báo cáo cuối, chưa có confidence interval. Lượt trước đã bị bỏ vì lỗi kiểu HANDLE64 ở phép đo RSS; báo cáo và JSON chỉ chứa lượt đo đúng đã chạy lại.

## Cache và công bằng

| Profile | Dự án | Warm hit/probe | Warm p95 ms | Cache byte | Dự án nhận ít nhất1 job | Worker dừng |
|---|---:|---:|---:|---:|---:|---|
| interactive_2D | 1 | 2/2 | 12.336 | 187264 | 1/1 | True |
| interactive_2D | 5 | 10/10 | 7.313 | 936320 | 5/5 | True |
| interactive_2D | 10 | 16/16 | 15.331 | 1498112 | 10/10 | True |
| interactive_2D | 20 | 16/16 | 18.568 | 1498112 | 13/20 | True |
| interactive_2D | 30 | 16/16 | 17.542 | 1498112 | 13/30 | True |
| batch_2D_heavy_64KiB | 1 | 2/2 | 25.968 | 1222540 | 1/1 | True |
| batch_2D_heavy_64KiB | 5 | 10/10 | 20.453 | 6112700 | 5/5 | True |
| batch_2D_heavy_64KiB | 10 | 16/16 | 23.315 | 9780320 | 10/10 | True |
| batch_2D_heavy_64KiB | 20 | 16/16 | 18.315 | 9780320 | 18/20 | True |
| batch_2D_heavy_64KiB | 30 | 16/16 | 20.016 | 9780320 | 17/30 | True |

20/30 dự án gửi40/60 job đồng thời: hệ thống nhận25 gồm1 chạy+24 pending, từ chối15/35 đúng sức chứa. Công bằng round-robin áp dụng job đã được nhận; không đảm bảo mọi dự án trong burst đều vào queue. JSON lưu thứ tự render và số job nhận từng dự án. Mỗi dự án chỉ gửi2 nên chưa kiểm bão riêng một dự án chạm cap4. Stale/superseded=0 vì scene/revision không cạnh tranh, không phải chứng minh cancellation dưới tải. Cache max16 khiến terminal cũ hiển thị expired; đây là lifecycle eviction, không phải lỗi render.

## Giới hạn tạm thời đề xuất

**Tạm dùng5 dự án tương tác đồng thời**, tối đa2 preview pending/project từ caller, với queue default24/per-project4 giữ nguyên. Tải10 dự án vẫn hoàn tất20 job nhưng interactive queue wait≈4s và batch wait≈12s; dùng10 như mức thử có giám sát sau khi caller xử lý reject/retry/backpressure, chưa coi là ngưỡng production. 20/30 không phù hợp burst2job/project vì rejection; không nâng queue chỉ để giấu quá tải.

Giữ1 render worker và profile6thread/8GiB estimate+16GiB reserve. Headroom RAM≈3GiB trên ngưỡng admission tại lúc đo; 8GiB là estimate, chưa hard cap RSS. Nếu RAM thực xuống<24GiB phải chờ resource thật. Thử này không gặp waiting_resources nên không suy rằng native scene lớn sẽ đủ RAM/VRAM.

**Native 3D vẫn CHỜ runtime/supervisor**: Store background bị chặn, không bypass/portable install. Cần benchmark Blender native theo runtime được chọn, scene thực, RSS/VRAM/process cleanup và UI/browser5–10 phiên trước bật cờ. Full pipeline/autopilot phụ thuộc paid-provider caps, FFmpeg/SQLite và dữ liệu thật chưa thử. `autopilot` mặc định2 và remote/provider caps không đổi; giới hạn preview này riêng.

Dữ liệu chi tiết: [`load_metrics.json`](images/bdd_performance/load_metrics.json). Không chạy fullsuite vì không sửa production. Không merge/commit/push trong phép thử này.
