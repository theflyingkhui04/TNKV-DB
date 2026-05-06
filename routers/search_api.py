import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from core.contracts import SearchResponse, SearchResultItem
from core.ingestion.indexer import global_index
from core.search.vectorizer import get_vectorizer
from core.search.ranker import search as ranker_search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/collections/{name}", response_model=SearchResponse)
def search_documents(
    name: str,
    q: str = Query(..., description="Câu truy vấn tìm kiếm"),
    top_k: int = Query(10, ge=1, le=100, description="Số kết quả trả về"),
):
    """Tìm kiếm tài liệu theo TF-IDF + Cosine Similarity, trả về Top-K."""
    start = time.time()

    # Vectorizer build trên index hiện tại
    vectorizer = get_vectorizer("manual")
    vectorizer.build_vectors(global_index)

    # Tokenize query giống ingestion pipeline
    query_tokens = q.lower().split()

    # Search: vectorize → cosine → min-heap top-K
    results = ranker_search(vectorizer, query_tokens, top_k=top_k)

    # Ghép content gốc từ index
    items = []
    for doc_id, score in results:
        doc = global_index.documents.get(doc_id)
        content = doc.content if doc else None
        items.append(SearchResultItem(doc_id=doc_id, score=round(score, 4), content=content))

    elapsed = (time.time() - start) * 1000

    return SearchResponse(
        query=q,
        total_found=len(results),
        results=items,
        execution_time_ms=round(elapsed, 2),
    )


@router.get("/collections/{name}/documents/{doc_id}")
def get_document(name: str, doc_id: str) -> Dict[str, Any]:
    """Lấy nội dung gốc của tài liệu theo doc_id."""
    doc = global_index.documents.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    return {
        "doc_id": doc.doc_id,
        "content": doc.content,
        "metadata": doc.metadata,
    }
