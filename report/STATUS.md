# Tổng quan bàn giao Day 19

**Nguyễn Nhân Sâm — 2A202602672 — 05/10/2026.** Đã hoàn thiện bộ artifact local của bài chuẩn và phần mở rộng. Đây là bài thực nghiệm có phân tích lỗi; không khẳng định mọi đáp án đều đúng. Chưa commit, push, đổi tên repo hoặc nộp VLearn. Nhánh hiện tại: `feature/day19-completion`.

## 1. Tiến độ theo kế hoạch

| Phần | Kết quả đã xác minh | File/chứng cứ |
| --- | --- | --- |
| Môi trường | OpenAI chuẩn được ghi là đường tham chiếu; lượt thật dùng gateway tương thích cho chat + Gemini embedding-001; Neo4j local kết nối được | checkpoints/PART01.md, scripts/run_local.py |
| Ontology | 7 label, 7 loại cạnh; source_doc_ids trên mọi cạnh; doc_id nguồn đầu/danh sách nguồn đúng schema thực tế | ONTOLOGY.md, graph_evidence.json |
| KG-1..KG-4 | Entity linking, graph extraction/build, Cypher context, GraphRAG answer đã viết; 48 test gốc đạt | src/graph.py, checkpoints/PART02.md |
| Kiểm tra | 64 test (48 gốc + 16 bổ sung); check hợp đồng 7 OK trước khi dựng đầy đủ | checkpoints/tests_final.txt, checkpoints/part02_check_after_priority.txt |
| Benchmark chuẩn | 6 câu × 2 pipeline, đủ judge/chi phí/latency; 176 chunks, 203 node / 378 cạnh | ../ket_qua_benchmark_kg.txt, benchmark_kg_standard.json, REPORT_KG.md |
| Phần mở rộng | 203 node embeddings 3072 chiều, BFS thực hiện bằng queue/visited, 378 triples có nguồn | node_index_metadata.json, triples.json, src/graph_retrieval.py |
| Benchmark mở rộng | 20 câu × 2 pipeline = 40 câu trả lời thật; có prompt, chunks, seeds, paths, facts, score/usage | benchmark_kg_extended.json, REPORT_KG_EXTENDED.md |
| Báo cáo/ảnh | Báo cáo chuẩn phân tích E2/E3/E4/E5; 3 ảnh Neo4j thật, đúng PNG | REPORT_KG.md, img/ |
| Rà bàn giao | Artifact/nguồn/BFS limits/schema đủ; grader/gold/test gốc không đổi; không phát hiện key local/API key patterns trong file để đưa vào Git hoặc lịch sử | checkpoints/delivery_audit.json (passed=true) |

## 2. Kết quả chính

| Bộ đo | Flat | Graph |
| --- | ---: | ---: |
| 6 câu chuẩn: keyword recall | 0.51 | 0.82 (Cypher) |
| 6 câu chuẩn: judge trung bình /2 | 1.33 | 1.67 |
| 6 câu chuẩn: thời gian/câu | 10.14 s | 12.89 s |
| 20 câu mở rộng: keyword recall | 0.649 | 0.978 (BFS) |
| 20 câu mở rộng: criterion recall | 0.615 | 0.967 |
| 20 câu mở rộng: judge=2 | 4/20 | 20/20 |
| 20 câu mở rộng: thời gian/câu | 11.20 s | 12.92 s |
| 20 câu mở rộng: p95 | 15.54 s | 16.06 s |

Graph bổ sung luật tốt hơn nhưng tăng prompt, chi phí chat và độ trễ trung bình. Đánh giá mở rộng có thêm ưu tiên seed và ngân sách 100 facts; không quy mọi cải thiện cho riêng thuật toán BFS. Judge cùng model trả lời, không phải chấm độc lập.

Chat dùng OpenAI-compatible API với model `gpt-6-luna`; embedding dùng Gemini `gemini-embedding-001`. Endpoint cụ thể giữ trong `.env` local. Chi phí thực tế embedding-001 chưa đo được vì response không trả token usage và trang giá hiện tại không niêm yết giá riêng model này. Query 20 câu: Flat $0.0029815, BFS $0.0164948 subtotal chat; judge tách riêng.

