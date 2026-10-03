# So sánh pipeline với workflow / công cụ điều phối / mã nguồn mở (nhóm B) — 2026-10-03

> Nghiên cứu nhóm B, nối tiếp `docs/SO_SANH_PHAN_MEM_NGOAI_2026-09-29.md` (nhóm A: sản phẩm dựng phim AI trọn gói). **0 USD**: chỉ đọc trang
> công khai (README, tài liệu, bài tổng hợp) — không đăng ký / đăng nhập / tải file / gọi API trả tiền. **Không sửa code.** Việc "nên làm"
> dưới đây là **đề xuất chờ người dùng chọn**, chưa vào `TODO.md`.

## 0. Cách làm và giới hạn
- Ngày đọc: **2026-10-03**. Lời trích ≤ 15 từ; còn lại tóm bằng lời mình. Khâu **K1–K10** lấy đúng bảng mục 1 của file 2026-09-29.
- Mức nguồn: **[A]** README / tài liệu / trang chính thức của dự án hoặc hãng (đọc trực tiếp hoặc qua trích dẫn kết quả tìm kiếm) ·
  **[B]** blog, bài so sánh bên thứ ba (có thể cũ / sai; nhất là số VRAM, giá) · **[R]** mã / tài liệu trong repo mình · **"không rõ"** = chưa tìm được nguồn.
- **Không tải, không chạy thử** công cụ nào → mọi so sánh là **tính năng được công bố**, không phải chất lượng đo thật trên nhân vật FF.
- **Phần cứng máy này** (đo bằng `nvidia-smi` khi viết): **GTX 1070 Ti, 8 GB VRAM** (kiến trúc Pascal, đời 2017). Mọi dòng "cần GPU" bên dưới phải đọc theo mức này.
  Số VRAM của bài [B] thường tính cho card 24 GB trở lên, kiến trúc mới → trên Pascal thực tế thường **chậm hơn nhiều hoặc không chạy được**; mình không đo nên ghi "chưa kiểm".
- **Không xác minh được / chỉ xác minh một phần** (nói thẳng):
  - **"Story2Video"** và **"VideoAgent" (làm phim)**: không tìm được repo / bài đúng tên làm phim. Kết quả "VideoAgent" là một khung *hiểu và dựng video* khác loại
    (arXiv 2606.23327, chỉ thấy tiêu đề); gần nhất với "Story…" là **StoryAgent** (arXiv 2411.04925) và **MAViS** (arXiv 2508.08487) — chỉ thấy tóm tắt, **không đọc mã**.
  - **FilmAgent** chỉ đọc tóm tắt bài (arXiv 2501.12909) qua kết quả tìm kiếm, không mở repo; giấy phép không rõ.
  - **MovieAgent**: README không ghi giấy phép (trong phần đọc được) → "không rõ".
  - **ViMax** có cả bài arXiv (2606.07649) lẫn nhiều bản fork trên GitHub; mình chỉ đọc README của repo gốc `HKUDS/ViMax`.
  - **ComfyUI + IP-Adapter / ControlNet / AnimateDiff**: chỉ đọc README ComfyUI (danh sách model video, giấy phép, API). Chi tiết IP-Adapter / ControlNet / AnimateDiff: **không đọc riêng**.
  - **Make / Zapier**, **Weights & Biases**, **Retool / Streamlit dashboards**, **Notion**: chỉ lướt qua bài so sánh [B] hoặc không đọc (ghi rõ ở từng mục).

## 1. Nhóm công cụ → khâu nào, học gì, giá và rủi ro
Ký hiệu cuối dòng: 💻 áp dụng ngay (0 USD) · 💵 thử có trần chi phí · ⛔ bỏ qua.

