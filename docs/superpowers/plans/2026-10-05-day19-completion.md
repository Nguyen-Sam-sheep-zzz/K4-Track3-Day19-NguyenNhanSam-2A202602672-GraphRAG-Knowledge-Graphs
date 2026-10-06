# Kế hoạch hoàn thiện Day 19 — GraphRAG / Knowledge Graphs

## Checkpoint bàn giao 05/10/2026

Bảng này cập nhật tiến độ cuối; phần bên dưới giữ thiết kế/checklist ban đầu để đối chiếu lịch sử.

- [x] Cấu hình chat gateway + Gemini embedding, Neo4j local.
- [x] KG-1..KG-4, ontology khớp schema, 48 test gốc và 16 test bổ sung đạt; 7 OK check trước benchmark.
- [x] Benchmark chuẩn cold 6 câu, đủ output/audit/judge; Graph recall 0.82 vs Flat 0.51. Q4/Q5 chưa đủ, đã phân tích lỗi với prompt/source thật.
- [x] 203 node embeddings 3072 chiều, BFS queue/visited 4 hop, 378 triples có nguồn.
- [x] Bộ 20 câu và 40 câu trả lời thật có trace; recall BFS 0.978 vs Flat 0.649. M17 còn lỗi phụ dù judge=2, đã ghi rõ.
- [x] ONTOLOGY, REPORT_KG, REPORT_KG_EXTENDED, DEMO, STATUS; ba ảnh Neo4j thật.
- [x] Rà nguồn/artifact/BFS limits, grader/gold/test gốc, secret/lịch sử Git: delivery_audit passed=true.
- [x] Cập nhật 06/10: người học xác nhận Google AI Studio free tier; embedding thực trả 0 USD theo xác nhận này, số token chưa đo được. Báo cáo và script sinh báo cáo phân biệt rõ hai thông tin.
- [ ] Bonus ontology +15: chưa thực hiện, không tự nhận.
- [x] Commit/push đã thực hiện trên nhánh `feature/day19-completion`; ngày 06/10/2026 tích hợp vào `main` để nộp. Đổi tên repo và nộp VLearn chưa thực hiện.

Các lỗi context/LLM/extraction còn lại được giữ trong báo cáo; hoàn tất artifact không đồng nghĩa mọi đáp án đúng. Ảnh là toàn viewport browser, thiếu OS window chrome; tên repo dài hơn mẫu SUBMISSION. Xem `report/STATUS.md` trước khi nộp.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Thực hiện trong chat hiện tại, báo cáo theo từng mốc; chỉ dùng subagent khi người dùng yêu cầu.

**Goal:** Hoàn thành bài theo rubric trong repository và có phần mở rộng đáp ứng bốn yêu cầu trong ảnh: trích xuất quan hệ, graph có node embeddings, retrieval bằng BFS, benchmark 20 câu multi-hop.

**Architecture:** Giữ Flat RAG hiện có và dựng Knowledge Graph trong Neo4j trên cùng hai KB. Pipeline chuẩn dùng vector search trên chunk, liên kết sang seed node, mở rộng xuyên KB bằng Cypher, rồi đưa chunk và graph facts cho LLM. Phần mở rộng có node embeddings, BFS và bộ benchmark riêng, không thay đổi bộ chấm gốc.

**Tech Stack:** Python 3.11, Neo4j 5 / Docker, neo4j driver, embeddings API, chat LLM, pytest.

**Spec / nguồn yêu cầu:** `README.md`, `LAB_GUIDE.md`, `SUBMISSION.md`, hợp đồng đầu `src/graph.py`, ảnh người dùng cung cấp trong chat ngày 05/10/2026. Người dùng đã yêu cầu bắt đầu theo từng phần; tiến độ và chứng cứ phần 1 ở `report/checkpoints/PART01.md`. Chưa triển khai KG-1..KG-4.

## Ràng buộc chung

