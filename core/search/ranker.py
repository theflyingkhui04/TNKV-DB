import heapq
from typing import List, Tuple

import numpy as np
from scipy.sparse import csr_matrix

from .vectorizer import BaseVectorizer


def cosine_similarity(
    tfidf_matrix: csr_matrix,
    query_vector: csr_matrix,
) -> np.ndarray:
    """Tính Cosine Similarity giữa query và tất cả docs.

    Vì vector đã L2-normalized, cosine = dot product.
    Trả về mảng 1-D float64 dài n_docs.
    """
    return np.asarray((tfidf_matrix @ query_vector.T).todense()).flatten()


def top_k_minheap(
    scores: "np.ndarray",
    doc_ids: List[str],
    k: int = 10,
) -> List[Tuple[str, float]]:
    """Lấy Top-K docs dùng Min-Heap. Độ phức tạp O(N log K).

    Returns
    -------
    list of (doc_id, score) sắp xếp giảm dần.
    """
    if k <= 0:
        return []

    # Min-heap giữ K phần tử lớn nhất: lưu (-score, doc_id) để heapq hoạt động như max-heap
    # hoặc dùng min-heap size K: push/pop để giữ top K
    heap: List[Tuple[float, str]] = []  # (score, doc_id) — min-heap

    for idx, score in enumerate(scores):
        if score <= 0:
            continue
        doc_id = doc_ids[idx] if idx < len(doc_ids) else str(idx)
        if len(heap) < k:
            heapq.heappush(heap, (score, doc_id))
        elif score > heap[0][0]:
            heapq.heapreplace(heap, (score, doc_id))

    # Sắp xếp giảm dần
    result = sorted(heap, key=lambda x: x[0], reverse=True)
    return [(did, score) for score, did in result]


def search(
    vectorizer: BaseVectorizer,
    query_tokens: List[str],
    top_k: int = 10,
) -> List[Tuple[str, float]]:
    """Pipeline: vectorize query → cosine sim → min-heap top-K.

    Returns list of (doc_id, score) sorted descending.
    """
    q_vec = vectorizer.vectorize_query(query_tokens)
    scores = cosine_similarity(vectorizer.tfidf_matrix, q_vec)
    return top_k_minheap(scores, vectorizer.doc_ids, k=top_k)
