# Phần 4 — Node embeddings, BFS và hoàn tất artifact local

05/10/2026. Lượt mở rộng `bench_kg_extended_benchmark_20261005-183106.json` và `../benchmark_kg_extended.json` đã đủ 40 rows. Graph giữ nguyên 203 node / 378 cạnh từ chuẩn; 203 node có vector Gemini 3072 chiều. Node indexing: 13 batch, 165.10 giây wall, thiếu giá/token usage Gemini. Export đủ 378 triples có source_doc_ids.

BFS có queue/visited, 4 hop, 180 node, bỏ MENTIONS, ưu tiên seed tên/alias rồi cosine; 100 facts. Dataset 20 câu có gold/criteria/nguồn và đường chứng cứ, gồm quan hệ và negative/multi-source reasoning. Không sửa bộ 6 câu gốc.

| Chỉ số | Flat | BFS |
| --- | ---: | ---: |
| Keyword recall | 0.649 | 0.978 |
| Criterion recall | 0.615 | 0.967 |
| Judge đủ ý | 4/20 | 20/20 |
| Mean latency | 11.20 s | 12.92 s |
| p95 | 15.54 s | 16.06 s |
| Query USD subtotal | 0.0029815 | 0.0164948 |

Judge không thay kiểm tra người: M17 còn nhận định sai về thiếu xác nhận MDMA, đã ghi báo cáo. Không coi 20/20 judge là hoàn toàn đúng. Chi phí Gemini chưa biết, 96 text embedding thành công trước lỗi batch quota được giữ audit riêng, không bị xóa dấu vết.

Rà cuối: 64 passed, 7 OK trước benchmark; grader/test/gold gốc không đổi. Ba ảnh thật chuyển container JPEG→PNG giữ pixel giống hệt, bản gốc trong cache. `delivery_audit.json`: passed=true; không phát hiện API key trong artifact/lịch sử Git. Chi tiết kết quả, các giới hạn, tên repo/ảnh cần kiểm tra trước nộp ở `../STATUS.md`. Bonus chưa làm. Chưa commit/push/nộp.
