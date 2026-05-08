import os
import pickle
from typing import Dict, Optional

from core.contracts import BaseInvertedIndex, Document, PostingsList, Posting

class InMemoryInvertedIndex(BaseInvertedIndex):
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.index: Dict[str, PostingsList] = {}
        self.total_documents = 0
        self.trigram_index: Dict[str, set] = {}

    def add_document(self, doc: Document) -> None:
        self.documents[doc.doc_id] = doc
        self.total_documents += 1
        
        for position, term in enumerate(doc.tokenized_content):
            if term not in self.index:
                self.index[term] = PostingsList(term=term)
            postings_list = self.index[term]
            existing_posting = next((p for p in postings_list.postings if p.doc_id == doc.doc_id), None)
            
            if existing_posting:
                existing_posting.frequency += 1
                existing_posting.positions.append(position)
            else:
                new_posting = Posting(doc_id=doc.doc_id, frequency=1, positions=[position])
                postings_list.postings.append(new_posting)
                postings_list.document_frequency += 1
                
            # Cập nhật Trigram Index cho từ vựng mới
            if len(term) == 1:
                tgs = [f"${term}$"]
            elif len(term) > 1:
                padded = f"${term}$"
                tgs = [padded[i:i+3] for i in range(len(padded) - 2)]
            else:
                tgs = []
            for tg in tgs:
                if tg not in self.trigram_index:
                    self.trigram_index[tg] = set()
                self.trigram_index[tg].add(term)

    def get_postings(self, term: str) -> Optional[PostingsList]:
        return self.index.get(term)

    def get_document_frequency(self, term: str) -> int:
        if term in self.index:
            return self.index[term].document_frequency
        return 0

    def get_total_documents(self) -> int:
        return self.total_documents

    def get_vocabulary(self) -> list:
        return list(self.index.keys())


    def compress_postings_vbyte(self, index: Dict[str, PostingsList]) -> Dict[str, bytes]:
        # --- VIẾT CODE CỦA BẠN Ở ĐÂY ---
        return index

    def decompress_postings_vbyte(self, compressed_data: Dict) -> Dict[str, PostingsList]:
        # --- VIẾT CODE CỦA BẠN Ở ĐÂY ---
        return compressed_data
        
    def save_to_disk(self, directory_path: str) -> None:
        os.makedirs(directory_path, exist_ok=True)
        file_path = os.path.join(directory_path, "index.pkl")
        
        compressed_index = self.compress_postings_vbyte(self.index)
        
        with open(file_path, "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "index": compressed_index,
                "total_documents": self.total_documents,
                "trigram_index": self.trigram_index
            }, f)

    def load_from_disk(self, directory_path: str) -> None:
        file_path = os.path.join(directory_path, "index.pkl")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = pickle.load(f)
                
                self.documents = data.get("documents", {})
                self.total_documents = data.get("total_documents", 0)
                
                self.index = self.decompress_postings_vbyte(data.get("index", {}))
                self.trigram_index = data.get("trigram_index", {})

global_index = InMemoryInvertedIndex()
