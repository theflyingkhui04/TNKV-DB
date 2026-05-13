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
    result: bytearray = bytearray()
    for num in numbers:
        if num < 0:
            raise ValueError(f"Không hỗ trợ số âm: {num}")

        # Phân tách num thành 7-bit chunks
        bytes_list: List[int] = []

        # Lấy 7 bits từ dưới lên trên
        while num > 0:
            bytes_list.append(num & 0x7F)
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

# Nén postings list
def compress_postings(doc_ids: List[int]) -> Tuple[bytes, int]:
    gaps = gap_encode(doc_ids)
    compressed = vb_encode(gaps)
    return compressed, len(doc_ids)

# Giải nén posting list
def decompress_postings(compressed_bytes: bytes, expected_count: int) -> List[int]:
    gaps = vb_decode(compressed_bytes)
    doc_ids = gap_decode(gaps)

    if len(doc_ids) != expected_count:
        raise ValueError(
            f"Không đúng số lượng phần tử: nén {len(doc_ids)} items, "
            f"mong đợi {expected_count}"
        )
    return doc_ids