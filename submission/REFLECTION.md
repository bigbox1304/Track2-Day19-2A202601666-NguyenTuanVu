# Reflection — Lab 19

**Tên:** Nguyễn Tuấn Vũ
**Cohort:** A20-K2  
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trong golden set, BM25 làm tốt nhất với nhóm `exact` (96,7%) vì các từ khóa kỹ
thuật trong query xuất hiện luôn trong tài liệu. Ở cấu hình Lite với
`bge-small-en-v1.5`, BM25 vẫn cao hơn vector ở nhóm `paraphrase` (33,3% so với
24,0%). Lý do có thể là model này chủ yếu được tối ưu cho tiếng Anh nên xử lý
paraphrase tiếng Việt chưa tốt. Với nhóm `mixed`, hybrid đạt kết quả tốt nhất
(100%) vì tận dụng được cả thông tin lexical và semantic. Điểm trung bình của
hybrid là 78,6%, cao nhất trong các mode. Nếu query là mã lỗi, tên API hoặc một
identifier cần khớp chính xác thì tôi sẽ không dùng hybrid, vì pure BM25 đã đủ
hiệu quả và latency thấp hơn. Pure vector sẽ phù hợp hơn với paraphrase nếu có
model multilingual tốt; lúc đó không cần dùng hybrid khi semantic đã tốt hơn
lexical khá rõ.

---

## Điều ngạc nhiên nhất khi làm lab này

Điều làm tôi bất ngờ nhất là embedding model tiếng Anh khiến vector search cho
paraphrase tiếng Việt kém hơn cả BM25. Qua lab này, tôi thấy tìm kiếm
“semantic” không phải lúc nào cũng tốt hơn, nhất là khi model không phù hợp với
ngôn ngữ và corpus đang dùng.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: Không
