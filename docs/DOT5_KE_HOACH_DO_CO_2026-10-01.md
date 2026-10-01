# Đợt 5 — đo các cờ còn lại trong một dự án thử có trần (kế hoạch, CHỜ NGƯỜI DÙNG DUYỆT TIỀN)

Nguồn: `docs/RA_SOAT_DASHBOARD_2026-10-01.md` mục 7, đợt 5. **Chưa chạy gì tốn tiền.** Hiện **27 cờ BẬT mà chưa thử thật** trên máy chính
(4 cờ đã thành `verified` ở đợt 1: `director_two_pass`, `voice_direction`, `project_budget`, `loudness_normalize`, `dialogue_take`).
Mỗi cờ chỉ thành `verified` khi có bằng chứng chạy thật (luật 4, `docs/CHUAN_XAY_DUNG.md`).

## Cần từ người dùng trước khi chạy
1. **Kịch bản mới** để chạy dự án thử (bạn đã nói sẽ test bằng kịch bản mới sau khi tối ưu). Đề xuất 30–45 s, ≥ 2 nhân vật có thoại, 1 cảnh hồi tưởng,
   1 cảnh có nơi 3D (tháp), 1 shot kỹ năng — để mỗi nhóm cờ dưới đây có chỗ áp dụng.
2. **Nạp tiền Claude API** (ngân sách chung đã hết $11,74 / $11,80): ⚙ → 💵 → “Đợt thử & Claude”. S11.2 còn 3 ý tưởng ≈ 0,45 USD.
3. **Trần cho dự án thử** — đề xuất (bạn quyết): Claude 2 USD · ảnh 4 USD · video 9 USD · tổng ≤ 15 USD (đúng trần bạn đã duyệt ở Bước 3 cũ).
   Ước tính chính xác từng khâu do code tính sau khi lập kế hoạch, hiện ở 💵 trước khi bạn khóa — không gửi gì trước khi bạn khóa.

## Nhóm theo cách đo (0 USD → tốn tiền)
| Nhóm | Cờ | Cách đo | Tiền |
|---|---|---|---|
| A. Dựng + âm thanh | `shot_transitions` `impact_shake` `music_breath` `sound_intent` `flashback_fx` `end_hold` `music_fit` `ambience_bed` `motion_trim` `shot_color_match` | **Đợt 4** (đã dựng 2 bản #8, xem bạn quyết) | 0 |
| A'. Cùng đợt dựng | `j_cut` | thêm vào bản dựng so sánh (cùng ffmpeg) | 0 |
| B. Claude nhẹ | `story_check` `film_crew` `profile_digest` (phần prompt) | chạy Lập kế hoạch trên kịch bản mới, so với lần không bật (đã có dữ liệu #8) | ≈ vài US cent mỗi lượt |
| C. QC | `scene_qc` `qc_team` | chạy trên ảnh của dự án thử; so ghi chú QC với mắt người (đã chốt: chỉ đo trên dự án MỚI) | ≈ 0,03 USD / khung (Claude) |
| D. Ảnh trả tiền | `scene_establishing` `storyboard_api` `end_frames` `camera_setups` `continuous_takes` | vẽ storyboard dự án thử, bạn duyệt lưới khung | theo ảnh (cỡ nhỏ nhất, “Thử rẻ”) |
| E. Giọng / video trả tiền | `audio_first` `voice_check_redo` `seedance_ref_groups` `seedance_subjects` `lip_sync` | giọng thật + vài clip Seedance Fast/Kling std 720p | phần lớn của trần video |
| F. Chưa đo được | `storyboard_auto_trust` | cần ≥ 50 ảnh người đã duyệt cùng look; dự án thử chỉ có ~12 → để khi đủ dữ liệu | — |

## Thứ tự chạy đề xuất (mỗi bước hỏi trước nếu vượt ước tính)
1. Đợt 4 xong → quyết nhóm A + `j_cut` (0 USD).
2. Bạn nạp Claude → chạy nốt S11.2 (3 ý tưởng, ≈ 0,45 USD) → chấm phiếu `docs/DO_S11_2_Y_TUONG_2026-10-01.md`.
3. Bạn gửi kịch bản mới → Lập kế hoạch (nhóm B) → xem ước tính → bạn duyệt trần → khóa.
4. Storyboard (nhóm C, D) → bạn xem lưới khung.
5. Video + giọng (nhóm E) chỉ cho shot cần; mỗi lần gen lại phải đổi đầu vào, tối đa 2 lần.
6. Sau mỗi nhóm: ghi bằng chứng (lệnh + số) vào `docs/KET_QUA_DOT5_<ngày>.md`, đổi `verified` + `why` trong `core/features.py`, cập nhật TODO.

## Rủi ro đã biết
- 5 cờ nhóm D/E đổi cách gửi model trả tiền → bật cùng lúc khó biết cờ nào gây lỗi: chạy **tắt hết, rồi bật từng nhóm** trong 🧪 Tính năng thử (preset “Ổn định” làm mốc).
- `lip_sync` / `seedance_subjects` đã có đo ở #14/#15 (01/10) nhưng chưa qua luồng chính nhiều người nói.
- Giá Seedance chưa xác minh (×1,3 trong ngân sách); ClipAI trả cost = 0 cho Seedance → đối chiếu bằng token (xem TODO tồn đọng).
