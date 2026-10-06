# Ghi chú chi phí — Gemini free tier

## Kết quả đã đo trong bài

- Chat dùng OpenAI-compatible API với model `gpt-6-luna`. Response có input/output token, nên báo cáo tính được subtotal chat theo bảng giá OpenAI chính thức hiện tại: `$0.10 / 1M input` và `$0.50 / 1M output` (short context). Đây là giá tham chiếu theo model; gateway có thể thu khác.
- Embedding dùng `gemini-embedding-001`. Response trả vector 3072 chiều nhưng không trả `prompt_tokens`; audit ghi `input_tokens=null`, `usd=null` cho các request embedding.
- Ngày 06/10/2026, Nguyễn Nhân Sâm xác nhận key của lượt thực nghiệm thuộc **Google AI Studio free tier**. Theo xác nhận này, **chi phí thực trả embedding = 0 USD** cho chunk indexing, node indexing, query và các lượt embedding thử/lỗi đã gọi.
- Số token embedding vẫn **chưa đo được**. `usd=null` trong log phản ánh bộ đo không có usage/đơn giá, không phải số tiền bị thu. Giữ nguyên log gốc và bổ sung thông tin free tier trong báo cáo; không suy ra free tier từ giá trị USD bằng 0 của bộ đo.
- Căn cứ về loại tài khoản là xác nhận của người học; chưa đối soát dashboard billing độc lập. Mức 0 USD chỉ áp dụng cho lượt này trên free tier, không áp dụng cho tài khoản trả phí hoặc mọi lượt chạy tương lai.

## Phân biệt chi phí thực trả và giá tham chiếu

1. Chi phí embedding thực trả của bài là **0 USD theo free tier do người học xác nhận**; không cần số token để tính khoản thực trả này. Nếu cần chứng từ độc lập, lưu bằng chứng loại tài khoản/usage từ project đã cấp `GEMINI_API_KEY`, che thông tin riêng.
2. Chi phí chat trong báo cáo vẫn là **ước tính theo token và bảng giá model**, chưa phải số tiền bị trừ qua dịch vụ cung cấp chat. Free tier Gemini chỉ áp dụng cho embedding của bài.
3. Khi chuyển sang dịch vụ trả phí, cần usage và đúng đơn giá để tính chi phí. OpenAI `text-embedding-3-small` có mức tham chiếu `$0.02 / 1M input tokens`; công thức là `input_tokens / 1,000,000 × 0.02`. Đây là model khác; phải chạy lại indexing và benchmark nếu chuyển, không gán giá này cho vector Gemini đã tạo.

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

Không đưa API key, `.env`, `.venv` hoặc billing screenshot chứa thông tin riêng vào repository. Báo cáo tách chi phí embedding free tier theo xác nhận người học, chat ước tính và số token embedding chưa đo được.
