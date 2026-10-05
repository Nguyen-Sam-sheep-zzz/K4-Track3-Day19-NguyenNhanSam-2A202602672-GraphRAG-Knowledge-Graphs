# Phần 1 — Môi trường và thiết kế ontology

Ngày thực hiện: 05/10/2026. Đây là checkpoint, chưa phải báo cáo benchmark hoặc bản nộp cuối.

**Cập nhật:** Gemini key đã được bổ sung và smoke thật đạt 3072 chiều (`part01_gemini.json`). KG-1..KG-4 đã triển khai ở PART02/PART03. Các mục dưới đây giữ lại hiện trạng lịch sử tại checkpoint đầu, không mô tả hiện trạng cuối.

## Kết quả đã xác minh

| Nội dung | Bằng chứng | Trạng thái |
| --- | --- | --- |
| Python / SDK | Python 3.11.7; pytest 9.1.1; dotenv 1.2.2; neo4j 6.2.0; openai 2.46.0 | Có thể chạy |
| Key local | Chỉ ghi set/missing, không đưa key vào checkpoint | Đã cấu hình |
| Neo4j | Driver verify_connectivity thành công; RETURN 1 trả 1; 0 node trước công việc | Kết nối và xác thực đạt; chưa dựng graph |
| Chat | DevQuota, gpt-6-luna; một request trả đúng OK; usage 19 input/5 output token | Smoke thật đạt |
| Embedding API | text-embedding-3-small tại DevQuota trả HTTP 503, model_not_found; models.list trả 36 model, không có ứng viên embedding | DevQuota chưa có lựa chọn embedding được xác nhận; đã chọn chuyển Gemini |
| Test gốc | 41 passed, 7 failed in 0.08s | Base đạt; graph TODO chưa triển khai |
| Ontology | Bảy label, bảy quan hệ, Crime cầu nối; source/đường Q1–Q6; sáu quyết định thiết kế | Đã điền thiết kế; chưa đối chiếu graph thật |

## Chẩn đoán cấu hình API

1. Tiến trình ban đầu có key/base URL kế thừa. Key kế thừa khác key trong .env. `load_dotenv(override=False)` không thay giá trị môi trường đã có; smoke ban đầu trả 401.
2. Thử đúng key trong .env nhưng .env thiếu base URL: request đến OpenAI chính thức trả 401 invalid_api_key.
3. Người dùng xác nhận key do gateway cấp và cung cấp https://sv.devquote.shop. Tài liệu DevQuota công khai xác nhận endpoint https://sv.devquote.shop/v1.
4. Bổ sung OPENAI_BASE_URL vào .env local, giữ nguyên key và model. Trong tiến trình kiểm tra, bỏ cấu hình provider kế thừa rồi nạp .env của dự án. Chat thành công.
5. Embedding vẫn lỗi model_not_found. Không coi đây là lỗi key vì chat đã xác thực được. Danh mục công khai của gateway không liệt kê text-embedding-3-small tại thời điểm kiểm tra.
6. Theo yêu cầu người dùng, gọi models.list trên API thật: 36 model, không có tên model embedding, configured chat có trong danh mục, configured embedding không có. Vì không có ứng viên embedding được quảng bá trong danh mục và model cấu hình đã lỗi, chưa có giá embedding nào để so sánh tại DevQuota. Người dùng chọn Gemini nếu gateway không cung cấp.
7. Đã chuyển `.env` local sang `EMBEDDING_PROVIDER=gemini`, `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`. Cần người dùng bổ sung GEMINI_API_KEY ở local; chưa gửi request Gemini, chưa xác minh quota/giá.

Ở các lần chạy tiếp theo cần dùng cấu hình .env của dự án một cách rõ ràng, tránh để key/base URL kế thừa của môi trường agent trộn với cấu hình local.

## Chi phí: điểm cần sửa trước benchmark

`src/llm.py` chưa có gpt-6-luna trong PRICES_PER_M nên smoke thành công ghi USD=0.0. Đây là thiếu bảng giá, **không phải** chứng cứ request miễn phí.

Nguồn đã đọc ngày 05/10/2026:

