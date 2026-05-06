import time
from fastapi import APIRouter

from core.contracts import SmartSearchRequest, SearchResponse, SearchResultItem
from core.ingestion.indexer import global_index
from core.search.vectorizer import get_vectorizer
from core.search.ranker import cosine_similarity, top_k_minheap

from core.smart.spell_checker import correct_query
from core.smart.rocchio import expand_query

router = APIRouter(prefix="/smart", tags=["smart"])

@router.post("/search", response_model=SearchResponse)
def smart_search(req: SmartSearchRequest):
    start_time = time.time()
    
    vectorizer = get_vectorizer("manual")
    vectorizer.build_vectors(global_index)
    
    query_tokens = req.query.lower().split()
    corrected_query_str = None
    
    if req.use_spell_check:
        vocab = set(vectorizer.vocabulary.keys())
        corrected_tokens, was_corrected = correct_query(query_tokens, vocab)
        if was_corrected:
            query_tokens = corrected_tokens
            corrected_query_str = " ".join(corrected_tokens)

    if req.use_rocchio and req.positive_feedback_ids:
        q_vector = expand_query(query_tokens, req.positive_feedback_ids, vectorizer)
    else:
        q_vector = vectorizer.vectorize_query(query_tokens)
    

    scores = cosine_similarity(vectorizer.tfidf_matrix, q_vector)
    results = top_k_minheap(scores, vectorizer.doc_ids, k=req.top_k)
    
    items = []
    for doc_id, score in results:
        doc = global_index.documents.get(doc_id)
        content = doc.content if doc else None
        items.append(SearchResultItem(doc_id=doc_id, score=round(score, 4), content=content))
        
    elapsed = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=req.query,
        total_found=len(results),
        results=items,
        execution_time_ms=round(elapsed, 2),
        corrected_query=corrected_query_str
    )
