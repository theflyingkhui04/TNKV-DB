# TNKV DB
> **The Lightweight Sparse Vector Database for IR Purists**

Hệ thống giả lập Cơ sở dữ liệu Vector thưa (Sparse Vector Database) được xây dựng bằng Python, sử dụng Inverted Index và mô hình không gian vector (Vector Space Model - TF-IDF) thay vì Deep Learning/Dense Vectors.

Dự án được thiết kế theo kiến trúc phân tán dạng Vertical Slices, tối ưu cho bài tập lớn môn "Truy xuất thông tin" (Information Retrieval).

## Kiến trúc hệ thống
Hệ thống bao gồm 3 module chính tương ứng với 3 tính năng giao tiếp qua FastAPI và chia sẻ State trên RAM:

1. **Ingestion & Storage (`core/ingestion/`)**: 
   - Đảm nhiệm tiền xử lý văn bản (Tokenize, Stopwords).
   - Xây dựng Inverted Index.
   - Nén danh sách Postings bằng thuật toán Variable Byte và lưu trữ xuống đĩa cứng (`.pkl`).

2. **Search & Ranking (`core/search/`)**: 
   - Vector hóa truy vấn (TF-IDF).
   - Tính toán độ tương đồng Cosine (Cosine Similarity).
   - Truy xuất Top-K văn bản phù hợp nhất sử dụng Min-Heap.

3. **Smart Experience (`core/smart/`)**: 
   - Bắt lỗi chính tả và gợi ý sửa lỗi truy vấn bằng Edit Distance.
   - Mở rộng truy vấn (Query Expansion) và phản hồi mức độ liên quan (Relevance Feedback) sử dụng thuật toán Rocchio.

## Yêu cầu môi trường
- Python 3.9+
- Khuyến nghị sử dụng môi trường ảo (virtual environment).

## Hướng dẫn cài đặt và chạy (How to run)

1. **Clone repository và di chuyển vào thư mục dự án**:
   ```bash
   git clone <repo-url>
   cd TNKV-DB
   ```

2. **Tạo và kích hoạt môi trường ảo (Virtual Environment)**:
   ```bash
   # Dành cho Windows
   python -m venv venv
   venv\Scripts\activate

   # Dành cho Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Cài đặt các thư viện cần thiết**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Khởi chạy FastAPI Server**:
   ```bash
   # Chạy server ở chế độ auto-reload cho development
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Xem tài liệu API**:
   - Truy cập vào: `http://localhost:8000/docs` (Swagger UI)
   - Truy cập vào: `http://localhost:8000/redoc` (ReDoc)