### 1.1 Mã nguồn mở "đoàn làm phim AI" (K1, K2, K3, K8)
| Dự án | Họ làm gì | Mình học / lấy gì | Chi phí · độ phức tạp · rủi ro | Nguồn |
|---|---|---|---|---|
| **ViMax** (HKUDS) | Ba luồng Idea2Video / Script2Video / Novel2Video; có "Agent Loop" với giao diện TUI + Web để thảo luận, sửa, điều khiển dựng. Theo dõi trạng thái nhân vật / bối cảnh qua ranh giới thời gian; **mỗi khung hình tạo 2 ứng viên song song, một model nhìn ảnh chọn bản tốt hơn**; kiểm tra nhất quán tự động. | (a) Ý "theo dõi trạng thái nhân vật qua các shot" ≈ Bible + dấu vân tay của mình — **mình đã có**. (b) "Tạo 2 ứng viên rồi VLM chọn" **ngược** quy ước mình (gen lại ≤ 2 lần, đổi đầu vào, mọi gen qua sổ chi) và **gấp đôi tiền ảnh** → không bắt chước. (c) Agent Loop = trò chuyện sửa kịch bản/dựng: mình có Director hai lượt + duyệt; không cần. | Giấy phép **MIT**; Python 3.12+; cần khóa LLM + ảnh + video bên thứ ba (tốn tiền, theo README). Không thay được ClipAI. Rủi ro: dự án mới, nhiều fork. | [A] README repo; [B] kết quả tìm kiếm cho arXiv 2606.07649 |
| **MovieAgent** (showlab) | Chuỗi suy luận phân cấp: các agent đạo diễn / biên kịch / họa sĩ storyboard / quản lý bối cảnh; từ kịch bản + "kho nhân vật" ra phim nhiều cảnh, có phụ đề + âm thanh ổn định. Dùng GPT-4o, ROICtrl (+ LoRA nhân vật), HunyuanVideo_I2V và SVD. | Phân vai agent ≈ bộ 3 vai Đạo diễn / Quay phim / Editor của mình — **mình đã có, có căn cứ + lý do hơn**. "Kho nhân vật có LoRA riêng" cần GPU huấn luyện → không hợp. | Cần conda + CUDA 12.1 + PyTorch 2.4 + tự tải trọng số; **GPU 8 GB Pascal: chưa kiểm, nhiều khả năng không đủ**. Giấy phép **không rõ**. README không nêu chỉ số đánh giá. | [A] README |
| **FilmAgent** | Đóng vai đạo diễn / biên kịch / diễn viên / quay phim trong không gian 3D ảo; hai kiểu cộng tác **Critique-Correct-Verify** và **Debate-Judge** để giảm bịa; người chấm trung bình 3,98/5; dùng GPT-4o vẫn hơn o1 đơn lẻ. | **Critique-Correct-Verify** ≈ Director hai lượt + Đạo diễn duyệt của mình (đã có). **Debate-Judge** (hai agent tranh luận, một agent phán) mình **chưa dùng** — hợp với *quyết định mơ hồ* (chọn model video theo cảnh, chọn kiểu chuyển cảnh). | Chỉ đọc bài; thêm lời gọi Claude (đã qua sổ chi). Chưa thấy ai đo Debate-Judge trên dữ liệu của mình → chỉ thử có trần. | [B] tóm tắt bài |
| **StoryAgent / MAViS** | Agent thiết kế truyện → storyboard → video → điều phối → **đánh giá kết quả**; StoryAgent dùng LoRA-BE để ổn định trong shot. | Có khâu "agent đánh giá" riêng — mình đã có agent QC + Tổ QC. Không có gì mới đủ để lấy. | Chỉ thấy tóm tắt; **không đọc mã**. | [B] |
| **CineForge** (arXiv 2608.29621) | "Tác tử tự cải thiện cho video dài" — chỉ thấy tiêu đề. | Không đọc → **không rõ**. | — | [B] (tiêu đề) |

**Kết luận 1.1**: không có dự án mở nào làm *đầy đủ* những gì mình có (cổng duyệt, trần chi phí 3 tầng, QC clip, khớp môi, bối cảnh 3D thật). Họ dừng ở "agent chia shot + gọi model tạo video". Chỗ duy nhất đáng thử: **Debate-Judge** cho quyết định mơ hồ.

### 1.2 ComfyUI và model video mã nguồn mở (K2, K4, K5)
| Mục | Nội dung |
|---|---|
| Là gì | Công cụ dựng workflow dạng đồ thị; chạy được dạng máy chủ không giao diện + có API cục bộ để tích hợp vào ứng dụng [A]. Hỗ trợ sẵn Wan 2.1/2.2, LTX-Video 2/2.3, HunyuanVideo 1.5, CogVideoX, Mochi… [A]. |
| Giải quyết khâu | **K4** (tạo video chạy máy mình, 0 USD tiền dịch vụ), **K2** (IP-Adapter / LoRA giữ nhân vật — **không đọc riêng**), **K3** (ControlNet depth/pose cho khung), **K5** (có node lip-sync cộng đồng — **không rõ**). |
| Phần cứng | README nói chạy được "tới thấp 4 GB VRAM + 8 GB RAM" nhờ truyền trọng số theo luồng [A] — **không nói tốc độ**. Bài [B]: Wan 2.2 TI2V-5B vừa 8 GB; Wan 14B 480p cần ~24 GB; 720p 14B cần 65–80 GB; LTX-2.3 24 GB (12 GB bản lượng tử hóa, cộng đồng báo); HunyuanVideo cũ 60–80 GB, bản 1.5 ~24 GB. **GTX 1070 Ti 8 GB**: chỉ có thể thử loại nhỏ (5B / GGUF), **chưa kiểm**, nên giả định là chậm và chất lượng thấp hơn Kling/Seedance. |
| Giấy phép | ComfyUI **GPL-3.0** [A] (chỉ *gọi qua API*, không nhúng mã vào repo mình thì không lây). Trọng số từng model có giấy phép riêng — **không đọc**. |
| Độ phức tạp | Cao: cài model hàng chục GB, quản lý node, tự dựng workflow nhất quán nhân vật (thứ Seedance/Kling "tham chiếu" của ClipAI làm sẵn). |
| **Nên học** | Không phải bản thân ComfyUI mà **ý "đồ thị node, mỗi node có đầu vào/đầu ra rõ + hàng chờ + xem lại workflow đã chạy"** → ý cho dashboard (mục 3). Riêng **depth / mannequin tham chiếu cho Seedance 2.5** (đã ghi ở bộ nhớ dự án): mình có sẵn **Blender + bối cảnh 3D thật**, render depth pass / mannequin thẳng từ Blender (0 USD) — không cần ComfyUI + ControlNet. |

→ **⛔ Bỏ qua chạy video bằng ComfyUI** (phần cứng không đủ, thua chất lượng hãng, mất tính nhất quán đã có). Chỉ **💻 thử nhỏ, không cam kết**: một workflow LTX/Wan-5B trên 1 ảnh để ghi *số đo thật* thời gian + VRAM vào `docs/` (nếu người dùng muốn biết giới hạn máy).

