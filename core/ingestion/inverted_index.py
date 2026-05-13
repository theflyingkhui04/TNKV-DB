from __future__ import annotations

import json
import os
import struct
import threading
from typing import Dict, Iterator, List, Optional, Tuple

from core.contracts import (
    BaseInvertedIndex,
    DictionaryEntry,
    Document,
    Posting,
    PostingsList,
)
from core.ingestion.compression import compress_postings, decompress_postings, compression_ratio

# 1. Node danh sách liên kết để lưu trữ postings list
class PostingsListNode:
    __slots__ = ("posting", "next")

    def __init__(self, posting: Posting) -> None:
        self.posting: Posting = posting
        self.next: Optional[PostingsListNode] = None

    def __repr__(self) -> str:  # pragma: no cover
        return f"Node({self.posting.doc_id}, freq={self.posting.frequency})"

# 2. Bảng Hash Map chỉ mục ngược
class HashMapInvertedIndex(BaseInvertedIndex):
    
    # Inner helper: gói gọn metadata của một term
    class _IndexEntry:
        __slots__ = ("head", "tail", "doc_frequency", "doc_id_set")

        def __init__(self) -> None:
            self.head: Optional[PostingsListNode] = None
            self.tail: Optional[PostingsListNode] = None
            self.doc_frequency: int = 0
            # Set để kiểm tra O(1) xem doc đã có posting chưa
            self.doc_id_set: set[str] = set()

    
    # Init
    def __init__(self) -> None:
        # Hash Map chính: term → _IndexEntry
        self._index: Dict[str, HashMapInvertedIndex._IndexEntry] = {}

        # Lưu nhanh Document gốc (doc_id → Document)
        self._documents: Dict[str, Document] = {}

        # Tổng số document đã được index
        self._total_documents: int = 0

        # Lock cho thread-safe write
        self._lock = threading.RLock()

    
    # Private helpers
    def _get_or_create_entry(self, term: str) -> "_IndexEntry":
        """Lấy hoặc tạo mới _IndexEntry cho term."""
        if term not in self._index:
            self._index[term] = HashMapInvertedIndex._IndexEntry()
        return self._index[term]

    def _insert_sorted(
        self,
        entry: "_IndexEntry",
        doc_id: str,
        frequency: int,
        positions: List[int],
    ) -> None:
        """
        Chèn Posting vào linked list theo thứ tự doc_id tăng dần.

        - Nếu doc_id đã tồn tại: cộng dồn frequency và merge positions.
        - Nếu chưa: tạo node mới chèn đúng vị trí sorted.
        """
        # Update nếu doc đã có trong list
        if doc_id in entry.doc_id_set:
            current = entry.head
            while current is not None:
                if current.posting.doc_id == doc_id:
                    current.posting.frequency += frequency
                    current.posting.positions.extend(positions)
                    current.posting.positions.sort()
                    return
                current = current.next
            return  # không thể xảy ra nhưng guard

        # Chèn node mới (sorted insert)
        new_node = PostingsListNode(
            Posting(doc_id=doc_id, frequency=frequency, positions=sorted(positions))
        )
        entry.doc_frequency += 1
        entry.doc_id_set.add(doc_id)

        # Danh sách rỗng
        if entry.head is None:
            entry.head = new_node
            entry.tail = new_node
            return

        # Chèn trước head
        if doc_id < entry.head.posting.doc_id:
            new_node.next = entry.head
            entry.head = new_node
            return

        # Tối ưu: nếu doc_id lớn nhất → append tail O(1)
        if doc_id > entry.tail.posting.doc_id:
            entry.tail.next = new_node
            entry.tail = new_node
            return

        # Tìm vị trí chèn giữa list
        prev = entry.head
        current = entry.head.next
        while current is not None and current.posting.doc_id < doc_id:
            prev = current
            current = current.next
        prev.next = new_node
        new_node.next = current

    def _iter_postings(self, head: Optional[PostingsListNode]) -> Iterator[Posting]:
        """Duyệt linked list, yield từng Posting."""
        current = head
        while current is not None:
            yield current.posting
            current = current.next

    
    # BaseInvertedIndex — PUBLIC API
    def add_document(self, doc: Document) -> None:
        """
        Dùng ``doc.term_frequencies`` và ``doc.tokenized_content`` để:
        - Tính frequency của từng term trong document
        - Ghi nhận vị trí xuất hiện (positional index)

        Args:
            doc: Document đã được tokenize (tokenized_content và
                 term_frequencies phải đã được điền bởi Preprocessor/Indexer).
        """
        with self._lock:
            if doc.doc_id in self._documents:
                raise ValueError(
                    f"doc_id '{doc.doc_id}' đã tồn tại. "
                    "Dùng update_document() nếu muốn cập nhật."
                )

            # Lưu document gốc
            self._documents[doc.doc_id] = doc
            self._total_documents += 1

            # Xây dựng positional info: term → list of positions
            term_positions: Dict[str, List[int]] = {}
            for pos, term in enumerate(doc.tokenized_content):
                if term not in term_positions:
                    term_positions[term] = []
                term_positions[term].append(pos)

            # Thêm vào hash map + linked list
            for term, positions in term_positions.items():
                frequency = len(positions)
                entry = self._get_or_create_entry(term)
                self._insert_sorted(entry, doc.doc_id, frequency, positions)

    def get_postings(self, term: str) -> Optional[PostingsList]:
        """
        Tra cứu Postings List cho một term — O(1)
        """
        entry = self._index.get(term)
        if entry is None:
            return None

        postings = list(self._iter_postings(entry.head))
        return PostingsList(
            term=term,
            document_frequency=entry.doc_frequency,
            postings=postings,
        )

    def get_document_frequency(self, term: str) -> int:
        entry = self._index.get(term)
        return entry.doc_frequency if entry is not None else 0

    def get_total_documents(self) -> int:
        return self._total_documents

    def get_vocabulary(self) -> List[str]:
        return list(self._index.keys())

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self._documents.get(doc_id)

    def get_all_doc_ids(self) -> List[str]:
        return list(self._documents.keys())

    def get_term_frequency(self, term: str, doc_id: str) -> int:
        entry = self._index.get(term)
        if entry is None or doc_id not in entry.doc_id_set:
            return 0
        for posting in self._iter_postings(entry.head):
            if posting.doc_id == doc_id:
                return posting.frequency
        return 0

    def get_stats(self) -> Dict[str, int]:
        return {
            "total_documents": self._total_documents,
            "vocabulary_size": len(self._index),
        }

    def merge(self, term_a: str, term_b: str, mode: str = "AND") -> List[str]:
        entry_a = self._index.get(term_a)
        entry_b = self._index.get(term_b)

        if mode == "AND":
            if entry_a is None or entry_b is None:
                return []
            result: List[str] = []
            node_a = entry_a.head
            node_b = entry_b.head
            while node_a is not None and node_b is not None:
                id_a = node_a.posting.doc_id
                id_b = node_b.posting.doc_id
                if id_a == id_b:
                    result.append(id_a)
                    node_a = node_a.next
                    node_b = node_b.next
                elif id_a < id_b:
                    node_a = node_a.next
                else:
                    node_b = node_b.next
            return result

        elif mode == "OR":
            result = []
            node_a = entry_a.head if entry_a else None
            node_b = entry_b.head if entry_b else None
            while node_a is not None and node_b is not None:
                id_a = node_a.posting.doc_id
                id_b = node_b.posting.doc_id
                if id_a == id_b:
                    result.append(id_a)
                    node_a = node_a.next
                    node_b = node_b.next
                elif id_a < id_b:
                    result.append(id_a)
                    node_a = node_a.next
                else:
                    result.append(id_b)
                    node_b = node_b.next
            while node_a is not None:
                result.append(node_a.posting.doc_id)
                node_a = node_a.next
            while node_b is not None:
                result.append(node_b.posting.doc_id)
                node_b = node_b.next
            return result

        else:
            raise ValueError(f"mode không hợp lệ: '{mode}'. Dùng 'AND' hoặc 'OR'.")

    
    def save_to_disk(self, directory_path: str) -> None:
        import pickle
        os.makedirs(directory_path, exist_ok=True)
        
        # Chuyển đổi Linked List sang dạng list thông thường để có thể serialize bằng Pickle
        serializable_index = {}
        for term, entry in self._index.items():
            postings_list = list(self._iter_postings(entry.head))
            serializable_index[term] = {
                "doc_frequency": entry.doc_frequency,
                "postings": postings_list
            }

        file_path = os.path.join(directory_path, "index.pkl")
        with open(file_path, "wb") as f:
            pickle.dump({
                "documents": self._documents,
                "index": serializable_index,
                "total_documents": self._total_documents
            }, f)

    def load_from_disk(self, directory_path: str) -> None:
        import pickle
        with self._lock:
            # Reset RAM
            self._index.clear()
            self._documents.clear()
            self._total_documents = 0

            file_path = os.path.join(directory_path, "index.pkl")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = pickle.load(f)
                    
                    self._documents = data.get("documents", {})
                    self._total_documents = data.get("total_documents", 0)
                    
                    # Nạp lại Linked List từ mảng postings
                    serializable_index = data.get("index", {})
                    for term, term_data in serializable_index.items():
                        entry = self._get_or_create_entry(term)
                        for p in term_data["postings"]:
                            self._insert_sorted(
                                entry,
                                doc_id=p.doc_id,
                                frequency=p.frequency,
                                positions=p.positions,
                            )

    def close(self) -> None:
        pass