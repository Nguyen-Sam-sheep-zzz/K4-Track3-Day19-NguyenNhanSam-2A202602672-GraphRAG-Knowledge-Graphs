# Phần 2 — Pipeline GraphRAG chuẩn

Đã hoàn thành KG-1..KG-4: chuẩn hóa tên tội; regex luật + LLM JSON cho tin; nạp Neo4j có nguồn; retrieval xuyên KB và ghép chunk/facts vào prompt.

Ngày 05/10/2026, `tests_core.txt`: **56 passed** (48 test gốc, 8 test bổ sung). `part02_check.txt`: đủ **7 OK**, graph nhỏ **148 node / 294 cạnh**, đường xuyên KB **2 cạnh**. Check sau sửa provenance có **45 facts** và Điều 251. API chat dùng DevQuota gpt-6-luna; embedding Gemini embedding 001, smoke **3072 chiều**.

Đã sửa lỗi JSON extraction bị nuốt thành danh sách rỗng; lỗi hiện ghi doc_id và dừng để rà nguồn. Alias được hợp nhất, node/cạnh giữ source_doc_ids. Case vẫn MERGE theo tên nên chưa khử trùng nhiều bài cùng vụ; teaser vụ Huy ở cuối bài Thành có thể tạo Case thứ hai. Giữ hiện tượng này làm chứng cứ giới hạn extraction.

Metering có bảng giá Luna 0.10/0.50 USD mỗi triệu token input/output. Model thiếu giá trả NaN ở hàm price; Usage.usd lưu **phần chi phí đã biết**, cùng unpriced_calls/missing_usage_calls. Audit mỗi request ghi USD/token null khi chưa biết. Gemini không trả prompt_tokens và giá model 001 chưa xác minh được trên trang giá hiện tại: không coi embedding miễn phí, chưa có tổng USD đầy đủ.

Lệnh chạy được lặp lại qua `python scripts/run_local.py bench_kg.py --check` / `--judge`. Launcher nạp .env local trong tiến trình con, giữ nguyên grader, xuất audit prompt/answer/usage và cache embeddings local bị Git ignore.

Benchmark đủ corpus và 6 câu đang thực hiện; checkpoint này chưa kết luận chất lượng hoặc toàn bài hoàn thành. Chưa commit/push/nộp.
