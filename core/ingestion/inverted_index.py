"""
core/ingestion/inverted_index.py

Triển khai Inverted Index dùng Hash Map (dict Python) kết hợp
Linked-List Node cho Postings List.

Cấu trúc bộ nhớ:
    _index: dict[str, PostingsListNode]
                │
                └─ term → PostingsListNode (head of linked list)
                              ├─ posting: Posting(doc_id, freq, positions)
                              └─ next: PostingsListNode | None

Implement đầy đủ interface BaseInvertedIndex từ contracts.py.
"""

from __future__ import annotations

import json
import os
import struct
import threading
from typing import Dict, Iterator, List, Optional, Tuple

from contracts import (
    BaseInvertedIndex,
    DictionaryEntry,
    Document,
    Posting,
    PostingsList,
)


# ===========================================================================
# 1. LINKED-LIST NODE  —  đơn vị lưu trữ từng Posting
# ===========================================================================

class PostingsListNode:
    """
    Node của danh sách liên kết đơn cho Postings List.

    Mỗi node giữ một Posting (doc_id, tần suất, vị trí xuất hiện)
    và con trỏ tới node kế tiếp.

    Danh sách được duy trì **đã sắp xếp tăng dần theo doc_id** để
    hỗ trợ phép AND / OR merge hiệu quả (merge-based query processing).
    """

    __slots__ = ("posting", "next")

    def __init__(self, posting: Posting) -> None:
        self.posting: Posting = posting
        self.next: Optional[PostingsListNode] = None

    def __repr__(self) -> str:  # pragma: no cover
        return f"Node({self.posting.doc_id}, freq={self.posting.frequency})"


# ===========================================================================
# 2. HASHMAP INVERTED INDEX
# ===========================================================================

