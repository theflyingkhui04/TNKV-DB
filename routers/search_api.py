import time
from typing import Optional

from fastapi import APIRouter, Query

from core.contracts import SearchResponse, SearchResultItem
from core.ingestion.indexer import global_index
from core.search.vectorizer import get_vectorizer
from core.search.ranker import search as ranker_search

router = APIRouter(prefix="/search", tags=["search"])

VALID_ALGORITHMS = {"manual", "sklearn", "bm25", "bm25+"}


@router.get("/collections/{name}", response_model=SearchResponse)
def search_documents(
    name: str,
    q: str = Query(..., description="Câu truy vấn tìm kiếm"),
    top_k: int = Query(10, ge=1, le=100, description="Số kết quả trả về"),
    algorithm: str = Query("manual", description=f"Thuật toán xếp hạng: {', '.join(sorted(VALID_ALGORITHMS))}"),
):
    """Tìm kiếm tài liệu theo TF-IDF/BM25 + Cosine Similarity, trả về Top-K."""
    if algorithm not in VALID_ALGORITHMS:
        from fastapi import HTTPException
        raise HTTPException(400, f"Invalid algorithm '{algorithm}'. Use one of: {VALID_ALGORITHMS}")

    start = time.time()

    vectorizer = get_vectorizer(algorithm)
    vectorizer.build_vectors(global_index)

    query_tokens = q.lower().split()
    results = ranker_search(vectorizer, query_tokens, top_k=top_k)

    items = []
    for doc_id, score in results:
        doc = global_index.documents.get(doc_id)
        content = doc.content if doc else None
        items.append(SearchResultItem(doc_id=doc_id, score=round(score, 4), content=content))

    elapsed = (time.time() - start) * 1000

    return SearchResponse(
        query=q,
        algorithm=vectorizer.algorithm_name,
        total_found=len(results),
        results=items,
        execution_time_ms=round(elapsed, 2),
    )
