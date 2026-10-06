# Phần 3 — Benchmark chuẩn và trạng thái tiếp tục

> **Cập nhật cuối 05/10/2026:** lượt cold benchmark chuẩn đã hoàn tất, artifact gốc tại `../../ket_qua_benchmark_kg.txt`, audit `bench_kg_benchmark_20261005-181513.json`, bảng phục hồi ở `../benchmark_kg_standard.json`. Graph cuối 203 node / 378 cạnh; Flat recall 0.51, judge 1.33, 10.14s/câu; Graph recall 0.82, judge 1.67, 12.89s/câu. Q4 vẫn sai khung tối đa dù prompt có khoản 4; Q5 thiếu văn bản khoản do cắt context. Phân tích đầy đủ tại `../REPORT_KG.md`. Launcher cuối không dùng cache để thay cold indexing. Các mục phía dưới giữ lịch sử lần trước, không dùng số cũ làm kết quả cuối.

Ngày 05/10/2026. Đây là checkpoint; chưa phải kết luận toàn bài sẵn sàng nộp.

## Lần chạy đầu đã hoàn tất

Artifact nguyên bản được lưu tại `part03_first_run.txt`. Model: DevQuota `gpt-6-luna` cho chat và Gemini `gemini-embedding-001` cho embedding; top_k=3, chunk_size=800, 176 chunks; graph 196 nodes / 365 relationships.

| Chỉ số | Flat | Graph |
| --- | --- | --- |
| Recall trung bình | 0.51 | 0.83 |
| Judge trung bình /2 | 1.33 | 1.83 |
| Thời gian trung bình/câu | 39.87 s | 30.91 s |
| Query USD phần đã biết/câu | 0.00013 | 0.00066 |
| Indexing USD phần đã biết | 0.00000 | 0.00786 |

USD trên là phần có giá/usage được xác minh, không phải tổng hóa đơn. Ở checkpoint 05/10, chưa có thông tin loại tài khoản và 188 request embedding thiếu token usage. Cập nhật 06/10: người học xác nhận Google AI Studio free tier, nên embedding thực trả 0 USD theo xác nhận đó; số token vẫn chưa đo được. Độ trễ là một lần đo, chịu biến động dịch vụ; chưa chứng minh Graph luôn nhanh hơn.

## Lỗi thực tế và sửa sau benchmark

- Q3 Graph trả đúng “2 đến 7 năm tù” nhưng keyword recall chỉ 0.67 do gold tìm nguyên văn “02 năm đến 07 năm”. Đây là lỗi phép đo E4; giữ nguyên bộ chấm.
- Q4 Graph chỉ trả tối đa khoản 1 là 7 năm, judge=1; gold hỏi mức cao nhất của Điều 255 là 20 năm hoặc chung thân. Đã thêm logic ưu tiên facts có khoản cao/chung thân/tử hình khi hỏi tối đa. Test riêng quan sát fail rồi pass. Chưa kết luận Q4 thực tế đã sửa đúng cho tới khi chạy lại và đọc câu trả lời.
- Neo4j có hai Case về Huy: `Vụ Cái Quang Huy vận chuyển ma túy qua sân bay Nội Bài` (nguồn teaser bài Thành) và `Vụ vận chuyển hơn 10kg ma túy từ Đức về Việt Nam qua sân bay Nội Bài` (bài gốc). Case name-only MERGE chưa gộp cùng vụ, làm chứng cứ E3.
- Q6 Graph nêu thêm vụ 8 đường dây có MDMA; cần đối chiếu “thuốc lắc” nguyên văn với extraction/gold trước kết luận. Judge 2 không thay thế kiểm tra nguồn.

## Kiểm tra sau sửa context

`tests_after_context_priority.txt`: **61 passed in 0.11s** (48 gốc + 13 bổ sung).

`part02_check_after_priority.txt`: **7/7 OK**, graph nhỏ 148 node / 294 cạnh, 45 facts và Điều 251. Check reset graph nhỏ; lần benchmark tiếp theo sẽ dựng graph đầy đủ lại.

## Tiến trình đang chạy

Benchmark chuẩn đang được chạy lại từ code sau sửa context. Một lần thử bị Gemini 429: free-tier EmbedContentRequestsPerMinutePerUserPerProjectPerModel limit=100, retry khoảng 39 giây. Launcher đã dùng cache embeddings local để hạn chế gọi lại; số liệu indexing của lần dùng cache phải được ghi là warm cache, không đem so trực tiếp với cold indexing lần đầu.

Tiến trình lần chạy lại hiện chưa có artifact cuối được xác nhận. Cần đọc output và kiểm tra graph/answer mới trước khi hoàn tất mốc 3.

## Phần mở rộng

Đã viết `src/graph_retrieval.py` (node index, cosine seeds, BFS queue/visited/depth/budget, triples và serialization), runner `bench_kg_extended.py`, dataset `data/benchmark_kg_20.json` có 20 câu với gold/criteria/source/evidence_path. Các test BFS offline đạt. **Chưa tạo node embeddings trên graph đầy đủ và chưa chạy 40 câu trả lời Flat/BFS thật**; chưa được coi là hoàn thành mốc này. Một số câu là negative/uncertainty multi-source reasoning, không phải mọi câu đều có đường graph thuần túy.

Tiếp theo: chốt benchmark chuẩn → chạy/kiểm tra phần mở rộng → cập nhật ONTOLOGY/REPORT_KG và báo cáo mở rộng → chụp 3 ảnh Neo4j thật → rà toàn bộ deliverables. Bonus +15 chưa thực hiện.

Chưa commit, push hoặc nộp VLearn. Grader, hai file test gốc và bộ 6 câu gốc không bị sửa.
