import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from core.contracts import SearchResponse, SearchResultItem
from core.ingestion.indexer import global_index
from core.search.vectorizer import get_vectorizer
from core.search.ranker import search as ranker_search
from core.search.utils import extract_snippet

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

    from core.search.utils import tokenize
    query_tokens = tokenize(q)
    results = ranker_search(vectorizer, query_tokens, top_k=top_k)

    items = []
    for doc_id, score in results:
        doc = global_index.documents.get(doc_id)
        content = doc.content if doc else None
        
        snippet = extract_snippet(content, query_tokens) if content else None
        
        items.append(SearchResultItem(doc_id=doc_id, score=round(score, 4), content=content, snippet=snippet))

    elapsed = (time.time() - start) * 1000

    return SearchResponse(
        query=q,
        algorithm=vectorizer.algorithm_name,
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

@router.get("/debug/stats")
def get_db_stats() -> Dict[str, Any]:
    """Lấy thống kê tổng quan của Database (dùng cho UI Khám phá)."""
    vocab = global_index.get_vocabulary()
    return {
        "total_documents": global_index.get_total_documents(),
        "vocabulary_size": len(vocab),
        "vocabulary_sample": vocab[:50]  # Trả về 50 từ khóa đầu tiên để preview
    }

@router.get("/debug/postings/{term}")
def get_term_postings(term: str) -> Dict[str, Any]:
    """Xem chi tiết Postings List và Dictionary Entry của một từ khóa."""
    term = term.lower()
    postings_list = global_index.get_postings(term)
    
    if postings_list is None or not postings_list.postings:
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found in index")
        
    entry = global_index.dictionary.get(term)
    disk_info = None
    if entry:
        disk_info = {
            "offset": entry.offset,
            "length_bytes": entry.length
        }
        
    return {
        "term": term,
        "document_frequency": postings_list.document_frequency,
        "disk_storage": disk_info,
        "postings": [
            {
                "doc_id": p.doc_id,
                "frequency": p.frequency,
                "positions": p.positions
            }
            for p in postings_list.postings
        ]
    }