### 1.3 Tự động hóa kéo-thả: n8n / Make / Zapier (K10)
| Mục | Nội dung |
|---|---|
| Giải quyết khâu | K10 (điều phối, thông báo, nối dịch vụ). Mình đã có **autopilot trong code + cổng duyệt + sổ chi** — chạy trực tiếp trên DB của mình. |
| Giá / giấy phép | **n8n**: giấy phép "Sustainable Use" (fair-code, **không phải OSI**), tự host dùng nội bộ miễn phí; chi phí chủ yếu máy chủ nhỏ ~$5–10/tháng [B]. **Make**: chỉ đám mây, gói có phí theo "credits" [B]. **Zapier**: tính theo tác vụ, đắt khi nhiều lượt [B]. |
| Rủi ro | Thêm một hệ thống thứ hai giữ trạng thái → **hai nguồn sự thật** với `jobs` / `autopilot`; vi phạm tinh thần `docs/CHUAN_XAY_DUNG.md` (mọi lời gọi tốn tiền phải qua sổ chi). Make/Zapier đưa dữ liệu video + kịch bản FF lên dịch vụ ngoài. |
| **Nên học** | Chỉ **thông báo ra ngoài khi cổng chờ** (webhook → kênh chat của đội) — làm bằng một hàm nhỏ trong code mình, không cần n8n. |

→ **⛔ bỏ qua n8n/Make/Zapier làm lõi**; **💻 làm webhook thông báo** (ý 9 mục 3). Cần người dùng xác nhận kênh nhận (nội bộ công ty).

### 1.4 Khung điều phối agent: LangGraph / CrewAI / AutoGen (K1, K10)
| Mục | Nội dung |
|---|---|
| Họ có | **LangGraph**: `interrupt()` tạm dừng đúng tại nút, lưu cả trạng thái vào "checkpointer", khôi phục bằng `thread_id`; có **"du hành thời gian"** — chạy lại từ một checkpoint cũ để rẽ nhánh [A tài liệu LangChain]. MIT. **CrewAI**: gói đám mây có hạn mức thực thi thấp (50 lượt/tháng gói free) [B]. **AutoGen**: miễn phí hoàn toàn nhưng vòng hội thoại mở **có thể tốn 5–10 lần token** nếu thiếu điều kiện dừng cứng [B]. |
| Mình đã có | Autopilot có cổng duyệt + trạng thái lưu DB (`core/autopilot.py`), `core/lineage.py`, nhân bản dự án, khóa chi phí cứng. Hai lượt Director cố định (không hội thoại mở) → **đúng hướng "dự đoán được chi phí"** mà bài [B] khen ở LangGraph. |
| **Nên học** | (a) Ý **"điểm dừng có tên + chụp trạng thái + chạy lại từ đó"** → nút "tạo nhánh từ cổng duyệt" (ý 8). (b) Quy tắc **mọi vòng tranh luận agent phải có trần lượt + trần token** — đã có tinh thần ở `feedback_hard_cost_locks`; ghi lại nếu thêm Debate-Judge. |
| Rủi ro | Nhúng LangGraph = phụ thuộc hệ sinh thái LangChain, viết lại autopilot đang chạy ổn → **không đáng**. |

→ **⛔ không nhúng**; **💻 chỉ mượn ý** (checkpoint/rẽ nhánh) khi làm dashboard.

### 1.5 Dựng tự động bằng mã: Remotion / MoviePy / ffmpeg (K7)
| Mục | Nội dung |
|---|---|
| Họ có | **Remotion**: dựng video bằng React, tham số hóa như props → hàng loạt biến thể. Giấy phép: **miễn phí cho cá nhân / công ty ≤ 3 người**, công ty lớn hơn trả ~$25/người/tháng hoặc $0,01/lượt render (tối thiểu $100/tháng) [A remotion.dev, qua tìm kiếm]. **MoviePy**: Python thuần, **MIT**, mỗi khung là mảng numpy [B]. |
| Mình đã có | `core/ffmpeg_studio.py`, `final_cut.py`, phụ đề vùng an toàn TikTok, chuyển cảnh vẽ, hồi tưởng, `rough_cut_review` (duyệt bản thô). ffmpeg trực tiếp **nhanh hơn và ít phụ thuộc** MoviePy. |
| **Nên học** | Remotion giỏi khi cần **hoạt họa chữ / thẻ tiêu đề tham số hóa** (phụ đề kiểu "từ đang nói sáng lên") — mình hiện làm bằng ffmpeg; chưa có nhu cầu đã chốt. |
| Rủi ro | Remotion cần Node + Chromium; nếu đội > 3 người dùng cho dự án thì **phải mua giấy phép** (đội Garena VN có thể vượt). |

→ **⛔ bỏ qua cả hai**; ghi Remotion là phương án nếu sau này cần phụ đề động kiểu "từ sáng lên" (kiểm lại giấy phép lúc đó).

### 1.6 Dựng thương mại có AI: Descript / Premiere / DaVinci Resolve (K7)
| Công cụ | Điểm đáng chú ý | Nguồn |
|---|---|---|
| **Descript** | Sửa video như sửa văn bản: xóa chữ trong bản chép lời thì cắt đúng đoạn; Underlord thực hiện chỉ dẫn nhiều bước bằng lời thường (bỏ chữ thừa, sửa ánh mắt, đặt bố cục, thêm b-roll…). Giá tính theo "AI credits" + giờ media; từ gói free đến ~$24–50/người/tháng. | [B] |
| **Premiere Pro** (26.x, 2026) | Chép lời + phụ đề, Enhance Speech, Generative Extend (kéo dài clip bằng khung AI), Media Intelligence (tìm cảnh theo nội dung); bản 26.5 (09/2026) có **Paper Edit: biến bản chép lời thành bản dựng thô**. | [B] |
| **DaVinci Resolve 20** | IntelliScript (dựng timeline từ kịch bản có sẵn), AI Multicam SmartSwitch (chọn góc theo tiếng + môi), Magic Mask v2, phụ đề động; một số tính năng chỉ ở bản Studio ($295). **Nguồn nói IntelliScript có ở bản miễn phí, nơi khác không rõ — chưa xác nhận.** | [A] thông cáo Blackmagic (qua tìm kiếm) + [B] |

