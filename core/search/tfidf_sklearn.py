from typing import Dict, List, Optional

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from .vectorizer import BaseVectorizer


class SklearnTfIdfVectorizer(BaseVectorizer):
    """TF-IDF vectorizer dùng scikit-learn TfidfVectorizer.

    Fit trên corpus từ Inverted Index, transform query cùng vocabulary/IDF.
    """

    def __init__(self):
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._vocabulary: Dict[str, int] = {}
        self._idf: Optional[np.ndarray] = None
        self._matrix: Optional[csr_matrix] = None
        self._doc_ids: List[str] = []

    def build_vectors(self, index) -> None:
        self._doc_ids = sorted(index.documents.keys())

        # Dùng tokenized_content đã tiền xử lý thay vì raw text
        corpus = [
            " ".join(index.documents[did].tokenized_content)
            for did in self._doc_ids
        ]

        self._vectorizer = TfidfVectorizer(
            tokenizer=lambda x: x.split(),
            token_pattern=None,
            lowercase=False,
            norm="l2",
        )
        self._matrix = self._vectorizer.fit_transform(corpus)
        self._vocabulary = self._vectorizer.vocabulary_
        self._idf = self._vectorizer.idf_

    def vectorize_query(self, query_tokens: List[str]) -> csr_matrix:
        query_text = " ".join(query_tokens)
        return self._vectorizer.transform([query_text])

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