class HashMapInvertedIndex(BaseInvertedIndex):
    """
    Inverted Index dùng Hash Map (dict) + Linked-List Postings.

    Hash Map
    ─────────────────────────────────────────────────────────────
    key   : term (str)
    value : _IndexEntry — gói (head node, df, doc_id set)

    Linked List (mỗi term có một list riêng)
    ─────────────────────────────────────────────────────────────
    head → Node(doc_id_A) → Node(doc_id_B) → ... → None
    Nodes được giữ sorted theo doc_id (string sort).

    Tại sao Linked List?
    - Insert O(n) nhưng đơn giản, phù hợp giai đoạn xây dựng index
    - Merge (AND/OR) hai postings list chạy O(m+n) nhờ sorted order
    - Dễ dàng nâng cấp lên Skip Pointers sau này

    Thread safety: dùng RLock cho mọi write operation.
    """

    # -----------------------------------------------------------------------
    # Inner helper: gói gọn metadata của một term
    # -----------------------------------------------------------------------
    class _IndexEntry:
        __slots__ = ("head", "tail", "doc_frequency", "doc_id_set")

        def __init__(self) -> None:
            self.head: Optional[PostingsListNode] = None
            self.tail: Optional[PostingsListNode] = None
            self.doc_frequency: int = 0
            # Set để kiểm tra O(1) xem doc đã có posting chưa
            self.doc_id_set: set[str] = set()

    # -----------------------------------------------------------------------
    # Init
    # -----------------------------------------------------------------------

    def __init__(self) -> None:
        # Hash Map chính: term → _IndexEntry
        self._index: Dict[str, HashMapInvertedIndex._IndexEntry] = {}

        # Lưu nhanh Document gốc (doc_id → Document)
        self._documents: Dict[str, Document] = {}

        # Tổng số document đã được index
        self._total_documents: int = 0

        # Lock cho thread-safe write
        self._lock = threading.RLock()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

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
        # --- Update nếu doc đã có trong list ---
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

        # --- Chèn node mới (sorted insert) ---
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
        if doc_id > entry.tail.posting.doc_id:  # type: ignore[union-attr]
            entry.tail.next = new_node           # type: ignore[union-attr]
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

    # -----------------------------------------------------------------------
    # BaseInvertedIndex — PUBLIC API
    # -----------------------------------------------------------------------

    def add_document(self, doc: Document) -> None:
        """
        Thêm Document vào index.

        Dùng ``doc.term_frequencies`` và ``doc.tokenized_content`` để:
        - Tính frequency của từng term trong document
        - Ghi nhận vị trí xuất hiện (positional index)

        Args:
            doc: Document đã được tokenize (tokenized_content và
                 term_frequencies phải đã được điền bởi Preprocessor/Indexer).

        Raises:
            ValueError: Nếu doc_id đã tồn tại trong index.
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
        Tra cứu Postings List cho một term — O(1) hash lookup.

        Args:
            term: Term cần tìm (đã lowercase/normalized).

        Returns:
            PostingsList đầy đủ, hoặc None nếu term không tồn tại.
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
        """
        Trả về DF của term — O(1).

        Args:
            term: Term cần tra.

        Returns:
            Số document chứa term. 0 nếu term không tồn tại.
        """
        entry = self._index.get(term)
        return entry.doc_frequency if entry is not None else 0

    def get_total_documents(self) -> int:
        """Trả về tổng số document đã index — O(1)."""
        return self._total_documents

    def get_vocabulary(self) -> List[str]:
        """
        Trả về toàn bộ vocabulary (danh sách term đã index).

        Dùng cho Spell Checker / Trigram / autocomplete.

        Returns:
            List các term, không đảm bảo thứ tự.
        """
        return list(self._index.keys())

    # -----------------------------------------------------------------------
    # Extra public methods (ngoài interface — tiện ích bổ sung)
    # -----------------------------------------------------------------------

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Lấy Document gốc theo doc_id — O(1)."""
        return self._documents.get(doc_id)

    def get_all_doc_ids(self) -> List[str]:
        """Trả về danh sách tất cả doc_id đã index."""
        return list(self._documents.keys())

    def get_term_frequency(self, term: str, doc_id: str) -> int:
        """
        Trả về TF(term, doc) — O(df) scan linked list.

        Args:
            term: Term cần tra.
            doc_id: Document cần tra.

        Returns:
            Tần suất xuất hiện. 0 nếu không tồn tại.
        """
        entry = self._index.get(term)
        if entry is None or doc_id not in entry.doc_id_set:
            return 0
        for posting in self._iter_postings(entry.head):
            if posting.doc_id == doc_id:
                return posting.frequency
        return 0

    def get_stats(self) -> Dict[str, int]:
        """Trả về thống kê nhanh của index."""
        return {
            "total_documents": self._total_documents,
            "vocabulary_size": len(self._index),
        }

    def merge(self, term_a: str, term_b: str, mode: str = "AND") -> List[str]:
        """
        Merge hai postings list — AND hoặc OR.

        Chạy O(m + n) nhờ sorted linked list.

        Args:
            term_a: Term thứ nhất.
            term_b: Term thứ hai.
            mode: "AND" (giao) hoặc "OR" (hợp).

        Returns:
            Danh sách doc_id thoả mãn điều kiện, đã sắp xếp.
        """
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

    # -----------------------------------------------------------------------
    # Persistence — save / load
    # -----------------------------------------------------------------------

    def save_to_disk(self, directory_path: str) -> None:
        """
        Lưu toàn bộ index xuống đĩa dưới dạng JSON.

        Tạo hai file:
          - ``dictionary.json``  : vocabulary + document_frequency
          - ``postings.json``    : toàn bộ postings (doc_id, freq, positions)
          - ``documents.json``   : nội dung document gốc + metadata

        Args:
            directory_path: Đường dẫn thư mục lưu trữ (sẽ được tạo nếu chưa có).
        """
        os.makedirs(directory_path, exist_ok=True)

        # --- dictionary.json ---
        dictionary: Dict[str, int] = {
            term: entry.doc_frequency
            for term, entry in self._index.items()
        }
        with open(os.path.join(directory_path, "dictionary.json"), "w", encoding="utf-8") as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)

        # --- postings.json ---
        postings_data: Dict[str, List[Dict]] = {}
        for term, entry in self._index.items():
            postings_data[term] = [
                {
                    "doc_id": p.doc_id,
                    "frequency": p.frequency,
                    "positions": p.positions,
                }
                for p in self._iter_postings(entry.head)
            ]
        with open(os.path.join(directory_path, "postings.json"), "w", encoding="utf-8") as f:
            json.dump(postings_data, f, ensure_ascii=False, indent=2)

        # --- documents.json ---
        docs_data: Dict[str, Dict] = {
            doc_id: {
                "doc_id": doc.doc_id,
                "content": doc.content,
                "tokenized_content": doc.tokenized_content,
                "term_frequencies": doc.term_frequencies,
                "metadata": doc.metadata,
            }
            for doc_id, doc in self._documents.items()
        }
        with open(os.path.join(directory_path, "documents.json"), "w", encoding="utf-8") as f:
            json.dump(docs_data, f, ensure_ascii=False, indent=2)

    def load_from_disk(self, directory_path: str) -> None:
        """
        Tải index từ đĩa. Xoá toàn bộ dữ liệu cũ trước khi load.

        Args:
            directory_path: Thư mục chứa các file đã lưu bởi save_to_disk().

        Raises:
            FileNotFoundError: Nếu thư mục hoặc file cần thiết không tồn tại.
        """
        with self._lock:
            # Reset
            self._index.clear()
            self._documents.clear()
            self._total_documents = 0

            # --- documents.json ---
            docs_path = os.path.join(directory_path, "documents.json")
            with open(docs_path, "r", encoding="utf-8") as f:
                docs_data = json.load(f)
            for doc_id, d in docs_data.items():
                self._documents[doc_id] = Document(
                    doc_id=d["doc_id"],
                    content=d["content"],
                    tokenized_content=d["tokenized_content"],
                    term_frequencies=d["term_frequencies"],
                    metadata=d.get("metadata", {}),
                )
            self._total_documents = len(self._documents)

            # --- postings.json ---
            postings_path = os.path.join(directory_path, "postings.json")
            with open(postings_path, "r", encoding="utf-8") as f:
                postings_data = json.load(f)

            for term, postings_list in postings_data.items():
                entry = self._get_or_create_entry(term)
                for p in postings_list:
                    self._insert_sorted(
                        entry,
                        doc_id=p["doc_id"],
                        frequency=p["frequency"],
                        positions=p["positions"],
                    )

    def close(self) -> None:
        """
        Giải phóng tài nguyên (in-memory index không cần đóng file pointer,
        method này tồn tại để tương thích interface với Disk-based Index).
        """
        pass  # No-op for in-memory implementation