- **Mình đã có tương đương**: IntelliScript ≈ kịch bản → timeline qua Director + `audio_first`; Paper Edit ≈ `rough_cut_review`. SmartSwitch (đa máy quay) **không áp dụng** (mình không có nhiều góc quay thật).
- **Nên học**: **sửa dựng theo lời thoại** (Descript / Paper Edit) — người duyệt đọc *bản chép lời của video cuối* và bấm bỏ / đổi chỗ câu thay vì kéo timeline. Mình đã có `faster-whisper` ở `tools/audio_listen.py` → có thể làm 0 USD, nhưng là việc lớn.
- **Rủi ro**: dùng chính các phần mềm này = xuất sang công cụ ngoài, mất khả năng tự động + sổ chi; chỉ hợp làm bước *chỉnh tay cuối*.

→ **⛔ bỏ qua việc dùng**; **💵/💻 cân nhắc "duyệt theo bản chép lời"** (mục 3, ý 11).

### 1.7 Quan sát / chi phí / đánh giá AI: Langfuse, LangSmith, Helicone, W&B (K9, K8, K10)
| Công cụ | Cách làm | Giá · giấy phép | Nguồn |
|---|---|---|---|
| **Langfuse** | Mỗi lời gọi LLM là một **span** có cha-con (cây vết); theo dõi token + chi phí theo bảng giá, **cho tự định công thức giá** (hợp dịch vụ trả theo đơn vị riêng); có quản lý prompt, **đánh giá (eval)**, **hàng chờ gán nhãn người**, bộ dữ liệu. | Lõi **MIT**, tự host miễn phí; đám mây Core $29 / Pro $199 mỗi tháng. Yêu cầu hạ tầng tự host (CSDL riêng…): **không rõ trong nguồn đã đọc**. | [B] |
| **Helicone** | Là **proxy**: đặt giữa app và nhà cung cấp, ghi mọi yêu cầu; tích hợp ~5 phút. | Free 10k yêu cầu/tháng (lưu 7 ngày); Pro $79. | [B] |
| **LangSmith** | Gắn chặt LangChain/LangGraph. | Free 5k vết/tháng; Plus $39/chỗ; **tự host chỉ gói Enterprise** (nguồn nói $100k+/năm). | [B] |
| **Weights & Biases** | Không đọc riêng → **không rõ**. | — | — |

- **Mình đã có**: sổ chi `usage_events` (`core/cost.py`, `core/budget.py`), **ước tính trước khi bấm**, **khóa cứng 3 tầng** — *mạnh hơn* các công cụ trên ở chỗ **chặn trước** (họ chủ yếu **ghi sau**) và tính cả tiền ClipAI/Deepix, không chỉ token LLM.
- **Chỗ mình thiếu**: **cây vết theo shot** (một clip đã gọi những lời gọi nào, bao nhiêu tiền, bao lâu, prompt nào, điểm QC nào) và **bảng so sánh các lần chạy** (evals).
- **Rủi ro nhúng**: gửi prompt kịch bản + ảnh nhân vật FF ra dịch vụ ngoài (nếu dùng đám mây); thêm một dịch vụ cần vận hành. Proxy Helicone **không thấy** lời gọi ClipAI (web/API riêng).
- **Nên học**: *cách hiển thị* (cây vết, bảng điểm theo lần chạy, ngưỡng cảnh báo chi phí) — làm trên dữ liệu mình có sẵn.

→ **⛔ không nhúng**; **💻 học giao diện** (ý 4, 5, 6 mục 3).

### 1.8 UI duyệt / giám sát: Label Studio, Retool / Streamlit, Linear / Notion (dashboard)
| Công cụ | Điểm đáng học | Nguồn |
|---|---|---|
| **Label Studio** (Apache 2.0, hỗ trợ video) | Hàng chờ **người duyệt**: mỗi mục có Chấp nhận / Từ chối; từ chối có **hai kiểu: loại bỏ hẳn hoặc đưa lại hàng chờ để sửa**. | [A] tài liệu HumanSignal (qua tìm kiếm) |
| **"Hộp thư agent" (agent inbox)** | Hàng chờ chứa việc AI làm xong đang chờ người: duyệt / sửa / từ chối / chuyển lên cấp trên; nên **cho agent chạy chế độ nháp vài tuần** trước khi cho tự thực hiện việc rủi ro thấp; mỗi mục có **chủ + trạng thái + ưu tiên**; mục khó chịu / gấp lên đầu. | [B] AgentMail, Nylas, Kortix |
| **Linear Intake / Triage** | Chỉ đọc tiêu đề trang; cách phân loại → **không rõ**. | — |
| **Retool / Streamlit / Notion** | Không đọc riêng → **không rõ**. Dashboard mình đã là Streamlit (`dashboard/`). | — |

