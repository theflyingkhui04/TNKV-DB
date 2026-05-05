import os
import pickle
from typing import Dict, Optional

from core.contracts import BaseInvertedIndex, Document, PostingsList, Posting

class InMemoryInvertedIndex(BaseInvertedIndex):
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.index: Dict[str, PostingsList] = {}
        self.total_documents = 0

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

    def get_postings(self, term: str) -> Optional[PostingsList]:
        return self.index.get(term)

    def get_document_frequency(self, term: str) -> int:
        if term in self.index:
            return self.index[term].document_frequency
        return 0

    def get_total_documents(self) -> int:
        return self.total_documents

    def save_to_disk(self, directory_path: str) -> None:
        os.makedirs(directory_path, exist_ok=True)
        file_path = os.path.join(directory_path, "index.pkl")
        
        with open(file_path, "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "index": self.index,
                "total_documents": self.total_documents
            }, f)

    def load_from_disk(self, directory_path: str) -> None:
        file_path = os.path.join(directory_path, "index.pkl")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = pickle.load(f)
                self.documents = data["documents"]
                self.index = data["index"]
                self.total_documents = data["total_documents"]

global_index = InMemoryInvertedIndex()
