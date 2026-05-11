import os
import pickle
import threading
from typing import Dict, Optional

from core.contracts import BaseInvertedIndex, Document, PostingsList, Posting, DictionaryEntry
from core.ingestion.compression import gap_encode, gap_decode, vb_encode, vb_decode

class InMemoryInvertedIndex(BaseInvertedIndex):
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.index: Dict[str, PostingsList] = {}
        self.dictionary: Dict[str, DictionaryEntry] = {}
        self.total_documents = 0
        self.trigram_index: Dict[str, set] = {}
        self.postings_file = None
        self.postings_lock = threading.Lock()

    def clear(self) -> None:
        with self.postings_lock:
            self.documents.clear()
            self.index.clear()
            self.dictionary.clear()
            self.total_documents = 0
            self.trigram_index.clear()
            if self.postings_file:
                self.postings_file.close()
                self.postings_file = None

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
                # Decode
                data = pickle.loads(payload)
                if isinstance(data, dict):
                    postings = []
                    
                    if "doc_ids_bytes" in data and data["doc_ids_bytes"] is not None:
                        # Dữ liệu đã được nén
                        gaps = vb_decode(data["doc_ids_bytes"])
                        doc_ids = gap_decode(gaps)
                        for i in range(len(doc_ids)):
                            postings.append(Posting(
                                doc_id=str(doc_ids[i]),
                                frequency=data["frequencies"][i],
                                positions=data["positions_list"][i]
                            ))
                    else:
                        # Dữ liệu không nén được (ví dụ doc_id là chữ 'D01')
                        for i in range(len(data["uncompressed_doc_ids"])):
                            postings.append(Posting(
                                doc_id=data["uncompressed_doc_ids"][i],
                                frequency=data["frequencies"][i],
                                positions=data["positions_list"][i]
                            ))
                            
                    return PostingsList(
                        term=data["term"],
                        document_frequency=data["df"],
                        postings=postings
                    )
                return data
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
        compressed_index = {}
        for term, postings_list in index.items():
            doc_ids = []
            frequencies = []
            positions_list = []
            uncompressed_doc_ids = []
            
            can_compress = all(p.doc_id.isdigit() for p in postings_list.postings)
            
            # Sắp xếp postings theo doc_id tăng dần để Gap Encoding hoạt động đúng (không sinh số âm)
            if can_compress:
                sorted_postings = sorted(postings_list.postings, key=lambda p: int(p.doc_id))
            else:
                # Nếu không nén bằng số, có thể sort theo chuỗi để đảm bảo tính nhất quán (tuỳ chọn)
                sorted_postings = sorted(postings_list.postings, key=lambda p: p.doc_id)
                
            for p in sorted_postings:
                if can_compress:
                    doc_ids.append(int(p.doc_id))
                uncompressed_doc_ids.append(p.doc_id)
                frequencies.append(p.frequency)
                positions_list.append(p.positions)
                
            doc_ids_bytes = None
            if can_compress:
                # Nén doc_ids bằng Gap Encoding + Variable Byte
                gaps = gap_encode(doc_ids)
                doc_ids_bytes = vb_encode(gaps)
            
            # Đóng gói các metadata khác cùng với bytes đã nén (hoặc không nén)
            payload = pickle.dumps({
                "term": term,
                "df": postings_list.document_frequency,
                "doc_ids_bytes": doc_ids_bytes,
                "uncompressed_doc_ids": [] if can_compress else uncompressed_doc_ids,
                "frequencies": frequencies,
                "positions_list": positions_list
            })
            compressed_index[term] = payload
            
        return compressed_index

    def decompress_postings_vbyte(self, compressed_data: Dict) -> Dict[str, PostingsList]:
        # Hàm này dùng nếu ta load toàn bộ vào RAM (không bắt buộc với Block Offset hiện tại)
        pass
        
    def save_to_disk(self, directory_path: str) -> None:
        if not self.index:
            return  # Không có gì trên RAM để lưu, bỏ qua để tránh xóa trắng disk
            
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