## 2. BẢNG SO SÁNH: khâu × (mình / công cụ ngoài tốt nhất) × nên làm
Công cụ ngoài tốt nhất trong **nhóm B** (nhóm A đã so ở file 09-29). Cột cuối: 💻 áp dụng ngay (0 USD) · 💵 thử có trần chi phí · ⛔ bỏ qua.

| Khâu | Mình đang có | Công cụ ngoài tốt nhất (nhóm B) | Khoảng cách | Nên làm |
|---|---|---|---|---|
| **K1** Kịch bản → shot | Director 2 lượt + Đạo diễn duyệt + người xem lần đầu + bộ kỹ năng 3 vai | FilmAgent: Critique-Correct-Verify **và Debate-Judge**; ViMax: Script2Video / Novel2Video | Mình hơn ở có căn cứ + người duyệt. Chưa có **Debate-Judge** cho quyết định mơ hồ. Chưa có **tách tiểu thuyết dài → tập** (Novel2Video). | 💵 thử Debate-Judge **một** quyết định (chọn model video theo cảnh) có trần lượt + token trên 1 dự án. Novel2Video: ⛔ (chưa có nhu cầu). |
| **K2** Nhất quán nhân vật / bối cảnh | Bible + hồ sơ chuẩn + bối cảnh 3D thật + dấu vân tay | ViMax: theo dõi trạng thái nhân vật/bối cảnh qua ranh giới shot; ComfyUI IP-Adapter / LoRA | Ý tưởng ViMax đã nằm trong Bible. LoRA/ComfyUI cần GPU huấn luyện — máy 8 GB Pascal không hợp. | ⛔ ComfyUI/LoRA. 💻 **chỉ số nhất quán danh tính bằng số** (ArcFace/DINO) để *đo* thay cho "Claude nhìn": xem K8. |
| **K3** Storyboard / animatic | Deepix + QC 2 lớp + cổng duyệt + animatic 0 USD | ViMax: 2 ứng viên + VLM chọn | Họ **tốn gấp đôi** để chọn; mình chọn bằng QC + người. | ⛔ không sinh 2 ứng viên (vi phạm "gen lại ≤ 2, đổi đầu vào"). |
| **K4** Video | Chọn model theo cảnh qua ClipAI (Kling / Seedance) | ComfyUI + Wan 2.2 / LTX / HunyuanVideo (chạy cục bộ) | Cục bộ = 0 USD tiền dịch vụ nhưng **chất lượng + nhất quán thấp hơn**, GPU 8 GB Pascal **chưa kiểm**, nhiều khả năng không đủ. | ⛔ làm lõi. 💻 (tùy chọn) đo thử 1 workflow Wan-5B/LTX nhỏ ghi giới hạn máy. Depth/mannequin: 💻 **render từ Blender** thay ControlNet. |
| **K5** Khớp môi | Seedance nhận giọng; một clip cả đoạn thoại; đo mốc môi MediaPipe (chỉ thời điểm) | **LatentSync** (Apache 2.0; 1.5 cần ≥ 8 GB, 1.6 ~18 GB), **MuseTalk** (MIT, nhẹ hơn), **Wav2Lip** (nhẹ, nhưng bản GAN **không cho dùng thương mại** theo [B]) | Mình chưa có đường **sửa môi sau khi gen** miễn phí (sync.so tốn tiền, đang tắt). LatentSync/MuseTalk sửa vùng mặt 256–512 px — **chưa rõ ra sao trên nhân vật 3D phong cách FF** (nhiều khả năng mặt giả không vào bộ phát hiện). | 💻 thử **một** clip ngắn bằng MuseTalk hoặc LatentSync-1.5 trên máy (0 USD tiền dịch vụ); đo bằng công cụ mốc môi mình có. Chỉ lấy nếu qua kiểm. Wav2Lip: ⛔. |
| **K6** Giọng / nhạc / SFX | TTS clone FF + âm thanh trước + −14 LUFS | (nhóm B không có gì mới; nhóm A: ElevenLabs) | — | ⛔ |
| **K7** Dựng | ffmpeg: chuyển cảnh vẽ, hồi tưởng, phụ đề an toàn TikTok, duyệt bản thô | Descript / Premiere Paper Edit (**sửa theo bản chép lời**); Remotion (phụ đề động tham số) | Mình **chưa có sửa dựng theo lời thoại**. Remotion bị giới hạn giấy phép khi đội > 3 người. | 💵/💻 "duyệt theo bản chép lời" (ý 11) — việc lớn, làm sau. Remotion/MoviePy ⛔. |
| **K8** QC | QC ảnh 2 lớp, QC clip, QC bản dựng cuối bằng máy, Tổ QC (Claude nhìn + code áp luật) | **ArcFace/DINO cosine** (nhất quán danh tính), **CLIP-score** (khớp chữ), **VMAF** (BSD+Patent, so bản nén với bản gốc), **DOVER/FAST-VQA** (chất lượng không cần bản gốc) | Mình dùng **Claude nhìn** → bài học riêng: model nhìn đúng nhưng kết luận sai. Số cosine là **kiểm bằng code** đúng triết lý "model khai, code áp luật". VMAF cần **bản tham chiếu**: video AI **không có** → chỉ hợp kiểm *bản xuất so với bản dựng gốc*. | 💻 **ArcFace/DINO + VMAF xuất-vs-gốc** thử trên mẫu có sẵn (0 USD, CPU). Lưu ý **trọng số InsightFace chỉ cho nghiên cứu phi thương mại** [B] → ưu tiên DINO/mô hình có giấy phép rõ; kiểm giấy phép trước. DOVER: 💻 thử nếu CPU đủ nhanh, chưa kiểm. |
| **K9** Chi phí | Sổ chi + ước tính trước + khóa cứng 3 tầng | Langfuse: cây vết + **công thức giá tùy chỉnh** + dashboard; Helicone: proxy | Mình **chặn trước** (họ ghi sau) → hơn. Thiếu **cây vết theo shot** và **biểu đồ tiêu hao theo thời gian / khâu**. | 💻 làm trong dashboard (ý 4, 5); ⛔ nhúng công cụ ngoài. |
| **K10** Vận hành / cộng tác | Autopilot + cổng + cờ + AI Dev System + hộp thư "📥 Việc cần bạn" | LangGraph: **tạm dừng có tên, chụp trạng thái, chạy lại từ điểm cũ**; n8n: webhook thông báo; Label Studio: từ chối 2 kiểu | Mình đã có hộp thư + mức tự động; thiếu hành động ngay trong hộp thư, nhật ký tự duyệt, rẽ nhánh từ cổng. | 💻 ý 1, 2, 7, 8, 9 mục 3. n8n/LangGraph/CrewAI ⛔ nhúng. |

