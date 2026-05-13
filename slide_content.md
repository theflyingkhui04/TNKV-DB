# NỘI DUNG VÀ KỊCH BẢN THIẾT KẾ SLIDE DỰ ÁN TNKV-DB

*Tài liệu này cung cấp chi tiết nội dung văn bản (text) và gợi ý hình ảnh/biểu đồ cần chèn cho từng slide trong bài báo cáo.*

---

## PHẦN 1: TỔNG QUAN DỰ ÁN

### Slide 1: Trang bìa
*   **Tiêu đề chính:** Xây dựng Hệ quản trị Cơ sở dữ liệu Vector thưa cho Tìm kiếm Thông tin (TNKV-DB)
*   **Tiêu đề phụ:** Báo cáo Đồ án môn học Information Retrieval
*   **Hình ảnh đề xuất:** Logo trường đại học (góc trên trái) và một biểu tượng minh họa Mạng lưới dữ liệu văn bản (Text Data Network / Vector Space) ở giữa.
*   **Nội dung văn bản:**
    *   Sinh viên thực hiện: Khôi, Nhật, Tùng
    *   Giảng viên hướng dẫn: [Điền tên Giảng viên]
    *   Thời gian: Năm học 2024-2025

### Slide 2: Đặt vấn đề và Mục tiêu Đề tài
*   **Tiêu đề Slide:** Đặt vấn đề và Mục tiêu
*   **Hình ảnh đề xuất:** Một hình minh họa (icon) so sánh sự khác biệt giữa tìm kiếm bằng cơ sở dữ liệu quan hệ (SQL LIKE) chậm chạp và tìm kiếm bằng cấu trúc chỉ mục.
*   **Nội dung văn bản (Bullet points):**
    *   **Thực trạng:** Dữ liệu phi cấu trúc (văn bản) ngày càng lớn. Việc tra cứu bằng cơ sở dữ liệu quan hệ không đáp ứng được tốc độ và độ chính xác.
    *   **Mục tiêu:** Tự xây dựng (build from scratch) một Core Engine cho Cơ sở dữ liệu Vector thưa với các yêu cầu:
        1. Xử lý và lập chỉ mục ngôn ngữ tiếng Việt.
        2. Tối ưu hóa tài nguyên phần cứng (RAM và Disk).
        3. Tích hợp tính năng xếp hạng và tìm kiếm thông minh.

---

## PHẦN 2: KIẾN TRÚC HỆ THỐNG VÀ TIỀN XỬ LÝ

### Slide 3: Sơ đồ Kiến trúc Hệ thống
*   **Tiêu đề Slide:** Kiến trúc Tổng thể TNKV-DB
*   **Hình ảnh đề xuất:** Vẽ một **Sơ đồ khối (Block Diagram)** chia làm 3 luồng rõ rệt: 
    1. *Ingestion Pipeline:* Document -> Tokenizer -> Indexer.
    2. *Storage Layer:* RAM (Hash Map) <-> Disk (postings.bin, index.pkl).
    3. *Search API:* User Request -> FastAPI -> TF-IDF/BM25 Ranker -> Streamlit UI.
*   **Nội dung văn bản:** Chỉ cần text tóm tắt chú thích cho biểu đồ, Giảng viên sẽ nhìn biểu đồ là chính.

### Slide 4: Giai đoạn Tiền xử lý văn bản (Preprocessing)
*   **Tiêu đề Slide:** Giai đoạn Tiền xử lý Dữ liệu
*   **Hình ảnh đề xuất:** Một quy trình minh họa biến đổi một câu gốc thành danh sách các từ khóa (tokens).
*   **Nội dung văn bản:**
    *   **Chuẩn hóa:** Loại bỏ ký tự đặc biệt, chuẩn hóa Unicode tiếng Việt (NFC).
    *   **Tách từ (Tokenization):** Phân tách câu thành các đơn vị có nghĩa.
    *   **Lọc từ dừng (Stopwords Removal):** Loại bỏ các từ nối vô nghĩa ("là", "và", "của") dựa trên bộ từ điển xây dựng sẵn nhằm giảm nhiễu.
    *   **Thống kê:** Tính toán Tần suất xuất hiện cục bộ (Term Frequency).

---

## PHẦN 3: CẤU TRÚC LẬP CHỈ MỤC VÀ LƯU TRỮ

