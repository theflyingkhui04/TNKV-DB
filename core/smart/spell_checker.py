from typing import List, Optional, Tuple, Set

def edit_distance(source: str, target: str) -> int:
    m = len(source)
    n = len(target)

    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if source[i - 1] == target[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
    return dp[m][n]

def generate_trigrams(word: str) -> List[str]:
    if len(word) == 0:
        return []
    if len(word) == 1:
        return [f"${word}$"]
    padded = f"${word}$"
    return [padded[i:i+3] for i in range(len(padded) - 2)]

def get_candidates(word: str, trigram_index: dict, top_k: int = 100) -> Set[str]:
    trigrams = generate_trigrams(word)
    trigram_count = len(trigrams)
    if trigram_count == 0:
        return set()
    
    match_counts = {}
    for tg in trigrams:
        if tg in trigram_index:
            for vocab_word in trigram_index[tg]:
                match_counts[vocab_word] = match_counts.get(vocab_word, 0) + 1
                
    candidates_scores = []
    for vocab_word, match in match_counts.items():
        vocab_trigram_count = len(vocab_word) if len(vocab_word) > 1 else 1
        jaccard = match / (trigram_count + vocab_trigram_count - match)
        candidates_scores.append((jaccard, vocab_word))
        
    candidates_scores.sort(key=lambda x: x[0], reverse=True)
    return {word for _, word in candidates_scores[:top_k]}

def find_closest_term(
    word: str,
    vocabulary: Set[str],
    trigram_index: dict,
    max_distance: int = 2,
) -> Optional[str]:
    best_word = None
    best_dist = max_distance + 1

    candidates = get_candidates(word, trigram_index, top_k=100)

    for candidate in candidates:
        if abs(len(candidate) - len(word)) > max_distance:
            continue
        dist = edit_distance(word, candidate)
        if dist < best_dist and dist <= max_distance:
            best_dist = dist
            best_word = candidate
    return best_word


def correct_query(
    query_tokens: List[str],
    vocabulary: Set[str],
    trigram_index: dict,
    max_distance: int = 2,
) -> Tuple[List[str], bool]:
    corrected_tokens = []
    was_corrected = False

    for token in query_tokens:
        if token in vocabulary:
            corrected_tokens.append(token)
        else:
            suggestion = find_closest_term(token, vocabulary, trigram_index, max_distance)
            if suggestion is not None:
                corrected_tokens.append(suggestion)
                was_corrected = True
                print(f"  [Spell Check] '{token}' → '{suggestion}'")
            else:
                corrected_tokens.append(token)
                print(f"  [Spell Check] '{token}' → không tìm thấy gợi ý, giữ nguyên.")
    return corrected_tokens, was_corrected