## 3. Dashboard: họ tổ chức thế nào, và 12 ý cụ thể cho dashboard của mình
### 3.1 So sánh cách tổ chức
| Khía cạnh | Công cụ ngoài (nhóm B + hộp thư agent) | Dashboard mình hiện có [R] | Chênh lệch chính |
|---|---|---|---|
| **Tổng quan dự án** | Langfuse: bảng chạy + cây vết; n8n/ComfyUI: lịch sử chạy + hàng chờ + biểu đồ node | `dashboard/overview.py` (4 thẻ: Kịch bản → Duyệt → Đang sản xuất → Video cuối), `home.py` (lưới thẻ dự án, lọc, hero) | Mình rất rõ **ở mức bước**; thiếu nhìn **shot × khâu** một màn. |
| **Hộp thư việc cần làm** | Agent inbox: mỗi mục có **chủ, trạng thái, ưu tiên**, hành động **duyệt / sửa / từ chối / chuyển lên** ngay trong dòng; Label Studio từ chối 2 kiểu | `header.inbox_card` + `core/inbox.py`: 6 loại việc (Ảnh, Video, Ngân sách, Tiền, Chạy tự động, Hạn mức), chỉ nút "Mở →" | Mình có hộp thư thật; **thiếu hành động tại chỗ**, **thiếu sắp theo mức chặn dây chuyền**, **thiếu hoãn / giao**. |
| **Mức tự động / cổng duyệt** | LangGraph: điểm dừng có tên + chụp trạng thái + chạy lại; "chế độ nháp → mới cho tự thực hiện" | `header.level_bar` + `core/automation.py` (3 thứ gom một lựa chọn: người duyệt + cổng + độ chặt QC); khóa khi đang chạy | Mình **mạnh** (một lựa chọn gom 3 thứ). Thiếu **xem trước "sẽ dừng ở đâu"** và **nhật ký tự duyệt có thể đảo ngược**. |
| **Tooltip / giải thích** | Langfuse: mỗi điểm đánh giá có **nhận xét + nguồn chấm** (người / model / code) | `docs/QUY_TAC_BO_CUC_UI_V2.md` mục 5–6: P1–P4, tooltip + popover, không còn nút ⓘ | Mình **hơn rõ rệt** về quy tắc. Thiếu **gắn nguồn của một con số** (code / Claude / người). |
| **Chi phí** | Langfuse / Helicone: biểu đồ theo thời gian, theo model, theo người dùng; cảnh báo ngưỡng | `header.money_card`, `team_screen.py` (bảng người), `status_line` có `_budget_bit`, `core/budget.py` | Mình **chặn trước + ước tính**; thiếu **biểu đồ tiêu hao** + **chi phí theo shot**. |
| **QC** | Langfuse: bảng **so điểm giữa các lần chạy**, bộ dữ liệu cố định để chấm lại | Pill trạng thái, `final_qc.py`, QC clip, chú thích QC dài trong popover | Mình có nhiều chỉ số nhưng **chưa xem xu hướng qua các lần gen lại**. |

