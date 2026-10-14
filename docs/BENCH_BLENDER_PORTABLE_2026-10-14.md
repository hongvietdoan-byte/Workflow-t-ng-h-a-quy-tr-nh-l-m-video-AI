# Benchmark Blender portable — 14/10/2026

Đo nhánh `codex/ban-dao-dien-hieu-nang`, production code giữ nguyên trong phép thử. Blender official portable5.0.1 (checksum do phiên chính xác minh), `--version` chạy lại qua native guard mới, mã trả0. Tổng phép thử 86.179s.

24 hộp synthetic,4 camera thật,640×360/sample8/Cycles CPU,6 threads cấu hình. `blockout_clay.submit_preview` → RenderQueue thật → wrapper đo → service `_execute` nguyên bản → plates3d.render → native Job Object. Cờ fakeON, assets/model lookup cô lập; không settings/data/API/UserEnv/Store hoặc phiên8501. Một producer/project cùng barrier, mỗi1job. Không suy ra burst2job/project.

Queue default1worker/24pending/per-project4, budget estimate8GiB + reserve16GiB, admission kiểm RAM thực≥24GiB. Chưa chứng minh waiting_resources vì RAM luôn đủ. Sources gồm exe/script được hash thật trước/sau; wall/wait gồm chi phí này. Timeout110s/job, global355s.

| Dự án/job | Done clay | Tổng s | Render p95 s | Chờ p95 s | Submit p95 ms | Status p95 ms | Python RSS MiB | Blender RSS MiB | RAM free min GiB | CPU peak % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1/1 | 1/1 | 7.283 | 6.911 | 0.119 | 2.122 | 0.086 | 51.77 | 417.27 | 25.813 | 740.5 |
| 5/5 | 5/5 | 24.801 | 4.848 | 20.042 | 13.371 | 0.066 | 50.38 | 414.26 | 25.762 | 745.0 |
| 10/10 | 10/10 | 53.488 | 6.861 | 48.458 | 19.07 | 0.057 | 53.79 | 414.44 | 25.685 | 773.7 |

16/16 job `clay=True`,4views và camera_kind=clay; không fallback2D. Mỗi mức1lượt, cold/không warm. p95 nearest-rank; không confidence interval. Chờ từ trước submit tới trước `_execute` (gồm hash), render gồm native + ghép sheet, wall tới đóng queue. Status là gọi service trực tiếp, không latency UI/Streamlit/browser.

CPU100%=một core; Python + owned Blender mẫu50ms, chia16 để đổi phần trăm16logicalCPU. Đỉnh773.7% gồm startup; threads6 là cấu hình renderer, không hard OSCPUcap. RSS mẫu có thể bỏ lỡ spike. RAMfree là toàn máy và có ứng dụng khác. GPU không dùng; baseline do phiên chính đo VRAM2975MiB, không đo native VRAMpeak và không claim tảiGPU.

Supervisor: 17 ownedroot spawn (1 version +16render); 17 root handle signaled + Job accounting active0; 17 Job close. Mỗi scenario activepeak1/remaining0; cả3queue closed/worker dừng. Theo dõi đúng handles từ Popen, không scanPID. ACTIVE_PROCESS_LIMIT1 + KILL_ON_JOB_CLOSE chặn child; NtResumeProcess phụ thuộc API ntdll nội bộ trên Windows máy này, không khẳng định mọi API supervisor đều documented.

Môi trường object fake trước imports/spawn (lượt đo gán object trực tiếp; probe lưu đổi sang patch.object.start cùng cơ chế thay object, chưa chạy lại sau đổi cú pháp), native explicit whitelist; TEMP/APPDATA riêng benchmark. Không credentials/registry/provider/modelreal; không log config/env/token. Không sửa production/commit/push/fullsuite. Cleanup chỉ thư mục temp thuộc phép thử sau xác minh tuyệt đối, không chạm .review_test_tmp.

Kết luận:5dựán/5preview hoàn tất24.8s,10/10 hoàn tất53.5s nhưng đợi cuối≈48.5s. Đây là bằng chứng native lower-bound scene nhỏ; chưa xác định tối đa dựán production, scene/modelthật, đa phiênUI, fullpipeline/autopilot hoặc capacity nhà cung cấp. Giữ1worker; cần backpressure/hiển thị chờ, không tăng queue để giấu latency.

[Metrics và proof](images/bdd_performance/portable_metrics.json) · [Probe tái lập](images/bdd_performance/portable_probe.py) · [Sheet1](images/bdd_performance/portable_1_project/sheet.png) · [Sheet5](images/bdd_performance/portable_5_project/sheet.png) · [Sheet10](images/bdd_performance/portable_10_project/sheet.png)