## 3. Các giới hạn phải nói khi trình bày

- Q4 chuẩn vẫn trả 7 năm khoản cơ bản dù prompt có mức cao nhất Điều 255; Q5 thiếu văn bản khoản sau cắt ngân sách facts, nên chưa trả đủ khung luật.
- Case khóa theo tên còn trùng Huy/Viện Pháp y; Q6 không được hiểu số Case là số vụ độc lập.
- M17/BFS nối đúng các Điều nhưng thêm nhận định thiếu xác nhận MDMA. Nguồn có 0,686g; serialization 100 facts bỏ mất lượng này, judge vẫn chấm 2. Vì vậy không nói “BFS đúng hoàn toàn 100%”.
- Bộ mở rộng có câu negative/uncertainty/phòng ngừa, không phải mọi câu đều có đường graph thuần túy. Luật trích regex, tin trích LLM; không tuyên bố LLM NER trên toàn corpus.
- Ba ảnh chụp toàn viewport Neo4j trong Codex, không crop/chỉnh nội dung. Screenshot API trả JPEG; đã đổi định dạng sang PNG và xác nhận pixel giải mã giống hệt, giữ bản gốc ở cache local. Ảnh không kèm thanh cửa sổ hệ điều hành; nếu giảng viên yêu cầu cả chrome cửa sổ desktop, cần tự chụp lại đúng quy cách đó.
- Corpus luật là snapshot của lab (BLHS 2015 sửa đổi 2017, Luật PCMT 2021); kết quả đối chiếu corpus không xác nhận luật hiện hành hoặc bản án của người cụ thể.

## 4. Bạn làm gì tiếp theo

1. Đọc [DEMO.md](DEMO.md) và [PRICING.md](PRICING.md) để hiểu luồng, lệnh và cách lấy giá thật; mở [REPORT_KG.md](REPORT_KG.md) và [REPORT_KG_EXTENDED.md](REPORT_KG_EXTENDED.md) khi trình bày số liệu.
2. Mở Neo4j tại http://localhost:7474/browser/; dùng query trong DEMO để trình bày đường Huy → Case → Crime ← Article, rồi giải thích lỗi trùng và ngân sách context.
3. Kiểm tra yêu cầu tên repository của lớp: SUBMISSION.md yêu cầu `K4-DAY19-HoVaTen-MSSV`, tên GitHub hiện tại dài hơn mẫu. Chưa tự đổi tên; cần xác nhận cách chấm tên.
4. Sau khi tự rà báo cáo/ảnh, commit/push lên GitHub và nộp link VLearn. Các bước này chưa được thực hiện trong lượt bàn giao local.

Bonus ontology +15 chưa làm; không có đo trước–sau ontology mới nên không tự nhận bonus. Neo4j còn chạy để bạn demo; khi xong có thể `docker stop neo4j-drug-kg`.

## 5. Chạy lại

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg.py --check
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg.py --judge
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg_extended.py --judge
.\.venv\Scripts\python.exe scripts/run_local.py scripts/capture_graph_evidence.py
.\.venv\Scripts\python.exe scripts/analyze_standard_results.py
.\.venv\Scripts\python.exe scripts/write_extended_report.py
.\.venv\Scripts\python.exe scripts/verify_delivery.py
```

Chỉ cần xem artifact hiện tại thì không phải chạy lại API. --check reset graph nhỏ, luôn chạy trước benchmark đầy đủ. Lượt mới có thể đổi extraction/đáp án do model/gateway; ảnh và báo cáo phải được rà lại cho khớp lượt đó. scripts/analyze_standard_results.py phục hồi JSON chuẩn, REPORT_KG.md cần cập nhật thủ công theo kết quả mới; báo cáo mở rộng được sinh bằng script. Dùng scripts/run_local.py để đọc đúng .env local, tránh cấu hình provider kế thừa từ môi trường Codex. Không commit .env, .venv, .cache.