### 3.2 Mười hai ý (mỗi ý kèm file / màn). Mọi ý **💻 0 USD**, không nhúng dịch vụ ngoài; tuân `QUY_TAC_BO_CUC_UI_V2.md` (một nút chính mỗi vùng, không điều khiển chỉ hiện khi rê chuột, không mất điều khiển cũ).
1. **Chụp trạng thái tại mỗi cổng duyệt** (LangGraph checkpoint). Khi autopilot dừng, lưu "ảnh chụp" (phiên bản kịch bản, điểm QC, ngân sách còn lại) để người duyệt xem **đúng cái đã thấy lúc đó** và sau này so. Liên quan: `core/autopilot.py`, `dashboard/next_step.py`, `core/lineage.py`.
2. **Hành động ngay trong hộp thư**. Thêm vào mỗi mục của "📥 Việc cần bạn": **Duyệt / Từ chối / Hoãn** (khi mục không cần xem chi tiết, vd. "Ngân sách" có nút Nâng trần có xác nhận). Giữ "Mở →" làm nút chính. Liên quan: `dashboard/header.py::inbox_card`, `core/inbox.py`.
3. **Sắp hộp thư theo "chặn dây chuyền"**: việc đang chặn autopilot / tiền hết lên đầu (đã có `level` bad/wait/warn/todo nhưng chưa sắp theo *thời gian chờ* và *số shot bị chặn*). Hiện "đã chờ 3 giờ · chặn 12 shot". Liên quan: `core/inbox.py`, `dashboard/header.py`.
4. **Cây vết một shot**: popover trên thẻ clip liệt kê *lần gen nào, đầu vào nào đổi, tiền, bao lâu, điểm QC* (kiểu span của Langfuse). Dữ liệu đã nằm ở `usage_events` + `jobs`. Liên quan: `dashboard/steps/step4.py`, `dashboard/steps/step2.py`, `core/db.py`, `core/lineage.py`.
5. **Biểu đồ tiêu hao vs trần 3 tầng + dự báo**: đường tiền đã chi theo thời gian, trần dự án / việc, và dòng "với tốc độ này còn đủ khoảng N lần gen lại". Liên quan: `dashboard/header.py::money_card`, `dashboard/team_screen.py`, `core/budget.py`, `core/cost.py`; dùng `meter(..., invert=True)` theo luật 5.
6. **Bảng điểm QC theo lần gen** (eval-run): mỗi hàng một lần gen lại, cột là chỉ số (đồng nhất mặt, trôi phong cách, khớp môi, độ ồn/LUFS), tô màu tốt lên / xấu đi so với lần trước — cho thấy gen lại đã **thật sự cải thiện** chưa (khớp quy ước "đã sửa" kèm bằng chứng). Liên quan: `dashboard/steps/step4.py`, `step5.py`, `core/final_qc.py`, `core/autoqc.py`.
7. **Từ chối hai kiểu** (Label Studio): "Loại bỏ" (bỏ khung) khác "Gửi lại kèm ghi chú" (vào hàng chờ gen lại, tính vào hạn mức gen lại ≤ 2). Ghi chú đi cùng **đổi đầu vào bắt buộc** để không gen lại y hệt. Liên quan: `dashboard/steps/step2.py` (thẻ ảnh), `dashboard/common.py::confirm_all`, `dashboard/design/screens/storyboard_cards.py`.
8. **"Tạo nhánh từ cổng duyệt"**: nhân bản dự án *từ một ảnh chụp* (ý 1) thay vì từ cuối — kiểu "du hành thời gian" LangGraph; tái dùng nhân bản dự án. Liên quan: `dashboard/header.py::_dialog_clone`, `core/archive.py`, `core/lineage.py`.
9. **Webhook thông báo khi cổng chờ / hết tiền / lỗi** (thay n8n): một cờ + một URL do người dùng cấu hình; không gửi nội dung kịch bản, chỉ "dự án #X đang chờ duyệt ở cổng Y". **Cần người dùng xác nhận kênh trước khi làm** (quy tắc: không gửi dữ liệu ra ngoài khi chưa được phép). Liên quan: `core/autopilot.py`, `core/inbox.py`, `dashboard/header.py::settings_menu`.
10. **Bản đồ nhiệt shot × khâu** ở "Đang sản xuất": mỗi shot một ô, mỗi khâu (ảnh · video · âm · QC) một màu theo pill chuẩn (Cần duyệt · Đang làm · Đã duyệt · Từ chối · Lỗi · Chờ gen), bấm ô mở thẻ shot. Giống bảng chạy n8n/ComfyUI nhưng theo shot. Liên quan: `dashboard/overview.py`, `dashboard/design/components.py` (pill/meter), `dashboard/design/screens/video_ui.py`.
11. **Nhật ký tự duyệt có đảo ngược + "xem trước sẽ dừng ở đâu"** cho `level_bar`: bên cạnh mô tả mỗi mức, hiện danh sách cổng sẽ dừng; sau khi chạy, liệt kê "tự duyệt N mục vì điểm ≥ ngưỡng" với nút **Đưa lại vào hàng duyệt** (khuyến nghị "chế độ nháp trước" của hộp thư agent). Liên quan: `dashboard/header.py::level_bar`, `core/automation.py`, `core/autopilot.py`.
12. **Gắn nguồn cho mỗi con số QC** (🧮 code · 🤖 Claude · 👤 người) ngay trong pill/tooltip, đi cùng nhận xét — để người duyệt biết điểm này là **luật chạy bằng code hay ý kiến model** (bài học Tổ QC: model nhìn đúng nhưng kết luận sai). Liên quan: `dashboard/design/components.py` (`pill`, `note`, `tip`), `core/autoqc.py`, `dashboard/steps/step2.py`.

*(Ý bổ sung, không đánh số vì lớn: **duyệt theo bản chép lời** — người duyệt bấm bỏ / đổi chỗ câu trong bản chép lời video cuối, dùng whisper sẵn có; xem K7 / mục 1.6.)*

## 4. Việc "nên làm" tóm lại (đề xuất, chờ người dùng chọn)
- **💻 Áp dụng ngay (0 USD, chỉ dashboard / code mình):** ý 1, 2, 3, 4, 5, 6, 7, 10, 11, 12 (mục 3.2); thử **ArcFace/DINO + VMAF (bản xuất vs bản dựng gốc)** trên mẫu có sẵn (kiểm giấy phép trọng số trước).
- **💻 Thử nhỏ không cam kết:** MuseTalk / LatentSync-1.5 trên **một** clip để xem có chạy trên 8 GB Pascal và có khớp môi nhân vật 3D không; đo thử 1 workflow Wan-5B / LTX nhỏ để *ghi số đo thật* của máy.
- **💵 Thử có trần:** **Debate-Judge** cho **một** quyết định mơ hồ trên 1 dự án (trần lượt + trần token; qua sổ chi + ước tính trước theo `CHUAN_XAY_DUNG.md`).
- **Cần người dùng xác nhận trước:** ý 8 (nhánh từ cổng), ý 9 (webhook ra ngoài).
- **⛔ Bỏ qua:** nhúng ComfyUI làm lõi video, n8n / Make / Zapier làm lõi, LangGraph / CrewAI / AutoGen, Langfuse / Helicone / LangSmith (nhúng), Remotion / MoviePy, Wav2Lip, "2 ứng viên + VLM chọn" kiểu ViMax, dùng Descript / Premiere / Resolve làm bước chính.

