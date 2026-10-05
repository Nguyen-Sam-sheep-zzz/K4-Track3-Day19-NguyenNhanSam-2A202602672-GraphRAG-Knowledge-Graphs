# Cách chạy và giải thích bài Day 19

## Luồng dữ liệu

18 Điều luật + 20 bài báo → chunk 800 ký tự → embedding Gemini → Flat lấy top-3 chunk → LLM trả lời.

GraphRAG dùng cùng chunk/model, thêm: regex tách luật + LLM trích JSON tin → Neo4j → Person/Case → Crime → Article/Clause → facts → LLM.

Phần mở rộng: text của từng node → embedding node → cosine chọn seed (ưu tiên tên/alias được hỏi) → BFS queue/visited tối đa 4 hop, 180 node → subgraph-to-text → LLM. BFS bỏ MENTIONS để tránh hub chất kéo theo nhiều Điều không liên quan. Đây là BFS trên tập cạnh được chọn, không phải duyệt tất cả cạnh.

## Lệnh PowerShell

```powershell
docker start neo4j-drug-kg
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg.py --check
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg.py --judge
.\.venv\Scripts\python.exe scripts/run_local.py bench_kg_extended.py --judge
.\.venv\Scripts\python.exe scripts/run_local.py scripts/capture_graph_evidence.py
```

`--check` xóa graph và dựng graph nhỏ, vì vậy chạy trước benchmark đầy đủ. `.env` local chọn OpenAI-compatible chat API và Gemini embedding; launcher chỉ thay môi trường của tiến trình con. Không commit .env, .venv hoặc .cache.

Benchmark mở rộng dùng lại vector chunk từ lần chuẩn vừa chạy và graph đó, rồi tính riêng node indexing. `--resume` chạy tiếp nếu config/model/corpus/graph giữ nguyên. Chưa có cache ở checkout mới thì chạy chuẩn trước.

## Ba query chụp ảnh

Mở http://localhost:7474/browser/ và kết nối bằng thông tin local. Chạy `:clear` trước từng query.

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC;
```

```cypher
MATCH p=(:Person)-[:INVOLVED_IN]->(:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(:Article)
RETURN p LIMIT 25;
```

```cypher
MATCH p=(:Person {name:'Cái Quang Huy'})-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(:Article)
OPTIONAL MATCH q=(k)-[:INVOLVES|LOCATED_IN]->()
RETURN p,q;
```

Chụp query + bảng/graph + Results overview nguyên trạng. Ảnh thứ ba chọn Huy, không phải Thành. Khi demo hãy mở file kết quả và đối chiếu đường Person → Case → Crime ← Article, rồi chỉ ra một lỗi thực tế. Không đồng nhất keyword recall với accuracy; judge do cùng LLM chấm cần đọc lại nguồn.

## Phạm vi pháp luật

Đây là benchmark corpus BLHS 2015 sửa đổi 2017 và Luật PCMT 2021 của lab. Khung luật trong corpus, giai đoạn bị bắt/truy tố và mức án đã tuyên là thông tin khác nhau. Không suy ra bản án của một người chỉ từ khối lượng chất hoặc cạnh cùng Case.