- Giữ nguyên `tests/test_base.py`, `tests/test_graph.py`, `bench_kg.py`, `data/benchmark_kg.json` của bài chuẩn. Không sửa bộ chấm để tạo điểm pass.
- Giữ nguyên chữ ký bốn interface KG-1..KG-4.
- Mọi node được tạo từ một tài liệu có `doc_id = Document.id`; node canonical dùng chung nhiều tài liệu cần provenance phù hợp, không gán tùy tiện một nguồn.
- Phần chuẩn phải có đường đi xuyên hai KB tối đa 4 cạnh theo hợp đồng `--check`.
- Cùng corpus, chat model, embedding model, `top_k` và chunking cho phép so sánh Flat / Graph. Ghi rõ khác biệt do phần mở rộng.
- `.env` và `.venv/` ở local; không đưa key vào artifact, báo cáo hoặc Git.
- Mọi số liệu và ảnh nộp là kết quả chạy thật; ảnh trong `docs/img/` là ảnh mẫu.
- Chưa commit, push, đổi tên repository hoặc nộp VLearn trong phạm vi đọc và lập kế hoạch này.
- Bảng USD trong `src/llm.py` là ước tính; model không có giá có thể bị tính 0 USD. Phải kiểm tra giá và cơ chế ghi usage trước khi kết luận chi phí.

## 1. Hiện trạng đã kiểm tra

| Thành phần | Hiện trạng ngày 05/10/2026 |
| --- | --- |
| Checkout | Nhánh `main`, HEAD `859e8d1`; remote khớp URL người dùng gửi. Chưa fetch để so sánh với HEAD GitHub hiện tại. |
| Corpus | 18 file Điều luật, 20 bài báo; có metadata nguồn và `sources.csv`. |
| Flat RAG | Chunking, vector store, agent và metering có sẵn. 41 test base pass offline; chưa benchmark API thực tế. |
| KG-1 | `link_entity` chưa viết, 5 test fail do `NotImplementedError`. |
| KG-2 | `build_graph` chưa viết. |
| KG-3 | `Neo4jGraph.context` chưa viết. |
| KG-4 | `GraphRAGAgent.answer` chưa viết, 2 test fail do `NotImplementedError`. |
| Môi trường | Python của `.venv` chạy được khi được truy cập đúng; container `neo4j-drug-kg` đang Up, mở cổng 7474 và 7687. Chưa xác thực Neo4j bằng driver hoặc kiểm tra API. |
| Báo cáo | `ONTOLOGY.md`, `REPORT_KG.md` là template. Chưa có file benchmark; `report/img/` chỉ có `.gitkeep`. |

Lệnh đã kiểm tra: `.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider`.

Kết quả: **7 failed, 41 passed in 0.30s**. Thất bại đúng tại các TODO, không phải bằng chứng base bị hỏng.

## 2. Hai bộ yêu cầu cần bao phủ

| Yêu cầu trong ảnh | Bài trong repository | Cách thực hiện đề xuất |
| --- | --- | --- |
| LLM-based NER, triples (subject, predicate, object) | Luật trích regex; tin tức trích bằng LLM thành JSON case/person/charge/substance | Giữ cách trích hỗn hợp phù hợp corpus. Xuất thêm triples có nguồn. Nếu giảng viên yêu cầu toàn corpus trích bằng LLM, bổ sung thử nghiệm extraction riêng và đo chi phí riêng. |
| NetworkX hoặc Neo4j; embedding cho node | Repo dùng Neo4j; embedding chỉ có ở chunk vector store | Dùng Neo4j; bổ sung biểu diễn văn bản và embedding cho node ở phần mở rộng. |
| Query → seed → BFS → subgraph-to-text → LLM | Repo dùng vector chunk + seed_facts + Cypher theo đường ontology | Hoàn thành Cypher cho bài chuẩn; bổ sung BFS có giới hạn ở phần mở rộng. Cypher nhiều bước hiện có không được gọi là BFS nếu chưa thực hiện đúng thuật toán. |
| So sánh trên 20 câu multi-hop: accuracy, latency, cost | 6 câu: 2 single-hop, 2 cross-kb, 1 cross-kb-multi-hop, 1 aggregation; đo recall và judge | Giữ 6 câu chuẩn; tạo thêm bộ 20 câu multi-hop và runner riêng. 20 bài báo không phải 20 câu benchmark. |

Phương án khuyến nghị: **bài chuẩn trước → phần mở rộng theo ảnh → bonus ontology nếu còn thời gian**. Chỉ làm theo repo sẽ chưa bao phủ đủ ảnh; thay hết bằng NetworkX sẽ tăng công việc vì mất sự tương thích với check và ảnh Neo4j.

## 3. Giải thích bài toán bằng một ví dụ

