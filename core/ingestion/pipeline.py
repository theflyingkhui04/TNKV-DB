from typing import List
from core.contracts import UpsertRequest, Document
from core.ingestion.indexer import global_index

def process_and_ingest(requests: List[UpsertRequest]) -> int:
    success_count = 0
    
    for req in requests:
        try:
            raw_text = req.content.lower()
            tokens = raw_text.split()

            term_frequencies = {}
            for token in tokens:
                term_frequencies[token] = term_frequencies.get(token, 0) + 1
                
            doc = Document(
                doc_id=req.doc_id,
                content=req.content,
                tokenized_content=tokens,
                term_frequencies=term_frequencies,
                metadata=req.metadata or {}
            )
            
            global_index.add_document(doc)
            
            success_count += 1
        except Exception as e:
            print(f"Lỗi khi xử lý document {req.doc_id}: {e}")
            
    global_index.save_to_disk("storage")
      
    return success_count