### Slide 5: Cấu trúc Chỉ mục ngược (Inverted Index)
*   **Tiêu đề Slide:** Cấu trúc Chỉ mục ngược trong Bộ nhớ
*   **Hình ảnh đề xuất:** Bảng vẽ minh họa Bảng băm (trái) trỏ các mũi tên sang cấu trúc Danh sách liên kết (phải) chứa danh sách tài liệu.
*   **Nội dung văn bản:**
    *   **Bảng Từ Vựng (Hash Map):** Đảm bảo tốc độ tra cứu từ khóa tức thời $O(1)$.
    *   **Danh sách Xuất hiện (Postings List):** Sử dụng Danh sách liên kết đơn (Singly Linked List) để lưu trữ `doc_id`, tần suất và vị trí.
    *   Các Node trong danh sách được sắp xếp tăng dần theo `doc_id` nhằm tối ưu hóa thuật toán Giao (Intersection) hai tập hợp với độ phức tạp $O(M + N)$.

### Slide 6: Cơ chế Lưu trữ trên Đĩa cứng (Disk-based Indexing)
*   **Tiêu đề Slide:** Tối ưu hóa Bộ nhớ với Disk-based Indexing
*   **Hình ảnh đề xuất:** Cấu trúc file chia làm 2 tầng (RAM chứa `index.pkl` - Disk chứa `postings.bin` với các khối dữ liệu và con trỏ byte offset).
*   **Nội dung văn bản:**
    *   **Vấn đề:** Nếu lưu toàn bộ chỉ mục trên RAM sẽ dẫn đến tràn bộ nhớ (Out of Memory).
    *   **Giải pháp phân tách tệp:**
        *   `index.pkl`: Chỉ nạp Bảng từ vựng và Metadata lên bộ nhớ trong.
        *   `postings.bin`: Lưu dữ liệu gốc.
    *   **Truy xuất ngẫu nhiên:** Sử dụng thao tác `seek()` dựa trên `offset` và `length` để đọc chính xác khối byte cần thiết mà không tải thừa dữ liệu.

### Slide 7: Nén Chỉ mục (Index Compression)
*   **Tiêu đề Slide:** Thuật toán Nén Chỉ mục
*   **Hình ảnh đề xuất:** Biểu đồ mô phỏng phép trừ Gap Encoding: `[10, 15, 22] -> [10, 5, 7]`.
*   **Nội dung văn bản:**
    *   **Mã hóa Khoảng cách (Gap Encoding):** Lưu trữ khoảng cách giữa các `doc_id` liên tiếp để thu nhỏ biên độ giá trị.
    *   **Mã hóa Variable Byte:** Biểu diễn các số nguyên nhỏ bằng ít byte hơn thay vì cố định 4 bytes/số nguyên.
    *   **Kết quả:** Tiết kiệm đáng kể tài nguyên đĩa cứng vật lý và giảm thiểu băng thông I/O khi đọc tệp (giảm thiểu kích thước tệp `postings.bin`).

---

## PHẦN 4: THUẬT TOÁN TRUY XUẤT VÀ XẾP HẠNG

### Slide 8: Đánh giá Trọng số với TF-IDF và Okapi BM25
*   **Tiêu đề Slide:** Mô hình Không gian Vector và Đánh giá Trọng số
*   **Hình ảnh đề xuất:** Hai công thức toán học của TF-IDF và BM25 được thiết kế đẹp mắt.
*   **Nội dung văn bản:**
    *   **Ma trận thưa (Sparse Matrix):** Xây dựng thuật toán tính toán TF-IDF không phụ thuộc thư viện có sẵn.
    *   **Thuật toán Okapi BM25:** Tối ưu hóa xếp hạng bằng cách chống bão hòa tần suất từ (Term Frequency Saturation) và chuẩn hóa theo độ dài tài liệu (Document Length Normalization).