Câu hỏi: “Lê Minh Thành bị tuyên bao nhiêu tháng tù, về tội gì, theo Điều nào và khung cơ bản bao nhiêu?”

- KB tin có tên người, mức án 36 tháng, tội danh.
- KB luật có Điều 251 và khoản 1: 02 năm đến 07 năm.
- Flat RAG lấy top-k đoạn văn; có thể lấy được bài báo nhưng thiếu đoạn luật.
- GraphRAG đi theo `Person → Case → Crime ← Article → Clause`, nhờ `Crime` chuẩn hóa nối hai nguồn, rồi chuyển dữ kiện thành văn bản cho LLM.

“Ontology” là thiết kế các loại node, loại cạnh và khóa định danh. “Multi-hop” là phải đi qua nhiều quan hệ để gom đủ dữ kiện. Graph bổ sung ngữ cảnh không đảm bảo câu trả lời luôn tốt hơn; benchmark sẽ kiểm chứng lợi ích và đánh đổi.

## 4. Các mốc thực hiện

### Mốc 0 — Xác nhận môi trường và cấu hình

**Files:** `.env` local, `requirements.txt`, `src/llm.py` (đọc; sửa nếu cấu hình thực tế có lỗi được xác nhận).

- [x] Chạy `.venv\Scripts\python.exe --version`; kiểm tra import `dotenv`, `neo4j`, SDK provider.
- [x] Kiểm tra các key bằng trạng thái `set` / `missing`, không in giá trị.
- [ ] Xác nhận chat và embedding provider cùng cấu hình cố định cho cả hai pipeline; chỉ rõ model và cách tính USD.
- [x] Xác thực driver kết nối Neo4j. Dùng database/container riêng cho bài vì các lệnh benchmark reset graph.
- [x] Lưu baseline `41 passed`, ghi 7 fail do TODO.

**Đạt khi:** môi trường offline chạy được và cấu hình sẵn cho smoke API/Neo4j. API chưa gọi được phải báo riêng, không thay kết quả thật bằng mock.

### Mốc 1 — Chốt ontology và đường trả lời

**Files:** sửa `report/ONTOLOGY.md`; tham chiếu `data/benchmark_kg.json`, corpus luật và tin.

**Interface thiết kế:** `Article`, `Clause`, `Crime`, `Case`, `Person`, `Substance`, `Location`; `Crime` là node cầu nối cho phiên bản đầu.

- [x] Đọc ba case Q3, Q4, Q5 và luật tương ứng; xác nhận đáp án bằng nguồn gốc.
- [x] Vẽ graph, liệt kê label, khóa `MERGE`, properties, cạnh và nguồn trích.
- [x] Viết đường đi hoặc giới hạn cho từng Q1–Q6, đặc biệt Q5 (ngưỡng MDMA) và Q6 (liệt kê nhiều vụ).
- [x] Chọn ba đánh đổi: regex/LLM, khóa node, mức chi tiết Điều/khoản/điểm.
- [x] Ghi rủi ro tên đồng nghĩa, case trùng, thiếu giai đoạn tố tụng, thiếu ngưỡng định lượng.

**Đạt khi:** mỗi câu hỏi có cách lấy đủ bằng chứng hoặc có giới hạn được giải thích. Bản thiết kế chỉ ghi label/quan hệ thật sẽ dựng.

### Mốc 2 — KG-1: chuẩn hóa và liên kết entity

**Files:** sửa `src/graph.py::link_entity`; dùng `tests/test_graph.py` gốc.

**Interface:** `link_entity(name: str, known: list[str], normalize=normalize_crime) -> str | None`.

- [ ] Chạy test hiện có để xác nhận trạng thái fail ban đầu.
- [ ] Chuẩn hóa cả hai phía, ưu tiên exact match, sau đó fuzzy match cutoff 0.8; trả nguyên văn phần tử trong `known` hoặc `None`.
- [ ] Chạy `.venv\Scripts\python.exe -m pytest tests/test_graph.py -k LinkEntity -v`.

**Đạt khi:** 5 test LinkEntity pass; không nối tên tội không liên quan.

### Mốc 3 — KG-2: dựng graph có provenance

**Files:** sửa `src/graph.py::build_graph`, helpers ghi/trích nếu cần; giữ `bench_kg.py` gốc.