- OpenAI: https://developers.openai.com/api/docs/models/gpt-6-luna — giá Standard cho text input/output lần lượt 0.10/0.50 USD mỗi triệu token; cache/processing có giá riêng.
- DevQuota: https://devquota.shop/models — công bố gpt-6-luna input/output 0.10/0.50 USD mỗi triệu token, cache read 0.01 và cache write 0.125.
- DevQuota docs: https://devquota.shop/docs — endpoint https://sv.devquote.shop/v1 trong hướng dẫn cấu hình.

Ước tính tham chiếu cho 19 input và 5 output của smoke theo giá input thường là 0.0000044 USD. Đây là phép tính từ giá công bố, chưa phải hóa đơn hoặc số dư đã đối chiếu; không thay đổi số USD=0.0 của raw artifact để che lỗi metering.

## Quyết định ontology

Baseline dùng schema gợi ý để giữ tương thích rubric: Article, Clause, Crime, Case, Person, Substance, Location. Crime nối tin sang luật. Mức án/tội riêng nằm trên cạnh Person → Case. Dự kiến bổ sung provenance cho node/cạnh dùng chung ở KG-2.

Các điểm đã thấy từ corpus:

- Q1 cần khoản 4 Điều 2 Luật PCMT; lấy riêng khoản 1 sẽ thiếu định nghĩa tiền chất.
- Q4 cần khoản 4 Điều 255, dù khoản không liệt kê chất. Chỉ chọn khoản bằng MENTIONS là thiếu.
- Q5 cần cả khối lượng nguồn và ngưỡng trong Điều 250; baseline chưa có rule numeric tự động.
- Q6 cần query các Case liên quan MDMA trên toàn graph và kiểm tra trùng vụ giữa bài.
- Cuối bài Thành có teaser vụ Huy; extraction phải tránh gán Huy vào vụ Thành hoặc tạo vụ trùng mà không kiểm tra.
- Một vụ có nhiều tội, như bài 36kg; không dùng toàn bộ tội của Case làm tội riêng cho từng người.

## Artifact và phạm vi thay đổi

- `report/ONTOLOGY.md`: thiết kế đầy đủ, ghi rõ chưa triển khai graph.
- `.env` local: thêm base URL DevQuota; chuyển embedding sang Gemini; key chat/model giữ nguyên, file vẫn ignored.
- `report/checkpoints/part01_setup.json`: smoke ban đầu, gồm Neo4j read-only.
- `report/checkpoints/part01_config_sources.json`: so sánh nguồn cấu hình đã che giá trị bí mật.
- `report/checkpoints/part01_project_env.json`: request với .env trước khi thêm gateway URL.
- `report/checkpoints/part01_gateway.json`: chat thành công, embedding model_not_found.
- `report/checkpoints/part01_gateway_models.json`: danh mục 36 model, không có ứng viên embedding.

Không sửa bộ chấm, corpus hay KG-1..KG-4 ở checkpoint này. Không reset database, commit, push hoặc nộp bài.

## Việc còn lại trước phần code graph

- Bổ sung GEMINI_API_KEY vào .env local rồi smoke Gemini. Chưa cài embedding local. Không gộp cấu hình/provider từ các lần thử khác nhau thành một bảng benchmark.
- Kiểm chứng model embedding đã chọn bằng smoke thực tế và ghi model/dimension/latency.
- Bổ sung metering gpt-6-luna có nguồn giá; không để bảng benchmark báo chi phí bằng 0 khi giá chưa biết.
- Sau khi môi trường đạt, làm KG-1 và KG-2 trên corpus nhỏ, rồi KG-3/KG-4 theo kế hoạch. Ontology sẽ được đối chiếu với graph thật sau KG-2.

## Tổng quan tiến độ

| Phần | Trạng thái |
| --- | --- |
| Môi trường | Python, Neo4j, chat đạt; embedding chưa đạt |
| Ontology | Thiết kế v1 hoàn thành, chờ graph thực nghiệm |
| KG-1 / KG-2 / KG-3 / KG-4 | Chưa triển khai |
| Benchmark 6 câu / 20 câu | Chưa chạy |
| Node embeddings / BFS | Chưa triển khai |
| Báo cáo cuối / ảnh / bonus | Chưa hoàn thành |
