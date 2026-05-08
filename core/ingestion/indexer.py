import os
import pickle
import threading
from typing import Dict, Optional

from core.contracts import BaseInvertedIndex, Document, PostingsList, Posting, DictionaryEntry

class InMemoryInvertedIndex(BaseInvertedIndex):
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.index: Dict[str, PostingsList] = {}
        self.dictionary: Dict[str, DictionaryEntry] = {}
        self.total_documents = 0
        self.trigram_index: Dict[str, set] = {}
        self.postings_file = None
        self.postings_lock = threading.Lock()

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
        if term in self.index:
            return self.index[term]
            
        if term in self.dictionary and self.postings_file is not None:
            entry = self.dictionary[term]
            with self.postings_lock:
                self.postings_file.seek(entry.offset)
                payload = self.postings_file.read(entry.length)
            
            try:
                # Decode (pickle)
                return pickle.loads(payload)
            except Exception:
                return None
                
        return None

    def get_document_frequency(self, term: str) -> int:
        if term in self.index:
            return self.index[term].document_frequency
        if term in self.dictionary:
            return self.dictionary[term].document_frequency
        return 0

    def get_total_documents(self) -> int:
        return self.total_documents

    def get_vocabulary(self) -> list:
        vocab = set(self.index.keys())
        vocab.update(self.dictionary.keys())
        return list(vocab)


    def compress_postings_vbyte(self, index: Dict[str, PostingsList]) -> Dict[str, bytes]:
        # --- VIẾT CODE CỦA BẠN Ở ĐÂY ---
        return index

    def decompress_postings_vbyte(self, compressed_data: Dict) -> Dict[str, PostingsList]:
        # --- VIẾT CODE CỦA BẠN Ở ĐÂY ---
        return compressed_data
        
    def save_to_disk(self, directory_path: str) -> None:
        os.makedirs(directory_path, exist_ok=True)
        
        if self.postings_file:
            self.postings_file.close()
            self.postings_file = None
            
        compressed_index = self.compress_postings_vbyte(self.index)
        
        postings_path = os.path.join(directory_path, "postings.bin")
        self.dictionary = {}
        offset = 0
        
        with open(postings_path, "wb") as pf:
            for term, payload in compressed_index.items():
                if not isinstance(payload, bytes):
                    payload = pickle.dumps(payload)
                
                length = len(payload)
                pf.write(payload)
                
                self.dictionary[term] = DictionaryEntry(
                    term=term,
                    document_frequency=self.index[term].document_frequency,
                    offset=offset,
                    length=length
                )
                offset += length
                
        file_path = os.path.join(directory_path, "index.pkl")
        with open(file_path, "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "dictionary": self.dictionary,
                "total_documents": self.total_documents,
                "trigram_index": self.trigram_index
            }, f)
            
        self.index.clear() # Clear RAM
        self.postings_file = open(postings_path, "rb")

    def load_from_disk(self, directory_path: str) -> None:
        if self.postings_file:
            self.postings_file.close()
            self.postings_file = None
            
        file_path = os.path.join(directory_path, "index.pkl")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = pickle.load(f)
                
                self.documents = data.get("documents", {})
                self.total_documents = data.get("total_documents", 0)
                self.dictionary = data.get("dictionary", {})
                self.trigram_index = data.get("trigram_index", {})
                
            self.index.clear()
            
        postings_path = os.path.join(directory_path, "postings.bin")
        if os.path.exists(postings_path):
            self.postings_file = open(postings_path, "rb")

    def close(self) -> None:
        if self.postings_file:
            self.postings_file.close()
            self.postings_file = None

global_index = InMemoryInvertedIndex()