**Interface:** `build_graph(graph, law_docs: list[Document], news_docs: list[Document], llm_fn) -> None`; lời gọi `llm_fn(prompt, json_mode=True)`.

- [ ] Dựng constraints và nạp Article/Clause/Crime bằng parser luật có sẵn.
- [ ] Trích news thành JSON bằng LLM, chuẩn hóa tội và chất, kiểm tra cấu trúc trước khi nạp.
- [ ] Không âm thầm coi JSON lỗi là “bài không có vụ việc”; ghi log lỗi và `doc_id` để kiểm tra.
- [ ] Chạy `.venv\Scripts\python.exe bench_kg.py --build --limit 2`; đọc graph thật và so với hai bài nguồn.
- [ ] Kiểm tra `doc_id`, số Article, Crime và đường nối hai KB; số tham khảo của guide là Article=18, Crime=13, còn số node tin phụ thuộc extraction.

**Đạt khi:** graph nhỏ có đúng dữ liệu nguồn và đường news → Crime → law. Không cần nạp cả 20 bài để phát hiện lỗi đầu tiên.

### Mốc 4 — KG-3 và KG-4: trả lời xuyên KB

**Files:** sửa `src/graph.py::Neo4jGraph.context`, `src/graph.py::GraphRAGAgent.answer`; thêm test hành vi mới riêng khi cần.

**Interfaces:** `context(question: str, doc_ids: list[str], max_facts=60) -> list[str]`; `answer(question: str, top_k=3) -> str`.

- [ ] KG-3 dùng `seed_facts` để tìm seed từ doc_id, tên hoặc alias; đi qua cầu nối lấy Điều/khoản, serialize facts dễ đọc.
- [ ] Đảm bảo câu về “tối đa” lấy các khoản cần thiết kể cả khoản không nhắc tên chất; Q4 là case kiểm tra trọng yếu.
- [ ] Với Q5, giữ nội dung ngưỡng, chất và khối lượng cần để suy luận; không xác nhận khoản chỉ vì cùng tên chất.
- [ ] Với aggregation Q6, truy xuất các vụ liên quan Substance, không giới hạn vô tình ở vài chunk của một vụ.
- [ ] Khử facts trùng và giới hạn prompt có chủ đích; giữ facts quan trọng trước khi áp dụng `max_facts`.
- [ ] KG-4 lấy chunk từ store, doc_id không trùng, gọi context, điền GRAPH_PROMPT rồi gọi cùng LLM với Flat.
- [ ] Chạy `.venv\Scripts\python.exe -m pytest tests/ -q` → mục tiêu 48 passed.
- [ ] Chạy `.venv\Scripts\python.exe bench_kg.py --check` → mục tiêu 7 dòng OK.

**Đạt khi:** cả unit tests và check graph thật đạt. Các check này chưa đủ để kết luận benchmark tốt.

### Mốc 5 — Benchmark chuẩn 6 câu

**Files:** sinh `ket_qua_benchmark_kg.txt`; cập nhật số liệu nháp `report/REPORT_KG.md`.

- [ ] Chạy `.venv\Scripts\python.exe bench_kg.py --judge` trên code cuối của pipeline chuẩn.
- [ ] Kiểm tra ba phần Indexing / Querying / Per question, model, top_k=3, chunk_size=800 và số node/rel.
- [ ] Đọc từng câu trả lời, đối chiếu nguồn và gold; không chỉ nhìn trung bình.
- [ ] Phân biệt keyword recall với độ đúng đáp án; judge 0/1/2 cũng cần kiểm tra thủ công khi mâu thuẫn.
- [ ] Tách chi phí indexing, query và judge. Runner chuẩn không ghi riêng toàn bộ chi phí judge vào file báo cáo; không coi USD pipeline là tổng hóa đơn API.

**Đạt khi:** có artifact sinh từ code, số liệu traceable, nhận xét lợi ích/hạn chế của GraphRAG dựa trên kết quả thật.

### Mốc 6 — Bổ sung đúng yêu cầu trong ảnh

**Files đề xuất:** tạo `src/graph_retrieval.py`, `scripts/export_triples.py`, `bench_kg_extended.py`, `data/benchmark_kg_20.json`, `tests/test_graph_retrieval.py`, `report/REPORT_KG_EXTENDED.md`. Không sửa runner/dataset chuẩn.

