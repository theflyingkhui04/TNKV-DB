# TNKV DB
> **The Lightweight Sparse Vector Database for IR Purists**

Hệ thống giả lập Cơ sở dữ liệu Vector thưa (Sparse Vector Database) được xây dựng bằng Python, sử dụng Inverted Index và mô hình không gian vector (Vector Space Model - TF-IDF, BM25) thay vì Deep Learning/Dense Vectors.

Dự án được thiết kế theo kiến trúc phân tán dạng Vertical Slices, tối ưu cho bài tập lớn môn "Truy xuất thông tin" (Information Retrieval).

## Kiến trúc hệ thống
Hệ thống bao gồm 3 module chính tương ứng với 3 tính năng giao tiếp qua FastAPI và chia sẻ State trên RAM:

1. **Ingestion & Storage (`core/ingestion/`)**: 
   - Đảm nhiệm tiền xử lý văn bản (Tokenize, Stopwords).
   - Xây dựng Inverted Index (Lập chỉ mục ngược).
   - Nén danh sách Postings bằng thuật toán Variable Byte và Gap Encoding.
   - Lưu trữ dạng Disk-based Indexing (Block Offset).

2. **Search & Ranking (`core/search/`)**: 
   - Vector hóa truy vấn (TF-IDF, Okapi BM25, BM25+).
   - Tính toán độ tương đồng (Cosine Similarity).
   - Truy xuất Top-K văn bản phù hợp nhất sử dụng Min-Heap.
   - Trích xuất Snippet & Highlight từ khóa tìm kiếm.

3. **Smart Experience (`core/smart/`)**: 
   - Bắt lỗi chính tả và gợi ý sửa lỗi truy vấn bằng N-gram/Trigram Index và Edit Distance.
   - Mở rộng truy vấn (Query Expansion) bằng thuật toán Rocchio (Relevance Feedback).

---

## Hướng dẫn Cài đặt & Khởi chạy

### 1. Yêu cầu môi trường
- Python 3.9+
- Khuyến nghị sử dụng môi trường ảo (virtual environment).

```bash
# Clone repository
git clone <repo-url>
cd TNKV-DB

# Tạo và kích hoạt môi trường ảo (Virtual Environment)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Khởi chạy Backend (FastAPI Server)
Mở terminal thứ nhất và chạy lệnh sau để khởi động API Server tại cổng `8000`:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- Truy cập tài liệu API tự động (Swagger UI): `http://localhost:8000/docs`

### 3. Khởi chạy Frontend (Web UI)
Mở terminal thứ hai (nhớ kích hoạt lại `venv`) và chạy lệnh sau để bật giao diện Streamlit:
```bash
streamlit run demo_ui.py
```
- Giao diện người dùng sẽ tự động mở tại `http://localhost:8501`. Tại đây bạn có thể nạp dữ liệu thủ công, upload file JSON, và trải nghiệm tìm kiếm thông minh trực quan.

---

## Danh sách API Endpoint

### 1. Ingestion API (Nạp dữ liệu)
- **`POST /ingestion/bulk`**
  - **Mô tả:** Nạp một hoặc nhiều tài liệu vào Inverted Index.
  - **Body (JSON):**
    ```json
    [
      {
        "doc_id": "D01",
        "content": "Nội dung văn bản cần tìm kiếm...",
        "metadata": {}
      }
    ]
    ```

### 2. Search API (Tìm kiếm Cơ bản)
- **`GET /search/collections/{name}`**
  - **Mô tả:** Tìm kiếm văn bản theo thuật toán cơ bản.
  - **Query Parameters:**
    - `q` (string): Câu truy vấn.
    - `top_k` (int, default: 10): Số kết quả trả về.
    - `algorithm` (string, default: "manual"): Lựa chọn `manual` (TF-IDF), `bm25` hoặc `bm25+`.

- **`GET /search/collections/{name}/documents/{doc_id}`**
  - **Mô tả:** Lấy nội dung gốc của một văn bản dựa vào `doc_id`.

### 3. Smart API (Tìm kiếm Nâng cao)
- **`POST /smart/search`**
  - **Mô tả:** Tìm kiếm tích hợp các tính năng thông minh như Spell Checker (Sửa lỗi chính tả) và Rocchio (Mở rộng truy vấn). Kết quả trả về kèm `snippet` đã được trích xuất và highlight từ khóa (`<mark>`).
  - **Body (JSON):**
    ```json
    {
      "query": "điện thoại xioami",
      "top_k": 10,
      "ranker": "tfidf",
      "use_spell_check": true,
      "use_rocchio": true,
      "positive_feedback_ids": ["D07"] 
    }
    ```
  - **Response (JSON):** Trả về `total_found`, thời gian `execution_time_ms`, câu query đã được sửa (`corrected_query`) và danh sách kết quả chứa `doc_id`, `score`, và `snippet`.