## 5. Rủi ro tổng hợp
- **Phần cứng**: GTX 1070 Ti 8 GB (Pascal) → mọi mô hình cục bộ (Wan 14B, HunyuanVideo, LatentSync 1.6) **không vừa**; số trong bài [B] chưa kiểm trên máy này.
- **Giấy phép**: ComfyUI GPL-3.0 (chỉ gọi qua API); n8n Sustainable Use (không OSI); Remotion cần giấy phép công ty khi > 3 người; **InsightFace: code MIT nhưng trọng số phi thương mại** [B]; Wav2Lip GAN không dùng thương mại [B]; LatentSync Apache 2.0; MuseTalk MIT; VMAF BSD+Patent; Label Studio Apache 2.0; Langfuse lõi MIT; LangSmith tự host chỉ Enterprise.
- **Nguồn [B] có thể sai/cũ** (giá, VRAM, giấy phép từng gói); **chưa tải / chạy** gì → chưa có bằng chứng chạy thật theo quy ước "đã sửa kèm bằng chứng".
- **Dữ liệu ra ngoài**: mọi dịch vụ đám mây (Langfuse Cloud, Make, Zapier, Descript) sẽ nhận prompt / ảnh nhân vật FF → không dùng nếu chưa cho phép.

## 6. Nguồn (đọc 2026-10-03)
- [A] ViMax README: https://github.com/HKUDS/ViMax · bài: https://arxiv.org/html/2606.07649v1
- [A] MovieAgent README: https://github.com/showlab/MovieAgent
- [B] FilmAgent (bài + tóm tắt): https://arxiv.org/pdf/2501.12909 · https://filmagent.github.io/
- [B] StoryAgent: https://arxiv.org/abs/2411.04925 · CineForge: https://arxiv.org/pdf/2608.29621 (chỉ thấy tiêu đề)
- [A] ComfyUI README: https://github.com/comfyanonymous/ComfyUI · [B] VRAM Wan/LTX/Hunyuan: https://www.spheron.network/blog/ai-video-generation-gpu-guide/ · https://localaimaster.com/blog/local-ai-video-generation
- [B] n8n / Make / Zapier: https://www.virtua.cloud/learn/en/concepts/n8n-vs-zapier-vs-make-cost-privacy · https://instapods.com/blog/n8n-pricing/
- [A] LangGraph HITL / checkpointers: https://docs.langchain.com/oss/python/langchain/human-in-the-loop · https://docs.langchain.com/oss/python/langgraph/checkpointers
- [B] LangGraph vs CrewAI vs AutoGen: https://pickaxe.co/post/crewai-vs-langgraph-vs-autogen · https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63
- [A] Remotion giấy phép: https://www.remotion.dev/docs/license/pricing · [B] https://sumeetkg.medium.com/video-as-code-which-library-should-you-choose-8807ac1bda6b
- [B] Descript: https://www.letscompareai.com/post/descript-underlord-update-faster-ai-video-editing-for-creators-in-2026 · Premiere 26.5: https://www.kylerholland.com/blog/premiere-pro-september-2026-whats-new/
- [A/B] DaVinci Resolve 20: https://www.blackmagicdesign.com/media/partial/release/20250404-02 · https://aitoolanalysis.com/davinci-resolve-20-review-ai-video-editing/
- [B] Langfuse / Helicone / LangSmith: https://www.premai.io/blog/llm-observability-setting-up-langfuse-langsmith-helicone-phoenix/ · https://www.openhelm.ai/blog/langsmith-vs-helicone-vs-langfuse-comparison
- [A] LatentSync: https://github.com/bytedance/LatentSync · [B] so sánh lip-sync: https://tomodahinata.com/en/blog/ai-lip-sync-talking-head-model-selection-guide-2026 · https://lipsync.com/compare/wav2lip-vs-latentsync
- [A] VMAF: https://github.com/Netflix/vmaf · [B] DOVER/FAST-VQA: https://www.forasoft.com/learn/video-quality/articles-vqm/open-source-no-reference-tools
- [A] InsightFace: https://github.com/deepinsight/insightface · [B] chỉ số danh tính: https://arxiv.org/html/2508.09476v2
- [A] Label Studio: https://github.com/HumanSignal/label-studio · https://docs.humansignal.com/guide/onboarding_reviewer
- [B] Hộp thư agent: https://ai.agentmail.to/agent-inbox-what-it-is-when-to-use-it-and-how-to-design-one-safely · https://developer.nylas.com/docs/cookbook/agents/inbox-zero/
- [R] Repo mình: `docs/SO_SANH_PHAN_MEM_NGOAI_2026-09-29.md`, `docs/QUY_TAC_BO_CUC_UI_V2.md`, `dashboard/header.py`, `dashboard/overview.py`, `dashboard/home.py`, `dashboard/next_step.py`, `core/inbox.py`, `core/cost.py`
