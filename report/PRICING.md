# Ghi chú chi phí và cách lấy giá thực tế

## Kết quả đã đo trong bài

- Chat dùng OpenAI-compatible API với model `gpt-6-luna`. Response có input/output token, nên báo cáo tính được subtotal chat theo bảng giá OpenAI chính thức hiện tại: `$0.10 / 1M input` và `$0.50 / 1M output` (short context). Đây là giá tham chiếu theo model; gateway có thể thu khác.
- Embedding dùng `gemini-embedding-001`. Response trả vector 3072 chiều nhưng không trả `prompt_tokens`; audit ghi `input_tokens=null`, `usd=null` cho các request embedding.
- Google hiện có mục giá cho **Gemini Embedding 2** ở `$0.20 / 1M text input tokens`: <https://ai.google.dev/gemini-api/docs/pricing>. Đây là model khác với `gemini-embedding-001`, nên không dùng giá Embedding 2 để gán ngược cho lượt chạy này.
- Vì vậy chi phí embedding thực tế của lượt benchmark này được ghi là **unknown / chưa xác định**, không ghi `$0` và không gọi là miễn phí.

## Muốn có số tiền thực tế

1. Mở billing/usage dashboard của project đã cấp `GEMINI_API_KEY`, lọc thời gian chạy benchmark và xem metric Embeddings. Đây là nguồn duy nhất cho số tiền bị trừ thật; API compatibility không cung cấp đủ token usage.
2. Nếu cần một benchmark có chi phí tính được ngay từ response, dùng OpenAI chính thức với `OPENAI_BASE_URL=https://api.openai.com/v1`, key hợp lệ và `text-embedding-3-small`, rồi chạy lại toàn bộ indexing/query/20 câu. OpenAI đang niêm yết model này ở `$0.02 / 1M input tokens`; công thức là `input_tokens / 1,000,000 × 0.02`. Không trộn vector Gemini cũ với vector OpenAI mới.
3. Nếu gateway sau này công bố một embedding model và đơn giá/token usage, cập nhật `src/llm.py`, chạy lại benchmark từ đầu và thay toàn bộ artifact chi phí.

## Nguồn giá chính thức đã đối chiếu

- Chat/model pricing: <https://developers.openai.com/api/docs/pricing> — `gpt-6-luna`, short-context input `$0.10` và output `$0.50` mỗi 1M token.
- OpenAI embedding model: <https://developers.openai.com/api/docs/models/text-embedding-3-small> — `$0.02` mỗi 1M input token.
- Gemini pricing: <https://ai.google.dev/gemini-api/docs/pricing> — có giá Gemini Embedding 2, nhưng không dùng để gán ngược cho `gemini-embedding-001` của lượt chạy này.

## Cấu hình tái lập hiện tại

```env
LLM_PROVIDER=openai
OPENAI_CHAT_MODEL=gpt-6-luna
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Không đưa API key, `.env`, `.venv` hoặc billing screenshot chứa thông tin riêng vào repository. Báo cáo hiện tại dùng số subtotal có bằng chứng và ghi rõ phần chưa đo được.