**Interfaces đề xuất:**

| Interface đề xuất | Output và hợp đồng |
| --- | --- |
| `export_triples(graph) -> list[dict]` | Mỗi record gồm `subject_id`, `subject`, `predicate`, `object_id`, `object`, `properties`, `source_doc_ids`. |
| `build_node_index(graph, embedding_fn) -> list[dict]` | Mỗi record gồm `node_id`, `labels`, `text`, `embedding`, `source_doc_ids`; embedding_fn dùng client metered, runner lấy Usage delta bằng helper `metered` hiện có. |
| `retrieve_seeds(question: str, node_index: list[dict], embedding_fn, top_k: int = 3) -> list[str]` | Trả node IDs không trùng, sắp theo cosine similarity; embedding_fn giống node indexing. |
| `bfs_subgraph(graph, seed_ids: list[str], max_hops: int = 4, max_nodes: int = 100) -> dict` | Trả `nodes`, `edges`, `paths`, `truncated`; BFS queue/visited theo level; không vượt max_nodes, không đi quá max_hops. |
| `subgraph_to_text(subgraph: dict, max_facts: int = 60) -> list[str]` | Một chuỗi cho mỗi fact kèm nguồn; khử trùng theo edge ID, giữ facts theo thứ tự BFS. |

Các chữ ký là đề xuất thiết kế cho phần mở rộng, chưa phải hàm có sẵn.

- [ ] Xuất subject/predicate/object kèm ID, properties và provenance; node/edge phải truy ngược được tới nguồn.
- [ ] Tạo text cho node từ tên, loại, summary hoặc nội dung luật; embed và ghi metadata model. Tính thêm chi phí node embeddings vào indexing.
- [ ] Tìm seed bằng vector node; kết hợp exact tên/alias khi phù hợp, nhưng không dùng gold để truy xuất.
- [ ] BFS có queue, visited, độ sâu và ngân sách node/fact; tránh chu trình, dừng đúng giới hạn; dùng Cypher đọc hàng xóm, không dựng hệ thống graph thứ hai.
- [ ] Kiểm thử trên graph nhỏ: đường đủ 4 hop, chu trình, node trùng, không có seed, budget và serialization nguồn. Test mới nằm riêng, giữ test gốc.
- [ ] Tạo đúng 20 câu multi-hop: phối hợp người–vụ–tội–Điều, chất–khối lượng–khoản và so sánh/tổng hợp nhiều nguồn. Mỗi câu có gold, ý bắt buộc, source IDs và đường chứng cứ; không chỉ đổi cách diễn đạt một câu.
- [ ] Runner mở rộng so sánh Flat và Graph+BFS trên cùng corpus/model; có thể ghi thêm Graph-Cypher như baseline thứ ba nếu cần giải thích riêng lợi ích BFS.
- [ ] Lưu question/answer, chunk IDs, seed IDs, đường BFS, graph facts, model/config, token, USD, thời gian mỗi câu trong JSON; sinh bảng bằng code.
- [ ] Báo cáo accuracy theo rubric đủ các ý bắt buộc được đối chiếu gold, keyword recall, judge, latency trung bình và p95, indexing/query/judge cost riêng. Không gọi keyword recall là accuracy.
- [ ] Kiểm tra bảng giá để model thiếu giá không được báo “miễn phí”; ghi unknown nếu không có giá/usage tin cậy.

**Đạt khi:** 20 câu đủ bằng chứng multi-hop; retrieval có node embeddings + BFS thật; artifact có 40 câu trả lời Flat/Graph và số liệu đủ kiểm tra. Lệnh dự kiến của runner mới: `.venv\Scripts\python.exe bench_kg_extended.py --questions data/benchmark_kg_20.json --judge`; lệnh chưa dùng được trước khi tạo runner.

### Mốc 7 — Chứng minh lỗi, chụp ảnh và hoàn thiện báo cáo

**Files:** sửa `report/REPORT_KG.md`, `report/ONTOLOGY.md`, `report/REPORT_KG_EXTENDED.md`; tạo ba ảnh ở `report/img/`.

