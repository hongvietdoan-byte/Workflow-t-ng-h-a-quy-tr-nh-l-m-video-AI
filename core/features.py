"""Features that change what is sent to a paid model but have not passed a real test (rule 5 of docs/CHUAN_XAY_DUNG.md): off by default
(except `default_on`: the person decided them on, see below) and kept out of the autopilot until a real run closes their test. `FEATURE_<NAME>=1` switches one on (e.g. for the GĐ-I trials).
When a real test passes, set `verified` to True here with the date and the report that shows it.

C1 (người dùng duyệt 15/10, docs/handoff/RA_QUYET_DINH_LOI_LAP_2026-10-15.md): `fixes_projects: [id dự án]` = cờ sửa lỗi gốc của dự án
đó — còn TẮT ở dự án mới hơn → ĐỎ ở 🧭 Trước khi chạy (core/before_run.py). `default_on: True` = người dùng QUYẾT bật (sổ quyết định
data/decisions.json) dù chưa thử thật: mặc định code bật, `verified` vẫn False (preset Ổn định vẫn chỉ bật cờ đã thử thật).
`costs: True` (rà 15/10) = bật lên là thêm lời gọi tốn tiền (Claude / gen / thêm ảnh hay lượt gọi) — nút bật hàng loạt cờ sửa lỗi
'(0 USD)' bỏ qua (before_run.costly_fix_flag đọc trường này, không dò chữ).
`report()` / `py -m core.features --report` = bảng trạng thái cờ thật (bật/tắt + nguồn) cho báo cáo kết thúc dự án."""
import os
from typing import Dict, List, Optional

