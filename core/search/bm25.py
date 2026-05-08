import math
from typing import Dict, List, Optional

import numpy as np
from scipy.sparse import csr_matrix

from .vectorizer import BaseVectorizer


class BM25Vectorizer(BaseVectorizer):
    """Okapi BM25 vectorizer.

    Công thức (mỗi term t trong doc d):
        IDF(t) = log((N - df + 0.5) / (df + 0.5) + 1)
        W(t,d) = IDF(t) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))

    Query vector = binary indicator (1 nếu term xuất hiện trong query).
    Score = dot product (không L2-normalize).
    """

    k1: float = 1.5
    b: float = 0.75
    _algorithm_name: str = "bm25"

    def __init__(self):
        self._vocabulary: Dict[str, int] = {}
        self._idf: Optional[np.ndarray] = None
        self._matrix: Optional[csr_matrix] = None
        self._doc_ids: List[str] = []
        self._doc_lengths: Optional[np.ndarray] = None
        self._avgdl: float = 0.0

    def build_vectors(self, index) -> None:
        self._vocabulary = {
            t: i for i, t in enumerate(sorted(index.index.keys()))
        }
        vocab_size = len(self._vocabulary)
        total_docs = index.get_total_documents()
        self._doc_ids = sorted(index.documents.keys())
        n_docs = len(self._doc_ids)

        # Document lengths & average
        self._doc_lengths = np.zeros(n_docs)
        for row, did in enumerate(self._doc_ids):
            self._doc_lengths[row] = len(index.documents[did].tokenized_content)
        self._avgdl = self._doc_lengths.mean() if n_docs > 0 else 1.0

        # IDF
        self._idf = np.zeros(vocab_size)
        for term, col in self._vocabulary.items():
            df = index.get_document_frequency(term)
            self._idf[col] = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)

        # BM25 weight matrix
        rows, cols, data = [], [], []
        for row, did in enumerate(self._doc_ids):
            doc = index.documents[did]
            dl = self._doc_lengths[row]
            for term, tf in doc.term_frequencies.items():
                if term in self._vocabulary:
                    col = self._vocabulary[term]
                    w = self._term_weight(tf, dl, self._idf[col])
                    rows.append(row)
                    cols.append(col)
                    data.append(w)

        self._matrix = csr_matrix(
            (data, (rows, cols)), shape=(n_docs, vocab_size)
        )

    def _term_weight(self, tf: int, dl: float, idf: float) -> float:
        """BM25 weight cho 1 term trong 1 doc."""
        num = tf * (self.k1 + 1)
        den = tf + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
        return idf * num / den

    def vectorize_query(self, query_tokens: List[str]) -> csr_matrix:
        vocab_size = len(self._vocabulary)
        # Binary indicator: 1 nếu term có trong query
        seen = set()
        cols, data = [], []
        for t in query_tokens:
            if t in self._vocabulary and t not in seen:
                cols.append(self._vocabulary[t])
                data.append(1.0)
                seen.add(t)
        rows = [0] * len(cols)
        return csr_matrix((data, (rows, cols)), shape=(1, vocab_size))

    @property
    def algorithm_name(self) -> str:
        return self._algorithm_name

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


class BM25PlusVectorizer(BM25Vectorizer):
    """BM25+ (thêm delta vào term weight).

    W(t,d) = BM25_W(t,d) + delta * IDF(t)
    delta mặc định = 1.0.
    """

    delta: float = 1.0
    _algorithm_name: str = "bm25+"

    def _term_weight(self, tf: int, dl: float, idf: float) -> float:
        bm25_w = super()._term_weight(tf, dl, idf)
        return bm25_w + self.delta * idf
