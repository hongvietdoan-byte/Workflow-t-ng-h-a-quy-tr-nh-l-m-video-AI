# Benchmark BURST Blender portable — 14/10/2026

Đo nhánh `codex/ban-dao-dien-hieu-nang`, không đổi production. Bổ sung BURST20/30 vào phép thử [portable1/5/10](BENCH_BLENDER_PORTABLE_2026-10-14.md); mỗi dự án một job, producer cùng barrier. Tổng 290.195s, Blender5.0.1 version trả0.

24 hộp synthetic,4 camera native,640×360/sample8/Cycles CPU,6 threads cấu hình. `submit_preview` → RenderQueue thật → `_execute` nguyên bản → plates3d → native Job Object. Queue mặc định1worker/24pending/per-project4; ngân sách8GiB render +16GiB dự trữ, RAMguard thật≥24GiB. Không ép nhận25, không sửa queue/guard. Timeout110s/job, global355s.

| Burst dự án | Nhận | Từ chối | Done clay4views | Wall s | Render p95 s | Chờ p95 s | Submit p95 ms | Status p95 ms | Python RSS MiB | Blender RSS MiB | RAMfree min GiB | CPU peak % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 20 | 0 | 20 | 130.104 | 8.176 | 115.578 | 23.982 | 0.054 | 54.82 | 415.14 | 24.135 | 775.5 |
| 30 | 25 | 5 | 25 | 159.766 | 7.251 | 148.402 | 78.77 | 0.049 | 55.76 | 416.84 | 24.208 | 777.7 |

45/45 job được nhận hoàn tất `clay=True`,4views, camera_kind=clay; không fallback2D, không lỗi. Burst30 nhận25 và từ chối5 vì hàng đợi đầy:1job đã rời pending sang worker nên còn24pending. Đây là giới hạn admission queue trong lượt đo, không phải tối đa phần cứng. Không claim30dự án/fullpipeline hoạt động đồng thời. Trạng thái reject thiếu job_id được xử lý ngay trước gọi status.

Mỗi mức chỉ một lượt. p95 nearest-rank; chờ từ trước submit tới `_execute`, gồm hash thật; wall tới queue đóng/worker dừng; render gồm native và ghép sheet. Status gọi service trực tiếp, không latency browser/Streamlit. Không đo riêng thời gian `waiting_resources`; RAMfree thấp nhất24.135GiB gần ngưỡng24GiB nên các ứng dụng khác có thể làm queue chờ. Không chứng minh tải scene/model thật, multiUI, autopilot, TTS/API hoặc giới hạn nhà cung cấp.

CPU100%=một core; mẫu50ms Python+owned Blender, chia16 cho máy16logicalCPU. Threads6 là cấu hình renderer, không hardcapOS. RSS mẫu có thể bỏ lỡ spike; RAMfree toàn máy. Không chạy GPU; baseline2975MiB kế thừa phép đo trước, không phải VRAMpeak của burst.

Supervisor: 46 ownedroot (1version+45render), 46 root handle signaled, 46 Job accounting active0, 46 Job closed. Cả2scenario ownedpeak1/remain0; queueclosed và workerstop đều true. Không quétPID hoặc dừng process ngoài Job. Temp riêng đã xóa sau kiểm đường dẫn tuyệt đối thuộc worktree và mọi worker dừng.

`patch.object(os,'environ',FAKE)` chạy trước import core/calls/spawn; child dùng native explicit whitelist. Feature/assets cô lập; model/legacy locator bị mock chặn. Không dùng provider/registry/Store, credentials, dashboard.env, data, paidAPI hoặc UI thật; không đọc/in môi trường thật. Không commit/push/fullsuite trong phép đo. Artifacts1/5/10 giữ nguyên.

Giữ1worker và queue24pending; hiển thị backpressure và chờ. Burst20 hoàn tất130.1s nhưng p95 chờ115.6s; burst30 chỉ25job được nhận, hoàn tất159.8s và p95 chờ148.4s. Chưa xác định tối đa dự án production.

[Metrics và proof](images/bdd_performance/portable_burst/burst_metrics.json) · [Probe tái lập](images/bdd_performance/portable_burst/burst_probe.py) · [Sheet20](images/bdd_performance/portable_burst/portable_20_project/sheet.png) · [Sheet30](images/bdd_performance/portable_burst/portable_30_project/sheet.png)