FEATURES: Dict[str, Dict] = {
    'subject_capacity_guard': {'label': 'Kho đầy / chưa rõ sức chứa → giữ job chờ, không đổi model',
                               'verified': False, 'why': 'Đ20 M1.5: chỉ thử offline; chưa có allocator đa tiến trình'},
    "motion_sfx": {"label": "SFX theo nhịp BYĐ (code 0 USD)", "verified": False,
                   "why": "Đ12v2: mốc ước tính, chưa nối caller Bước 5/chưa thử sản xuất"},
    'blockout_clay_sheet': {'label':'Tấm duyệt khối clay (Blender cục bộ, 0 USD)', 'verified':False,
                           'why':'Đ11v2: chưa nghiệm thu ảnh Kho thật'},
    'director_blockout': {'label':'Đạo diễn khai sơ đồ khối (Claude, cần báo giá)', 'verified':False,
                         'why':'Đ11v2: dữ liệu giả, tối đa hai lượt sửa; chưa thử sản xuất'},
    "continuity_from_ui": {"label": "Ô giữ bố cục theo shot (0 USD)", "verified": False, "why": "Đ18 việc 3: kiểm dữ liệu giả, chưa thử sản xuất"},
    'shot_popup': {'label': 'Popup icon cuối từng shot (0 USD)', 'verified': False,
                   'why': 'Đ17 việc 2: clip/ảnh/âm thanh cục bộ, chưa thử sản xuất'},
    "package_overrides": {
        "label": "Chỉnh Gói gửi kèm theo shot (bỏ/thêm/ghim và hoàn tác)",
        "verified": False,
        "why": "Đợt 8: lõi dữ liệu kiểm bằng ảnh giả; chưa nối runner/Dashboard, chưa thử sản xuất.",
    },
    "layout_drift_review": {
        "label": "Sửa dàn cảnh v3: ghi lệch bố cục ảnh đã duyệt vào Tổ rà soát (0 USD)",
        "verified": False,
        "why": "Đ8 việc 2: hồi quy bằng tệp/CSDL tạm; chưa thử thật, chưa nối đường ghi tay và Dashboard",
    },
    "short_lock_outfit": {
        "label": "Nhận diện ngắn: bỏ đồ thường với chủ thể có ảnh OUTFIT riêng",
        "verified": False,
        "why": "Đ8 việc 2: MAXIM KL/KELLY KL; cờ tắt giữ nguyên prompt, chưa thử thật",
    },
    "tickets_admin_ui": {"label": "Trang Phiếu 8502 (Owner đăng nhập mới duyệt được; còn lại chỉ đọc)", "verified": False, "why": "Đợt 9 + đăng nhập 8502 (12/10): thử CSDL tạm, chưa dùng thật"},
    "lao_dai_pet": {"label": "Pet Lão Đại chỉ đọc", "verified": False,
                     "why": "Đợt 9: backend thử CSDL tạm; chưa kiểm GUI Windows"},
    "bg_autoqc": {"fixes_projects": [27], "costs": True, "label": "Vòng nền tự bắt đầu kiểm tra ảnh/clip vừa xong (không cần mở trang dự án)", "verified": False,
        "why": "Hộp thư 12/10 17:58: #27 ảnh xong kẹt 'succeeded' ~1 giờ khi không ai mở trang; gọi Claude QC qua sổ chi + trần như khi mở trang"},
    "layout_from_follow": {"fixes_projects": [27], "costs": True, "label": "Shot giữ bố cục (continuity_from): chờ ảnh shot nguồn, thử mẫu kéo shot nguồn, ảnh nguồn vẽ lại → ⚠ cũ", "verified": False,
        "why": "Hộp thư 12/10 19:17: #27 shot 15/17 giữ bố cục theo shot 18 — gửi trước ảnh nguồn thì thiếu ảnh bố cục; nguồn vẽ lại không báo cũ. "
               "TỐN TIỀN khi bật: ảnh ⚠ cũ được chạy tự động / ▶ Gen ảnh vẽ lại (ảnh + motion + clip mỗi shot giữ bố cục)"},
    "subject_auto_cleanup": {"fixes_projects": [27], "label": "Giao bản cuối / cất dự án → lập DRY-RUN xem xét khung ảnh ĐÃ BỊ LOẠI, chờ duyệt xóa từng lần "
                                      "(chạy nền, 0 USD)",
        "verified": True,       # 13/10 người dùng duyệt tính năng (Kho chủ thể đầy 100/100 ở #27); thư viện giả lập, chưa chạy thật
        "why": "13/10 #27: Kho chủ thể đầy vì khung ảnh bị loại vẫn nằm trong Kho; chỉ xóa khung job image_gen 'rejected' của đúng dự án"},
    "framing_guard": {"fixes_projects": [27], "label": "Giữ bố cục video: khung cuối khác khoảng cách máy → không gửi (VÀNG); clip đổi bố cục / lùi máy / "
                               "cắt cảnh / người nhảy vọt → ĐỎ, không tự duyệt (đo OpenCV, 0 USD)", "verified": False,
        "why": "13/10 #27 lỗi hệ thống 2: shot 17 Seedance lùi máy + vẽ mặt đồng hồ ×3 (QC chấm 1,00), shot 16 khung cuối Kelly ở xa → "
               "nhảy cóc; ngưỡng đặt trên clip thật #27, chưa chạy trong sản xuất (core/framing_guard.py)"},
    "back_view_guard": {"fixes_projects": [27], "label": "Shot quay lưng: motion bỏ tả mặt/mắt + câu 'giữ lưng về máy cả shot' (0 USD)", "verified": False,
        "why": "13/10 #27 shot 4: motion tả 'lips pressed / slow blink' cho Kelly quay lưng → Seedance quay mặt cô ra máy giữa shot"},
    "end_state_fresh": {"fixes_projects": [27], "costs": True, "label": "Sửa end_state: ô sửa ở Bước 1/3 + bản dịch motion_en cũ của trường đã sửa không gửi im lặng (dịch lại qua sổ chi)",
        "verified": False,
        "why": "13/10 #27 lỗi 6: end_state sửa mà motion_en.end_state vẫn là bản dịch cũ → prompt code viết gửi trạng thái cuối cũ, tự duyệt"},
    "stale_code_alarm": {"label": "Báo Dashboard / vòng nền chạy code cũ ≠ HEAD — kể cả CỔNG KHÁC (8503/8504): sổ cổng + sha, băng vàng, "
                                  "diag stale_code; chỉ báo, không chặn (0 USD)", "verified": False,
        "why": "V3.1 M1.7 (G55, #31): Dashboard 8503 chạy core cũ sau cập nhật → FAIL_SOURCE; 20/10 8503/8504 chạy code cũ cả ngày, "
               "stop_dashboard.ps1 chỉ tắt 8501 (thêm -All). Thử bằng repo giả + pid giả, chưa chạy máy chính"},
    "diag_merge": {"label": "Gộp chẩn đoán lặp theo (mã, shot) trong 24 giờ — một dòng đếm số lần, giữ câu mới nhất (0 USD)",
        "verified": False,
        "why": "V3.1 M1.7 (G56, #31 15–18/10): change_review_hold 4 435 lần, plate_stale 337 lần — câu đổi theo job nên khóa "
               "'cùng câu trong 10 phút' không gộp được; thử bằng CSDL tạm"},
    "budget_notice_d01": {"label": "Câu cảnh báo ngân sách theo D01 khi mức dự tính = 0 USD: 'chưa có mức dự tính', không ghi '$0.00' "
                                   "như trần (vẫn gửi, chỉ cảnh báo)", "verified": False,
        "why": "V3.1 M1.7 (A14, #33): trích riêng = 0 USD → cảnh báo 'mức dự tính $0.00' lặp lại; D01: không thêm điểm chặn theo ngân sách"},
    "tts_lowercase_caps": {"fixes_projects": [27], "label": "TTS: hạ chữ thường từ tiếng Việt viết IN HOA trước khi gửi (giữ tên/từ game; phụ đề giữ chữ gốc, 0 USD)",
        "verified": False,
        "why": "13/10 #27 lỗi 9: 'BÌNH TĨNH' đọc thành 'bình tỉnh' (đo F0); viết thường thì đúng thanh — mới thử tay 1 câu"},
    "send_claim": {"fixes_projects": [27], "label": "Giữ chỗ gửi job trong CSDL — 2 tiến trình (script + Dashboard) không gửi trùng một job (0 USD)", "verified": False,
        "why": "Hộp thư 12/10 19:58: #27 job 776 gửi 2 lần (script + vòng nền), Deepix tạo 2 task; khóa lượt chỉ trong một tiến trình"},
    "poll_claim": {"label": "Giữ chỗ hỏi/tải kết quả job trong CSDL — 2 tiến trình không cùng tải + duyệt một job; gửi không rõ kết quả "
                            "(hết giờ / 5xx) thì KHÔNG gửi lại, chờ đối soát (0 USD)", "verified": False,
        "why": "V3.1 M1.2 (A1, #33): job 1162 succeeded 2 lần (bg_poll tiến trình riêng + Dashboard), QC đọc ảnh dở → tự gen lại 1163; "
               "thử bằng 2 kết nối SQLite + provider giả, chưa chạy thật (C3-2: bật sau nghiệm thu)"},
    "world_map_sentences": {"label": "Câu vị trí sinh từ world map (M3.3): CHỈ đề xuất + so câu hiện tại, báo REVIEW khi trái/phải ngược map — "
                                     "không đổi prompt gửi đi (cần world_map, 0 USD)",
        "verified": False,
        "why": "V3.1 DP11 (G41–G50, gốc P31-G46): thử offline trên #31 trước; thay câu tả tay = việc sau khi người duyệt map"},
    "world_map": {"label": "World map theo cảnh THỬ NGHIỆM OFFLINE (M3.1): dựng + lưu data/projects/<pid>/world/scene_<cảnh>.json (3D / 2D / "
                           "tương đối / UNKNOWN, version, provenance, invalidation) — không ai trong luồng gen đọc, không chặn gen (0 USD)",
        "verified": False,
        "why": "V3.1 DP8 (G2-4, D06): chỉ offline để người duyệt map #31 cảnh 4/6/8 trước; bật chặn / câu vị trí = việc sau (Cấp 3)"},
    "pause_before_submit": {"label": "Kiểm tạm dừng dự án NGAY TRƯỚC khi gửi job (cả job thử lại / đổi model) — đang dừng thì job giữ "
                                     "hàng đợi có lý do, không gửi (0 USD)", "verified": False,
        "why": "V3.1 M1.3 (G36, #31): tạm dừng 03:42:31 vẫn gửi job 1075 lúc 03:42:41 — runner chỉ kiểm paused đầu lượt quét; "
               "thử bằng provider giả, chưa chạy thật (C3-2: bật sau nghiệm thu)"},
    "send_estimate": {"label": "Ước tính giá ĐÚNG gói sẽ gửi: video nháp theo bậc nháp (480p) + video tham chiếu, bản cao 1080p nâng từ nháp "
                               "tính cả video vào, Claude qua claude_cli = 0 USD API (chỉ đổi con số báo giá, không chặn gì — 0 USD)",
        "verified": False,
        "why": "V3.1 M1.6 (A7–A9 #33, G31 #31): nút Gen video báo 9,13 USD (720p + D6 API) khi gửi nháp 480p; nháp có video tham chiếu "
               "≈ 1,37 × bảng giá; bản cao 1080p sổ chi cao hơn ước tính ~24 %; pregen_check cộng Claude giá API dù chạy claude_cli. "
               "Hiệu chuẩn 2 điểm task ClipAI (docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md mục 5), chưa đối chiếu sổ chi thật"},
    "refusal_skip_same_picture": {"label": "Seedance từ chối gói nhóm vì MỘT ảnh (content[N]): shot nào còn ảnh đó trong gói từng shot thì "
                                           "sang Kling ngay, bỏ bước \"Seedance từng shot\" chắc chắn bị từ chối lại (0 USD)",
        "verified": False,
        "why": "V3.1 C-G36B (G36 phần 2, #31 1057→1065→1071): lần thử lại đầu đi Seedance từng shot với đúng ảnh dạng/vật đã bị "
               "từ chối → phí một lượt; đổi thứ tự người dùng chốt 2026-09-27 nên để TẮT tới khi người dùng duyệt — thử bằng provider giả"},
    "locomotion_end_frame": {"fixes_projects": [27], "label": "Shot chạy/đi: không gửi khung cuối vẽ khi clip sinh dài hơn shot × 1,3 + câu mốc cảnh vật khi máy bám theo (0 USD)",
        "verified": False,
        "why": "Hộp thư 12/10 18:13: #27 shot 3 job 782 (shot 1–2 s, Kling sinh 3 s, khung cuối 'vài bước' ở giây 3 + máy bám sau) chạy tại chỗ; "
               "job 783 bỏ khung cuối + câu mốc cảnh vật chạy thật — mới 1 lần thử"},
    "auto_send_self_fix": {"fixes_projects": [24], "costs": True, 
        "label": "Vòng nền tự gửi job tự sửa (QC gen lại) khi không có chạy tự động",
        "verified": False,
        "why": "Hộp thư 12/10 00:55: #24 job 679/680 kẹt queued, phải gửi tay; qua đúng cổng tiền/trần của nút bấm",
    },
    "support_tickets": {"label": "Kho phiếu Tiểu Nhị / Lão Đại", "verified": False,
                        "why": "Đợt 9: chỉ thử CSDL tạm, chưa bật sản xuất"},
    "chat_prompts": {
        "label": "D6 'đường như chat': trước khi gửi, MỘT lượt Claude nhìn đúng các ảnh sẽ gửi + ý đồ + mô tả của bạn viết lại prompt ảnh / "
                 "video thành một đoạn liền mạch (bản code ghép làm dữ kiện; code chỉ kiểm) — tốn 1 lượt Claude có ảnh / shot",
        "verified": False, "costs": True,
        "why": "Người dùng 14/10 (docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md mục 3b–3c): chưa thí điểm — chạy tools/d6_pilot.py trên 3–5 shot #27 trước",
    },
    "motion_prose": {"fixes_projects": [28], 
        "label": "Prompt video viết bằng code (khi D6 tắt / vượt trần / bị chặn): diễn xuất thành câu kể thay vì nhãn rời "
                 "'Acting — face: …', máy 'track' nói rõ chiều (lùi trước mặt / bám sau lưng) khi chữ shot cho biết (0 USD)",
        "verified": False,
        "why": "Thử D6 14/10 #28 (code ghép) vs #29 (Claude viết): shot 1 chạy cầu thang flow 5,8 vs 13,0; B viết máy 'tracks backward "
               "holding the same distance' + diễn xuất liền câu. Căn cứ là 1 cặp, nhiều biến cùng đổi (ảnh khung đầu khác), chưa tách. #29 shot 3–4 rơi về code ghép (chat_prompt_cap) cũng gần đứng hình. "
               "Mới kiểm bằng test + dựng lại chữ từ scenes.data thật, chưa gen thật",
    },
    "side_truth": {"fixes_projects": [28], 
        "label": "Trái/phải: kịch bản ghi 'bên trái/phải' (của nhân vật) + shot ghi rõ máy sau lưng / trước mặt → code quy đổi sang "
                 "FRAME-LEFT / FRAME-RIGHT và chèn một câu vào prompt ảnh + video; không chắc hướng máy / nhiều nhân vật → VÀNG, "
                 "không đoán (0 USD)",
        "verified": False,
        "why": "Thử D6 #28/#29 (14/10): kịch bản 'núp bên TRÁI tường keo' → Kelly núp sai bên; trước chỉ là luật chữ ở "
               "knowledge/model_guides. Chưa gen thật với câu mới",
    },
    "travel_truth": {"fixes_projects": [30], 
        "label": "Hướng chạy: shot di chuyển từ chỗ đứng 3D này sang chỗ đứng của shot kế (nối liền, cùng cảnh) mà chênh độ cao rõ "
                 "(≥ 1,5 m, dốc ≥ 0,12) → code chèn MỘT câu lên/xuống + chiều so với máy của nền vào prompt ảnh + video; chữ shot trái "
                 "nền / thiếu dữ liệu 3D → VÀNG, không đoán (0 USD)",
        "verified": False,
        "why": "Kiểm thật #30 shot 1 (14/10): kịch bản A chân cầu thang (z 3,9) → B bậc cao nhất (z 8,5) mà ảnh Kelly chạy XUỐNG; "
               "trước đó không câu nào nói hướng chạy. Mới kiểm bằng tools/replay_payload.py + test, chưa gen thật",
    },
    "script_pose_fix": {"fixes_projects": [28], 
        "label": "Tư thế theo kịch bản: vế kịch bản chỉ ghi 'đứng' mà BYĐ (một người) toàn quỳ/ngồi → code sửa BYĐ thành đứng sau "
                 "lượt Đạo diễn + ghi lý do; ca mơ hồ giữ VÀNG; không đụng BYĐ người dùng khóa tay (0 USD)",
        "verified": False,
        "why": "Thử D6 #28 shot 3 (14/10): 'Kelly đứng sát, núp…' → BYĐ quỳ → ảnh + clip ngồi xổm. Mới kiểm bằng test + dữ liệu #27/#28",
    },
    "mix_bus": {
        "label": "Nhạc nén riêng dưới bus hiệu ứng (SFX) 8–12 dB (ffmpeg, 0 USD)",
        "verified": False,
        "why": "C5b / Đ12v3 mục 2 (14/10): đo trên tín hiệu tổng hợp; chưa nghe bản dựng thật.",
    },
    "post_fx_render": {
        "label": "Hậu kỳ nhiễu sóng/glitch/nhấp nháy theo post_fx (ffmpeg, 0 USD)",
        "verified": False,
        "why": "ĐỢT 6 (11/10): chỉ thử clip ffmpeg tổng hợp; chưa xem bản dựng thật.",
    },
    "ref_beats_tool": {
        "label": "Công cụ CLI tạo dải ảnh và mẫu nhịp video ref cục bộ",
        "verified": False,
        "why": "ĐỢT 6 việc 2 (11/10): đã thử video tổng hợp; chưa thử ref sản xuất, chỉ bật tay cho CLI",
    },
    "shot_lessons_db_order": {
        "label": "Công cụ bài học shot: thứ tự từ CSDL và cảnh báo thiếu ánh xạ nhịp",
        "verified": False,
        "why": "Đợt 6 việc 3: chỉ CLI, CSDL chỉ đọc; chưa thử trên dự án thật",
    },
    "seedance_sample_mode": {
        "label": "Thử độ nét Seedance 2.5: 720p hoặc bản mẫu 480p → bản cuối 1080p; kết quả thử riêng",
        "verified": False,
        "why": "Người dùng 07/10 duyệt khôi phục S4.11 để so A+/B Khủng Long Đỏ; bản cuối chưa chạy thật. Mỗi bước ghi sổ chi.",
    },
    "voice_check_redo": {
        "label": "Chạy tự động: tạo lại giọng thoại bị cờ lỗi (cắt/thiếu chữ/ngắt quãng) một lần",
        "verified": False,
        "why": "AU-f mới (2026-09-24): ngưỡng độ dài/im lặng và so chữ nghe được chưa đo trên giọng Việt thật — cờ sai thì trả tiền TTS vô ích",
    },
    "film_crew": {
        "label": "Tổ làm phim: Director đọc bộ nguyên tắc Đạo diễn + Quay phim (knowledge/roles/) thay cho 3 tài liệu rải rác (cinematography_basics, film_director_method, dialogue_craft), ghi tradeoffs",
        "verified": True,       # 08/10 người dùng duyệt: #22 Khủng Long Đỏ Director chạy bộ mới (tradeoffs, Tầng B, duyệt 2 cảnh) — docs/KIEM_22_TINH_NANG_KLD_2026-10-08.md
        "why": "Đã chạy thật #22 (06/10): Director 6 lượt Claude với bộ nguyên tắc mới, director_raw có tradeoffs, Đạo diễn duyệt 2/2 "
               "cảnh; video người dùng xác nhận đạt 08/10. Còn mở: chưa A/B với bộ cũ"
    },
    "director_two_pass": {
        "label": "Director hai lượt (dự án chia shot): Tầng A Đạo diễn viết Bible + ý đồ từng cảnh, Tầng B Quay phim chia shot MỖI cảnh "
                 "một lượt (phần chung cache), code Đạo diễn duyệt bảng shot so với ý đồ",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): #8 chạy thật hai lượt, Đạo diễn duyệt 6/6 cảnh (TONG_KET_DU_AN_8 mục 3)
        "why": "Đã chạy thật: #8 (28–29/09) Director hai lượt, Đạo diễn duyệt 6/6 cảnh; người dùng duyệt 29/09 (S6.5). Lý do ban đầu (GĐ5, "
               "26/09: mới thử bằng Claude giả lập) đã hết hiệu lực (core/director_two_pass.py)",
    },
    "voice_direction": {
        "label": "Chỉ đạo giọng lồng: câu thoại có `delivery` (cảm xúc, cường độ, nhịp, ngắt, nhấn, thẻ v3) → tham số TTS + chữ gửi TTS",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): #8 — 23 câu thoại đúng giọng, đúng người (4 giọng VN)
        "why": "Đã chạy thật: #8 có 23 câu thoại đúng giọng, đúng người (4 giọng VN); người dùng duyệt 29/09 (S6.5). Còn mở: thẻ [whispers] "
               "với giọng Việt chưa nghe thử riêng (tài liệu ElevenLabs mâu thuẫn về `speed` của eleven_v3)",
    },
    "loudness_normalize": {
        "label": "Chuẩn hóa độ to bản giao về −14 LUFS / đỉnh thật −1,5 dBTP (loudnorm 2 lượt, tăng/giảm tuyến tính) khi số đo lệch mục tiêu",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): bản giao #8 đo −14 LUFS
        "why": "Đã chạy thật: bản giao #8 đo −14 LUFS; người dùng duyệt 29/09 (S6.5). Còn mở: chưa nghe thử một bản được chuẩn hóa trên điện "
               "thoại (editing.md E8, D11: không nền tảng nào công bố LUFS)",
    },
    "shot_color_match": {
        "label": "Khớp màu giữa các shot cùng nơi + cùng nhóm cỡ cảnh (điểm đen/trắng, ám màu của vật xám) — sửa bản sao clip lệch trước khi dựng",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E5, D7): đo thật #7 thấy 2/7 shot lệch điểm đen/trắng 0,14–0,15 (một phần do nội dung khung); sửa thử đưa "
               "về ~0,04 — chưa có người xem bản dựng đã khớp màu",
    },
    "j_cut": {
        "label": "Cắt J: câu của người nói mới vào sớm 0,25 s trước khi hình cắt sang shot của họ (không đè câu trước)",
        "verified": False,
        "why": "GĐ4 (editing.md E1, D1): chưa nghe thử bản dựng có cắt J trên giọng Việt lồng — phụ đề đi theo giọng nên cũng vào sớm",
    },
    "music_breath": {
        "label": "Nhạc lặng 0,6 s ngay trước cú ngoặt (phần kịch bản TWIST / CAO TRÀO, hoặc shot ⭐ đầu tiên)",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E4, D6): chưa nghe thử; khoảng lặng dài/ngắn là gu dựng — bật khi người dùng nghe và đồng ý",
    },
    "music_story_arc": {
        "label": "Nhạc nền theo đường cảm xúc cả truyện (N3): chặng mở đầu → căng → ngoặt → cao trào → kết, MỘT bản nhạc AI liền mạch "
                 "đổi chặng đúng giây bước ngoặt trên bản dựng; tách bài chỉ khi đổi chất liệu (bài gốc), nối mượt; điểm vào bài tự động; "
                 "ducking đều 8–12 dB",
        "verified": True,        # 14/10 người dùng: BẬT mặc định ("nhạc nền theo đoạn cảnh là MẶC ĐỊNH", TODO việc 13 ngày 07/10)
        "why": "Người dùng chốt 08/10 (docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 3) và 14/10 cho bật mặc định. Mới thử bằng tín "
               "hiệu tổng hợp (ducking 8,3–11,7 dB với giọng −26…−14 dBFS); nghe bản dựng nhiều bài thật lần đầu ở tập 2 #27",
    },
    "sound_intent": {
        "label": "Nhạc theo ý đồ âm thanh của Đạo diễn từng shot: tắt hẳn từ shot 'cut' tới shot 'in', lặng 0,6 s trước shot 'breath'",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-26 (director.md Đ9, bài học Handbook ch. V): chưa nghe thử bản dựng có nhạc ngắt theo shot; tắt thì bản dựng "
               "ghi lại số ý đồ chưa áp (manifest `sound_intent`)",
    },
    "flashback_fx": {
        "label": "Hồi tưởng ở khâu Dựng: shot hồi tưởng có flash trắng vào/ra, màu ấm nhạt + viền tối (người xem biết là ký ức)",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-28 (sau #8, người dùng: hồi tưởng không có hiệu ứng nên không ai biết là hồi tưởng): mới thử bằng ffmpeg trên clip "
               "#8, chờ người dùng xem bản dựng lại",
    },
    "end_hold": {
        "label": "Giữ hình shot cuối ít nhất 2,5 s (kéo dài khung cuối) để cái kết không lướt qua",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-28 (sau #8: hai shot kết mỗi shot 1 s, người dùng thấy kết cụt): chờ người dùng xem bản dựng lại",
    },
    "continuous_takes": {
        "label": "Đoạn diễn liên tục theo góc máy: mỗi vị trí máy (camera_setup) quay TRỌN đoạn diễn liên tục của cảnh, rồi mỗi shot được "
                 "cắt đúng chỗ của nó trong đoạn — cắt xen các góc mà động tác vẫn liền (cần bật cùng camera_setups)",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. 2026-09-29 (kế hoạch S3.4, sau #8: mỗi shot gen riêng, chuyển động bắt đầu lại ở mỗi điểm cắt): mới thử bằng test ffmpeg — "
               "chưa biết model video có diễn trọn đoạn 8–15 s đúng thứ tự không, và trả tiền nhiều giây hơn cho mỗi góc",
    },
    "shot_transitions": {
        "label": "Chuyển cảnh từng chỗ nối theo `transition_in` của shot (chớp trắng, tối đi, lia nhòe, lao vào khung) — vẽ trong hai clip "
                 "kề nhau nên độ dài phim không đổi",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S3.6): mới thử bằng test ffmpeg — chưa xem trên bản dựng thật (lia nhòe / lao vào khung có thể lộ "
               "giả trên clip AI)",
    },
    "story_check": {
        "label": "Người xem lần đầu: 1 lượt Claude chỉ đọc cái sẽ hiện trên màn hình (hành động, thoại, chữ — không đọc ý đồ Director) rồi "
                 "kể lại truyện và chỉ chỗ khó hiểu, trước khi làm ảnh",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S3.2, sau #8: truyện cụt, Maxim trúng đạn không thấy ai bắn): mới thử bằng Claude giả lập — chưa biết "
               "người xem Claude có bắt đúng chỗ người xem thật thấy khó hiểu không (lần chạy kiểm K)",
    },
    "rough_cut_review": {
        "label": "Duyệt bản dựng thô (P0–P1 chỉ đo, 0 USD): sau khi ghép, đo nhịp thật của bản dựng so với ý đồ Đạo diễn (độ dài cảnh so `target_s`, "
                 "đỉnh `peak` có shot đủ dài không, khoảng lặng) + tấm khung quanh điểm cắt ≤ 12 ảnh. Lượt Claude Biên tập viên + Đạo diễn là P2, chưa có",
        "verified": False,
        "why": "2026-10-02 (kế hoạch docs/KE_HOACH_DUYET_BAN_THO_2026-10-02.md, P0–P1): mới thử bằng test + fixture; chưa chạy trên bản dựng thật, "
               "chưa biết các số đo có giúp người dùng thấy đúng chỗ nhịp chùng hay không",
    },
    "audio_first": {
        "label": "Timeline theo âm thanh: tạo giọng ngay sau Director, kéo độ dài từng shot theo giọng thật, kiểm tổng so với mục tiêu "
                 "kịch bản (±10 %) và khóa timeline TRƯỚC khi làm ảnh / video",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S2, sau #8: dự kiến 58 s ra 83 s vì giọng làm sau clip): mới thử bằng test, chưa chạy trên dự án thật",
    },
    "music_fit": {
        "label": "Nhạc nền đi theo cảnh thật: dời / co giãn từng đoạn của bản nhạc đã soạn cho khớp đầu mỗi cảnh trên bản dựng (miễn phí)",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-28 (sau #8: nhạc soạn cho timeline 64 s, phim thành 84,5 s — đổi nhạc lệch cảnh, người dùng: nhạc phải đi theo "
               "diễn biến): chờ người dùng nghe bản dựng lại",
    },
    "impact_shake": {
        "label": "Rung khung hình 0,25 s ở những giây có hiệu ứng va chạm / nổ / súng trong bản trộn",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E6, D9): chưa xem thử trên bản dựng thật; rung sai chỗ làm người xem khó chịu",
    },
    "ambience_bed": {
        "label": "Âm nền mỗi cảnh từ thư viện âm thanh của bạn (theo thời tiết → giờ → bối cảnh), nhỏ dưới thoại, lặp đủ dài",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E3, D4/D5): thử #7 — cảnh ngày khu nhà trên đảo nhận 'Bird Ambience'; cảnh đêm không có âm đêm trong "
               "thư viện nên để trống (báo) — chưa nghe bản trộn",
    },
    "speed_ramp": {
        "label": "Quay chậm / dừng hình khi cắt shot: shot không thoại có `speed` < 1 (nội suy khung) hoặc `freeze_end_s` (editing.md E10)",
        "verified": False,
        "why": "2026-09-26 (người chấm bộ 3 vai): đã thử bằng ffmpeg trên clip mẫu (test), chưa xem trên clip Kling/Seedance thật — nội "
               "suy chuyển động có thể làm méo tay/vũ khí khi chuyển động nhanh; xem A/B trên clip có sẵn trước khi bật",
    },
    "motion_trim": {
        "label": "Cắt shot từ clip dài: dời điểm bắt đầu (≤ 1 s) khi hành động chính đến muộn (đo chuyển động trong clip)",
        "verified": False,
        "why": "GĐ4 (editing.md E1, D2): thử #7 shot 3 — giọt lệ lăn từ 1,1 s, bộ chọn dời 1,0 s (hợp lý); rủi ro: model tự chèn cảnh "
               "khác cuối clip cũng là 'chuyển động mạnh' — giới hạn 1 s, bỏ qua shot thoại / nối liền / khớp môi",
    },
    "profile_digest": {
        "label": "Hồ sơ nhân vật rút gọn: prompt ảnh dùng lock_medium (≤ 500 ký tự), prompt video dùng lock_short (≤ 200) thay cho bản đầy đủ",
        "verified": False,
        "why": "V4 4.4 (core/profile_digest.py): bản rút gọn bỏ bớt chi tiết — chưa đo model ảnh có giữ đúng nhân vật với bản ngắn không (GĐ8)",
    },
    "camera_setups": {
        "label": "Quay theo vị trí máy: Director/Quay phim gán camera_setup cho shot (một clip cho nhiều shot cùng góc)",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. Chạy thử 2A (H5): một cặp shot tiết kiệm 33% nhưng mất khung nhấn riêng — cần thử thêm ở cảnh thoại dày trước khi bật",
    },
    "seedance_ref_groups": {
        "label": "Video Seedance chỉ ảnh tham chiếu (đánh dấu tờ thiết kế): gộp 2–4 shot liền của một cảnh thành một lần gen (mỗi shot có "
                 "ảnh storyboard riêng) → bị từ chối thì Seedance từng shot → rồi Kling (người dùng chốt thứ tự 2026-09-27). Thay nhóm H5",
        "verified": False,
        "why": "Thử 2026-09-27 (docs/PHAN_TICH_GOP_SHOT_2026-09-27.md mục 6): 2/2 lần gen qua bộ lọc, cắt 3 shot đúng storyboard — mới thử "
               "bằng công cụ riêng trên 1 cảnh ban ngày, chưa chạy qua luồng chính / cảnh tháp đêm / cắt clip theo điểm cắt dò được",
    },
    "scene_qc": {
        "label": "QC theo cảnh: lớp 0 bằng code (số mặt, cỡ cảnh đo bằng mặt, vùng an toàn, mặt đủ sáng) + lớp 1 Claude MỘT lượt mỗi cảnh "
                 "(tấm ghép các khung + ảnh toàn cảnh + ảnh chuẩn nhân vật, hỏi có/không kèm bằng chứng) — thay QC từng ảnh + QC đồng bộ",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. Rà soát 2026-09-27 (docs/RA_SOAT_CLAUDE_KY_NANG_2026-09-27.md): QC từng ảnh không phân biệt ảnh lỗi (0,67) với ảnh tốt (0,69) "
               "trên 54 ảnh #8 — QC mới chưa đo trên bộ nhãn",
    },
    "project_budget": {
        "label": "Ngân sách dự án chia theo khâu (ảnh, video, Claude từng khâu), code tính ngay sau bảng shot, người duyệt thì KHÓA: mọi "
                 "lời gọi trả tiền kiểm trần khâu + tổng trước khi gửi; chạy tự động chờ duyệt ngân sách trước khi gen ảnh",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): #8 — khóa cứng chặn đúng ở trần (TONG_KET_DU_AN_8 mục 3, Chi phí)
        "why": "Đã chạy thật: #8 — khóa cứng chặn đúng ở trần (TONG_KET_DU_AN_8 mục 3); người dùng duyệt 29/09 (S6.5). Lý do ban đầu "
               "(28/09: #8 ước 12,45 USD, chưa làm video đã chi 16,38) là chính điều khóa này ngăn. Lỗi B1 01/10 (khâu Claude 'khác' bị chặn vì "
               "max_tokens mặc định) đã sửa",
    },
    "scene_qc_claude": {
        "label": "QC theo cảnh lớp 1: Claude MỘT lượt mỗi cảnh tự chạy khi đủ khung (tắt: khung mới đi thẳng tới người duyệt, lớp 0 "
                 "bằng code vẫn chạy; bật agent QC thì agent thay lớp này)",
        "verified": False,
        "why": "Nghiệm thu 2026-09-27 trên 33 khung có nhãn của #8 không đạt (bỏ lọt 6 khung dán, báo nhầm 12/21 khung tốt); chấm lại cả "
               "cảnh sau mỗi lần vẽ lại tốn ~0,5 USD Claude chỉ để ghi chú (docs/CHAY_THU_2026-09-27_NHAT_KY.md phát hiện 44)",
    },
    "next_glow": {
        "label": "Nút bước chính to + nút của bước kế sáng xanh (nhãn 👉 Bấm tiếp, một đích mỗi lúc); mỗi người tắt riêng ở ⚙ → Hệ thống",
        "verified": True,       # 2026-10-07 người dùng duyệt bật mặc định cho mọi tài khoản ("ai muốn tắt thì tắt sau")
        "why": "Người dùng 07/10: người mới chưa từng biết quy trình cũng dùng được — bật sẵn ở mọi tài khoản. Chỉ đổi giao diện "
               "(CSS), không đổi gì gửi tới model trả phí; đã chụp màn thật trên cloud (nút Lập kế hoạch, Duyệt tất cả ảnh sáng đúng)",
    },
    "chat_first": {
        "label": "Tab Kịch bản kiểu chat: khung chat lớn ở giữa nhận chữ + ảnh + video + nhạc + file kịch bản; code xếp loại tệp 0 USD "
                 "(chắc thì gắn ngay vào Kho / video ref cảnh / thư mục nhạc, không chắc thì hỏi lại trong chat); các thẻ chi tiết gấp vào ⚙ Chi tiết",
        "verified": False,
        "why": "Người dùng 07/10 (Khủng Long Đỏ mục 10, Đợt 1): code + test ở cloud, chưa thử trên Dashboard thật. Không đổi gì gửi tới "
               "model trả phí; bật để thử bố cục mới, tắt = màn cũ y nguyên",
    },
    "idea_to_script": {
        "label": "💡 Ý tưởng thô → kịch bản ở Bước 1: Biên kịch (Claude) hỏi lại ≤ 5 câu → 3 hướng → dàn ý theo giây → kịch bản đúng khuôn, "
                 "code kiểm, người duyệt từng lượt + màn 2 cột tô phần thêm (S11.1)",
        "verified": True,       # 2026-10-06 người dùng duyệt bật mặc định (S14.43 mục 5)
        "why": "S14.22 cổng S11.2 ĐẠT: người dùng chấm phiếu 05d (docs/DO_S11_2_Y_TUONG_2026-10-05d.md) TB 4,20 ≥ 4,0, đo thật 0,709 USD; "
               "06/10 người dùng duyệt bật mặc định — dùng khi người dùng yêu cầu hoặc khi kịch bản sơ sài (Claude hỏi trong khung chat, chưa tự chi)",
    },
    "horizon_needs_sky": {
        "label": "Cổng ảnh→video: chỉ so đường chân trời khi nền CÓ trời (V3.1 M3.5) — trong nhà / từ trên cao / render không trời → bỏ kiểm "
                 "chân trời có lý do (VÀNG, không ĐỎ); có trời hoặc không rõ → kiểm như cũ",
        "verified": False,
        "why": "#31 G20: S22 trong phòng, S39 từ trên cao bị báo 'lệch nền 3D' vì mép tường/sàn bị đo như chân trời. Chưa chạy trên ảnh thật",
    },
    "qc_false_alarm_fix": {
        "label": "Sửa báo nhầm QC (V3.1 M4.5): QC lớp 0 bỏ kiểm cỡ cảnh khi bố cục qua vai / sau lưng (A5); Tổ rà soát nhận tên video "
                 "tham chiếu của shot (A6)",
        "verified": False,
        "why": "#33: S2 sau lưng nhóm bị đo nhầm 'WS, xin MS' → tự gen lại ép thắt lưng (A5); shot 6 bị báo 'không có video tham chiếu' "
               "(#877, A6). Chỉ bớt báo nhầm, không chặn gì. Chưa chạy trên dữ liệu thật",
    },
    "video_qc_shadow": {
        "label": "QC video SHADOW (V3.1 M4.2): đo clip đứng yên ≥ 1,5 s, khung 0 khác ảnh đầu, chuyển cảnh chép từ video ref; ghi bằng chứng "
                 "theo mã M4.1 vào <dự án>/qc_shadow/video_qc.jsonl — KHÔNG đổi điểm QC, không giữ job, không gen lại",
        "verified": False,
        "why": "#31 G51 (đơ 6 s, chạy tại chỗ), G28 (khung 0 khác ảnh đầu), #33 B8 (chép chuyển cảnh ref) chỉ người thấy. Ngưỡng chưa "
               "hiệu chuẩn (benchmark M4.6) → chỉ ghi, chưa chặn. Chưa chạy trên clip thật",
    },
    "continuity_shadow": {
        "label": "Logic XUYÊN SHOT shadow (V3.1 M4.3): giữa 2 shot liền cùng nhóm — vật đang cầm biến mất, đổi dạng, đổi hướng đi trên khung "
                 "(chỉ khi chữ nói rõ) → ghi bằng chứng + đồ thị phụ thuộc + shot 'cần xem' theo kết quả QC logic chuỗi; KHÔNG chặn, 0 USD",
        "verified": False,
        "why": "#31 G52 (logic chuỗi 39 clip), G51 (súng biến mất), G41 (hướng chạy) chỉ người / Claude thấy; chạy sau qc_sequence_logic. "
               "Chưa chạy trên dữ liệu thật",
    },
    "send_preview_panel": {
        "label": "Thẻ clip Bước 4: khung gập \"Gói sẽ gửi\" (dựng bằng đúng đường nút Gen — thứ tự ảnh ref, nhãn, prompt, giá send_estimate; "
                 "không gửi, không gọi Claude/nhà cung cấp) + khung \"QC shadow\" (đọc M4.2 / M4.3 / M4.1) — CHỈ XEM (V3.1 M4.7)",
        "verified": False,
        "why": "Người dùng không thấy gói thật sẽ gửi trước khi trả tiền và không thấy kết quả QC shadow theo shot. Chưa chạy trên dữ liệu thật",
    },
    "continuity_state": {
        "label": "continuity_state SHADOW (V3.1 M3.4): trạng thái mong đợi giữa 2 shot liền từ BYĐ (vật cầm giữ / mất / đổi tay, tư thế cuối → "
                 "đầu, nơi chốn, hướng trên khung) + quan sát của QC shadow (M4.2 / M4.3) + đồ thị phụ thuộc → <dự án>/world/continuity_state.json; "
                 "mức REVIEW, KHÔNG chặn, 0 USD",
        "verified": False,
        "why": "#31 G51 (súng biến mất), G52 (logic chuỗi 39 clip), G1 (đạo cụ sang cảnh khác) chỉ người thấy. Chạy sau QC logic chuỗi. "
               "Chưa chạy trên dữ liệu thật",
    },
    "whitebox_height_dummy": {
        "label": "Người nộm whitebox đúng chiều cao hồ sơ Kho (height_m) + máy ở tầm mắt 0,93 × height_m, pitch eye (≤ 5°) / slightly_high "
                 "(cúi ~10°); thiếu chiều cao → báo, không im lặng (V3.1 M3.2, offline — không gửi gì thêm cho model)",
        "verified": False,
        "why": "G2 (người sai tỉ lệ so nền), G3 (#31 shot 28 khai eye mà pitch +17,3°), A10. Whitebox cũ cố định mắt 1,6 m, khối 1,8 m. "
               "Chưa render thử trên máy chính",
    },
    "final_black_freeze": {
        "label": "Kiểm bản dựng cuối: đoạn màn hình ĐEN (≥ 0,5 s) và ĐỨNG HÌNH (> 1,5 s) bằng ffmpeg blackdetect / freezedetect — chỉ "
                 "cảnh báo (cần xem), không chặn xuất (V3.1 M4.4)",
        "verified": False,
        "why": "Người dùng 11/10: video không được đơ; G51 (#31 shot 13 đơ 6 s). Ngưỡng chưa hiệu chuẩn trên bản dựng thật",
    },
    "qc_evidence": {
        "label": "Ghi BẰNG CHỨNG QC theo schema V3.1 M4.1 (qc_runs / qc_findings; chưa có bảng → <dự án>/qc_shadow/qc_evidence.jsonl) song "
                 "song với QC hiện có — shadow: không đổi quyết định, không giữ job (nay nối: kiểm bản dựng cuối)",
        "verified": False,
        "why": "Không đo được báo nhầm theo mã khi 9 đường QC ghi 5 dạng khác nhau (thiết kế M4.1). Bảng = migration Cấp 3 (chưa áp CSDL thật)",
    },
    "repair_router": {
        "label": "Repair router theo mã lỗi (V3.1 M5.1) — CHỈ ĐỀ XUẤT: QC không đạt → kế hoạch sửa (đổi đầu vào gì, lần mấy / trần, khi nào "
                 "dừng hỏi người) ghi ở ⚙ Chẩn đoán; KHÔNG tự gửi job (tự gửi = Cấp 3)",
        "verified": False,
        "why": "Luật 6 CHUAN_XAY_DUNG + G2-6 (router mặc định TẮT). Chưa chạy trên dữ liệu thật",
    },
    "release_gate": {
        "label": "Cổng phát hành (V3.1 M5.2): trước nút Xuất bản hiện checklist 8 mục đo được — shot đã duyệt, kiểm bản dựng, lớp ⚠ cũ, đối "
                 "soát chi phí, gửi không rõ kết quả, lỗi CAO mở, việc chờ người, lineage — ĐẠT / CHƯA ĐẠT; CHỈ cảnh báo, không chặn xuất",
        "verified": False,
        "why": "Thiết kế M5.2 (shadow trước; chặn = guarded, Cấp 3). Chưa chạy trên dự án thật",
    },
    "qc_observe_enum": {
        "label": "QC ảnh: model khai quan sát enum, code quyết điểm (Đ14)",
        "verified": False,
        "why": "Chưa thử thật; cờ tắt mặc định, không chắc → VÀNG chờ người, không trừ điểm",
    },
    "qc_team": {
        "label": "Tổ QC nhiều tầng (docs/THIET_KE_TO_QC_2026-10-01.md): bảng shot → mệnh đề kiểm tra, code đo trước (mặt, hướng mắt, màu trời), "
                 "chuyên viên Nhân vật trả lời có cấu trúc 1 lượt / khung, bảng luật code kết luận — thay lớp 1 của QC theo cảnh",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. GĐ3 01/10 trên #8: mũ đúng 5/5 nhưng trái/phải do model đúng ~50 % → trái/phải chỉ đánh dấu cho người, không tự chặn; "
               "người dùng 01/10 bật thử trên dự án mới — mọi khung vẫn chờ người (ghi chú của Tổ QC), chưa tự duyệt / vẽ lại",
    },
    "qc_agent": {
        "label": "Agent QC điều tra nhiều bước (Claude có công cụ: xem khung / cắt sát / ghép dải nhiều khung / ảnh chuẩn / bộ đo / ghi "
                 "kết luận) theo sổ tay kiểm tra — thay lớp 1 của QC theo cảnh",
        "verified": False,
        "why": "Thử 2026-09-27 bằng agent trong phiên làm việc (không qua API): 11 lỗi chặn đúng trên #8, người dùng xác nhận; bản trong "
               "app (core/qc_agent.py) chưa đo trên bộ nhãn",
    },
    "scene_qc_trusted": {
        "label": "Cho QC theo cảnh (lớp 1, Claude) TỰ duyệt / tự vẽ lại — chỉ bật khi đã qua nghiệm thu (bắt đủ lỗi nhìn thấy rõ, báo nhầm ≤ 10 %)",
        "verified": False,
        "trainee": True,       # 15/10 người dùng (#31 đợt thử cờ): học việc — mọi khung vẫn chờ người, chỉ ghi 'sẽ tự duyệt' / 'sẽ vẽ lại' (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 15/10: khung vẫn chờ người như khi tắt; trainee_log ghi 'sẽ tự duyệt' / 'sẽ vẽ lại' + lý do để so với "
               "người (core/trainee.py RULES scene_qc_trusted); bật thật chỉ khi đủ chuẩn và bạn duyệt. Nghiệm thu 2026-09-27 trên 33 ảnh ghép có nhãn của #8 (tools/experiments/qc_regression.py): bắt 6/12 lỗi rõ nhưng không lần "
               "nào vì đúng lỗi, cho qua 6 khung chữ nhật dán + tháp Big Ben, báo nhầm 12/21 ảnh tốt → khi tắt: mọi khung chờ người, "
               "nhận xét của QC chỉ là ghi chú",
    },
    "scene_establishing": {
        "label": "Mỗi cảnh kịch bản một ảnh toàn cảnh ngang 2048×1152 (nơi chốn + giờ + ánh sáng, không người) vẽ từ ảnh bối cảnh của Kho, "
                 "làm ảnh tham chiếu nơi chốn chung cho mọi shot của cảnh; câu ánh sáng theo giờ (đêm vẫn sáng mặt)",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. Thử 2026-09-27 (#8 cảnh 1, tools/experiments/scene_wide_test.py): 1 ảnh ngang + 4 khung storyboard ngang/hơn 4 frame #7 — "
               "mới 1 cảnh đêm; chưa thử cảnh ngày, chưa qua luồng chính",
    },
    "lip_sync": {
        "label": "Khớp môi: shot cận đánh dấu được Seedance tạo kèm giọng (người dùng chốt 2026-09-26 không dùng sync.so — shot trung/toàn "
                 "không khớp môi, được báo)",
        "verified": False,
        "why": "Kế hoạch V4 GĐ3: chưa thử thật; Seedance không công bố hỗ trợ tiếng Việt — thử 1 shot cận giọng Việt (~$0,60) trước khi tin",
    },
    "seedance_subjects": {
        "label": "S4.7: ảnh gửi Seedance (chế độ chỉ ảnh tham chiếu: khung storyboard + ảnh định danh, shot kỹ năng) đi qua Kho chủ thể "
                 "ClipAI — ảnh KHÔNG đánh dấu, tải một lần theo sha256, gửi asset://; kho từ chối / chưa duyệt xong → gửi ảnh đánh dấu "
                 "như cũ (P2m) và báo",
        "verified": True,       # 08/10 người dùng duyệt: #22 26 lần gửi qua Kho chủ thể, 0 lần lùi về ảnh đánh dấu, 8/9 clip duyệt
        "why": "Đã chạy thật #22 (06–07/10): diag video/subjects ×26 đều info, 0 từ chối / lùi về ảnh đánh dấu, 8/9 clip duyệt đi qua "
               "Kho chủ thể, 2–3 người mỗi shot. Còn mở: nhóm nhiều shot (seedance_ref_groups gộp) chưa chạy"
    },
    "dialogue_take": {
        "label": "Khớp môi (c) — S4.2: shot thoại thấy mặt người nói (cả shot trung / nhiều người) đi trong clip nhóm Seedance 2.5 kèm MỘT "
                 "track giọng của cả nhóm + câu thoại, tên người nói và mốc giây trong prompt (thay 'không khớp môi' khi không có sync.so)",
        "verified": True,       # 01/10 người dùng: S4.2 khớp môi (c) OK (dự án thử #14, 2,82 USD)
        "why": "Đã chạy thật 01/10 (S4.2, dự án #14, 2,82 USD) và người dùng xác nhận OK; A/B S4.6 vòng 2 (29/09, #10): một clip 3 câu / 3 "
               "người nói cho đúng người mở miệng đúng lượt. Còn mở: độ khớp đo 0,39–0,53 < 0,65 (S4.10) — hướng tiếp: mốc 0,1 s / dời giọng",
    },
    "anchor_by_spot": {"fixes_projects": [28], 
        "label": "Ảnh neo theo chỗ đứng: shot ở chỗ KHÁC neo cả cảnh (chỗ có 2+ shot) neo vào shot rộng nhất tại chỗ đó; cảnh báo khi neo chưa duyệt",
        "verified": False,
        "why": "Đ18 việc 2; sửa 14/10 (thử D6 #28: shot 2–5 cùng đỉnh bậc thang không ảnh nào nối nhau) — neo = shot rộng nhất tại chỗ, "
               "shot ở chỗ neo cả cảnh / shot một mình giữ như cũ. Chưa thử thật; đề xuất bật cho tập 2",
    },
    "storyboard_api": {
        "label": "Vẽ ảnh các shot của một cảnh bằng MỘT storyboard Deepix (shot rộng nhất làm neo, cùng ảnh tham chiếu) — cách Weave Canvas",
        "verified": True,       # 08/10 người dùng duyệt: #22 7/9 ảnh duyệt dùng ảnh neo storyboard (cảnh 6 shot + cảnh nhảy 3 shot)
        "why": "Đã chạy thật #22: 7/9 ảnh duyệt có ref storyboard + frame 1 (scene anchor), cảnh 1 (6 shot, có hành động) và cảnh 2 (3"
               " shot nhảy, 2 người); video đạt 08/10. Lỗi 'khoảnh khắc MỚI' đã sửa bằng mã"
    },
    "place_render_refs": {
        "label": "Ảnh render 3D đúng góc máy từng shot (và góc rộng nhất của cảnh) làm ẢNH THAM CHIẾU cho model vẽ cả cảnh — không ghép; "
                 "prompt thêm số đo thật (ống kính, độ cao máy, vị trí đầu–chân nhân vật, đường chân trời, hướng nắng); đo độ khớp nền sau khi vẽ",
        "verified": True,       # 08/10 người dùng duyệt: #22 9/9 ảnh duyệt có render 3D, place_match ×26, nền đúng 11,5 s đoạn nhảy
        "why": "Đã chạy thật trả tiền #22 (06–07/10): 9/9 ảnh duyệt có ref place_render (độ khớp nền 0,35–0,51), video nhảy giữ nền "
               "render 3D suốt 11,5 s; người dùng xác nhận video đạt 08/10. Bài học: prompt cũ / ảnh toàn cảnh ngoài tường có thể "
               "thắng render (feedback_scene_location_change_checklist)"
    },
    "end_frames": {
        "label": "Ảnh khung cuối cho shot có end_state (vẽ thêm 1 ảnh, gửi clip khung đầu + cuối)",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. K1/K2 (kế hoạch tổng K-a): tốn thêm 1 ảnh mỗi shot đổi trạng thái; chưa thử thật Kling end_frame với khung vẽ từ ảnh đầu",
    },
    "ui_v2": {
        "label": "Giao diện v2 kiểu “AI product”: nền tối aurora, thẻ kính, nút gradient + glow, thanh bước viên thuốc, pill trạng thái, chữ gradient (lớp thiết kế dashboard/design/, chạy trên cùng các màn hiện có)",
        "verified": True,
        "why": "2026-10-05 người dùng duyệt (S14.14): ui_v2 thành mặc định, gỡ giao diện cũ. G-a (06/10) đã gỡ luồng cũ ở nhóm nhẹ (Kịch bản "
               "step1_*, Video step4, Theo dõi admin, khung app/ui) — ở đó cờ không còn tác dụng; nhóm nặng (Storyboard, Bản giao, Nhóm, header) "
               "vẫn đọc cờ tới khi G-b gỡ nốt (S13: docs/KE_HOACH_GIAO_DIEN_V2_2026-10-01.md)",
    },
    "storyboard_auto_trust": {
        "label": "Tự bỏ qua cổng duyệt storyboard khi QC đã đủ tin cậy (≥ 90% khớp người trên ≥ 50 ảnh cùng look) và storyboard không có cờ",
        "verified": False,
        "trainee": True,       # 08/10 người dùng: học việc — chạy + ghi quyết định, so với người, không tác động (docs/KE_HOACH_HOC_VIEC_2026-10-08.md)
        "why": "🎓 Học việc từ 08/10 (KIEM_22: kết luận T): chạy bóng, ghi trainee_log để so với người, không đổi phim; bật thật chỉ khi đủ chuẩn và bạn duyệt. W8 (kế hoạch tổng): chưa có đủ ảnh người duyệt cùng look để đo — bật khi số đo đạt và người dùng đồng ý",
    },
    "ai_label": {
        "label": "Nhãn \"nội dung có dùng AI\" góc trên bản dựng (và các bản xuất khổ khác) — cho thị trường bắt buộc nhãn; "
                 "chữ nhãn: AI_LABEL_TEXT",
        "verified": False,
        "why": "S0.14 T6 (người dùng duyệt 2026-09-29): 《微短剧发展管理办法》 (TQ, hiệu lực 2026-09-01) bắt nhãn AI ở vị trí rõ trong mỗi tập; "
               "phát ở VN không bắt buộc — bật khi phát ở nơi cần",
    },
    "speaker_tags": {
        "label": "Prompt Kling có thoại mà chưa nêu tên người nói → code thêm \"X speaks (mouth moving, no sound).\" + người còn lại "
                 "trong khung \"listens, mouth closed\" (tắt: chỉ báo trong chẩn đoán)",
        "verified": False,
        "why": "S0.14 T2 (2026-09-29): tài liệu chính thức Kling 3.0 gắn thoại theo tên nhân vật; người thử thấy Kling chia thoại giữa "
               "nhân vật chưa chuẩn — chưa thử thật câu thêm có làm đúng người mở miệng hơn không (core/speaker_lint.py)",
    },
    "hero_takes": {
        "label": "Shot ⭐ (hero / money_shot) gửi riêng được gen THÊM một bản cùng đầu vào; code đo lớp 0 cả hai, bản ít lỗi hơn được dùng, "
                 "ngang nhau thì giữ cả hai cho bạn chọn ở Bước 4 (ước tính tính 2 bản)",
        "verified": False,
        "why": "S0.14 T4 (người dùng duyệt 2026-09-30): người làm phim AI TQ 'cảnh xịn = gen nhiều rồi chọn'; dồn tiền vào vài shot then "
               "chốt thay vì gen lại mọi shot (core/hero_takes.py) — chưa chạy thật; thêm ≈ 1 USD mỗi shot ⭐ Seedance 2.5 4–5 s",
    },
    "skill_dossier": {
        "label": "Hồ sơ kỹ năng nhân vật (data/skills/<TÊN>): Director đọc các giai đoạn + luật kịch bản; shot có kỹ năng gửi kèm khung "
                 "hình thật của giai đoạn đó làm ảnh tham chiếu + câu tả chuẩn cho ảnh và video + danh sách không được vẽ; báo chữ trái hồ sơ",
        "verified": False,
        "why": "Người dùng 2026-09-30: #8 tả kỹ năng Kenta sai (rút katana, lốc phá tường) vì chỉ có vài dòng chữ. Hồ sơ Kenta xem 30 "
               "khung/giây video chính thức; chưa thử thật — thử trước 1 cảnh ngắn Kenta dùng kỹ năng",
    },
    "seedance_video_edit": {
        "label": "Sửa clip bằng Seedance 2.5 (S4.12, Advanced Edit): gửi clip lỗi làm bản gốc duy nhất + câu sửa một chỗ "
                 "(`omni_reference_task_type: edit`) thay vì sinh lại — adapter ClipAI `submit_video_edit`",
        "verified": False,
        "why": "S4.12 (2026-10-01, docs/KET_QUA_S4_11_S4_12_2026-10-01.md): thử 1 clip #8; tính tiền cả giây clip nguồn + giây ra",
    },
    "director_rewrite": {
        "label": "Đạo diễn viết lại prompt shot trước mỗi lần gen lại (người từ chối kèm ghi chú / QC từ chối kèm lỗi): sửa đúng chỗ gây "
                 "lỗi, lưu bản cũ, thẻ ảnh/clip hiện so sánh cũ/mới + nút dùng lại prompt cũ — thay cho nối 'Fix: …' cuối prompt",
        "verified": False,
        "why": "S14.17 người dùng duyệt 04/10, chưa chạy thật Claude (core/prompt_rewrite.py; Claude lỗi → quay về 'Fix: …' + diag)",
    },
    "change_review_frames": {"fixes_projects": [24], "costs": True, 
        "label": "Tổ rà soát phân biệt khung đầu, quá trình và khung cuối; đếm nhịp chuyển động thay vì câu",
        "verified": False,
        "why": "Đ10.5: ca #24 dựng lại ngoại tuyến, chưa thử thật Claude; mặc định tắt",
    },
    "change_review": {"fixes_projects": [24], "costs": True, 
        "label": "Tổ rà soát tác động: MỌI thay đổi (kịch bản / shot / hồ sơ + ảnh Kho) được bắt bằng trigger; luật code rà các khâu liên "
                 "quan (nền 3D, ảnh neo, câu tả, motion, khung cuối, video, shot kề) + agent Claude rà lệch nghĩa — mỗi thay đổi một lần, "
                 "không trần (người dùng chốt 10/10); mục đỏ chặn gen tốn tiền của shot tới khi sửa / bỏ qua",
        "verified": False,
        "why": "10/10 sau QC #24 (đổi máy mà ảnh neo / storyboard / câu tả cũ vẫn dùng): người dùng yêu cầu, chưa chạy thật",
    },
    "change_review_motion": {"fixes_projects": [27], "costs": True, 
        "label": "Tổ rà soát rà cả lần SỬA MOTION PROMPT (Bước 3 / viết lại): mục Claude cũ của shot được rà lại theo bản mới (đúng → tự "
                 "đóng, hết giữ gen); mỗi lần sửa một lời gọi Claude qua sổ chi như thay đổi shot. C1 (14/10): cả bản motion Đạo diễn TỰ viết "
                 "lại trước lần gen lại cũng được rà NGAY tại chỗ — xanh gửi luôn (không chờ vòng nền), ĐỎ khâu motion/video → viết lại "
                 "thêm một lần rồi mới giữ; không có Claude → chỉ luật code, không giữ",
        "verified": False,
        "why": "Rà chuỗi 13/10 C4 (#27 shot 16): sửa motion prompt không sinh thay đổi → mục đỏ khâu motion cũ giữ gen mãi tới khi bấm tay. "
               "TỐN TIỀN khi bật: thêm lời gọi Claude mỗi lần prompt đổi; thử CSDL tạm + Claude giả, chưa chạy thật",
    },
    "video_gate": {"fixes_projects": [27], "default_on": True, 
        "label": "Cổng trước gửi video: ảnh khung đầu phải qua kiểm nền 3D (plate_layout không ĐỎ, hoặc bạn bấm Bỏ qua có lý do) và CẢ "
                 "nhóm shot liền mạch đã duyệt ảnh — chưa đủ thì clip GIỮ chờ, có lý do (0 USD)",
        "verified": False,
        "why": "Rà gốc video #27 V7 (13/10): 25 job video bỏ vì ảnh duyệt rồi mới thấy nền sai 3D / shot kề đổi nền sau khi gen; thử "
               "CSDL tạm, chưa chạy thật",
    },
    "qc_framing_cap": {"fixes_projects": [27], "costs": True, "default_on": True, 
        "label": "QC video: so bố cục ảnh khung đầu ↔ khung CUỐI clip (+ render 3D, khung cuối dự kiến); đo máy thấy đổi bố cục → hạ "
                 "trần điểm motion_match / artifacts",
        "verified": False,
        "why": "Rà gốc video #27 V11 (13/10): 912 lùi máy + mặt đồng hồ, 858, 782 chạy tại chỗ đều QC ≥ 0,93. Đổi prompt QC (thêm 1–3 "
               "ảnh/clip) — chưa chạy thật Claude",
    },
    "stage_camera": {
        "label": "Sân khấu 3D v2: shot có máy đã GIẢI từ yêu cầu khung (trường stage_camera — đã đo che khuất bằng tia, người dùng duyệt "
                 "tấm ghép) thì nền 3D dùng đúng máy đó: không tự tính lại theo cỡ/góc, không gom chung setup, không dời máy khi sát tường",
        "verified": False,
        "why": "V4 #24 (09/10): camera 9 shot đã duyệt ở tools/experiments/stage_v2_p24 — chưa render nền thật bằng cờ này",
    },
    "stage_auto": {"fixes_projects": [31], "costs": True,
        "label": "Sân khấu 3D tự động (mọi dự án): mỗi cảnh trên một bối cảnh 3D → Đạo diễn (Claude, sổ chi, ước tính trước) khai dàn "
                 "cảnh người + vật theo tọa độ + yêu cầu khung; code giải máy (chỉ ô đi tới được từ chỗ đứng — không lọt ngoài tường), "
                 "Blender đo → trường stage_camera; vị trí cuối cảnh trước giữ cho cảnh sau cùng sân khấu; shot không đạt sau 2 lượt "
                 "giữ ở cổng nền 3D. Bỏ G0 cho shot đã có máy sân khấu",
        "verified": False,
        "why": "Kế hoạch docs/KE_HOACH_NOI_SAN_KHAU_3D_TU_DONG_2026-10-15.md (người dùng duyệt 15/10, sổ quyết định "
               "stage-auto-plan-2026-10-15): #27–#31 0 shot có stage_camera vì Sân khấu v2 chỉ chạy tay ở #24. Chưa thử thật — "
               "thử 1 cảnh #31 trước (≈ 0,23–0,91 USD Claude)",
    },
    "stage_crew": {"costs": True,
        "label": "Sân khấu 3D CHIA VAI: Đạo diễn dàn cảnh (chỗ đứng theo nhịp + ý đồ) → Quay phim đặt máy (sách dp.md, khai ý đồ / "
                 "che có chủ ý) → Blender đo → bảng đối chiếu 'đã khai ↔ đo được' → Quay phim tự sửa máy / đề nghị dời người (Đạo "
                 "diễn thắng) / giữ lệch có lý do → duyệt chốt. Thay một vai 'Đạo diễn kiêm Quay phim' của stage_auto",
        "verified": False,
        "why": "Kế hoạch docs/KE_HOACH_CHIA_VAI_SAN_KHAU_2026-10-16.md (người dùng duyệt 16/10): #31 shot 10 Kelly chắn xe nôi 237 % "
               "khung, máy chúc trái ý 'nhìn lên' mà bộ kiểm vẫn ĐẠT. Chưa thử — ca thử shot 10 cảnh 3 #31 ngoại tuyến 0 USD; "
               "API: đo chi phí xong người dùng mới quyết bật",
    },
    "stage_handheld_props": {
        "label": "Sân khấu 3D: vũ khí / đồ cầm tay (Kho, có kích thước) vào dàn cảnh như đạo cụ theo nhịp — ẩn tới nhịp xuất hiện, "
                 "nằm chỗ khai hoặc `cam_tay` nhân vật (code tính điểm tay) → Quay phim khai được 'phải thấy súng', Blender đo % thấy. "
                 "Không vẽ vào ảnh nền",
        "verified": False,
        "why": "16/10 #31 cảnh 3: súng SKORP hiện ra ở xe nôi rồi nằm trong tay Kelly — không phải vật dàn cảnh nên shot 11–13 "
               "'thấy rõ súng' chỉ đo được qua xe nôi / Kelly. Bật → đầu vào sân khấu cảnh có vũ khí đổi (lượt API chạy lại tốn "
               "tiền) — bật cho cảnh MỚI, thử ngoại tuyến 0 USD trước",
    },
    "stage_crew_user_approve": {"default_on": True,
        "label": "Sân khấu chia vai: bước DUYỆT CHỐT do người dùng (xem ảnh ghép nhìn từ trên theo nhịp + clay) thay vai Đạo diễn — "
                 "shot giữ ở cổng tới khi duyệt",
        "verified": False,
        "why": "Người dùng 16/10: bước D cho #31 tôi tự duyệt qua ảnh ghép",
    },
    "director_camera_plan": {
        "label": "G0 Đạo diễn đặt máy 3D: mỗi cảnh liên tục một sơ đồ (đạo cụ, chỗ đứng theo nhịp, trục 180°) + bộ 3–4 góc máy dùng "
                 "lại (shot cùng góc + cùng cỡ = cùng máy, render một lần); Đạo diễn xem render nền từng góc (khai quan sát, code kết "
                 "luận, sửa ≤ 2 vòng rồi báo bạn); sau khi vẽ ảnh code so bố cục ảnh với render (chỉ đánh dấu)",
        "verified": False,
        "why": "G0 (người dùng 09/10, docs/KE_HOACH_DAT_MAY_3D_2026-10-09.md): chưa chạy thật — thử trên #24 (Claude ≈ vài cent: sơ đồ "
               "+ duyệt render, báo giá trước) rồi mới bật",
    },
    "shot_intent": {
        "label": "K1a Đạo diễn điền bảng ý đồ shot (BYĐ): mỗi shot thêm khối `byd` (thành phần, tư thế + vùng che, dạng, máy, nơi "
                 "chốn) — code kiểm, sai thì gửi lỗi cho Đạo diễn sửa ≤ 2 vòng (lượt Claude nhỏ), còn sai → VÀNG có lý do; lưu "
                 "scenes.data.byd cho lớp kiểm nhận diện / chạy khô đọc",
        "verified": False,
        "why": "K1a (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md, A14/A19/A29): mới thử bằng Claude giả lập — chưa chạy Đạo diễn thật "
               "có BYĐ (thêm token ra mỗi shot + tối đa 2 lượt sửa, ước tính hiện ở nút Director)",
    },
    "video_pregen": {
        "label": "K3 lớp code kiểm video TRƯỚC gen (0 USD): khung đầu = ảnh đã duyệt hiện hành (job + sha), khung cuối đã duyệt + khớp "
                 "ket_thuc BYĐ, thời lượng hợp model + thoại, video/ảnh tham chiếu theo luật model, motion đủ đầu–đỉnh–cuối + chuyển "
                 "động máy enum, vân tay gói khác lần gen trước (N10) — ĐỎ thì giữ job chờ người, VÀNG gửi + ghi ⚙ Chẩn đoán",
        "verified": False,
        "why": "K3 (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.4b, A17): mới thử bằng CSDL tạm + provider giả — chưa chạy trên "
               "dự án thật (đo báo nhầm trên #24 trước khi bật)",
    },
    "murch_knowledge": {
        "label": "Bộ não prompt Đợt 2: Director + motion đọc thang ưu tiên cảm xúc (Murch), motion đọc kỷ luật I2V (giữ trước, hỏng thì "
                 "giảm chuyển động, check_flags gọi tên rủi ro), Director đọc phương pháp âm thanh; người xem lần đầu chấm thêm cam_xuc",
        "verified": False,
        "why": "S14.20 (05/10): chỉ thêm tài liệu vào prompt (≈ +9 nghìn ký tự mỗi lần chạy Director/motion); chưa so prompt Bước 3 "
               "thật trên dự án cũ (nghiệm thu Đợt 2 cần Claude thật)",
    },
    "auto_voice_cast": {
        "label": "Tự gắn giọng tiếng Việt từ phân tích cảnh: Director ghi giới tính/tuổi/tính cách vai có thoại (cùng lượt Claude), luật "
                 "0 USD gắn giọng data/voices_vi.json (vai chính giọng đầu), quá 2 vai cùng giới → dùng lại giọng + biến thể cao độ "
                 "±2–3 nửa cung (ffmpeg sau TTS) + tốc độ ClipAI; không ghi đè giọng người dùng chọn",
        "verified": False,
        "why": "S14.26 (05/10): chưa chạy Director thật với khối voice_traits; biến thể cao độ ffmpeg chưa nghe thử trên 4 giọng VN "
               "(giọng nam +3 nửa cung có thể nghe méo) — bật để thử ở dự án mới (core/voice_casting.py)",
    },
    "asset_checklist": {
        "label": "Bảng kê tài nguyên trước Director: một lượt Claude rẻ (không ảnh) đọc kịch bản, kê nhân vật/nơi/đồ vật/vũ khí/thú "
                 "cưng/trang phục cần thấy, ghép với Kho (code kiểm lại id + loại) → bảng ✅ đã gắn / có trong Kho / ⚠️ thiếu, gắn "
                 "nhanh trước khi trả tiền cho Director",
        "verified": False,
        "why": "S14.23 (05/10): chưa chạy Claude thật; nghiệm thu = 2 kịch bản thật (Kho đủ / Kho thiếu) — báo đúng cái thiếu, "
               "không báo nhầm cái đã có (core/asset_checklist.py, prompts/27_asset_checklist.md)",
    },
    "kelly_knowledge": {
        "label": "Tri thức kênh Kelly (GỢI Ý trộn được): Biên kịch đọc 4 khuôn kịch bản dựng chắc được + kỹ thuật né + hook/nhịp/cú chốt; "
                 "Đạo diễn, Quay phim, Biên tập (Dựng) mỗi vai đọc một tài liệu ngắn",
        "verified": False,
        "why": "S14.34 (05/10): mẫu MỘT kênh, 40 clip (độ tin tối đa 'có thể'); chỉ thêm ≈ 3,5 nghìn ký tự mỗi vai; chưa so kịch bản/shot "
               "thật khi bật (cần bản ghi Claude thật S14.34 bước 3)",
    },
    "kld_lessons_prompts": {"fixes_projects": [22], "costs": True, 
        "label": "Bài học #22 Khủng Long Đỏ vào prompt: Đạo diễn (phụ kiện trang phục giữ trạng thái, chữ nhiều nghĩa tra ảnh Kho, động tác "
                 "theo video mẫu, soát thoại kịch bản dán tay, dữ liệu khớp môi), Quay phim (dữ liệu chuyển động #22), Motion (ngoại lệ "
                 "ref-only, shot có người cần hành động thấy được), QC clip (issues tả trạng thái đúng, look_drift ref-only = đặc tính model)",
        "verified": False,
        "why": "KLD-8/9/12/14/15/25 08/10, chờ dự án mới đo (độ tin 1 dự án #22; docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md mục 4)",
    },
    "p24_lessons": {"fixes_projects": [24], "costs": True, 
        "label": "Bài học duyệt ảnh #24 (11/10) vào Đạo diễn / Quay phim (prompt 17, 20, 29): thấy-được theo độ cao máy, vị trí sau "
                 "động tác di chuyển (điểm cuối `den`), giữ bố cục shot đã duyệt, phủ đủ nhịp + chi tiết của ref emote, cỡ khung chứa "
                 "biên độ, hiệu ứng màn hình để hậu kỳ; Sân khấu 3D v3 gửi lại Đạo diễn cả mục VÀNG 'nhịp di chuyển' (trong 2 lượt đã ước tính)",
        "verified": False,
        "why": "11/10 người dùng soi ảnh #24 (shot 5 miệng giếng, 7/9/10 yêu nữ sát thành 0,25 m, shot 8 ref khóc 3 nhịp); kiểm VÀNG bằng "
               "code (core/shot_lessons, prompt_formula) chạy không cần cờ — cờ này chỉ thêm cách nghĩ vào prompt; chờ dự án mới đo",
    },
    "lesson_judge": {
        "label": "Agent chấm bài học (CHẾ ĐỘ BÓNG): Claude chấm mỗi bài học theo 6 tiêu chí (AI ghi khoản trừ + bằng chứng, code tính "
                 "điểm), ghi vào lịch sử duyệt để so với người — KHÔNG tự duyệt, không đổi bài học hay kiến thức nào",
        "verified": False,
        "why": "S14.24 (06/10): mới thử bằng MockJudge; ngưỡng 0,85 mượn QC ảnh. Bật tự duyệt (cờ sau) chỉ khi ≥ 10 cặp agent↔người, "
               "đồng thuận ≥ 90 %, agent-lỏng-quá = 0 (core/lesson_judge.py agreement())",
    },
    "palette_check": {
        "label": "Màu chính nhân vật đo bằng code (0 USD): so sắc màu vùng thân (đã cân trắng) với ảnh tham chiếu đã duyệt và với các "
                 "khung cùng cảnh; bỏ đêm / hoàng hôn / cận mặt / trang phục riêng — ghi chú 'lệch màu trang phục' cho người xem, "
                 "không tự từ chối / vẽ lại",
        "verified": False,
        "why": "S14.51 (06/10, ý từ tài liệu Prompt Spider): mới thử trên ảnh tổng hợp (sáng tối hơn 45 % bản đầu báo nhầm, bản nới thì "
               "không); ngưỡng hue ±30° / giữ 25 % chưa hiệu chỉnh trên ảnh thật — bật khi ~20 khung #8 cho báo nhầm ≤ 10 %; vùng thân "
               "ước theo hộp mặt — dáng nghiêng có thể đo sai",
    },
    "risk_tags": {
        "label": "Bài học lỗi: tách tag 'motion' thành 6 trục rủi ro I2V (face_morph, body_deform, wardrobe_drift, background_drift, "
                 "motion_overload, text_logo_corrupt) + identity/physics/lipsync/audio; lỗi không gán được tag hiện ở 'Chưa phân loại' + diag",
        "verified": False,
        "why": "S14.20 (05/10): bảng lessons còn 0 bài học, từ khóa chưa đo trên lỗi thật; tag hiếm hơn → có thể không đủ ngưỡng 3 lần / "
               "2 dự án (chưa hạ ngưỡng, chờ Đợt 5 có phân bố thật)",
    },
    "feedback_to_mistakes": {
        "label": "Bài học lỗi: góp ý của bạn (Bước 5 'dùng được chứ?' / góp ý cảnh, chấm ≤ 2/5, khâu Đạo diễn / Ảnh / Chuyển động, "
                 "viết ≥ 15 ký tự) được ghi thành lỗi để gom bài học (vẫn cần 3 lần / 2 dự án + bạn duyệt)",
        "verified": False,
        "why": "S14.25 (06/10, Đợt 6a): chưa có góp ý thật nào qua luồng này; chưa đo góp ý của người có khớp từ khóa loại lỗi "
               "(lỗi không khớp → 'Chưa phân loại' + diag)",
    },
    "outfit_strip_model": {"fixes_projects": [22], 
        "label": "Ảnh OUTFIT có người mẫu: prompt ảnh + video thêm câu 'bỏ tóc/mặt/dáng của người mẫu trong ảnh trang phục; phụ kiện "
                 "(mũ, khẩu trang…) đeo đúng như ảnh suốt clip'",
        "verified": False,
        "why": "KLD-7 (người dùng duyệt 08/10, #22 Khủng Long Đỏ): tóc Kelly KL lẫn màu bạc của người mẫu trong ảnh trang phục (544/545 bị "
               "loại, ≈ 2,8 USD) dù prompt đã có 'chỉ lấy quần áo'. Câu mới đổi đầu ra model trả tiền và chưa thử — cần thử 1 shot rẻ "
               "(ảnh + clip 720p) trước khi bật",
    },
    "asset_english_names": {"label": "Tên tiếng Anh khi tạo Kho + cảnh báo vật/style chưa có ảnh mẫu đúng tên", "verified": False,
        "why": "Đ17v3 #27 torii/Nỏ: kiểm tên bằng aliases hiện có, 0 USD; chưa nghiệm thu thật, chỉ bật riêng"},
    "film_grammar_check": {"label": "Kiểm hướng nhìn, 30°, lead room/headroom theo sân khấu (VÀNG, 0 USD)", "verified": False,
        "why": "Đ11v4: chưa hiệu chỉnh trên ca thật; thiếu tọa độ/hướng mặt báo VÀNG; bật riêng"},
    "camera_match_qc": {"label": "So ảnh/khung đầu-cuối clip với máy bằng công cụ local (VÀNG, 0 USD)", "verified": False,
        "why": "Đ11v4: cỡ mặt/mắt/chân trời, ngưỡng chưa hiệu chỉnh; không model local thì VÀNG; bật riêng"},
    "continuity_layout": {"fixes_projects": [27], "label": "Kiểm nhất quán hướng đi + bố cục giữa shot (VÀNG, báo cáo Đạo diễn)", "verified": False,
        "why": "Hộp thư 12/10 15:51 (#27): hướng đi ghi trong image_prompt/blocking không được kiểm; đi ngược chiều vào cổng, cổng/tường đổi bên, đồng đội nằm biến mất"},
    "ambient_motion": {"fixes_projects": [24], "costs": True, 
        "label": "Lớp chuyển động nền nhẹ theo bối cảnh, thời tiết và giờ; thiếu thì VÀNG",
        "verified": False,
        "why": "Đ10.6 ca #24 shot 9 dựng lại ngoại tuyến; chưa thử thật, mặc định tắt",
    },
    "prompt_formula": {
        "label": "Công thức prompt (F1-A): sau mỗi lượt Đạo diễn / mỗi lần lưu prompt, code kiểm phần bắt buộc của prompt ảnh + motion, "
                 "mâu thuẫn (khung ↔ tư thế, luật người ↔ quái, máy tĩnh ↔ đẩy), chi tiết ghê không tiết chế, vật lao sát người không "
                 "đường đi, viết chồng thêm, cùng món đồ khác màu giữa shot → scenes.data formula_check + ⚙ Chẩn đoán (0 USD)",
        "verified": True,       # 09/10 người dùng duyệt công thức F0 (docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md) — chỉ đọc + ghi, chưa chặn gửi
        "why": "Người dùng duyệt F0 09/10; kiểm bằng câu thật #22/#24 (tests/test_prompt_formula.py). Chỉ ghi kết quả, không đổi thứ gửi "
               "model; phiên chính nối red_issues vào _blocked sau",
    },
    "project_prop_lock": {"fixes_projects": [27], 
        "label": "Khóa đạo cụ dự án: shot chỉ nói 'assault rifle' / 'glue wall' chung chung → prompt ảnh nêu đích danh món Kho đã gắn "
                 "(SKORP, Bom keo…) + mô tả + ảnh tham chiếu đúng dạng (ảnh có variant chỉ gửi khi shot nhắc variant); nhiều món cùng "
                 "loại → VÀNG, không đoán (0 USD)",
        "verified": False,
        "why": "Lỗi thật #27 (12/10): Kho gắn SKORP + Bom keo mà ảnh ra AK / tường keo mỗi shot một kiểu. Chưa chạy thật — bật rồi "
               "gen 1 shot rẻ để so",
    },
    "skill_object_guard": {"fixes_projects": [27], 
        "label": "Vật kỹ năng (tường keo…): prompt ảnh + motion bỏ từ dễ hiểu sai (elevator/door/thang máy/cửa) → tả hình dạng/chất "
                 "liệu + câu cấm; tường XUẤT HIỆN LUÔN khi ném (chữ tả quá trình → 'already standing at full height'); skin = hoa "
                 "văn theo ảnh DẠNG TRIỂN KHAI (không 'metal-panel'); Kho đưa Đạo diễn kèm lưu ý; shot ném keo → VÀNG gợi ý GHÉP "
                 "code cắt cứng, Kho thiếu ảnh dạng triển khai → VÀNG 'skin tả bằng chữ' (0 USD)",
        "verified": False,
        "why": "Lỗi hệ thống 3 #27 (13/10): skin Gloowall OB55 'cửa thang máy' → model vẽ thang máy thật (cửa mở, nhìn xuyên, người "
               "đứng trong), shot 16 gen 6 lần hỏng, giao bằng ghép code. Chưa gen thật với chữ mới",
    },
    "ref_mark_off_face": {"fixes_projects": [27], 
        "label": "Ảnh tham chiếu đánh dấu gửi Seedance: dấu '+' đỏ đặt ở GÓC ảnh (không trên mặt) + luôn kèm câu cấm dấu/chữ thập trên "
                 "mặt, đầu, người; không bao giờ dấu trên mắt (kể cả ảnh khung đầu, kể cả sau khi bị từ chối — đi bậc tuyến) (0 USD)",
        "verified": False,
        "why": "Lỗi hệ thống 4 #27 (13/10): Kho chủ thể đầy → gửi ảnh đánh dấu cũ (dấu + trên mắt) → Seedance 2.5 chép dấu lên mặt "
               "Kelly shot 8–9, 18. Kiểu corner_plus chưa thử qua bộ lọc người thật",
    },
    "plate_view_sentence": {"fixes_projects": [27], "default_on": True, 
        "label": "Prompt video Seedance: ảnh khung đầu quyết bố cục + khoảng cách máy; render 3D chỉ là tham chiếu kiến trúc (không còn "
                 "câu 'render quyết kiến trúc'); render khác góc máy → nói rõ 'góc máy khác' (đo OpenCV, 0 USD)",
        "verified": False,
        "why": "Rà gốc video #27 V1 (13/10, shot 17 job 858/912): plate máy sát đất ↔ khung đầu máy cao sau lưng Kelly; câu 'PLACE "
               "render decides architecture' → Seedance lùi máy + vẽ mặt đồng hồ. Chưa gen thật với câu mới",
    },
    "group_keep_approved": {"fixes_projects": [27], "default_on": True, 
        "label": "Nhóm Seedance: shot NGƯỜI đã duyệt (còn mới) không bị gen lại theo bạn cùng nhóm — nhóm có shot đã duyệt lẫn shot "
                 "chưa đạt thì mỗi shot đi riêng (0 USD)",
        "verified": False,
        "why": "Rà gốc video #27 V8 (13/10, G3): (5,6) 788→879 shot 6 đã duyệt bị gen lại vì shot 5; (10,11) ba vòng. Chưa chạy thật",
    },
    "motion_consistency_lint": {"fixes_projects": [27], "default_on": True, 
        "label": "Kiểm trước gửi: diễn xuất có động tác của shot kề (lấn shot), số nhịp hành động > số giây → VÀNG có lý do (0 USD)",
        "verified": False,
        "why": "Rà gốc video #27 V9 (13/10, G11): s15 diễn xuất 'ném' (của shot 16), s6 'dừng, ngước lên' (shot 7), s20 1,5 s ba nhịp "
               "→ 859 không tới trạng thái cuối. Chỉ cảnh báo, chưa so với người",
    },
    "character_state_lock": {"fixes_projects": [27], "default_on": True, 
        "label": "Trạng thái nhân vật chỉ có trong chữ (vd Kelly bóng mờ) → motion code viết thêm câu giữ trạng thái cả shot + VÀNG "
                 "thiếu ảnh trạng thái (0 USD)",
        "verified": False,
        "why": "Rà gốc video #27 V10 (13/10, G10): ảnh danh tính Kelly dạng thường, chữ 'bóng mờ' → cuối shot 9 mất bóng mờ. Chưa gen thật",
    },
    "ref_rule_early": {"fixes_projects": [27], "default_on": True, 
        "label": "Ảnh tham chiếu sai luật ClipAI (tỉ lệ 0,4–2,5, cạnh ≥ 300 px): đệm nền trơn khi Kho không có ảnh khác + ĐỎ trước khi "
                 "xếp / báo giá thay vì hỏng lúc gửi (0 USD)",
        "verified": False,
        "why": "Rà gốc video #27 V13 (13/10, G13): shot 17 job 798 ảnh 488×1280 (0,38) chỉ bị bắt lúc gửi. Chưa gửi thật bản đệm",
    },
    "plate_anchored_image": {"fixes_projects": [27], 
        "label": "Ảnh vẽ bám render 3D: câu NỀN của prompt ảnh sinh từ plate (mốc, khoảng cách, chân trời) thay chữ nền tự do của Đạo "
                 "diễn (bỏ → VÀNG), render là ẢNH 1 + câu 'giữ đúng nền ảnh 1', kiểm sau vẽ bằng code → ĐỎ/VÀNG (0 USD)",
        "verified": False,
        "why": "Lỗi hệ thống 1 sau #27 tập 1 (13/10, shot 17/21 job 893/744): plate đứng thứ 7 trong 9 ảnh, chữ Đạo diễn tả 'nhà mái đỏ, "
               "tường chắn' → model vẽ theo chữ. Chưa chạy thật — bật rồi gen lại 1 shot rẻ, so với render",
    },
    "qc_sequence_logic": {"costs": True,
        "label": "QC logic CẢ CHUỖI clip theo thứ tự truyện: mỗi nhóm cảnh một tờ ghép (khung đầu/giữa/cuối mỗi shot) + câu hành động → "
                 "Claude kiểm vị trí/độ cao nền giữa shot liền nhau, nhân–quả (địch đã gục), hành động kịch bản nhắc tới có shot thể "
                 "hiện, thứ tự hợp lý (nút ở Bước 4, Claude ≈ vài cent / nhóm)",
        "verified": False,
        "why": "#31 19/10 người dùng chỉ ra lỗi GIỮA các shot mà QC từng clip không thấy: nhặt súng trên thềm cỏ nâng cao (S10/11/13) "
               "khác mặt đất S8; S18 địch đã gục vẫn xả súng; S19 nói 'vừa hạ gục Xúc Tu Đỏ' không có shot. Chưa chạy thật (ước ~0,1 USD #31)",
    },
    "two_tier_quality": {
        "label": "Video 2 bậc chất lượng: MỌI shot gen NHÁP Seedance 2.5 480p trước (gen lại ≤ 2), người duyệt rồi 'Gen bản cao' "
                 "(Seedance 2.5 nâng từ nháp, model khác gửi lại ở bậc cao; gen lại ≤ 1); gen thẳng chỉ khi người chọn (13/10). Bỏ qua 'Thử rẻ'",
        "verified": False,
        "why": "N1 (người dùng chốt 08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 5a): bản cuối draft_task 1080p "
               "chưa chạy thật lần nào (≈ 2,1 USD / 4 s ước tính) — phải chạy thật 1 lần (hỏi giá trước) rồi mới bật",
    },
}


# ---- 🧪 Tính năng thử (rà soát 01/10, đợt 2): the person picks a preset / flips one flag on screen instead of editing dashboard.env ----
# preset "custom" (default, nothing saved) = the old rule: FEATURE_<NAME> env, else `verified` / `default_on`.
# "stable" = only the flags that passed a real test (`verified`); "experimental" = every flag but the ones that did harm.
# A per-flag choice made on screen wins over the preset and the env. Stored in data/feature_settings.json (this computer, not in git).
# 🔒 15/10 (người dùng: "những cờ nào đã được kiểm chứng thì mặc định bật, không để bị tắt nữa"): `verified: True` = KHÓA BẬT — on in
# every preset, whatever the 🧪 choice or FEATURE_<NAME>=0 says (an old OFF there is ignored and SAID by `locked_off_ignored()`);
# save_settings refuses to set it off / học việc. The only way to turn a verified flag off is the code: drop `verified` or move it
# into REMOVED. A locked flag that needs another (REQUIRES) does nothing while that one is off — tests/test_feature_settings names it.
PRESETS = {"custom": "Theo dashboard.env (hiện tại)", "stable": "Ổn định — chỉ tính năng đã thử thật",
           "experimental": "Thử nghiệm — bật hết các tính năng chưa thử thật"}
# GĐ6 / rà soát 01/10 mục 3.2 named 3 harmful flags; S14.9 (Gói L, 06/10) removed them from the code — nothing left to keep off here.
HARMFUL: tuple = ()
# Flags that spend money with nobody clicking (a background loop sends paid jobs): the "experimental" preset never turns them on —
# only a choice on 🧪 or FEATURE_<NAME>=1 does (rà quy ước 7, 12/10: a machine on "experimental" would start paying the moment it pulls).
OPT_IN_ONLY: tuple = ("motion_sfx", "anchor_by_spot", "continuity_from_ui", "blockout_clay_sheet", "director_blockout", "auto_send_self_fix", "qc_observe_enum", "shot_popup", "bg_autoqc", "asset_english_names", "film_grammar_check", "camera_match_qc", "stage_crew",
                      "stage_handheld_props")
# S14.9 (Gói L, 06/10, người dùng: cờ gây hại phải bị xóa, không chỉ tắt): flags taken out of the code — the code now always does
# what it did with the flag OFF. An old choice in data/feature_settings.json or a FEATURE_<NAME> line in dashboard.env naming one is
# ignored (said by `removed_in_use()`, never an error). Reasons + dates: docs/TODO_LICH_SU.md.
REMOVED: Dict[str, str] = {
    "layout_to_model": "GĐ6: model chép góc máy từ trên cao + người tí hon của ảnh bố cục ghép",
    "chain_previous_auto": "GĐ6: nối ảnh shot trước bất kể cỡ cảnh → shot cận kéo theo bố cục toàn cảnh",
    "setcheck_autofix": "GĐ6: QC đồng bộ chuẩn theo số đông, sửa sai người rồi tự trả tiền gen lại",
    "location_plates": "Ghép phông xanh lên nền 3D: tạm ngưng từ 27/09 (#8), thay bằng place_render_refs / scene_establishing",
    "closeup_start_frame": ("18/10 người dùng (#31): gỡ — cận thấy mặt đi Kling từ khung đầu trái quyết định video-route-2026-10-13 (video "
                            "hết Seedance 2.5, Kling chỉ đường lùi); A/B S4.6 01/10 (docs/KET_QUA_S4_2_S4_6_2026-10-01.md) đã kết luận khung "
                            "đầu KHÔNG giữ mặt tốt hơn chỉ-ảnh-tham-chiếu, biểu cảm mạnh còn kém; Kling mất gộp nhóm, cần vẽ khung cuối; "
                            "cờ vẫn bật ở máy chính nên 7 shot cận #31 lọt sang Kling (G24, docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md)"),
}
_SETTINGS = {"stamp": None, "path": None, "data": None}


def settings_path() -> str:
    return os.environ.get("FEATURE_SETTINGS_FILE") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                                   "data", "feature_settings.json")


