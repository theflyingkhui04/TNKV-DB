from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

# ==========================================
# 1. FASTAPI SCHEMAS (PYDANTIC MODELS)
# ==========================================

class UpsertRequest(BaseModel):
    """Schema cho request thêm mới văn bản vào hệ thống."""
    doc_id: str = Field(..., description="Mã định danh của văn bản")
    content: str = Field(..., description="Nội dung văn bản cần lưu trữ")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata bổ sung")


class SearchRequest(BaseModel):
    """Schema cho request tìm kiếm cơ bản."""
    query: str = Field(..., description="Chuỗi truy vấn từ người dùng")
    top_k: int = Field(10, ge=1, le=100, description="Số lượng kết quả trả về tối đa")


class SmartSearchRequest(SearchRequest):
    """Schema cho request tìm kiếm nâng cao (kế thừa SearchRequest)."""
    use_spell_check: bool = Field(False, description="Bật tính năng sửa lỗi chính tả truy vấn")
    use_rocchio: bool = Field(False, description="Bật tính năng mở rộng truy vấn (Rocchio)")


class SearchResultItem(BaseModel):
    """Schema cho một phần tử kết quả tìm kiếm."""
    doc_id: str = Field(..., description="Mã định danh của văn bản")
    score: float = Field(..., description="Điểm độ tương đồng (Cosine Similarity)")
    content: Optional[str] = Field(None, description="Trích đoạn hoặc nội dung văn bản (tuỳ chọn)")


class SearchResponse(BaseModel):
    """Schema cho response trả về của API tìm kiếm."""
    query: str = Field(..., description="Truy vấn đã được sử dụng (có thể đã qua sửa lỗi)")
    total_found: int = Field(..., description="Tổng số lượng văn bản tìm thấy có chứa các terms")
    results: List[SearchResultItem] = Field(default_factory=list, description="Danh sách Top-K kết quả")
    execution_time_ms: float = Field(..., description="Thời gian thực thi tìm kiếm (tính bằng ms)")
    corrected_query: Optional[str] = Field(None, description="Truy vấn sau khi sửa lỗi chính tả (nếu có)")


# ==========================================
# 2. DATA CLASSES (INTERNAL STRUCTURES)
# ==========================================

@dataclass
class Document:
    """Cấu trúc lưu trữ nội bộ cho một văn bản."""
    doc_id: str
    content: str
    tokenized_content: List[str] = field(default_factory=list)
    term_frequencies: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Posting:
    """Cấu trúc cho một phần tử trong Postings List."""
    doc_id: str
    frequency: int
    positions: List[int] = field(default_factory=list)


@dataclass
class PostingsList:
    """Cấu trúc đại diện cho danh sách các Posting của một term."""
    term: str
    document_frequency: int = 0
    postings: List[Posting] = field(default_factory=list)
    
    # Payload đã nén bằng Variable Byte
    encoded_payload: Optional[bytes] = None


# ==========================================
# 3. INTERFACES (ABSTRACT BASE CLASSES)
# ==========================================

class BaseInvertedIndex(ABC):
    """
    Interface bắt buộc cho Inverted Index.
    Người làm Storage implement class này, người làm Search gọi các method này.
    """

    @abstractmethod
    def add_document(self, doc: Document) -> None:
        """Thêm một văn bản vào chỉ mục."""
        pass

    @abstractmethod
    def get_postings(self, term: str) -> Optional[PostingsList]:
        """Lấy danh sách postings cho một term cụ thể."""
        pass

    @abstractmethod
    def get_document_frequency(self, term: str) -> int:
        """Trả về Document Frequency (DF) của term để tính IDF."""
        pass

    @abstractmethod
    def get_total_documents(self) -> int:
        """Trả về tổng số lượng văn bản đã index."""
        pass

    @abstractmethod
    def save_to_disk(self, directory_path: str) -> None:
        """Lưu cấu trúc index xuống đĩa cứng (serialize thành file, nén Variable Byte)."""
        pass

    @abstractmethod
    def load_from_disk(self, directory_path: str) -> None:
        """Tải cấu trúc index từ đĩa cứng lên RAM."""
        pass
