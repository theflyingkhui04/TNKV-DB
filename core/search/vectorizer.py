from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np
from scipy.sparse import csr_matrix


class BaseVectorizer(ABC):
    """Interface chung cho các TF-IDF vectorizer."""

    @abstractmethod
    def build_vectors(self, index) -> None:
        """Xây dựng TF-IDF matrix từ Inverted Index."""
        pass

    @abstractmethod
    def vectorize_query(self, query_tokens: List[str]) -> csr_matrix:
        """Chuyển query tokens thành TF-IDF sparse vector."""
        pass

    @property
    @abstractmethod
    def vocabulary(self) -> Dict[str, int]:
        """Mapping term -> column index."""
        pass

    @property
    @abstractmethod
    def idf_values(self) -> np.ndarray:
        """IDF values cho mỗi term trong vocabulary."""
        pass

    @property
    @abstractmethod
    def tfidf_matrix(self) -> csr_matrix:
        """Document-term TF-IDF sparse matrix (n_docs x n_terms)."""
        pass

    @property
    @abstractmethod
    def doc_ids(self) -> List[str]:
        """Danh sách doc_id tương ứng với các hàng trong tfidf_matrix."""
        pass


def get_vectorizer(mode: str = "manual") -> BaseVectorizer:
    """Factory tạo vectorizer theo mode."""
    if mode == "manual":
        from .tfidf_manual import ManualTfIdfVectorizer
        return ManualTfIdfVectorizer()
    elif mode == "sklearn":
        from .tfidf_sklearn import SklearnTfIdfVectorizer
        return SklearnTfIdfVectorizer()
    else:
        raise ValueError(f"Unknown vectorizer mode: {mode}. Use 'manual' or 'sklearn'.")