MODES = ("on", "trainee", "off")
_YES = ("1", "true", "on", "yes")
_NO = ("0", "false", "off", "no")


def trainee_list() -> list:
    """Flags that have the 🎓 học việc mode (literal `"trainee": True` in FEATURES — devsys reads it with ast)."""
    return [k for k, v in FEATURES.items() if v.get("trainee")]


def settings() -> Dict:
    """{"preset": custom|stable|experimental, "flags": {name: bool}, "modes": {name: "trainee"}} — re-read when the file changes.
    Học việc (08/10) lives in its own key "modes": code that reads "flags" with bool(v) must never see "trainee" (it would be ON)."""
    path = settings_path()
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        stamp = None
    if _SETTINGS["stamp"] != stamp or _SETTINGS["path"] != path:
        data = {"preset": "custom", "flags": {}, "modes": {}}
        if stamp is not None:
            try:
                import json
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                if raw.get("preset") in PRESETS:
                    data["preset"] = raw["preset"]
                data["flags"] = {k: bool(v) for k, v in (raw.get("flags") or {}).items() if k in FEATURES}
                data["modes"] = {k: "trainee" for k, v in (raw.get("modes") or {}).items()
                                 if k in FEATURES and FEATURES[k].get("trainee") and v == "trainee" and k not in data["flags"]}
                data["dropped"] = sorted(k for k in (raw.get("flags") or {}) if k in REMOVED)   # S14.9: ignored, said
            except (OSError, ValueError, AttributeError):
                pass
        _SETTINGS.update(stamp=stamp, path=path, data=data)
    return _SETTINGS["data"]


