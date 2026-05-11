import re
import string
from typing import List

def tokenize(text: str) -> List[str]:
    """
    Tiền xử lý văn bản: chuyển chữ thường, loại bỏ dấu câu và tách từ.
    """
    if not text:
        return []
    text = text.lower()
    for p in string.punctuation:
        text = text.replace(p, ' ')
    return text.split()

def extract_snippet(content: str, query_tokens: List[str], context_words: int = 15) -> str:
    """
    Trích xuất snippet 15-20 từ xung quanh từ khóa tìm kiếm và highlight chúng.
    """
    if not content:
        return ""
        
    if not query_tokens:
        words = content.split()
        snippet = " ".join(words[:context_words * 2])
        return snippet + "..." if len(words) > context_words * 2 else snippet
        
    escaped_tokens = [re.escape(token) for token in query_tokens]
    # \b matches word boundaries. We use re.IGNORECASE for case-insensitive matching
    pattern = re.compile(r'\b(' + '|'.join(escaped_tokens) + r')\b', re.IGNORECASE)
    
    words = content.split()
    best_idx = -1
    
    # Tìm vị trí xuất hiện đầu tiên của bất kỳ token nào
    for i, word in enumerate(words):
        if pattern.search(word):
            best_idx = i
            break
            
    if best_idx == -1:
        snippet_words = words[:context_words * 2]
        snippet = " ".join(snippet_words)
        return snippet + "..." if len(words) > context_words * 2 else snippet
        
    start_idx = max(0, best_idx - context_words)
    end_idx = min(len(words), best_idx + context_words + 1)
    
    snippet_words = words[start_idx:end_idx]
    snippet = " ".join(snippet_words)
    
    if start_idx > 0:
        snippet = "..." + snippet
    if end_idx < len(words):
        snippet = snippet + "..."
        
    # Thay thế các từ khóa bằng thẻ <mark> bôi đậm
    highlighted_snippet = pattern.sub(r'<mark>\1</mark>', snippet)
    
    return highlighted_snippet
