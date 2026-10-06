# Phần mở rộng — Node embeddings + BFS và 20 câu hỏi

**Nguyễn Nhân Sâm — 2A202602672 — 05/10/2026.** Dữ liệu gốc có 18 Điều luật, 20 bài báo, 176 chunks; graph cùng lượt chuẩn có 203 node / 378 cạnh. Artifact: benchmark_kg_extended.json (40 câu trả lời và trace), node_index_metadata.json, triples.json và graph_evidence.json. Bộ 6 câu/grader gốc được giữ nguyên.

## 1. Phương pháp và phạm vi

Chat: OpenAI-compatible API, model `gpt-6-luna`; embedding: Gemini `gemini-embedding-001`. Endpoint cụ thể giữ trong `.env` local và không đưa key vào báo cáo. Cả hai pipeline dùng chung chunk 800 ký tự, top-3 vector chunks và model. Lượt mở rộng dùng lại vector chunk và KG đã trả phí ở lượt chuẩn, không đo cold indexing lần nữa. Graph có thêm node indexing được đo riêng. Các câu M01–M17 phối hợp quan hệ người/vụ/tội/luật, so sánh lượng/mức án và trạng thái; M18–M20 kiểm tra thiếu phủ luật, chất chưa xác định và sự kiện phòng ngừa. Vì vậy đây là 20 câu suy luận nhiều nguồn; không gọi mọi câu là một đường multi-hop graph thuần túy. Gold/criteria/source IDs/evidence_path nằm trong data/benchmark_kg_20.json, được thiết kế từ corpus lab, không phải benchmark độc lập của giảng viên.

Tin được LLM trích JSON người/vụ/tội/chất; luật tách bằng regex. Xuất subject–predicate–object kèm nguồn cho 378 cạnh. Không tuyên bố toàn corpus NER bằng LLM: phần luật là parser có cấu trúc. Nếu ảnh được chấm theo yêu cầu LLM extraction cho mọi tài liệu thì cần hỏi giảng viên về cách hiểu này.

Node text ghép label/tên/id/title/summary/text/aliases, giới hạn nội dung 3500 ký tự; tạo **203 vector 3072 chiều** bằng Gemini và ghi embedding/model/text vào Neo4j. 13 batch, 16 văn bản/batch (batch cuối ít hơn); metadata chỉ xuất chiều/model/nguồn, vector đầy đủ ở Neo4j và cache local.

Query → embedding → seed: ưu tiên tất cả Person được nhắc tên/alias; nếu câu tổng hợp nhắc Substance thì ưu tiên chất; còn lại top-3 cosine node vectors. Vì có ưu tiên tên, không phải mọi seed đều được chọn thuần bằng cosine. BFS dùng queue/visited, duyệt cạnh hai chiều, tối đa **4 hop / 180 node**, loại **MENTIONS** để tránh hub chất kéo theo nhiều luật. Đây là BFS trên tập cạnh đã chọn. Serialize tối đa **100 facts**, ưu tiên văn bản khoản/summary và cạnh người/vụ/tội. LLM nhận cả facts và cùng top-3 chunks.

Trace có seed IDs, nodes, edges, đường khám phá đầu tiên theo BFS, truncated flag, facts, chunks và prompt thật. Giới hạn 4 hop áp dụng từ seed; không có nghĩa mọi fact nằm trên cùng một đường nhân quả. 0 / 20 câu chạm giới hạn node; số node tối đa đã duyệt 92, facts tối đa 100. Cắt facts vẫn có thể mất thông tin dù truncated=false (flag này chỉ báo ngân sách node).

## 2. Kết quả

Accuracy dưới đây = tỷ lệ câu được cùng LLM judge chấm **2/2** với gold; không phải accuracy do con người kiểm chứng độc lập. Keyword recall và criterion recall đều dùng substring, có thể bỏ sót diễn đạt tương đương hoặc nhận nhầm phủ định. Không đồng nhất ba thước đo.

| Chỉ số | Flat | Graph+BFS |
| --- | ---: | ---: |
| Số câu | 20 | 20 |
| Keyword recall trung bình | 0.649 | 0.978 |
| Criterion recall trung bình | 0.615 | 0.967 |
| Accuracy theo judge đủ ý | 20.0% | 100.0% |
| Judge trung bình /2 | 1.200 | 2.000 |
| Latency trung bình/câu | 11.20 s | 12.92 s |
| Latency p95/câu | 15.54 s | 16.06 s |
| Query subtotal USD /20 câu | 0.0029815 | 0.0164948 |
| Query embedding calls thiếu token usage trong bộ đo | 20 | 40 |