def save_settings(preset: str = None, flags: Dict = None, modes: Dict = None) -> Dict:
    """Write the choice (flags: {name: True|False|None}; None removes the single choice; modes: {name: "on"|"trainee"|"off"|None} —
    "on"/"off" are stored in "flags" as before, "trainee" only in "modes" and only for a flag that has that mode). Atomic.
    🔒 15/10: OFF / học việc for a `verified` flag raises ValueError (nothing is written); True / None for it is harmless. Callers that
    save many flags at once leave locked flags out (dashboard/header.py, core/before_run.enable_fix_flags only saves True)."""
    import json
    cur = {"preset": settings()["preset"], "flags": dict(settings()["flags"]), "modes": dict(settings().get("modes") or {})}
    if baseline_active() and preset not in ("stable", "experimental"):
        # M7.2 (rà C-M72): lần lưu ĐẦU trên máy theo baseline → gieo baseline (đã bảo vệ) vào tệp, không thì baseline thôi áp và mọi cờ
        # khác "rơi" về mặc định không báo. C-M72-FIX: chỉ gieo cờ ĐANG theo baseline (env FEATURE_X thắng — không đè thành tệp 🧪);
        # chọn preset Ổn định / Thử nghiệm ở lần đầu = chọn theo preset, không gieo.
        for k in FEATURES:
            b = baseline_state(k)
            if b is None or locked(k) or b == default_state(k) or source(k) != "baseline":
                continue
            if b == "trainee":
                cur["modes"][k] = "trainee"
            else:
                cur["flags"][k] = b == "on"
    if preset is not None:
        if preset not in PRESETS:
            raise ValueError(f"preset không có: {preset}")
        cur["preset"] = preset
    for k, v in (flags or {}).items():   # 🔒 checked for every name before anything is written (nothing half-saved)
        if k in FEATURES and v is not None and not v and locked(k):
            raise _locked_error(k)
    for k, v in (modes or {}).items():
        if k in FEATURES and v in ("off", "trainee") and locked(k):
            raise _locked_error(k)
    for k, v in (flags or {}).items():
        if k in REMOVED:                  # S14.9: an old page / script still naming a removed flag — nothing to set
            continue
        if k not in FEATURES:
            raise ValueError(f"không có tính năng {k}")
        cur["modes"].pop(k, None)
        if v is None:
            cur["flags"].pop(k, None)
        else:
            cur["flags"][k] = bool(v)
    for k, v in (modes or {}).items():
        if k in REMOVED:
            continue
        if k not in FEATURES:
            raise ValueError(f"không có tính năng {k}")
        if v is not None and v not in MODES:
            raise ValueError(f"chế độ không có: {v}")
        if v == "trainee" and not FEATURES[k].get("trainee"):
            raise ValueError(f"'{k}' không có chế độ học việc")
        cur["flags"].pop(k, None)
        cur["modes"].pop(k, None)
        if v == "trainee":
            cur["modes"][k] = "trainee"
        elif v is not None:
            cur["flags"][k] = v == "on"
    if not cur["modes"]:
        cur.pop("modes")
    path = settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    _SETTINGS["stamp"] = object()         # two saves in one clock tick keep the same mtime: never serve the old cache (test flake 04/10)
    return settings()


