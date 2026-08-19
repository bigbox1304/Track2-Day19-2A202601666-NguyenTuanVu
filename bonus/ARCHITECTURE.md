# Hybrid Memory Assistant cho người dùng Việt Nam

**Tác giả:** Lương Sỹ Linh  
**Phạm vi:** Minimal POC, chạy độc lập không cần API key. Bản production sẽ thay
in-memory adapter bằng Qdrant và Feast.

## Mục tiêu và luồng dữ liệu

Trợ lý cần phân biệt ba loại trí nhớ. Episodic memory là các đoạn hội thoại,
tài liệu và ghi chú cụ thể; nó thay đổi liên tục và cần semantic retrieval.
Stable profile là các đặc điểm tương đối bền như ngôn ngữ, tốc độ đọc và chủ đề
ưa thích. Recent activity là tín hiệu ngắn hạn như các query trong một giờ qua.

```text
User text/query
      |
      +--> chunk + embed + metadata ------------------+
      |                                                |
      |                                         Qdrant vector store
      |                                      (filter user_id, RRF search)
      |
      +--> event stream --> Feast offline/online feature views
                              |                 |
                              +--> PIT join    +--> online lookup
                                                |
                top memories + profile + recent activity
                              |
                         LLM final response
```

POC trong `agent.py` dùng vector hash deterministic và dictionary profile để
chạy được trên máy sạch. Đây là adapter mô phỏng đúng interface; trong hệ thật,
embedding phải đến từ model multilingual và profile phải được phục vụ qua Feast.

## Quyết định 1: chunking episodic memory

Tôi chọn semantic-lite chunk: tách theo câu, sau đó gộp tối đa hai câu hoặc
khoảng 180 từ. Mỗi chunk giữ `user_id`, timestamp, nguồn và topic metadata.
Per-message chunk có độ chính xác cao cho câu hỏi chi tiết nhưng tạo quá nhiều
vector, mất ngữ cảnh và tăng storage cost. Per-conversation chunk giảm số vector
nhưng một đoạn hội thoại dài sẽ làm retrieval trả về context loãng, đồng thời
chiếm nhiều context window khi đưa vào LLM. Chunk semantic vừa giữ được một ý
trọn vẹn, vừa giới hạn kích thước prompt. Tradeoff là bộ tách câu đơn giản có
thể chia sai ở viết tắt hoặc code-switching; production nên dùng tokenizer tiếng
Việt và giới hạn theo token thay vì số từ.

## Quyết định 2: feature schema và nơi lưu

Stable profile dùng tabular features vì chúng cần được giải thích và lookup nhanh:
`preferred_language`, `reading_speed_wpm`, `topic_affinity`, `active_hours`, và
`profile_updated_at`. Entity là `user_id`; nguồn là profile event hoặc batch
consolidation; TTL của profile là 30 ngày. Recent activity là một feature view
riêng gồm `queries_last_hour`, `recent_topics` và `long_query_at_night`, có TTL
1 giờ và được cập nhật qua streaming Push API. Tôi chọn tabular làm canonical
source thay vì chỉ lưu một user embedding: tabular dễ debug, dễ PIT join và dễ
giải thích tại sao assistant cá nhân hóa một câu trả lời. Embedding sở thích có
thể là feature phụ để re-rank, nhưng không nên thay thế profile chính.

Episodic memory nằm ở vector store, không nằm trong Feast. Qdrant đảm nhiệm
similarity search, payload filter theo `user_id` và hybrid RRF; Feast đảm nhiệm
feature freshness và point-in-time correctness. Tách hai hệ giúp re-index memory
theo giờ mà không phải materialize lại toàn bộ profile theo tuần.

## Quyết định 3: freshness theo use case

Không dùng một TTL cho mọi dữ liệu. Với tài liệu user vừa đọc và query ngay sau
đó, streaming Push API cập nhật episodic vector và recent-activity feature trong
vòng dưới một giây; nếu trễ, câu hỏi “tôi vừa đọc gì?” sẽ sai ngữ cảnh. Với
recommendation đọc tiếp, refresh batch khoảng năm phút là đủ: chi phí thấp hơn
streaming liên tục và profile không cần thay đổi từng giây. Với báo cáo sở thích
ổn định hoặc memory consolidation, daily batch là hợp lý; hệ thống có thể gộp
nhiều memory tương tự thành summary và cập nhật `topic_affinity`. Tradeoff là
freshness càng cao thì chi phí event processing, write amplification và xử lý lỗi
càng lớn. Streaming feature cần idempotency key để retry không đếm một query hai
lần.

## Một lựa chọn bị loại bỏ

Tôi xem xét lưu episodic memory như embedding feature trong Feast, nhưng chọn
Qdrant riêng vì hai vòng đời khác nhau. Memory mới có thể xuất hiện mỗi phút và
cần ANN retrieval; profile lại cần schema, TTL và PIT join. Dồn cả hai vào một
feature store làm retrieval khó kiểm soát, re-index tốn kém và tăng rủi ro dùng
future data trong training. Tôi cũng không chọn per-user Qdrant collection ở
quy mô lớn: isolation dễ hiểu hơn nhưng hàng nghìn collection làm vận hành và
backup phức tạp; payload filter với `user_id` là lựa chọn cân bằng hơn, dù phải
kiểm tra authorization ở mọi query.

## Vietnamese-context considerations

User Việt Nam thường code-switch giữa tiếng Việt và thuật ngữ English như
“cloud security”, có thể gõ không dấu hoặc typo theo âm thanh. Tokenizer chỉ dùng
whitespace là baseline tốt để giữ identifier như `k8s`, nhưng không xử lý tốt
biến thể dấu và từ ghép. Production nên normalize Unicode, lưu cả bản gốc và
bản normalized, bổ sung synonym/phonetic normalization có kiểm soát, rồi so sánh
pyvi hoặc underthesea với whitespace bằng Precision@10. Embedding phải là
multilingual; bài Lab cho thấy `bge-small-en-v1.5` có thể làm paraphrase tiếng
Việt kém hơn BM25. Với dữ liệu cá nhân, `user_id` phải được filter ở vector store,
feature lookup và cache namespace; cần mã hóa at rest, audit log và tuân thủ
quy định bảo vệ dữ liệu cá nhân của Việt Nam.

## Giới hạn của POC

POC chưa xử lý encryption at rest, multi-device sync, CRUD/forget memory, phân
quyền thật, retry của stream, model multilingual production hay scale-out Qdrant.
Vector hash chỉ để demo logic; không dùng nó để đánh giá chất lượng retrieval.
Bước tiếp theo là thay adapter bằng Qdrant + Feast, thêm test isolation giữa hai
user và đo freshness end-to-end.

## Vibe-coding log

Prompt hiệu quả nhất là yêu cầu interface nhỏ với schema, TTL và output cụ thể.
Embedding model vẫn phải được chọn bằng benchmark và judgment của người thiết kế.