### Slide 9: Cấu trúc Min-Heap trong tìm kiếm Top-K
*   **Tiêu đề Slide:** Tối ưu Tốc độ Trích xuất Kết quả (Top-K Retrieval)
*   **Hình ảnh đề xuất:** Biểu đồ minh họa Cấu trúc cây Min-Heap kích thước K chứa các tài liệu có điểm số cao nhất.
*   **Nội dung văn bản:**
    *   Tính toán độ tương đồng bằng công thức Khoảng cách Cosine (Cosine Similarity).
    *   Thay vì sắp xếp toàn bộ hàng triệu kết quả bằng thuật toán Sorting $O(N \log N)$, hệ thống áp dụng cấu trúc **Hàng đợi ưu tiên (Priority Queue / Min-Heap)**.
    *   Đạt được kết quả Top-K với độ phức tạp tối ưu $O(N \log K)$.

---

## PHẦN 5: TÍNH NĂNG TÌM KIẾM NÂNG CAO

### Slide 10: Tự động sửa lỗi chính tả (Spell Checking)
*   **Tiêu đề Slide:** Đề xuất Sửa lỗi Chính tả Tốc độ cao
*   **Hình ảnh đề xuất:** Minh họa việc chặt từ "hello" thành trigrams: `"$he", "hel", "ell", "llo", "lo$"`.
*   **Nội dung văn bản:**
    *   **Khó khăn:** Thuật toán Levenshtein (Edit Distance) có độ phức tạp quá cao nếu so khớp với toàn bộ từ vựng.
    *   **Tối ưu bằng Chỉ mục N-gram:** Xây dựng Trigram Index để lọc nhanh Top 50 ứng viên có hệ số Jaccard Similarity cao nhất.
    *   Chỉ áp dụng Edit Distance trên tập ứng viên thu gọn, tăng tốc độ xử lý lên hàng trăm lần.

### Slide 11: Mở rộng truy vấn (Rocchio Algorithm)
*   **Tiêu đề Slide:** Phản hồi Thích hợp và Mở rộng Truy vấn
*   **Hình ảnh đề xuất:** Công thức toán học của Rocchio và luồng minh họa `User Feedback -> Vector hóa bài viết -> Cộng gộp Vector Truy vấn`.
*   **Nội dung văn bản:**
    *   Cơ chế (Relevance Feedback) thu thập thông tin đánh giá độ liên quan từ người dùng.
    *   Ứng dụng thuật toán Rocchio để dịch chuyển vector truy vấn về phía không gian chứa các tài liệu hữu ích.
    *   Khai thác hiện tượng đồng xuất hiện từ khóa (Co-occurrence) để hệ thống Vector thưa có thể lập bản đồ ngữ nghĩa tương đối mà không cần dùng Mô hình Học Sâu (Deep Learning).

---

## PHẦN 6: DEMO VÀ TỔNG KẾT

### Slide 12: Giao diện và Trải nghiệm Người dùng
*   **Tiêu đề Slide:** Giao diện Tương tác (Web UI)
*   **Hình ảnh đề xuất:** Chụp màn hình (Screenshot) giao diện Streamlit với kết quả tìm kiếm được highlight (in đậm/đổi màu) phần chứa từ khóa (Snippet).
*   **Nội dung văn bản:**
    *   Xây dựng API Backend độc lập bằng FastAPI.
    *   Hiển thị trích đoạn văn bản (Snippets) tương ứng với truy vấn.
    *   Giao diện thân thiện để thao tác phản hồi Rocchio.

### Slide 13: Kết luận và Hướng phát triển
*   **Tiêu đề Slide:** Kết luận
*   **Nội dung văn bản:**
    *   **Kết quả đạt được:** Tự xây dựng thành công bộ máy tra cứu (Core Engine) đáp ứng các tiêu chuẩn khắt khe về kỹ thuật lưu trữ và xử lý của môn học.
    *   **Hướng phát triển:**
        *   Tiến hành đánh giá hệ thống bằng các độ đo học thuật chuyên sâu như Mean Average Precision (MAP) và NDCG trên bộ dữ liệu chuẩn.
        *   Tích hợp kỹ thuật Dense Vector (Embedding) để hướng tới Tìm kiếm Lai (Hybrid Search).

---
*Gợi ý thuyết trình: Trong quá trình trình bày Slide 11 (Rocchio), người nói nên giải thích ví dụ thực tế đã quan sát được về việc truy vấn "xứ Huế", tick chọn bài "Bánh mì xứ Huế" khiến kết quả trả về hiển thị thêm các bài về "Ẩm thực". Giảng viên sẽ đánh giá rất cao độ am hiểu về bản chất thuật toán của nhóm.*