def _env(name: str) -> str:
    return os.environ.get("FEATURE_" + name.upper(), "").strip().lower()


# ---- V3.1 M7.2 (sổ v31-ep-k4-k6-flag-baseline-reset-2026-10-21, docs/BANG_CHUNG_CHOT_CO_2026-10-21.md mục 3 thứ tự F) ------------------
# data/flag_baseline.json (trong git) = trạng thái cờ sản xuất, chụp bằng `py -m core.features --baseline-capture` trên máy chính. Chỉ là
# "hạt giống" cho máy CHƯA có data/feature_settings.json (worktree / cloud / Codex) — không bao giờ ghi đè lựa chọn của máy đã cấu hình.
# Đứng sau env, trước mặc định; bảo vệ: không bật cờ `costs` / OPT_IN_ONLY, cờ học việc tối đa trainee. Bộ test tắt (FEATURE_BASELINE_FILE
# rỗng — tests/__init__.py); FEATURE_BASELINE=0 tắt ở mọi máy.
_BASELINE = {"stamp": None, "path": None, "data": None, "problem": None}


def baseline_path() -> str:
    """"" = baseline tắt (FEATURE_BASELINE_FILE đặt rỗng)."""
    env = os.environ.get("FEATURE_BASELINE_FILE")
    if env is not None:
        return env
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "flag_baseline.json")


