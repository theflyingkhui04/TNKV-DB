import math
from typing import Dict, List, Optional

import numpy as np
from scipy.sparse import csr_matrix

from .vectorizer import BaseVectorizer


class ManualTfIdfVectorizer(BaseVectorizer):
    """TF-IDF vectorizer code tay dùng scipy sparse matrix.

    Công thức:
        TF(t,d)  = 1 + log10(tf)   nếu tf > 0, ngược lại 0
        IDF(t)   = log10(N / df)
        TF-IDF   = TF * IDF
        Sau đó L2-normalize mỗi vector.
    """

    def __init__(self):
        self._vocabulary: Dict[str, int] = {}
        self._idf: Optional[np.ndarray] = None
        self._matrix: Optional[csr_matrix] = None
        self._doc_ids: List[str] = []

    # ---- build ----

    def build_vectors(self, index) -> None:
        # 1. Vocabulary: sort terms để kết quả xác định
        self._vocabulary = {
            term: idx
            for idx, term in enumerate(sorted(index.index.keys()))
        }
        vocab_size = len(self._vocabulary)
        total_docs = index.get_total_documents()
        self._doc_ids = sorted(index.documents.keys())

        # 2. IDF cho mỗi term
        self._idf = np.zeros(vocab_size)
        for term, col in self._vocabulary.items():
            df = index.get_document_frequency(term)
            if df > 0:
                self._idf[col] = math.log10(total_docs / df)

        # 3. TF-IDF sparse matrix
        rows, cols, data = [], [], []
        for row, doc_id in enumerate(self._doc_ids):
            doc = index.documents[doc_id]
            for term, tf in doc.term_frequencies.items():
                if term in self._vocabulary:
                    col = self._vocabulary[term]
                    tfidf = (1 + math.log10(tf)) * self._idf[col]
                    rows.append(row)
                    cols.append(col)
                    data.append(tfidf)

        self._matrix = csr_matrix(
            (data, (rows, cols)),
            shape=(len(self._doc_ids), vocab_size),
        )
        self._matrix = self._l2_normalize(self._matrix)

    # ---- query ----

    def vectorize_query(self, query_tokens: List[str]) -> csr_matrix:
        vocab_size = len(self._vocabulary)

        # TF cho query
        query_tf: Dict[str, int] = {}
        for t in query_tokens:
            query_tf[t] = query_tf.get(t, 0) + 1

        # TF-IDF sparse vector
        cols, data = [], []
        for term, tf in query_tf.items():
            if term in self._vocabulary:
                col = self._vocabulary[term]
                tfidf = (1 + math.log10(tf)) * self._idf[col]
                cols.append(col)
                data.append(tfidf)

        rows = [0] * len(cols)
        vec = csr_matrix((data, (rows, cols)), shape=(1, vocab_size))
        return self._l2_normalize(vec)

    # ---- helpers ----

    @staticmethod
    def _l2_normalize(mat: csr_matrix) -> csr_matrix:
        """L2-normalize từng hàng của sparse matrix."""
        norms = np.sqrt(np.asarray(mat.multiply(mat).sum(axis=1)).flatten())
        norms[norms == 0] = 1.0
        return mat.multiply(1.0 / norms[:, np.newaxis])

    # ---- properties ----

    @property
    def algorithm_name(self) -> str:
        return "tf-idf"

    @property
    def vocabulary(self) -> Dict[str, int]:
        return self._vocabulary

    @property
    def idf_values(self) -> np.ndarray:
        return self._idf

    @property
    def tfidf_matrix(self) -> csr_matrix:
        return self._matrix

    @property
    def doc_ids(self) -> List[str]:
        return self._doc_ids