Latency đo wall time retrieval + query embedding + chat, gồm pacing Gemini; judge đo riêng. p95 dùng nearest-rank trên 20 câu; đây là một lượt đo, không chứng minh tốc độ ổn định qua nhiều lần.

| Câu | Loại | Flat: keyword / criteria / judge / giây | BFS: keyword / criteria / judge / giây |
| --- | --- | --- | --- |
| M01 | person-law | 0.75 / 0.50 / 1 / 8.69s | 1.00 / 1.00 / 2 / 11.36s |
| M02 | person-law | 0.75 / 0.75 / 1 / 10.86s | 1.00 / 1.00 / 2 / 11.29s |
| M03 | status-law | 0.75 / 0.80 / 1 / 10.55s | 1.00 / 1.00 / 2 / 12.42s |
| M04 | person-law | 0.75 / 0.75 / 1 / 14.83s | 1.00 / 1.00 / 2 / 11.72s |
| M05 | person-law | 0.75 / 0.75 / 1 / 8.43s | 1.00 / 1.00 / 2 / 13.02s |
| M06 | charge-separation | 0.50 / 0.60 / 1 / 8.25s | 1.00 / 1.00 / 2 / 10.46s |
| M07 | person-law | 0.67 / 0.50 / 1 / 10.66s | 1.00 / 1.00 / 2 / 10.82s |
| M08 | alias-law | 0.50 / 0.50 / 1 / 12.11s | 1.00 / 0.83 / 2 / 15.14s |
| M09 | status-law | 0.25 / 0.40 / 1 / 13.74s | 1.00 / 1.00 / 2 / 12.76s |
| M10 | quantity-law | 0.33 / 0.20 / 1 / 15.54s | 1.00 / 1.00 / 2 / 10.56s |
| M11 | quantity-law | 0.60 / 0.60 / 1 / 9.11s | 1.00 / 1.00 / 2 / 12.47s |
| M12 | negative-status | 1.00 / 1.00 / 2 / 9.08s | 1.00 / 1.00 / 2 / 12.93s |
| M13 | multi-case-law | 0.25 / 0.25 / 1 / 13.26s | 1.00 / 1.00 / 2 / 16.06s |
| M14 | quantity-uncertainty | 0.75 / 0.75 / 1 / 9.35s | 1.00 / 1.00 / 2 / 12.84s |
| M15 | quantity-hypothetical | 1.00 / 1.00 / 2 / 16.96s | 0.75 / 1.00 / 2 / 12.60s |
| M16 | multi-charge-law | 0.40 / 0.40 / 1 / 13.37s | 1.00 / 1.00 / 2 / 13.56s |
| M17 | aggregation-law | 0.43 / 0.00 / 1 / 12.77s | 1.00 / 1.00 / 2 / 19.24s |
| M18 | coverage-negative | 1.00 / 1.00 / 2 / 9.17s | 1.00 / 1.00 / 2 / 11.44s |
| M19 | uncertain-substance | 0.80 / 0.75 / 2 / 9.05s | 0.80 / 0.50 / 2 / 14.58s |
| M20 | prevention-law | 0.75 / 0.80 / 1 / 8.23s | 1.00 / 1.00 / 2 / 13.16s |

## 3. Indexing, query và judge cost

| Thành phần | USD chat tham chiếu / embedding thực trả theo free tier | Ghi chú |
| --- | ---: | --- |
| Chunk indexing dùng chung từ lượt chuẩn | $0.0000000 | 176 Gemini embeddings free tier; số token chưa đo được |
| KG extraction dùng chung từ lượt chuẩn | $0.0075246 | 20 chat extraction; giá tham chiếu, không phải hóa đơn gateway |
| Node indexing thêm cho BFS | $0.0000000, 165.10s wall | 13 batch /203 embeddings free tier; số token chưa đo được |
| Query Flat 20 câu | $0.0029815 chat tham chiếu + $0 embedding | 20 Gemini query embeddings free tier; số token chưa đo được |
| Query BFS 20 câu | $0.0164948 chat tham chiếu + $0 embedding | 40 Gemini query embeddings free tier; số token chưa đo được |
| Judge Flat 20 câu | $0.0014534 | Tách khỏi query |
| Judge BFS 20 câu | $0.0013293 | Tách khỏi query |

