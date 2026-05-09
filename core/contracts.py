from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import datetime


# ===========================================================================
# 0. COLLECTION  —  Không gian lưu trữ độc lập
# ===========================================================================

class CollectionStatus(str, Enum):
    """Trạng thái vòng đời của một Collection."""
    ACTIVE   = "active"    # Đang hoạt động bình thường
    BUILDING = "building"  # Đang được index / re-index
    READONLY = "readonly"  # Chỉ đọc (đang backup / migrate)
    DELETED  = "deleted"   # Đã xoá mềm, chờ dọn dẹp


@dataclass
class CollectionConfig:
    """
    Cấu hình khởi tạo cho một Collection.

    Tất cả tham số đều có giá trị mặc định hợp lý — người dùng chỉ cần
    truyền ``name`` là đủ để tạo một collection hoạt động được.
    """
    # Thuật toán xếp hạng mặc định cho Collection này
    default_ranker: str = "tfidf"          # "tfidf" | "bm25" | "bm25+"

    # BM25 hyperparameters (bỏ qua nếu ranker là tfidf)
    bm25_k1: float = 1.5
    bm25_b:  float = 0.75

    # Giới hạn kích thước
    max_documents: Optional[int] = None    # None = không giới hạn

    # Lưu trữ
    persist_on_disk: bool = True           # False = in-memory only
    index_directory: Optional[str] = None  # None = tự sinh từ collection name

    # Pipeline tiền xử lý
    use_spell_check: bool = False
    use_stopword_filter: bool = True
    language: str = "vi"                   # "vi" | "en" | "mixed"


@dataclass
class CollectionStats:
    """Thống kê runtime của một Collection (chỉ đọc, được cập nhật tự động)."""
    total_documents: int = 0
    total_terms: int = 0                   # Kích thước từ điển (vocabulary size)
    avg_document_length: float = 0.0       # Trung bình số token/document
    index_size_bytes: int = 0              # Dung lượng index trên đĩa
    last_updated: Optional[datetime.datetime] = None


@dataclass
class Collection:
    """
    Không gian lưu trữ độc lập — đơn vị quản lý cấp cao nhất của TNKV-DB.

    Mỗi Collection bao gồm:
      - Danh sách Document riêng biệt
      - Inverted Index riêng biệt (tách biệt hoàn toàn với các Collection khác)
      - Cấu hình và thống kê của riêng nó

    Ví dụ sử dụng:
        col = Collection(
            name="legal_docs",
            description="Văn bản pháp luật Việt Nam",
            config=CollectionConfig(default_ranker="bm25", language="vi"),
        )
    """
    name: str
    description: str = ""
    config: CollectionConfig = field(default_factory=CollectionConfig)
    stats: CollectionStats = field(default_factory=CollectionStats)
    status: CollectionStatus = CollectionStatus.ACTIVE
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pydantic schemas dành cho Collection API endpoints
# ---------------------------------------------------------------------------

class CreateCollectionRequest(BaseModel):
    """Schema cho request tạo Collection mới."""
    name: str = Field(..., min_length=1, max_length=128,
                      pattern=r"^[a-zA-Z0-9_\-]+$",
                      description="Tên định danh duy nhất (chỉ chữ/số/gạch)")
    description: str = Field("", description="Mô tả ngắn về Collection")
    default_ranker: str = Field("tfidf", description="Thuật toán xếp hạng mặc định")
    persist_on_disk: bool = Field(True, description="Lưu index xuống đĩa hay không")
    language: str = Field("vi", description="Ngôn ngữ chủ đạo (vi/en/mixed)")
    max_documents: Optional[int] = Field(None, ge=1,
                                         description="Giới hạn số document tối đa")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict,
                                               description="Metadata tuỳ chọn")


class CollectionInfoResponse(BaseModel):
    """Schema cho response thông tin một Collection."""
    name: str
    description: str
    status: str
    default_ranker: str
    language: str
    total_documents: int
    total_terms: int
    avg_document_length: float
    index_size_bytes: int
    last_updated: Optional[str] = None
    created_at: str