def baseline() -> Dict:
    """{"flags": {name: "on"|"trainee"|"off"}, ...} của tệp baseline ({} khi không có / tắt). Tệp hỏng → {} + baseline_problems()."""
    path = baseline_path()
    try:
        stamp = os.stat(path).st_mtime_ns if path else None
    except OSError:
        stamp = None
    if _BASELINE["stamp"] != stamp or _BASELINE["path"] != path:
        data, problem = {}, None
        if stamp is not None:
            try:
                import json
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                flags = raw.get("flags") if isinstance(raw, dict) else None
                if not isinstance(flags, dict):
                    raise ValueError("thiếu bảng flags")
                data = dict(raw, flags={k: ("on" if v is True else "off" if v is False else str(v))
                                        for k, v in flags.items() if k in FEATURES})
            except (OSError, ValueError, AttributeError) as e:
                problem = f"baseline cờ {path} hỏng ({type(e).__name__}: {e}) — bỏ qua, máy dùng mặc định code"
        _BASELINE.update(stamp=stamp, path=path, data=data, problem=problem)
    return _BASELINE["data"]


def baseline_problems() -> List[str]:
    baseline()
    return [_BASELINE["problem"]] if _BASELINE["problem"] else []


def baseline_active() -> bool:
    """Baseline có hiệu lực: không phải bộ test, không FEATURE_BASELINE=0, có tệp baseline, và máy CHƯA có tệp 🧪 (thứ tự F)."""
    if _TEST_BYPASS or os.environ.get("FEATURE_BASELINE", "").strip().lower() in _NO or not baseline_path():
        return False
    settings()                                        # đã stat tệp 🧪 (cache theo mtime) — không stat thêm mỗi lần đọc cờ
    if _SETTINGS["stamp"] is not None:
        return False
    return bool(baseline().get("flags"))