Giá chat tham chiếu gpt-6-luna: $0.10 input / $0.50 output mỗi triệu token (<https://developers.openai.com/api/docs/pricing>); số USD chat không phải hóa đơn dịch vụ. Ngày 06/10/2026, người học xác nhận key Gemini của lượt này thuộc **Google AI Studio free tier**, nên **embedding thực trả 0 USD theo xác nhận này**, gồm chunk/node indexing và query. Số token embedding vẫn chưa đo được do API không trả usage; trường unpriced_calls/ usd=null trong JSON gốc được giữ để phản ánh giới hạn bộ đo. Chưa đối soát billing độc lập; không áp dụng mức 0 USD cho tài khoản trả phí hoặc mọi lượt tương lai. Xem PRICING.md.

Lần node indexing đầu lỗi 429 sau 6 batch (96 văn bản); đã lưu audit/error riêng ở checkpoints/extended_batch_429_audit.json và .err, rồi thêm pacing theo số văn bản/batch. 96 embedding thành công của lần lỗi tiêu thụ quota và thời gian ngoài lượt 203 vector; chi phí thực trả vẫn 0 USD theo free tier được người học xác nhận. Tests pacing đạt. Giữ audit các lời gọi đã thực hiện.

## 4. Đọc kết quả và giới hạn

Phần BFS cải thiện việc đưa khoản luật vào prompt và giữ đủ quan hệ cho so sánh nhiều người. Có thể đối chiếu các câu M06 (tách tội/án), M08 (tên/alias + khung cao nhất), M10/M11 (lượng riêng và ngưỡng), M12 (hủy khởi tố, không gán cùng tội) và M14 (viên không tự đổi thành gam) trong JSON. Báo cáo chuẩn vẫn giữ Q4/Q5 chưa đủ; kết quả mở rộng không thay thế các câu chuẩn.

Không quy toàn bộ chênh lệch cho riêng BFS: pipeline này đồng thời thêm node embeddings, ưu tiên seed theo tên, loại cạnh MENTIONS và tăng ngân sách facts 60→100 so với chuẩn. Chưa có ablation Graph-Cypher/BFS trên cùng 20 câu. Gold từ corpus này và cùng model trả lời/chấm có thể thiên lệch; số liệu không chứng minh chất lượng pháp lý bên ngoài corpus.

**Lỗi còn quan sát được dù judge=2:** M17/BFS nối đúng các Điều nhưng thêm câu “Ngữ cảnh không xác định chất ma túy trong vụ của Đông có phải MDMA hay không”. Nguồn news-100260930085028036 xác nhận 0,686g MDMA tại buồng bệnh; graph_evidence cũng có lượng này. Trace M17 đã duyệt 84 node, truncated=false, nhưng 100 facts cuối không chứa 0,686g và top-3 chunk không bù được. Vì vậy model từ chối dựa trên context thiếu, rồi judge vẫn chấm 2 do gold tập trung ánh xạ tội/Điều. Đây là mất dữ kiện tại serialization cộng với tiêu chí judge chưa kiểm tra phát biểu phụ; cần dành ngân sách cho INVOLVES/amount của người/vụ được hỏi và rà claim theo nguồn. Không gọi accuracy judge là toàn bộ đáp án đúng 100%.

M15/BFS diễn đạt “1 năm đến 5 năm” tương đương “01 năm đến 05 năm” trong corpus; keyword must_include “05 năm” có thể làm recall thấp dù judge=2. Criterion recall cho phép vài diễn đạt tương đương, vẫn là kiểm tra substring và chưa thay đánh giá ngữ nghĩa.

Case dùng khóa tên còn trùng vụ Huy/Viện Pháp y; nhiều tội trong một Case có thể làm nhiễu nếu không xét charge riêng của người. Status/negation/quantities chưa có ontology sự kiện/ngưỡng riêng, nên vẫn dựa raw chunks và summary LLM. BFS loại MENTIONS cũng có thể làm mất đường hữu ích. Provenance xác định tài liệu đóng góp, không bảo đảm extraction đúng. Các câu không có Person/Crime trong graph vẫn cần fallback chunk.

## 5. Tái lập

```powershell
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg.py --judge
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg_extended.py --judge
.\.venv\Scripts\python.exe scripts/run_local.py scripts/capture_graph_evidence.py
.\.venv\Scripts\python.exe scripts/write_extended_report.py
```

--resume chỉ tiếp tục khi config, graph fingerprint và question hash không đổi; --check phải chạy trước benchmark chuẩn vì nó reset graph. Lượt tương lai có thể khác do dịch vụ/extraction không hoàn toàn tái lập; giữ artifact hiện tại làm bằng chứng. Bản bàn giao đã đưa lên main; người học tự nộp VLearn. Bonus ontology +15 không được tuyên bố.
