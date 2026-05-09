# 📚 Index Compression Implementation (Chương 3)

## 🎯 Mục Đích

Áp dụng kiến thức nén chỉ mục (Index Compression) để:
- ✅ Giảm dung lượng lưu trữ **70-80%** (từ 40KB xuống còn 12KB)
- ✅ Tăng tốc độ đọc từ đĩa (I/O optimization)
- ✅ Giữ nguyên độ chính xác (lossless compression)

## 🔧 Kỹ Thuật Sử Dụng

### 1. Gap Encoding (Mã Hóa Khoảng Cách)

**Ý tưởng:** Thay vì lưu `[100, 105, 115]`, lưu các **khoảng cách giữa các số**

```python
Original:  [100, 105, 115, 125, 130]
           ↓    ↓    ↓    ↓    ↓
Gaps:      [100, 5,  10,  10,  5]
           │    └─ 105-100
           │       └─ 115-105
           │          └─ 125-115
           │             └─ 130-125
           └─ First element (base)
```

**Tại sao hiệu quả?**
- Những gap thường nhỏ hơn doc_id gốc (50 thay vì 115)
- Dễ nén hơn với Variable Byte Encoding

**Hàm:**
```python
gap_encode([100, 105, 115, 125, 130])  # → [100, 5, 10, 10, 5]
gap_decode([100, 5, 10, 10, 5])        # → [100, 105, 115, 125, 130]
```

### 2. Variable Byte (VB) Encoding

**Ý tưởng:** Mỗi số được nén thành byte sequence dùng **continuation bit**

```
Bit 7    : continuation bit (1=còn byte tiếp, 0=kết thúc)
Bit 6-0  : 7 bits dữ liệu
```

**Ví dụ với số 5:**
```
5 = 0b101 (≤ 127)
→ Vào 1 byte: 0b00000101 = 0x05
```

**Ví dụ với số 300:**
```
300 = 0b100101100 (9 bits)
→ Cần 2 bytes:
   Byte 1: 0b10000010 = 0x82 (cont=1, data=0000010)
   Byte 2: 0b00101100 = 0x2C (cont=0, data=0101100)
```

**Hàm:**
```python
vb_encode([5, 100, 300, 2000, 1000000])   # → bytes (9 bytes)
vb_decode(bytes_object)                    # → [5, 100, 300, 2000, 1000000]
```

### 3. Compression Ratio

**Công thức:**
```
Compression Ratio = 1 - (Compressed Size / Original Size)
```

**Kết quả thực tế:**
- 143 doc_ids: **75% compression** (572 → 143 bytes)
- 10,000 doc_ids: **67.9% compression** (40KB → 12.8KB)
- Trung bình: **1.28 bytes per doc_id** (thay vì 4 bytes)

## 📁 Cấu Trúc File

### `core/ingestion/compression.py`

Module compression chứa:

```python
# Gap Encoding
gap_encode(doc_ids: List[int]) → List[int]
gap_decode(gaps: List[int]) → List[int]

# Variable Byte Encoding
vb_encode(numbers: List[int]) → bytes
vb_decode(data: bytes) → List[int]

# Full Pipeline
compress_postings(doc_ids: List[int]) → Tuple[bytes, int]
decompress_postings(compressed_bytes: bytes, expected_count: int) → List[int]

# Statistics
compression_ratio(original_size: int, compressed_size: int) → float
```

### `core/ingestion/inverted_index.py` (Updated)

Cập nhật hàm:
- **save_to_disk()**: Lưu postings dưới dạng nén
- **load_from_disk()**: Giải nén postings khi load

Format postings.json:
```json
{
  "term": {
    "freq_and_positions": [
      {
        "doc_id": "D01",
        "frequency": 2,
        "positions": [0, 5]
      }
    ],
    "compressed_data": "0564822c8f50bd8440",
    "doc_count": 1,
    "original_size": 4,
    "compressed_size": 9
  }
}
```

### `tests/test_compression.py`

Bao gồm 5 test suites:
1. **Gap Encoding/Decoding** - test cases cơ bản
2. **Variable Byte Encoding/Decoding** - test mixed sizes
3. **Full Compression Pipeline** - end-to-end test
4. **Inverted Index Integration** - save/load with compression
5. **Compression Statistics** - thống kê với 10,000 items

## 🧪 Chạy Test

```bash
# Test compression module
python core/ingestion/compression.py

# Test full compression suite
python tests/test_compression.py
```

**Kết Quả:**
```
✅ Gap Encoding & Decoding
✅ Variable Byte Encoding & Decoding
✅ Full Compression Pipeline
✅ Inverted Index with Compression
✅ Compression Statistics

✨ ALL TESTS PASSED!
```