class ListCollectionsResponse(BaseModel):
    """Schema cho response danh sách Collections."""
    total: int = Field(..., description="Tổng số Collection hiện có")
    collections: List[CollectionInfoResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Interface bắt buộc cho Collection Manager
# ---------------------------------------------------------------------------

class BaseCollectionManager(ABC):
    """
    Interface quản lý vòng đời Collection.
    Storage layer implement class này; API layer gọi các method này.
    """

    @abstractmethod
    def create_collection(self, request: CreateCollectionRequest) -> Collection:
        """Tạo và đăng ký một Collection mới."""
        pass

    @abstractmethod
    def get_collection(self, name: str) -> Optional[Collection]:
        """Lấy Collection theo tên. Trả về None nếu không tồn tại."""
        pass

    @abstractmethod
    def list_collections(self) -> List[Collection]:
        """Liệt kê tất cả Collection đang ACTIVE."""
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """Xoá mềm một Collection. Trả về True nếu thành công."""
        pass

    @abstractmethod
    def update_stats(self, name: str, stats: CollectionStats) -> None:
        """Cập nhật thống kê runtime sau mỗi lần upsert / re-index."""
        pass

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        """Kiểm tra nhanh xem Collection có tồn tại không."""
        pass


# ===========================================================================
# 1. FASTAPI SCHEMAS (PYDANTIC MODELS)
# ===========================================================================

class UpsertRequest(BaseModel):
    """Schema cho request thêm mới văn bản vào hệ thống."""
    doc_id: str = Field(..., description="Mã định danh của văn bản")
    content: str = Field(..., description="Nội dung văn bản cần lưu trữ")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata bổ sung")


class SearchRequest(BaseModel):
    """Schema cho request tìm kiếm cơ bản."""
    query: str = Field(..., description="Chuỗi truy vấn từ người dùng")
    top_k: int = Field(10, ge=1, le=100, description="Số lượng kết quả trả về tối đa")
    ranker: str = Field("tfidf", description="Thuật toán xếp hạng (tfidf, bm25, bm25+)")


class SmartSearchRequest(SearchRequest):
    """Schema cho request tìm kiếm nâng cao (kế thừa SearchRequest)."""
    use_spell_check: bool = Field(False, description="Bật tính năng sửa lỗi chính tả truy vấn")
    use_rocchio: bool = Field(False, description="Bật tính năng mở rộng truy vấn (Rocchio)")
    positive_feedback_ids: List[str] = Field(default_factory=list, description="Danh sách ID tài liệu phản hồi tích cực")


class SearchResultItem(BaseModel):
    """Schema cho một phần tử kết quả tìm kiếm."""
    doc_id: str = Field(..., description="Mã định danh của văn bản")
    score: float = Field(..., description="Điểm độ tương đồng (Cosine Similarity)")
    content: Optional[str] = Field(None, description="Nội dung văn bản (tuỳ chọn)")
    snippet: Optional[str] = Field(None, description="Đoạn trích chứa từ khóa được highlight")


class SearchResponse(BaseModel):
    """Schema cho response trả về của API tìm kiếm."""
    query: str = Field(..., description="Truy vấn đã được sử dụng (có thể đã qua sửa lỗi)")
    algorithm: str = Field("tf-idf", description="Thuật toán xếp hạng đang dùng")
    total_found: int = Field(..., description="Tổng số lượng văn bản tìm thấy có chứa các terms")
    results: List[SearchResultItem] = Field(default_factory=list, description="Danh sách Top-K kết quả")
    execution_time_ms: float = Field(..., description="Thời gian thực thi tìm kiếm (tính bằng ms)")
    corrected_query: Optional[str] = Field(None, description="Truy vấn sau khi sửa lỗi chính tả (nếu có)")


# ===========================================================================
# 2. DATA CLASSES (INTERNAL STRUCTURES)
# ===========================================================================

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


@dataclass
class DictionaryEntry:
    """Cấu trúc ánh xạ từ vựng trên RAM tới file Postings trên ổ cứng (Task Disk-based Indexing)."""
    term: str
    document_frequency: int
    offset: int
    length: int


# ===========================================================================
# 3. INTERFACES (ABSTRACT BASE CLASSES)
# ===========================================================================

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
    def get_vocabulary(self) -> List[str]:
        """Trả về danh sách toàn bộ từ vựng (dùng cho Spell Checker/Trigram)."""
        pass

    @abstractmethod
    def save_to_disk(self, directory_path: str) -> None:
        """Lưu cấu trúc index xuống đĩa cứng (thành Block offset cho Disk-based)."""
        pass

    @abstractmethod
    def load_from_disk(self, directory_path: str) -> None:
        """Tải cấu trúc index từ đĩa cứng (tải Dictionary lên RAM, mở file Postings)."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Đóng các file pointer khi kết thúc (dùng cho Disk-based Indexing)."""
        pass