def _paid(name: str) -> bool:
    """Cờ tốn tiền: `costs`, OPT_IN_ONLY, hoặc trong before_run.PAID_FLAGS (rà C-M72: director_rewrite / director_camera_plan /
    two_tier_quality / stage_camera không có `costs` nhưng đổi lời gọi trả tiền)."""
    if FEATURES[name].get("costs") or name in OPT_IN_ONLY:
        return True
    from . import before_run
    return name in before_run.PAID_FLAGS


def _guarded(name: str, want: Optional[str]) -> Optional[str]:
    """Bảo vệ của baseline: không bao giờ BẬT (kể cả học việc) cờ tốn tiền / OPT_IN_ONLY; cờ học việc tối đa trainee; giá trị lạ / học
    việc cho cờ không có học việc → None (không nói gì, rơi về mặc định)."""
    meta = FEATURES[name]
    if want not in MODES:
        return None
    if want in ("on", "trainee") and _paid(name):
        return None
    if meta.get("trainee") and want == "on":
        return "trainee"
    if want == "trainee" and not meta.get("trainee"):
        return None
    return want


def baseline_state(name: str) -> Optional[str]:
    """Trạng thái baseline (đã qua bảo vệ) của cờ, None khi baseline không áp / không nói về cờ này."""
    if not baseline_active():
        return None
    return _guarded(name, baseline()["flags"].get(name))


LOCKED_TEXT = "🔒 đã kiểm chứng — khóa bật (chỉ sửa code mới tắt)"


# Set to True ONLY by tests/__init__.py (the older tests that describe the code path with a verified flag OFF through
# FEATURE_<NAME>=0 / flags_off) — a module attribute, so no dashboard.env line or environment variable can unlock a real run.
_TEST_BYPASS = False


def _lock_bypassed() -> bool:
    return _TEST_BYPASS is True


def locked(name: str) -> bool:
    """🔒 15/10: a `verified` flag (not removed) is always ON — no 🧪 choice, preset or FEATURE_<NAME> turns it off."""
    return name not in REMOVED and name in FEATURES and bool(FEATURES[name]["verified"]) and not _lock_bypassed()


def _locked_error(name: str) -> ValueError:
    return ValueError(f"'{name}' đã kiểm chứng — khóa BẬT; muốn tắt phải sửa code: bỏ verified hoặc đưa vào REMOVED "
                      f"(core/features.py)")


def locked_off_ignored() -> Dict[str, str]:
    """{locked flag: Vietnamese note} for every 🔒 flag an old choice still tries to turn off — a "flags": false / "modes" entry in
    data/feature_settings.json or a FEATURE_<NAME>=0 (or =trainee) line. Ignored (the flag stays on), said in 🧪 and --report."""
    out = {}
    s = settings()
    for k in FEATURES:
        if not locked(k):
            continue
        why = []
        if s["flags"].get(k) is False:
            why.append("lựa chọn TẮT cũ trong data/feature_settings.json")
        if k in (s.get("modes") or {}):
            why.append("chế độ học việc cũ trong data/feature_settings.json")
        env = _env(k)
        if env in _NO or env == "trainee":
            why.append(f"dòng FEATURE_{k.upper()}={env} (dashboard.env / môi trường)")
        if why:
            out[k] = f"'{k}' {LOCKED_TEXT} — bỏ qua " + " và ".join(why) + "; cờ vẫn BẬT"
    return out


def state(name: str) -> str:
    return _state(name, settings())


def _state(name: str, s: Dict) -> str:
    """"on" / "trainee" (🎓 học việc: runs and records its decision, never acts) / "off". Order (KE_HOACH_HOC_VIEC_2026-10-08 mục 1):
    removed flag → 🔒 verified flag (15/10: always on) → choice on the 🧪 screen (modes / flags) → preset (stable: only verified;
    experimental: a học-việc flag is trainee, never on) → FEATURE_<NAME> (=trainee, or =1 for a học-việc flag → trainee; real ON only
    from 🧪; =0 off) → baseline (M7.2: chỉ máy chưa có tệp 🧪, có bảo vệ) → default_state() (`verified` or `default_on`)."""
    if name in REMOVED:
        return "off"
    if locked(name):
        return "on"
    meta = FEATURES[name]
    trainee = bool(meta.get("trainee"))
    if name in (s.get("modes") or {}):
        return "trainee"
    if name in s["flags"]:
        return "on" if s["flags"][name] else "off"
    verified = bool(meta["verified"])
    env = _env(name)
    if s["preset"] == "stable":
        return "on" if verified else "off"
    if s["preset"] == "experimental":
        if env in _NO:
            return "off"
        if trainee:
            return "trainee"
        return "on" if ((name not in HARMFUL and name not in OPT_IN_ONLY) or env in _YES) else "off"
    if trainee and (env in _YES or env == "trainee"):
        return "trainee"
    if env in _YES:
        return "on"
    if env in _NO or env == "trainee":
        return "off"
    return baseline_state(name) or default_state(name)


def default_state(name: str) -> str:
    """The state with nothing chosen anywhere (no 🧪 file, preset custom, no FEATURE_<NAME>): "on" when `verified` or `default_on`
    (the person decided it on — data/decisions.json), else "off"."""
    if name in REMOVED:
        return "off"
    meta = FEATURES[name]
    return "on" if (meta["verified"] or meta.get("default_on")) else "off"


def on(name: str) -> bool:
    """True only when the flag is really ON (it may act): chosen on screen (🧪), or by the preset / FEATURE_<NAME>=1 / `verified`.
    A 🎓 học-việc flag is never on() — every old caller stays without effect. A flag removed in S14.9 (`REMOVED`) is always off."""
    return state(name) == "on"


def shadow(name: str) -> bool:
    """🎓 học việc: run the role, record its decision in trainee_log, change nothing."""
    return state(name) == "trainee"


def active(name: str) -> bool:
    """On or học việc — where the code only CHOOSES A BRANCH (e.g. the old QC must not come back while scene_qc is học việc)."""
    return state(name) != "off"


# S14.4 C1b (04/10): a flag that only works together with another one (dialogue_take: the runner asks lipsync.enabled() = lip_sync
# first). Shown in 🧪 instead of a flag that looks ON and does nothing. B1 học việc: qc_team only runs inside scene_qc (by active()).
REQUIRES = {"dialogue_take": ("lip_sync",), "qc_team": ("scene_qc",), "change_review_frames": ("change_review",), "change_review_motion": ("change_review",),
            "ambient_motion": ("prompt_formula",), "plate_anchored_image": ("place_render_refs",),
            "anchor_by_spot": ("storyboard_api",),
            # rà 15/10: máy sân khấu chỉ được nền 3D dùng khi stage_camera bật; nền 3D cần place_render_refs
            "stage_auto": ("stage_camera", "place_render_refs"),
            "stage_crew": ("stage_auto",), "stage_crew_user_approve": ("stage_crew",), "stage_handheld_props": ("stage_auto",)}


def unmet(name: str) -> list:
    """The flags `name` needs that are off (empty when it is off itself or has no needs) — on or học việc both count (active())."""
    if name not in REQUIRES or not active(name):
        return []
    return [n for n in REQUIRES[name] if not active(n)]


def unmet_all() -> Dict[str, str]:
    """{flag: Vietnamese warning} for every flag that is ON but has no effect because a flag it needs is off."""
    return {k: f"'{k}' đang bật nhưng không có tác dụng: cần bật thêm {', '.join(repr(n) for n in miss)}"
            for k in REQUIRES for miss in [unmet(k)] if miss}


def why_state(name: str) -> str:
    """Why `state(name)` is what it is (shown in 🧪)."""
    miss = unmet(name)
    base = _why_state(name)
    if shadow(name):
        base += " — 🎓 học việc: chạy và ghi quyết định để so với bạn, không tác động (bật thật chỉ ở màn 🧪)"
    return base + (f" — ⚠ không có tác dụng: cần bật thêm {', '.join(miss)}" if miss else "")


def _why_state(name: str) -> str:
    if locked(name):
        return LOCKED_TEXT
    s = settings()
    if name in s["flags"] or name in (s.get("modes") or {}):
        return "bạn chọn trên màn này"
    if s["preset"] == "stable":
        return "preset Ổn định: " + ("đã thử thật" if FEATURES[name]["verified"] else "chưa thử thật → tắt")
    if s["preset"] == "experimental":
        return "preset Thử nghiệm" + ((" (cờ từng gây hại → tắt)" if name in HARMFUL and on(name) is False else
                                     " (hậu kỳ tùy chọn → chỉ bật khi chọn riêng)" if name == 'shot_popup' and on(name) is False else
                                     " (tự tiêu tiền → chỉ bật khi chọn riêng)" if name in OPT_IN_ONLY and on(name) is False else ""))
    env = _env(name)
    if env:
        return "dashboard.env / môi trường" + (f" (FEATURE_{name.upper()}={env} với cờ học việc → học việc)"
                                                if FEATURES[name].get("trainee") and (env in _YES or env == "trainee") else "")
    if baseline_state(name):
        return f"baseline cờ sản xuất ({baseline_path()}) — máy chưa có lựa chọn riêng"
    if FEATURES[name]["verified"]:
        return "mặc định: đã thử thật → bật"
    if FEATURES[name].get("default_on"):
        return "mặc định: người dùng quyết bật (sổ quyết định data/decisions.json) → bật, chưa thử thật"
    return "mặc định: chưa thử thật → tắt"


def on_unverified() -> Dict[str, Dict]:
    """S6.3 (kế hoạch sau #8): features switched ON by the person (FEATURE_<NAME>=1) that have not passed a real test yet — what a cut
    made now is really trying out (#8 used 23 of them; nobody could tell which part of the film came from which). 🎓 học việc flags are
    not in it (they change nothing in the cut)."""
    return {k: v for k, v in FEATURES.items() if on(k) and not v["verified"]}


def removed_in_use() -> Dict[str, str]:
    """S14.9: {removed flag: Vietnamese note} for every removed flag still named in data/feature_settings.json or switched ON by a
    FEATURE_<NAME> env line — ignored (the code always runs as with it off), said in 🧪 instead of a silent no-op."""
    out = {}
    for k in settings().get("dropped") or []:
        out[k] = f"'{k}' đã bị bỏ khỏi code (S14.9) — lựa chọn cũ trong data/feature_settings.json bị bỏ qua: {REMOVED[k]}"
    for k in REMOVED:
        if k not in out and _env(k) in _YES:
            out[k] = f"'{k}' đã bị bỏ khỏi code (S14.9) — dòng FEATURE_{k.upper()}=1 không còn tác dụng: {REMOVED[k]}"
    return out


def pending() -> Dict[str, Dict]:
    """Features still waiting for their real test and not running at all (shown so an off feature is never a mystery). 🎓 học việc
    flags are not in it — they run (see trainee_list())."""
    return {k: v for k, v in FEATURES.items() if not active(k)}


