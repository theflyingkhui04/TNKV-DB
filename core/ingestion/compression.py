from typing import List, Tuple

# 1. GAP ENCODING
def gap_encode(doc_ids: List[int]) -> List[int]:
    if not doc_ids:
        return []
    gaps: List[int] = [doc_ids[0]]
    for i in range(1, len(doc_ids)):
        gap = doc_ids[i] - doc_ids[i - 1]
        gaps.append(gap)
    return gaps


def gap_decode(gaps: List[int]) -> List[int]:
    if not gaps:
        return []
    doc_ids: List[int] = [gaps[0]]
    for i in range(1, len(gaps)):
        last_doc_id = doc_ids[-1]
        gap = gaps[i]
        doc_ids.append(last_doc_id + gap)
    return doc_ids



# 2. VARIABLE BYTE ENCODING
def vb_encode(numbers: List[int]) -> bytes:
    """
    Mã hóa Variable Byte (VB).

    Mỗi số được nén thành một chuỗi byte:
    - Bit cao nhất (bit 7) là continuation bit (1 = còn byte tiếp, 0 = kết thúc)
    - Bit 6-0 (7 bits) chứa dữ liệu

    Ví dụ với số 5:
        5 = 0b101
        Nhỏ hơn 128, nên vào 1 byte:
        0b00000101 = 0x05

    Ví dụ với số 300 = 0b100101100:
        Cần 2 bytes:
        - Byte 1: 0b10000010 = 0x82 (continuation=1, data=0000010)
        - Byte 2: 0b00101100 = 0x2C (continuation=0, data=0101100)

    Args:
        numbers: Danh sách các số (thường là gaps sau gap encoding)

    Returns:
        Chuỗi byte đã nén
    """
    result: bytearray = bytearray()

    for num in numbers:
        if num < 0:
            raise ValueError(f"Không hỗ trợ số âm: {num}")

        # Phân tách num thành 7-bit chunks
        bytes_list: List[int] = []

        # Lấy 7 bits từ dưới lên trên
        while num > 0:
            bytes_list.append(num & 0x7F)  # Lấy 7 bits thấp
            num >>= 7

        # Nếu số là 0, thêm 1 byte 0x00
        if not bytes_list:
            bytes_list = [0]

        # Đảo ngược để bytes_list[0] là byte đầu tiên
        bytes_list.reverse()

        # Set continuation bit cho tất cả bytes trừ byte cuối
        for i in range(len(bytes_list) - 1):
            bytes_list[i] |= 0x80  # Set bit 7

        # Thêm vào result
        result.extend(bytes_list)

    return bytes(result)


def vb_decode(data: bytes) -> List[int]:
    """
    Giải mã Variable Byte (VB).

    Đọc byte stream và extract lại danh sách các số.

    Args:
        data: Chuỗi byte đã nén bởi vb_encode()

    Returns:
        Danh sách các số ban đầu
    """
    numbers: List[int] = []
    current_num = 0
    i = 0

    while i < len(data):
        byte = data[i]
        continuation_bit = (byte & 0x80) >> 7
        data_bits = byte & 0x7F

        # Dịch trái 7 bits để chứa dữ liệu mới
        current_num = (current_num << 7) | data_bits

        # Nếu không có continuation bit, số này kết thúc
        if continuation_bit == 0:
            numbers.append(current_num)
            current_num = 0

        i += 1

    return numbers



# 3. HELPER: Compress & Decompress PostingsList


def compress_postings(doc_ids: List[int]) -> Tuple[bytes, int]:
    """
    Nén danh sách DocID bằng Gap Encoding + Variable Byte Encoding.

    Args:
        doc_ids: Danh sách doc_id (integers) **đã sắp xếp**

    Returns:
        (compressed_bytes, original_count): bytes nén và số lượng phần tử gốc
    """
    gaps = gap_encode(doc_ids)
    compressed = vb_encode(gaps)
    return compressed, len(doc_ids)


def decompress_postings(compressed_bytes: bytes, expected_count: int) -> List[int]:
    """
    Giải nén danh sách DocID từ compressed format.

    Args:
        compressed_bytes: Bytes đã nén bởi compress_postings()
        expected_count: Số lượng phần tử gốc (dùng để verify)

    Returns:
        Danh sách doc_id gốc

    Raises:
        ValueError: Nếu số phần tử sau giải nén không khớp expected_count
    """
    gaps = vb_decode(compressed_bytes)
    doc_ids = gap_decode(gaps)

    if len(doc_ids) != expected_count:
        raise ValueError(
            f"Decompression mismatch: got {len(doc_ids)} items, "
            f"expected {expected_count}"
        )

    return doc_ids



# 4. STATISTICS


def compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Tính tỉ lệ nén.

    Args:
        original_size: Kích thước gốc (bytes)
        compressed_size: Kích thước sau nén (bytes)

    Returns:
        Tỉ lệ nén (0 = không nén, 1 = nén hoàn toàn)
    """
    if original_size == 0:
        return 0.0
    return 1.0 - (compressed_size / original_size)


if __name__ == "__main__":
    # ===== TEST GAP ENCODING =====
    print("=" * 70)
    print("TEST 1: Gap Encoding & Decoding")
    print("=" * 70)

    doc_ids = [100, 105, 115, 125, 130]
    print(f"Original: {doc_ids}")

    gaps = gap_encode(doc_ids)
    print(f"Gaps:     {gaps}")

    decoded = gap_decode(gaps)
    print(f"Decoded:  {decoded}")
    assert decoded == doc_ids, "Gap encoding/decoding mismatch!"
    print("✅ Gap encoding/decoding OK\n")

    # ===== TEST VB ENCODING =====
    print("=" * 70)
    print("TEST 2: Variable Byte Encoding & Decoding")
    print("=" * 70)

    test_numbers = [5, 100, 300, 2000, 1000000]
    print(f"Original: {test_numbers}")

    vb_encoded = vb_encode(test_numbers)
    print(f"Encoded (hex): {vb_encoded.hex()}")
    print(f"Encoded size: {len(vb_encoded)} bytes")

    vb_decoded = vb_decode(vb_encoded)
    print(f"Decoded: {vb_decoded}")
    assert vb_decoded == test_numbers, "VB encoding/decoding mismatch!"
    print("✅ Variable Byte encoding/decoding OK\n")

    # ===== TEST FULL COMPRESSION =====
    print("=" * 70)
    print("TEST 3: Full Compression Pipeline")
    print("=" * 70)

    doc_ids_large = list(range(1, 1001, 7))  # [1, 8, 15, ..., 994]
    print(f"DocID list size: {len(doc_ids_large)}")

    # Original size (4 bytes per int32)
    original_size = len(doc_ids_large) * 4
    print(f"Original size: {original_size} bytes")

    # Compress
    compressed, count = compress_postings(doc_ids_large)
    print(f"Compressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {compression_ratio(original_size, len(compressed)):.1%}")

    # Decompress
    decompressed = decompress_postings(compressed, count)
    assert decompressed == doc_ids_large, "Full compression pipeline mismatch!"
    print("✅ Full compression pipeline OK\n")

    print("=" * 70)
    print("✨ All tests passed!")
    print("=" * 70)
