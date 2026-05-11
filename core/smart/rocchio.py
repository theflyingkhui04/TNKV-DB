from typing import List
import numpy as np
from scipy.sparse import csr_matrix

from core.search.vectorizer import BaseVectorizer

def apply_rocchio(
    q_vector: csr_matrix,
    relevant_vectors: csr_matrix,
    alpha: float = 1.0,
    beta: float = 0.75
) -> csr_matrix:
    if relevant_vectors.shape[0] == 0:
        return q_vector
    centroid = relevant_vectors.mean(axis=0)
    q_new = alpha*q_vector + beta*centroid
    q_new_sparse = csr_matrix(q_new)

    norms = np.sqrt(np.asarray(q_new_sparse.multiply(q_new_sparse).sum(axis=1)).flatten())
    norms[norms == 0] = 1.0
    q_new_normalized = q_new_sparse.multiply(1.0 / norms[:, np.newaxis])

    return q_new_normalized


def expand_query(
    query_tokens: List[str],
    relevant_ids: List[str],
    vectorizer: BaseVectorizer,
    alpha: float = 1.0,
    beta: float = 0.75
) -> csr_matrix:
    q_vector = vectorizer.vectorize_query(query_tokens)
    
    if not relevant_ids:
        return q_vector
        
    row_indices = []
    for doc_id in relevant_ids:
        try:
            idx = vectorizer.doc_ids.index(doc_id)
            row_indices.append(idx)
        except ValueError:
            continue
            
    if not row_indices:
        return q_vector
        
    matrix_csr = vectorizer.tfidf_matrix.tocsr()
    relevant_vectors = matrix_csr[row_indices]
    return apply_rocchio(q_vector, relevant_vectors, alpha, beta)
