# Nguồn tiếng Trung — sản xuất AI短剧 (S phiên 2026-09-29)

Theo phương pháp `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 3. Tất cả đọc/tra ngày **2026-09-29**. Độ tin: **cao** = chính
người/tổ chức làm nghề nói việc mình làm, tài liệu chính thức của công cụ, hoặc báo chí có phỏng vấn trực tiếp; **vừa** = cá
nhân/trang có biên tập chia sẻ kinh nghiệm thực chiến (không phải phỏng vấn của bên thứ ba xác minh), hoặc bài đọc được nhờ
tổng hợp WebSearch (không đọc trọn); **thấp** = mang tính quảng cáo sản phẩm rõ, không kiểm chứng được. Cột "Đọc" ghi trọn
văn (qua trình duyệt) hay chỉ tóm tắt/snippet WebSearch.

## A. Tài liệu chính thức model

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| 1 | Doubao Seedance 2.5 提示词指南 | 火山引擎 (Volcengine/ByteDance) — tài liệu chính thức | Cấu trúc prompt, tham chiếu đa phương thức, mốc giây, khác biệt với 2.0, 10+ case lỗi thường gặp kèm ví dụ | https://docs.volcengine.com/docs/ark/seedance-2-5-prompt-guide?lang=zh | cao | trọn văn | Nguồn quan trọng nhất đợt này — đọc hết qua trình duyệt (WebFetch bị chặn JS) |
| 2 | Seedance 2.0 文生视频提示词编写指南 | 火山引擎 — tài liệu chính thức | Khung 4 thành phần: chủ đề/nội dung cốt lõi, phong cách/tông, chi tiết hình ảnh/chuyển động, định dạng kỹ thuật | https://www.volcengine.com/article/40840 | cao | tóm tắt có cấu trúc (WebFetch, không phải toàn văn) | Bổ sung cho #1; #1 mới và chi tiết hơn |
| 3 | ClipAI — tài liệu chính thức (đã có từ trước) | ClipAI/ByteDance | Seedance Model Selection, Seed Audio 1.0 Guide, Game Video Production | https://clipai.ingarena.net/docs/ | cao | trọn văn (đợt trước) | Dẫn lại từ `docs/CAP_NHAT_CLIPAI_2026-09-28.md`; không fetch lại |
| 4 | Kling AI Open Platform — 概览 | 快手 Kuaishou — tài liệu chính thức | API tổng quan | https://www.klingai.com/document-api/guides/get-started/overview | — | trang không tải được nội dung (chặn/lazy-load) | Chưa dùng được làm căn cứ — cần đọc lại lượt sau |

## B. Quy trình sản xuất AI短剧 (production workflow)

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| 5 | The Paper (澎湃新闻) — "AI颠覆剧组，七天打造爆款短剧" | Báo chính thống, phỏng vấn Zhu Jiang (朱江) — CEO 井英科技 (CreativeFitting), đạo diễn Cui Yi (崔伊) | 7 bước quy trình, đội hình co giãn 1→10 người, chi phí ≈20% quay thật | https://www.thepaper.cn/newsDetail_forward_30692653 | cao | trọn văn (WebFetch) | 2025-04-22; case cụ thể có tên phim, tên người |
| 6 | Yicai (第一财经) — bài kinh tế ngành AI漫剧/短剧 | Chen Yangyuan (陈杨园), biên tập Liu Jia | Chi phí/phút, tốc độ sản xuất, ROI, tên công ty (灵鹃动画/Lingju Animation) | https://www.yicai.com/news/103084978.html | cao | trọn văn (WebFetch) | 2026-03-13; báo kinh tế chính thống, có số liệu ROI 1.05–1.2, tỷ lệ có lãi ~20% |
| 7 | CNBlogs — "AI短剧制作全攻略，我总结了这些经验" | 小吴努力中 (cá nhân, tự nhận đã làm) | 4 giai đoạn cụ thể (kịch bản→phân cảnh→sinh video→lồng tiếng/dựng), chi phí công cụ theo giây, 4 nguyên tắc viết prompt ảnh tĩnh | https://www.cnblogs.com/wuuu/p/19095969 | vừa–cao | trọn văn (WebFetch) | 2025-09-17; kinh nghiệm cá nhân nhưng có số liệu cụ thể (giá, tỷ lệ thành công 20%) |
| 8 | Zhihu — "AI短剧全流程生成技术指南" | AIAgent学习研究 (bút danh cá nhân) | Từ 豆包 (kịch bản) → 豆包 (phân cảnh) → 即梦 Seedance2.0 Fast (video) → 剪映 (dựng), có prompt mẫu | https://zhuanlan.zhihu.com/p/2008560818791407761 | vừa | trọn văn (browser) | 2026-02-21; hướng dẫn thực hành từng bước, không phải chuyên gia có tên tuổi |
| 9 | WebSearch tổng hợp — 天工短剧工作台 (36氪/搜狐) | 36氪, 搜狐 — báo công nghệ | Vai trò "đạo diễn AI agent", lộ trình 2026: lập dự án→kịch bản hoá→kho tài sản nhân vật/cảnh→phân cảnh→sinh video từng shot→lồng tiếng→hậu kỳ→QC→phát hành→đo dữ liệu | https://www.36kr.com/p/3897777804002950 , https://www.sohu.com/a/1051125928_121948416 | vừa | snippet only | Chưa đọc trọn bài — cần đọc lại nếu dùng làm căn cứ chính |

## C. Nội dung — kịch bản short drama

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| 10 | Sohu — "AI短剧脚本怎么写？30分钟出大纲的5步全攻略" | Tác giả ẩn danh, trang tổng hợp có biên tập | Nguyên lý 3 chữ (nhanh/gắt/chuẩn), 4 quy trình viết kịch bản, 5 kỹ thuật nâng cao | https://www.sohu.com/a/1047926541_121123989 | vừa | trọn văn (WebFetch) | Không rõ tác giả cụ thể — dùng làm khung tham khảo, không phải luật cứng |
| 11 | Tahou (塔猴) — "10个爆款钩子公式" | Trang quan sát AI ("AI观察者"), tác giả ẩn danh | 10 công thức mở đầu/hook, cảnh báo 3 điểm thất bại | https://www.tahou.com/article/203357461598752773 | vừa | trọn văn (WebFetch) | Trang tổng hợp ngành, không phải phỏng vấn 1 biên kịch cụ thể |
| 12 | WebSearch tổng hợp — nội dung phù hợp/AI优劣势 (thepaper, huxiu, cbndata) | Báo công nghệ (虎嗅, 澎湃, CBNData) | Thể loại hợp AI (kỳ ảo, kinh dị — hiệu ứng "uncanny valley" tự nhiên hợp kinh dị), thể loại không hợp (tình cảm hiện thực đòi diễn xuất tinh tế); mô hình "AI+người thật" | https://m.thepaper.cn/newsDetail_forward_32877551 , https://www.huxiu.com/article/4872259.html | vừa | snippet only | Tổng hợp qua WebSearch, chưa đọc trọn từng bài — dùng làm gợi ý, không phải luật |

## D. Prompt craft

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| (1,2,3) | *(xem nhóm A — đây là nguồn chính cho PROMPT.md)* | | | | | | |
| 13 | Feishu wiki "可灵学习手册" (万象AI实验室/MixAILab) | Cộng đồng, tác giả "user 4870" / 高帆文化, 50万+ độc giả, cập nhật liên tục từ 2024 | 12 mẹo viết prompt (rất chung chung — độ chi tiết thấp hơn tài liệu Seedance 2.5) | https://yunyinghui.feishu.cn/wiki/I55CwRyeSiPhmNkztwdcJ3jdnbc | vừa | trọn văn phần liên quan (browser) | Kho kiến thức cộng đồng lớn (giống WaytoAGI), nhiều chuyên mục khác (AI短剧学习专区, Seedance…) chưa khai thác hết — có thể quay lại |

## E. Nhất quán nhân vật/cảnh/giọng

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| 14 | Zhihu — "解决AI短剧角色、场景、声音一致性，3个关键方案" | "AI也不要香菜" (cá nhân, tự nhận đã thực chiến) | 3 giải pháp cụ thể: thẻ hồ sơ nhân vật điện ảnh, lưới 9 ô không gian cảnh, tách giọng tham chiếu từ clip trước | https://zhuanlan.zhihu.com/p/2050534732618905039 | vừa | trọn văn (browser) | 2026-06-17; có prompt mẫu cụ thể, 5 lượt tán thành — mức phổ biến thấp, coi là 1 cách làm không phải chuẩn ngành |
| 15 | WebSearch tổng hợp — CHAR 资产库, LoRA/Dreambooth, IP-Adapter | Nhiều bài CSDN/Zhihu (kỹ thuật) | Phương pháp kỹ thuật nền: huấn luyện LoRA 20 ảnh góc khác nhau, IP-Adapter | (nhiều URL trong kết quả tìm kiếm, chưa fetch riêng) | vừa | snippet only | Nền tảng kỹ thuật SD/ComfyUI — không phải cách ClipAI/Seedance dùng (ClipAI dùng kho chủ thể chính thức, xem `docs/CAP_NHAT_CLIPAI_2026-09-28.md`) |

## F. Ngành & chi phí

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| (5,6) | *(xem nhóm B — đây là nguồn chính cho chi phí)* | | | | | | |

## G. Âm nhạc/BGM (bổ sung theo yêu cầu 2026-09-29)

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc | Ghi chú |
|---|---|---|---|---|---|---|---|
| 16 | Zhihu — "短剧剪辑技巧——怎么给短剧配乐，音乐音效设计" | 曲多多音乐素材网 — tài khoản tổ chức đã xác thực ("已认证机构号"), đơn vị bán nhạc bản quyền cho short drama | Nhịp cảm xúc 4 giai đoạn (giữ người mở đầu→thiết kế phản转→nén nhịp/vào thẳng điểm sướng→kết thúc gài悬念), 15 playlist theo thể loại cụ thể (phục thù/hào môn, tổng tài/ngọt sủng, xuyên không/hệ thống, cung đấu, huyền huyễn, trinh thám…) | https://zhuanlan.zhihu.com/p/2070521242822743278 | vừa–cao | trọn văn (browser) | 2026-08-11; nguồn ngành (bán dịch vụ nhạc cho AI短剧) nên có thể thiên lệch quảng cáo gói dịch vụ, nhưng bảng ánh xạ thể loại↔nhạc cụ thể và có dẫn chứng nghề |
| 17 | Zhihu — "短剧/微电影的原创配乐：用AI生成，成本直降90%" | "阿饱饱" (cá nhân, bài tự ghi "bao gồm nội dung AI hỗ trợ") | Cấu trúc prompt nhạc "phong cách+nhạc cụ+cảm xúc+BPM/tempo", số liệu chi phí truyền thống vs AI, quy trình 4 bước, cảnh báo bản quyền giọng ca sĩ | https://zhuanlan.zhihu.com/p/2048406672863934095 | thấp–vừa | trọn văn (browser) | 2026-06-11; mang tính quảng cáo 1 công cụ cụ thể (蘑兔AI) — chỉ dùng số liệu ngành chung, KHÔNG dùng để giới thiệu công cụ |
| 18 | WebSearch tổng hợp — nguyên tắc âm lượng/âm hiệu short drama | Nhiều bài CSDN/SegmentFault (chưa xác định tác giả cụ thể) | BGM 10–15% âm lượng so với thoại; bộ âm hiệu bắt buộc (tát, tim đập, chuyển cảnh chớp trắng, dừng đột ngột, tiếng mở cửa); cấu trúc prompt nhạc AI "phong cách+nhạc cụ+cảm xúc+tốc độ", ghi rõ "instrumental/no lyrics" để tránh AI sinh giọng hát chồng lời thoại | (tổng hợp WebSearch, không có 1 URL đại diện) | thấp | snippet only | Số liệu lặp lại ở nhiều bài tổng hợp — coi là quy ước phổ biến trong ngành, không có nguồn cụ thể xác minh được |
| — | ClipAI — Seed Audio 1.0 Guide (đã có, nhóm A #3) | ClipAI/ByteDance — chính thức | 1 lệnh sinh cả track thoại+nhạc+hiệu ứng+nền; khoá giọng bằng tối đa 3 mẫu; mốc 100ms; không SSML | https://clipai.ingarena.net/docs/ | cao | trọn văn (đợt trước) | Nguồn chính thức duy nhất về công cụ nhạc mà pipeline đang/sẽ dùng |

## Nguồn cân nhắc nhưng KHÔNG dùng làm căn cứ kỹ thuật
- Zhihu "Seedance 2.0 提示词官方指南" (p/2050274027709768829): WebFetch trả 403, chưa đọc được — không trích dẫn nội dung.
- Kling AI Open Platform docs: trang không tải được nội dung qua công cụ hiện có — chưa dùng làm căn cứ, chỉ ghi nhận là có tồn tại tài liệu chính thức.
- "可灵驯服指南", GitHub `kling-ai-guide`, các trang tổng hợp prompt bên thứ ba khác (Fliki, Higgsfield…): theo quy ước đã có trong `research/craft/NGUON.md`, không dùng làm nguồn kỹ thuật chính thức cho Kling/Seedance.
- Bài quảng cáo công cụ nhạc cụ thể (#17) chỉ dùng phần số liệu ngành, không dùng để khuyến nghị công cụ.

**Tổng: 18 dòng nguồn mới** (nhóm A–G) + 1 dòng dẫn lại từ nguồn ClipAI đã có trước. Chưa đạt mốc 20–30 đầy đủ như đề bài mong muốn —
lý do: nhiều trang chặn WebFetch (Zhihu 403, Kling docs không tải nội dung), phải chuyển sang trình duyệt tốn thêm lượt; đã ưu
tiên đọc trọn văn các nguồn chính thức (#1, #5, #6, #7, #14, #16, #17) hơn là thêm nhiều dòng snippet-only cho đủ số.

## H. Lượt 2 (2026-09-29) — Kling chính thức, người làm có tên, luật mới

| # | Nguồn | Tác giả/tổ chức | Chủ đề | URL | Độ tin | Đọc |
|---|---|---|---|---|---|---|
| 19 | Kling VIDEO 3.0 Model Guide | Kling AI (快手) — chính thức | Multi-Shot tự động / tự viết, 3–15 s, Element Binding (ảnh/video + giọng), thoại 5 ngôn ngữ (không có tiếng Việt), gắn thoại theo nhân vật, khung đầu–cuối | https://kling.ai/quickstart/klingai-video-3-model-user-guide | cao | trọn trang (WebFetch) |
| 20 | 「可灵 AI」驯服指南 V2.0 | 可灵 (bản chia sẻ trên 轻雀文档) | Công thức 主体+运动+场景+(镜头语言+光影+氛围) | https://docs.qingque.cn/d/home/eZQDp092-vzqbhb02KUdurkwP | vừa–cao | trang tải được một phần |
| 21 | 搜狐 — 可灵 3.0 提示词指南 | trang tổng hợp, dẫn lại acceptprompt.com | Công thức 3.0 thêm 声音; viết như lời đạo diễn; mô tả giọng = tuổi+chất giọng+tốc độ+cảm xúc+ngôn ngữ | https://www.sohu.com/a/1036042907_121123989 | vừa | tóm tắt WebFetch |
| 22 | 量子位 — 可灵3.0 … 分镜逻辑封神 | Jay, 2026-02-07 | Thử thật Multi-Shot; điểm yếu chia thoại giữa nhân vật | https://www.qbitai.com/2026/02/377608.html | vừa | tóm tắt WebFetch |
| 23 | 品玩 — 他用仨AI，10天"肝"出全网刷屏AI短剧 | 黄小艺, 2024-07-16 | 陈坤 (闲人一坤): quy trình trailer 《山海奇镜》, truyện là trụ chính | https://www.pingwest.com/a/296655 | cao (phỏng vấn) | tóm tắt WebFetch |
| 24 | 百度 TA说 — 《山海奇镜》导演陈坤 | phỏng vấn | Đội 10 người, 2 tháng, chọn truyện đơn giản vì giới hạn kỹ thuật | https://wapbaike.baidu.com/tashuo/browse/content?id=ea61c9a4208a0aff39ef48fb | vừa | snippet WebSearch |
| 25 | 澎湃 — 《山海奇镜之劈波斩浪》：AI制作的跨越与技术局限 | 金云水, 王帅帅 (同济大学), 2025-02-24 | Phê bình: khớp môi, vi biểu cảm, tương tác | https://m.thepaper.cn/newsDetail_forward_30225424 | cao | tóm tắt WebFetch |
| 26 | 腾讯新闻/潮新闻 — AI短剧"Action"｜"抽"出来的爆款 | 潮新闻, 2026-09-05 | Phỏng vấn nhiều người (陈妍, 王昊, 雷迪克…), số lần gen, chi phí, DataEye 98,7% | https://news.qq.com/rain/a/20260905A03MPK00 | cao | tóm tắt WebFetch |
| 27 | 腾讯新闻/潮新闻 — 不拍戏、不搭景，我在电脑前"抽"出一部短剧 | 潮新闻, 2026-09-02 | Quy trình 抽卡师 6 bước, nhóm 15 s, 4–15 lần/clip | https://news.qq.com/rain/a/20260902A08U3500 | cao | tóm tắt WebFetch |
| 28 | 虎嗅 — 横店消亡，短剧新生：2026，AI抽卡师接管片场 | 岳涌, 2026-04-29 | 张强 (tên giả): "tách xác suất", ~500 clip cho 1 cảnh | https://www.huxiu.com/article/4854701.html | vừa | tóm tắt WebFetch |
| 29 | WaytoAGI — Chat with Wiki: 分镜提示词 / 视频脚本和分镜 | WaytoAGI (cộng đồng) | Cấu trúc prompt phân cảnh, cột nhạc/âm hiệu trong bảng | https://www.waytoagi.com/zh/question/65668 ; https://www.waytoagi.com/question/57530 | vừa–thấp | snippet WebSearch |
| 30 | 新华网 — 《微短剧发展管理办法》9月1日起施行 | 新华社, 2026-07-31 | AI tác phẩm phải có nhãn nhắc mỗi tập | https://www.news.cn/20260731/9d0579e4587648fb83580e0fec008e12/c.html | cao | tóm tắt WebFetch |

Không đọc được: Zhihu p/2020810861183254701 (曲多多, nhắc 梁雨箫 — 403); phát biểu của 梁雨箫 chỉ biết qua snippet tìm kiếm → không dùng làm căn cứ.
