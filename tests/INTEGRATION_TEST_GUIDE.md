# Integration Test Hướng Dẫn

Tệp này kiểm tra toàn bộ pipeline TNKV-DB: nạp data → tìm kiếm cơ bản → sửa chính tả → mở rộng truy vấn.

## Chuẩn bị

1. **Cài đặt dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Đảm bảo corpus.json tồn tại:**
   ```
   tests/corpus.json
   ```

## Chạy Test

### Bước 1: Khởi động FastAPI server

```bash
cd c:\Users\nhat\Desktop\TNKV-DB
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Bước 2: Chạy integration test (terminal khác)

```bash
cd c:\Users\nhat\Desktop\TNKV-DB
python tests/integration_test.py
```

## Kịch Bản Test

### Bước 1: Nạp Dữ Liệu
- POST `/ingestion/bulk` với 8 tài liệu từ corpus.json
- Kiểm tra: Tất cả 8 tài liệu được nạp thành công

### Bước 2: Tìm Kiếm Cơ Bản
- GET `/search/collections/default?q=điện thoại&algorithm=manual`
- Kiểm tra: Tìm thấy các tài liệu liên quan đến điện thoại

### Bước 3: Sửa Lỗi Chính Tả
- POST `/smart/search` với query "diện thoai" (có lỗi) + `use_spell_check=true`
- Kiểm tra: Hệ thống sửa lỗi và trả về kết quả cho "điện thoại"

### Bước 4: Rocchio Feedback (Mở Rộng Truy Vấn)
- POST `/smart/search` với query "tai nghe" + `use_rocchio=true` + phản hồi tích cực (D03, D04)
- Kiểm tra: Kết quả được mở rộng dựa trên feedback

### Bước 5: Kiểm Tra Độ Ổn Định Bộ Nhớ
- Chạy 5 truy vấn liên tiếp
- Kiểm tra: app.state không bị crash, thời gian đáp ứng ổn định

## Lỗi Thường Gặp

### "Connection refused"
- Đảm bảo FastAPI server đang chạy
- Kiểm tra port 8000 không bị dùng bởi chương trình khác

### "File not found: tests/corpus.json"
- Đảm bảo bạn đang chạy từ thư mục gốc của project
- Kiểm tra tests/corpus.json tồn tại

### "No documents found"
- Bước nạp dữ liệu có thể thất bại
- Kiểm tra API logs trên server

## Kết Quả Mong Đợi

```
✅ Tất cả 8 tài liệu được nạp thành công
✅ Tìm kiếm cơ bản trả về 5+ kết quả
✅ Tìm kiếm với sửa chính tả trả về kết quả đúng
✅ Rocchio feedback mở rộng truy vấn hiệu quả
✅ Trung bình thời gian: ~50-100ms (tùy thuộc vào máy)
✅ Bộ nhớ ổn định - không bị crash sau 5 truy vấn
```

## Giám Sát Bộ Nhớ (Tuỳ chọn)

Nếu bạn muốn giám sát bộ nhớ chi tiết hơn, chạy trong một terminal khác:

```bash
# Windows - sử dụng Task Manager hoặc:
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Select-Object Name, WorkingSet

# Linux/Mac
top -p $(pgrep -f "uvicorn")
```

## Tài Liệu Liên Quan

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [SmartSearch API](../routers/smart_api.py)
- [Search API](../routers/search_api.py)
- [Ingestion API](../routers/ingestion_api.py)