- [ ] Tìm ít nhất hai nhóm lỗi thực tế E1–E6; ưu tiên E2 thiếu khoản luật, E3 trùng thực thể, E4 phép đo, E5 graph facts lệch câu trả lời khi có bằng chứng.
- [ ] Với mỗi lỗi ghi hiện tượng, Cypher + kết quả hoặc nguyên văn câu trả lời, nguyên nhân, cách sửa và đánh đổi. Không tạo lỗi giả để đủ báo cáo.
- [ ] Điền hai bảng chi phí, Q1–Q6, tỉ lệ Graph/Flat và kết luận từ số liệu của mình.
- [ ] Đối chiếu labels/relationships thực tế với ONTOLOGY.md; nêu giới hạn ontology và extraction.
- [ ] Sau lần dựng graph đầy đủ cuối cùng, chụp `kg_count.png`, `kg_cross_kb.png`, `kg_my_case.png`; ảnh thứ ba dùng người khác Lê Minh Thành.
- [ ] Ảnh chụp toàn cửa sổ, thấy truy vấn và Results overview; không dùng ảnh mẫu, không cắt/chỉnh sửa ảnh để nộp.
- [ ] Chạy check trước benchmark cuối: `--check` reset graph nhỏ, vì vậy không chạy check sau lần dựng cuối rồi chụp nhầm graph thiếu dữ liệu.

**Đạt khi:** báo cáo, số liệu và graph cùng phiên bản; đủ ảnh và ít nhất hai lỗi có chứng cứ.

### Mốc 8 — Rà bài và bàn giao cho người dùng

- [ ] Xác nhận 48 test gốc pass, 7 OK check; test mở rộng báo riêng.
- [ ] Kiểm tra không còn NotImplementedError tại KG-1..KG-4.
- [ ] Kiểm tra đủ kết quả 6 câu và 20 câu, báo cáo, ontology và ba ảnh; số liệu khớp artifact.
- [ ] Kiểm tra Git tracked files/lịch sử không có `.env`, `.venv/` hoặc key, không in key trong kết quả rà soát.
- [ ] Đối chiếu quy định tên repo `K4-DAY19-HoVaTen-MSSV` với tên hiện tại dài hơn; chưa tự đổi tên, cần xác nhận quy định lớp có bắt buộc đúng mẫu hay không.
- [ ] Bàn giao file thay đổi, lệnh chạy, kết quả, vấn đề còn lại và hướng dẫn commit/push/VLearn. Chỉ thực hiện các bước xuất bản khi người dùng yêu cầu.

## 5. Bonus ontology +15: làm sau phần bắt buộc

- Bản đầu theo ontology gợi ý tạo baseline, lưu kết quả thật thành `ket_qua_benchmark_kg.hint.txt`.
- Chọn một cải tiến có ý nghĩa: node/ngưỡng định lượng để hỗ trợ Q5, hoặc giai đoạn tố tụng tránh gán “bị bắt” thành “đã kết án”. Đổi tên label không được coi là cải tiến.
- Có source và unit test cho logic mới; đo trước/sau cùng cấu hình; viết mục 7 ONTOLOGY.md.
- Cần cả mục tiêu cải thiện, bằng chứng thực tế và competency question được cải thiện. Chưa đo thì chỉ gọi là đề xuất, không khẳng định đạt bonus.

## 6. Thời gian dự kiến và ưu tiên

| Phần | Ước tính làm chủ động, không gồm chờ API/môi trường |
| --- | --- |
| Môi trường, đọc corpus, ontology | 45–75 phút |
| KG-1..KG-4, graph nhỏ, test/check | 2–3 giờ |
| Benchmark chuẩn, lỗi, ảnh, báo cáo | 1.5–2 giờ |
| Node embeddings, BFS, 20 gold questions, runner và báo cáo mở rộng | 3–5 giờ |
| Bonus nếu chọn | 1–3 giờ thêm |

Đây là ước tính kế hoạch, không phải cam kết thời gian. Phần chuẩn khoảng một buổi; bao phủ cả ảnh thường cần thêm một buổi. API pricing/model/khối lượng corpus thực tế quyết định chi phí, không dùng ước tính USD của README làm kết quả đã đo.

Ưu tiên điểm: code đúng hợp đồng → ontology khớp graph → kết quả thật → phân tích hai lỗi có bằng chứng → ảnh đúng quy cách → phần mở rộng theo ảnh → bonus. Đỗ 48 test không đồng nghĩa hoàn thành bài: rubric dành nhiều điểm cho thiết kế và phân tích.