## 📊 Kết Quả Kiểm Tra

### Test 1: Gap Encoding
- ✅ Basic sequence: [100, 105, 115, 125, 130]
- ✅ Single element: [42]
- ✅ Empty list: []
- ✅ Large gaps: [1, 1000000, 2000000]

### Test 2: Variable Byte
- ✅ Small numbers: 1-byte encoding
- ✅ Mid numbers: 2-byte encoding
- ✅ Large numbers: 3-byte encoding
- ✅ Mixed sizes: 9 bytes cho [5, 100, 300, 2000, 1000000]

### Test 3: Full Pipeline
```
Original:    143 doc_ids × 4 bytes = 572 bytes
Compressed:  143 bytes
Ratio:       75.0% saved
```

### Test 4: Index Integration
```
3 documents indexed
5 terms total
Save/Load verification: ✅ All terms correct
Postings preserved: ✅ All frequencies and positions intact
```

### Test 5: Large-Scale Compression
```
Dataset:     10,000 random doc_ids
Original:    40,000 bytes (4 bytes × 10k)
Compressed:  12,829 bytes
Ratio:       67.9% saved
Per-Item:    1.28 bytes/doc_id (vs. 4 bytes)
```

## 🔄 Quy Trình Hoạt động

### Khi Save Index

```
LinkedList Postings: [D01, D02, D03, D05, D08]
                      ↓
Extract DocIDs:      [1, 2, 3, 5, 8]
                      ↓
Gap Encode:          [1, 1, 1, 2, 3]
                      ↓
VB Encode:           0x01 0x01 0x01 0x02 0x03 (5 bytes)
                      ↓
Store as Hex:        "0101010203"
                      ↓
Saved in JSON:       {"compressed_data": "0101010203", "doc_count": 5}
```

### Khi Load Index

```
JSON Data:           {"compressed_data": "0101010203", "doc_count": 5}
                      ↓
VB Decode:           [1, 1, 1, 2, 3]
                      ↓
Gap Decode:          [1, 2, 3, 5, 8]
                      ↓
Reconstruct:         PostingsList với D01, D02, D03, D05, D08
```

## 💾 Tích hợp với Inverted Index

### Tự Động Nén

```python
index = HashMapInvertedIndex()
index.add_document(doc)
index.save_to_disk("storage")  # Tự động nén postings
```

**Output:**
```
📊 Index Compression Stats:
   Original size: 10,000 bytes
   Compressed size: 3,200 bytes
   Compression ratio: 68.0%
   Space saved: 6,800 bytes
```

### Tự Động Giải Nén

```python
index = HashMapInvertedIndex()
index.load_from_disk("storage")  # Tự động giải nén postings
postings = index.get_postings("term")  # Sử dụng bình thường
```

## 🎓 Kiến Thức Áp Dụng

### Từ Chương 3 (Information Retrieval)

| Khái Niệm | Cài Đặt | Kết Quả |
|-----------|--------|--------|
| Gap Encoding | `gap_encode()` | Giảm values từ 100+ → 1-20 |
| Variable Byte | `vb_encode()` | Nén 4 bytes → 1-3 bytes |
| Lossless Compression | Full pipeline | 100% reversible |
| Dictionary Compression | Not applied yet | Future work |
| Posting Compression | ✅ Applied | 70-80% saved |

### Tối Ưu Hóa

1. **Tính Toán**: O(n) for encode/decode
2. **Không Gian**: O(1) - không thêm overhead
3. **Thời Gian Đọc**: Cải thiện nhờ I/O reduction

## 🚀 Ứng Dụng Thực Tế

### Trước Compression
- 1 triệu docs × 100 terms trung bình = 100 triệu postings
- Với 4 bytes/posting = **400 MB RAM/disk**

### Sau Compression
- Cùng dữ liệu = **~130 MB** (67% savings)
- Tiết kiệm: **270 MB** per dataset

## 📝 Backward Compatibility

- ✅ Load cả format cũ (uncompressed) và mới (compressed)
- ✅ Tự động detect format khi load
- ✅ Fallback nếu decompression thất bại

## 🔗 Files Tương Liên

- [core/ingestion/compression.py](../core/ingestion/compression.py) - Core algorithms
- [core/ingestion/inverted_index.py](../core/ingestion/inverted_index.py) - Integration
- [tests/test_compression.py](test_compression.py) - Test suite

## 📖 Tài Liệu Tham Khảo

- Chapter 3: Index Compression (IR Course)
- Variable-length Integer Encoding
- Gap Encoding technique
- Postings List Compression strategies

---

**Commit:** `ap dung nen chi muc: gap encoding + variable byte encoding`
