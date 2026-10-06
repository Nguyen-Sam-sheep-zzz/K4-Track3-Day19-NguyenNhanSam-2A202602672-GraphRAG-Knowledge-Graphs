# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** Nguyễn Nhân Sâm — **MSSV:** 2A202602672 — **Ngày:** 05/10/2026.

**Đường API cần phân biệt:** OpenAI chuẩn là `https://api.openai.com/v1`. Chat dùng **OpenAI-compatible API**, model `gpt-6-luna`, qua endpoint cấu hình local; embedding dùng Gemini `gemini-embedding-001`. Báo cáo định danh theo model/giao thức, không phụ thuộc tên gateway. Top_k=3, chunk_size=800; corpus 18 Điều luật + 20 bài báo, 176 chunks; Neo4j có **203 node / 378 cạnh**.

## 1. Chi phí

Hai bảng sao chép nguyên văn từ file kết quả:

```text
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176         0        0   0.00000    219.3
graph       196     35866     7876   0.00752    517.5

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.51   1.33      729       77   0.00011    10.14
graph       0.82   1.67     4451      154   0.00052    12.89
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | ---: | ---: | ---: |
| Indexing USD chat phần định giá được | 0.00000 | 0.00752 | Flat = 0 nên không chia tỷ lệ USD |
| Embedding thực trả (indexing và query) | 0 USD | 0 USD | Google AI Studio free tier theo xác nhận người học |
| Indexing thời gian | 219.3 s | 517.5 s | 2.36× |
| Mỗi câu: USD phần định giá được | 0.00011 | 0.00052 | 4.73× từ số làm tròn |
| Mỗi câu: thời gian | 10.14 s | 12.89 s | 1.27× |
| Mỗi câu: input token được ghi nhận | 729 | 4451 | 6.11× |

USD trong output gốc là subtotal chat có token usage, dùng bảng giá OpenAI tham chiếu gpt-6-luna $0.10 input / $0.50 output mỗi triệu token (<https://developers.openai.com/api/docs/pricing>); không phải hóa đơn dịch vụ chat. Ngày 06/10/2026, người học xác nhận key Gemini dùng **Google AI Studio free tier**, nên chi phí thực trả cho 176 embedding indexing và 12 embedding query là **0 USD theo xác nhận này**. API không trả prompt_tokens, nên số token embedding vẫn chưa đo được; không suy ra free tier từ cột USD hoặc thay số token thiếu thành token đo được. Log gốc giữ usd=null cho embedding để bảo toàn dữ liệu API. Chưa đối soát billing độc lập; căn cứ và phạm vi áp dụng ghi trong `report/PRICING.md`.

Graph indexing gồm cùng chunk embeddings và 20 chat extraction: riêng extraction 35,866 input / 7,876 output token, subtotal **$0.0075246**. Query Graph tăng vì prompt chứa facts luật/người/vụ. Judge được gọi ngoài usage query của grader: **12 lần, $0.0007981 subtotal và 105.30 giây API**, tách ở JSON chuẩn.

Đây là cold chunk indexing, không thay lời gọi API bằng embedding cache. Launcher chờ khoảng 0.7 giây mỗi văn bản Gemini để dưới quota 100/phút; thời gian bảng bao gồm pacing, graph và ghi audit. API latency thuần không đồng nhất wall time. Với embedding free tier bằng 0 USD, phần chênh lệch USD tham chiếu đến từ chat extraction và prompt query. Graph tốn hơn cả indexing và query theo giá chat tham chiếu, nên không có điểm hòa vốn USD trong cấu hình này. Chi phí indexing Flat bằng 0 nên tỷ lệ USD Graph/Flat không xác định; không gọi là 0 lần.

## 2. Từng câu hỏi

Judge: 0 sai, 1 đúng một phần, 2 đủ theo LLM judge. Recall là khớp chuỗi keyword, không phải accuracy được con người kiểm chứng.

| Câu | Loại | Flat recall / judge | Graph recall / judge | Bên tốt hơn | Vì sao |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa | Cả hai đủ định nghĩa tiền chất; Graph nêu khoản 4 Điều 2. |
| Q2 | single-hop-news | 1.00 / 2 | 1.00 / 2 | Hòa | Tin đã có hai tên lãnh án tử hình. |
| Q3 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Thêm Điều 251 và khung cơ bản 02–07 năm cho mức án 36 tháng. |
| Q4 | cross-kb | 0.33 / 1 | 0.67 / 1 | Graph thêm Điều, cả hai chưa đủ | Trả tối đa khoản 1 là 7 năm, thiếu mức cao nhất Điều 255. |
| Q5 | cross-kb-multi-hop | 0.40 / 1 | 0.60 / 1 | Graph thêm Điều, cả hai chưa đủ | Biết tội/chất/lượng nhưng thiếu văn bản khoản để đối chiếu ngưỡng 100g. |
| Q6 | aggregation | 0.00 / 1 | 0.67 / 2 | Graph bao phủ rộng hơn, còn trùng | Tìm được Viện Pháp y/Sầm Sơn; 5 Case không có nghĩa 5 vụ độc lập. |

Recall trung bình Graph tăng 0.31 điểm, judge tăng 0.34 trên thang 2. Lợi ích rõ nhất Q3; Q1/Q2 Flat đã đủ. Không gọi Q4/Q5 hoàn toàn đúng vì recall tăng. Mẫu 6 câu chưa chứng minh kết quả tổng quát.

## 3. Phân tích lỗi

### E2 — Cắt context làm mất nội dung khoản ở Q5

**Hiện tượng:** Graph Q5 trả: “Ngữ cảnh không nêu ngưỡng khối lượng, nội dung các khoản của **Điều 250 BLHS** hay khung hình phạt tương ứng.”

**Bằng chứng:** prompt Q5/graph ở benchmark_kg_standard.json có cạnh Clause Điều 250 khoản 4 MENTIONS MDMA, nhưng không có văn bản khoản 4 hoặc chuỗi “khối lượng 100 gam trở lên”. Cạnh nhắc chất không chứa ngưỡng. Corpus khoản 4 Điều 250 có khung “20 năm, tù chung thân hoặc tử hình”, điểm b MDMA từ 100 gam trở lên. Đường Huy tới Điều 250 có trong ảnh kg_my_case.png; query kiểm chứng:

```cypher
MATCH (a:Article {id:'Điều 250 BLHS'})-[:HAS_CLAUSE]->(cl:Clause {number:4})
RETURN a.id, cl.text;
```

**Nguyên nhân:** seed edges theo doc_id/chất quá nhiều. Câu không hỏi “cơ bản/tối đa” hoặc số Điều cụ thể có nhiều facts đồng điểm; quy tắc ưu tiên độ ngắn đẩy khoản dài ra ngoài ngân sách 60 facts. Corpus có luật, nhưng prompt không còn nội dung cần thiết.

**Đề xuất sửa:** dành ngân sách riêng cho khoản của Article nối đúng Crime, trước seed edges; giữ văn bản ngưỡng và lượng chất có nguồn. Đo lại sau sửa. BFS mở rộng ưu tiên Clause text nhưng được đánh giá riêng, không thay điểm chuẩn.

### E3 — Một vụ Huy thành hai Case

**Hiện tượng:** Graph Q6 liệt kê hai tên về cùng vụ Huy.

**Bằng chứng:** graph_evidence.json lưu query và hai hàng thật:

```cypher
MATCH (p:Person {name:'Cái Quang Huy'})-[r:INVOLVED_IN]->(k:Case)
RETURN p.name AS person,k.name AS case_name,k.doc_id AS doc_id,r.charge AS charge;
```

| case_name | doc_id | charge |
| --- | --- | --- |
| Vụ Cái Quang Huy vận chuyển ma túy qua sân bay Nội Bài | news-100260918080821054 | vận chuyển trái phép chất ma túy |
| Vụ vận chuyển hơn 9,6kg ma túy từ Đức về Việt Nam | news-100260917203001265 | vận chuyển trái phép chất ma túy |

**Nguyên nhân:** teaser cuối bài Thành giới thiệu Huy, LLM trích thành Case. MERGE Case.name không gộp hai cách đặt tên. Constraint UNIQUE chỉ chứng minh duy nhất theo khóa tên.

**Đề xuất sửa:** nhận diện body/teaser trong extraction; đồng nhất Case theo sự kiện/người/thời gian/địa điểm và giữ nhiều nguồn. Rà trước gộp để không nhập nhầm hai đợt vận chuyển. Giữ raw corpus chung cho cả hai pipeline. Baseline chưa khử trùng hoàn toàn.

### E5 — Q4 bỏ qua khoản cao nhất dù prompt có

**Hiện tượng:** Graph Q4 trả “Theo **khoản 1 Điều 255 BLHS** ... mức tối đa theo khoản này là **7 năm tù**.”

**Bằng chứng:** prompt Q4/graph trong JSON chuẩn mở đầu bằng khoản 4 Điều 255: “phạt tù 20 năm hoặc tù chung thân”. Query nato_law trong graph_evidence.json trả đủ khoản 1–5 Điều 255. Lượt này không thể quy Q4 chỉ cho retrieval thiếu khoản.

**Nguyên nhân:** model trả khung cơ bản cho một người chưa xác định tình tiết, thay vì mức cao nhất toàn Điều. Prompt còn có luật/tội khác do Case nhiều tội và seed chung. Ưu tiên facts tối đa đã chạy nhưng chưa bảo đảm model sử dụng đúng.

**Đề xuất sửa:** phân biệt “cao nhất toàn Điều” với “khung áp dụng cho người cụ thể”, chọn Crime theo charge riêng của người, kiểm tra grounded answer. Không suy ra Nato sẽ nhận chung thân; chỉ đối chiếu snapshot luật của lab.

### E4 — Điểm Q6 không phát hiện đếm trùng

**Hiện tượng:** Q6 Graph recall=0.67, judge=2, nhưng liệt kê 5 Case gồm hai tên Huy; hai bài Viện Pháp y/Sầm Sơn cũng cần phân biệt sự kiện với số bài.

**Bằng chứng:** kết quả Q6 mục 4 “Vụ vận chuyển hơn 9,6 kg ...” và mục 5 “Vụ Cái Quang Huy ... Nội Bài”; query E3 xác nhận hai nguồn cùng vụ. Giữ nguyên explanation/score judge trong JSON.

**Nguyên nhân:** recall tìm chuỗi, judge so gold ngắn, không có tiêu chí số thực thể duy nhất. Bao phủ tên không thay kiểm tra duplicate.

**Đề xuất sửa:** kiểm tra sự kiện duy nhất và nguồn, bổ sung phạt duplicate trong đánh giá mở rộng; giữ nguyên bộ chấm gốc. Judge=2 không đồng nghĩa đúng hoàn toàn qua rà nguồn.

## 4. Kết luận

KG hữu ích khi nối người/vụ ở tin với tội/Điều/khoản ở luật: Q3 recall tăng 0.33→1.00, judge 1→2. KG mở rộng Q6 vượt top-3 chunk, nhưng extraction/khóa tên gây trùng và sai gán.

Flat đủ với định nghĩa hoặc thông tin nằm trong một tin: Q1/Q2 đều judge=2, query subtotal thấp hơn và nhanh hơn ở lượt này. Graph indexing 2.36×, input prompt 6.11×, query thời gian 1.27×. Chọn KG khi cần quan hệ nhiều nguồn và kiểm soát được provenance, đồng nhất thực thể, ngân sách context. Không suy ra Graph luôn thắng. Node embeddings + BFS/20 câu được đo riêng trong REPORT_KG_EXTENDED.md.

## 5. Tự kiểm và ảnh

```text
$ .venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
................................................................         [100%]
64 passed in 0.14s
```

48 test gốc + 16 test bổ sung. Check hợp đồng được chạy trước benchmark đầy đủ vì --check reset graph nhỏ:

```text
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[provider] chat = openai:gpt-6-luna | embedding = gemini:gemini-embedding-001
[OK] KG-2 build_graph: 148 node / 294 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 45 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00078. Graph nhỏ (luật + 1 bài) vẫn còn trong Neo4j để bạn xem; chạy --judge để dựng graph đầy đủ.
```

Ba ảnh thật: img/kg_count.png, img/kg_cross_kb.png, img/kg_my_case.png. Người chọn: **Cái Quang Huy**. Chụp toàn viewport Neo4j Browser trong Codex, không crop/chỉnh sửa. API in-app browser không kèm thanh cửa sổ hệ điều hành; nếu người chấm yêu cầu cả chrome cửa sổ desktop thì cần chụp lại. Graph có 7 label, 7 loại cạnh, 0 cạnh thiếu source_doc_ids.

Bonus ontology +15 chưa thực hiện. Chưa commit/push/nộp VLearn.

## Vấn đề gặp phải

Chat dùng OpenAI-compatible API và chạy ổn với model gpt-6-luna; embedding dùng Gemini vì API chat-compatible không cung cấp model embedding đã thử. Gemini 429 quota 100 văn bản/phút: launcher paced single texts và thêm pacing theo số text batch sau lỗi thật (checkpoints/extended_batch_429.err). Docker Desktop lỗi thư mục runtime socket cũ; giữ backup rồi khởi động lại, không xóa database. Các lỗi đáp án/context còn lại đã ghi mục 3, không sửa grader hoặc gold để che lỗi.