# ---- C1 (15/10): cờ sửa lỗi dự án trước + bảng trạng thái thật ------------------------------------------------------------------
def fix_flags_off(project_id: Optional[int]) -> List[Dict]:
    """Flags that fix a root error of an EARLIER project (`fixes_projects` has an id < project_id) and are OFF now (học việc counts as
    not off: it runs). Never the OPT_IN_ONLY / HARMFUL ones (they spend money with nobody clicking / did harm: a choice, not a miss).
    [{"name", "projects", "label", "why"}]."""
    if not isinstance(project_id, int) or isinstance(project_id, bool):
        return []
    out = []
    for name, meta in FEATURES.items():
        fixed = [n for n in meta.get("fixes_projects") or [] if n < project_id]
        if not fixed or name in OPT_IN_ONLY or name in HARMFUL or state(name) != "off":
            continue
        out.append({"name": name, "projects": fixed, "label": meta.get("label", ""), "why": meta.get("why", "")})
    return out


SOURCES = {"removed": "đã bỏ khỏi code", "locked": LOCKED_TEXT, "settings": "màn 🧪 (data/feature_settings.json)", "preset": "preset",
           "env": "dashboard.env / môi trường (FEATURE_<NAME>)", "baseline": "baseline cờ sản xuất (data/flag_baseline.json)",
           "default": "mặc định code"}


def source(name: str) -> str:
    """Where state(name) comes from — the same order as state(): removed / locked / settings / preset / env / default."""
    if name in REMOVED:
        return "removed"
    if locked(name):
        return "locked"
    s = settings()
    if name in s["flags"] or name in (s.get("modes") or {}):
        return "settings"
    if s["preset"] in ("stable", "experimental"):
        return "preset"
    if _env(name):
        return "env"
    return "baseline" if baseline_state(name) else "default"


def report() -> List[Dict]:
    """The real state of every flag on THIS machine (end-of-project reports are generated from this, never written by hand)."""
    preset = settings()["preset"]
    rows = []
    for name, meta in FEATURES.items():
        src = source(name)
        rows.append({"name": name, "state": state(name), "on": on(name), "source": src,
                     "source_text": SOURCES[src] + (f" {preset}" if src == "preset" else ""),
                     "default": default_state(name), "verified": bool(meta["verified"]), "locked": locked(name),
                     "default_on": bool(meta.get("default_on")),
                     "fixes_projects": list(meta.get("fixes_projects") or []), "label": meta.get("label", "")})
    return rows


def report_md(rows: Optional[List[Dict]] = None) -> str:
    rows = report() if rows is None else rows
    icon = {"on": "✅ bật", "trainee": "🎓 học việc", "off": "⬜ tắt"}
    out = [f"Trạng thái cờ thật — preset {settings()['preset']}, tệp {settings_path()}", "",
           "| cờ | trạng thái | nguồn | mặc định code | đã thử thật | sửa lỗi dự án |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['name']} | {icon.get(r['state'], r['state'])} | {r['source_text']} | {r['default']}"
                   f"{' (người dùng quyết)' if r['default_on'] else ''} | {'có' if r['verified'] else 'chưa'} | "
                   + (", ".join(f"#{n}" for n in r["fixes_projects"]) or "—") + " |")
    notes = list(locked_off_ignored().values()) + list(removed_in_use().values())    # ignored old choices: said, never silent
    if notes:
        out += ["", "Lựa chọn cũ bị bỏ qua:"] + [f"- {n}" for n in notes]
    return "\n".join(out)


# ---- M7.2: cấu hình hiệu lực + hash + drift --------------------------------------------------------------------------------------
def _machine() -> str:
    import platform
    return platform.node() or "?"


def config_hash(states: Optional[Dict[str, str]] = None) -> str:
    """Dấu vân tay 16 hex của trạng thái hiệu lực mọi cờ — hai máy / hai lần chạy cùng hash = cùng cấu hình cờ."""
    import hashlib
    import json
    states = {n: state(n) for n in FEATURES} if states is None else states
    return hashlib.sha256(json.dumps(sorted(states.items()), ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def effective_config() -> Dict:
    """{flags: {cờ: on|trainee|off}, sources: {cờ: nguồn}, hash, baseline_active, machine} — cấu hình cờ THẬT của máy này."""
    flags = {n: state(n) for n in FEATURES}
    return {"flags": flags, "sources": {n: source(n) for n in FEATURES}, "hash": config_hash(flags),
            "baseline_active": baseline_active(), "machine": _machine()}


def _snapshot_path(data_dir: str, pid) -> str:
    return os.path.join(data_dir, str(pid), "flag_config.json")


def remember_config(data_dir: str, pid) -> Optional[str]:
    """Ghi cấu hình cờ hiệu lực của dự án `pid` (<data>/<pid>/flag_config.json) — mốc để dự án sau so drift. Lỗi ghi → None (không chặn)."""
    import datetime
    import json
    cfg = effective_config()
    snap = {"hash": cfg["hash"], "flags": cfg["flags"], "machine": cfg["machine"],     # `at` tới micro giây: drift chọn dự án gửi CUỐI
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")}
    path = _snapshot_path(data_dir, pid)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return path
    except OSError:
        return None


def drift(data_dir: str, pid) -> List[str]:
    """Cảnh báo drift của dự án `pid` so với mốc cấu hình mới nhất của DỰ ÁN KHÁC: cờ đã bật / học việc ở dự án trước mà nay tắt; dự án
    trước chạy ở máy khác với hash khác. Không có mốc → []. Chỉ đọc."""
    import json
    best = None
    try:
        names = os.listdir(data_dir)
    except OSError:
        return []
    for d in names:
        if d == str(pid):
            continue
        path = _snapshot_path(data_dir, d)
        try:
            with open(path, encoding="utf-8") as f:
                stamp = str(json.load(f).get("at") or "")      # lần GỬI cuối (runner ghi mỗi lần gửi) — không theo mtime
        except (OSError, ValueError, AttributeError):
            if not os.path.exists(path):
                continue
            stamp = ""
        if best is None or stamp > best[0]:
            best = (stamp, d, path)
    if best is None:
        return []
    try:
        with open(best[2], encoding="utf-8") as f:
            snap = json.load(f)
    except (OSError, ValueError):
        return [f"mốc cấu hình cờ dự án #{best[1]} hỏng ({best[2]}) — không so được drift"]
    now = {n: state(n) for n in FEATURES}
    out = [f"cờ {n} {'bật' if was == 'on' else 'học việc'} ở dự án #{best[1]} nay TẮT ({why_state(n)})"
           for n, was in sorted((snap.get("flags") or {}).items()) if n in now and was in ("on", "trainee") and now[n] == "off"]
    if snap.get("machine") and snap["machine"] != _machine() and snap.get("hash") != config_hash(now):
        out.append(f"dự án #{best[1]} chạy ở máy khác ({snap['machine']}) với cấu hình cờ khác (hash {snap.get('hash')} ≠ {config_hash(now)})")
    return out


# ---- M7.2: baseline chụp / so ---------------------------------------------------------------------------------------------------
def baseline_capture(path: Optional[str] = None) -> str:
    """Chụp trạng thái hiệu lực máy này thành tệp baseline (chạy trên MÁY CHÍNH rồi commit). Trả đường dẫn."""
    import datetime
    import json
    path = path or baseline_path()
    if not path:
        raise ValueError("baseline đang tắt (FEATURE_BASELINE_FILE rỗng) — không có chỗ ghi")
    cfg = effective_config()
    data = {"flags": cfg["flags"], "hash": cfg["hash"], "machine": cfg["machine"],
            "captured": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "note": "M7.2: chỉ áp ở máy CHƯA có data/feature_settings.json; không bật cờ costs / OPT_IN_ONLY; học việc tối đa trainee"}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)
    _BASELINE["stamp"] = object()
    return path


def baseline_diff() -> Dict:
    """here: cờ mà tệp baseline ghi khác trạng thái hiệu lực máy này (máy chính sau khi chụp phải = []); fresh: một máy MỚI (chưa có tệp 🧪,
    không env) sẽ khác máy này ở cờ nào và vì sao (bảo vệ costs / OPT_IN, học việc tối đa trainee, baseline không ghi)."""
    raw = baseline().get("flags") or {}
    here, fresh = [], []
    for n in FEATURES:
        now = state(n)
        if n in raw and raw[n] != now:
            here.append({"name": n, "now": now, "baseline": raw[n]})
        if n in REMOVED:
            new, why = "off", "đã bỏ khỏi code"
        elif FEATURES[n]["verified"]:
            new, why = "on", "khóa"
        else:
            g = _guarded(n, raw.get(n))
            new = g or default_state(n)
            why = ("baseline" if g == raw.get(n) else "baseline bị bảo vệ hạ (" + (
                "cờ tốn tiền / OPT_IN không bao giờ tự bật" if _paid(n)
                else "học việc tối đa trainee" if FEATURES[n].get("trainee") else "giá trị không áp được") + ")") if g or n in raw \
                else "baseline không ghi → mặc định code"
        if new != now:
            fresh.append({"name": n, "now": now, "fresh": new, "why": why})
    return {"path": baseline_path(), "active_here": baseline_active(), "here": here, "fresh": fresh}


# ---- M7.2 / K6: bỏ lựa chọn riêng an toàn (preview, xác nhận ở UI, sao lưu, khôi phục) ---------------------------------------------
MAX_BACKUPS = 30


def _backup_dir() -> str:
    return os.path.join(os.path.dirname(settings_path()), "backup")


def backup_settings() -> Optional[str]:
    """Chép tệp 🧪 hiện tại vào <data>/backup/feature_settings.<giờ>.json. Không có tệp → None."""
    import datetime
    import shutil
    src = settings_path()
    if not os.path.isfile(src):
        return None
    os.makedirs(_backup_dir(), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dst = os.path.join(_backup_dir(), f"feature_settings.{stamp}.json")
    shutil.copy2(src, dst)
    for old in list_backups()[MAX_BACKUPS:]:          # giữ MAX_BACKUPS bản mới nhất
        try:
            os.remove(old["path"])
        except OSError:
            pass
    return dst


def list_backups() -> List[Dict]:
    """Bản sao lưu tệp 🧪, mới nhất trước: [{path, name, n_flags}]."""
    import json
    out = []
    d = _backup_dir()
    for name in sorted(os.listdir(d), reverse=True) if os.path.isdir(d) else []:
        if not (name.startswith("feature_settings.") and name.endswith(".json")):
            continue
        path = os.path.join(d, name)
        try:
            with open(path, encoding="utf-8") as f:
                n = len((json.load(f).get("flags") or {}))
        except (OSError, ValueError, AttributeError):
            n = None
        out.append({"path": path, "name": name, "n_flags": n})
    return out


def _state_with(data: Dict, name: str) -> str:
    """Trạng thái của `name` nếu tệp 🧪 là `data` — thuần (không đụng cache chung: luồng nền / phiên khác đọc cờ cùng lúc)."""
    return _state(name, data)


def reset_preview() -> List[Dict]:
    """Cờ đổi trạng thái nếu bỏ mọi lựa chọn riêng (giữ preset): [{name, now, after, why}]."""
    cur = settings()
    bare = {"preset": cur["preset"], "flags": {}, "modes": {}}
    out = []
    for n in sorted(set(cur["flags"]) | set(cur.get("modes") or {})):
        now, after = state(n), _state_with(bare, n)
        if now != after:
            out.append({"name": n, "now": now, "after": after})
    return out


def reset_choices() -> Optional[str]:
    """Sao lưu tệp 🧪 rồi bỏ mọi lựa chọn riêng (giữ preset). Trả đường dẫn bản sao lưu."""
    cur = settings()
    path = backup_settings()
    save_settings(flags={k: None for k in list(cur["flags"])}, modes={k: None for k in list(cur.get("modes") or {})})
    return path


def restore_settings(path: str) -> Optional[str]:
    """Khôi phục một bản sao lưu (chỉ tệp trong thư mục backup). Sao lưu bản đang dùng trước; trả đường dẫn bản đó. Lựa chọn cũ tắt cờ 🔒
    vẫn bị bỏ qua như mọi khi (locked_off_ignored)."""
    import json
    real = os.path.realpath(path)
    name = os.path.basename(real)
    if os.path.normcase(os.path.dirname(real)) != os.path.normcase(os.path.realpath(_backup_dir())) \
            or not name.startswith("feature_settings.") or not name.endswith(".json"):
        raise ValueError(f"{path} không phải bản sao lưu cài đặt cờ ({_backup_dir()})")
    with open(real, encoding="utf-8") as f:
        text = f.read()
    raw = json.loads(text)
    if not isinstance(raw, dict) or not isinstance(raw.get("flags", {}), dict):
        raise ValueError(f"{path} không đúng dạng cài đặt cờ")
    before = backup_settings()                    # C-M72-FIX: có thể dọn chính bản cũ nhất (giữ MAX_BACKUPS) — ghi từ nội dung đã đọc
    tmp = settings_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, settings_path())
    _SETTINGS["stamp"] = object()
    return before


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")       # bảng có dấu + biểu tượng: cửa sổ cp1252 không in được
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="py -m core.features", description="Trạng thái cờ tính năng thật trên máy này")
    ap.add_argument("--report", action="store_true", help="bảng trạng thái mọi cờ (bật/tắt + nguồn)")
    ap.add_argument("--json", action="store_true", help="xuất JSON thay bảng")
    ap.add_argument("--project", type=int, help="liệt kê cờ sửa lỗi dự án trước còn TẮT với dự án này")
    ap.add_argument("--baseline-capture", action="store_true", help="chụp trạng thái hiệu lực máy này vào data/flag_baseline.json (máy chính)")
    ap.add_argument("--baseline-diff", action="store_true", help="so baseline với máy này (máy chính phải 0 cờ đổi) + máy mới sẽ khác gì")
    ap.add_argument("--config", action="store_true", help="cấu hình cờ hiệu lực + hash")
    a = ap.parse_args(argv)
    if a.baseline_capture:
        print(f"Đã chụp baseline: {baseline_capture()} (hash {config_hash()})")
        return 0
    if a.baseline_diff:
        d = baseline_diff()
        if a.json:
            print(json.dumps(d, ensure_ascii=False, indent=1))
            return 0
        print(f"Baseline {d['path'] or '(tắt)'} · áp ở máy này: {'có' if d['active_here'] else 'không (máy đã có tệp 🧪)'}")
        for p_ in baseline_problems():
            print("⚠ " + p_)
        print(f"So với máy này: {len(d['here'])} cờ đổi")
        for r in d["here"]:
            print(f"  {r['name']}: máy này {r['now']} · baseline {r['baseline']}")
        print(f"Máy MỚI (chưa có tệp 🧪, không env) sẽ khác máy này ở {len(d['fresh'])} cờ:")
        for r in d["fresh"]:
            print(f"  {r['name']}: {r['now']} → {r['fresh']} ({r['why']})")
        return 0
    if a.config:
        cfg = effective_config()
        print(json.dumps(cfg, ensure_ascii=False, indent=1) if a.json else f"hash {cfg['hash']} · máy {cfg['machine']} · baseline "
              f"{'áp' if cfg['baseline_active'] else 'không áp'} · bật {sum(v == 'on' for v in cfg['flags'].values())} / "
              f"học việc {sum(v == 'trainee' for v in cfg['flags'].values())} / tắt {sum(v == 'off' for v in cfg['flags'].values())}")
        return 0
    if a.project is not None:
        rows = fix_flags_off(a.project)
        print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else
              "\n".join(f"{r['name']}: sửa lỗi " + ", ".join(f"#{n}" for n in r["projects"]) + f" — {r['why'][:140]}" for r in rows)
              or f"Không có cờ sửa lỗi dự án trước nào TẮT với dự án #{a.project}")
        return 0
    if a.report or a.json:
        print(json.dumps(report(), ensure_ascii=False, indent=1) if a.json else report_md())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
