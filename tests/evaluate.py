"""Script chấm điểm tự động: tính Precision, Recall cho bộ truy vấn test.

Usage:
    cd TNKV-DB
    python -m tests.evaluate
    # hoặc
    python tests/evaluate.py
"""

import json
import os
import sys
import time
from typing import Dict, List, Set, Tuple

# Đảm bảo import được core module khi chạy từ bất kỳ đâu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.contracts import UpsertRequest
from core.ingestion.pipeline import process_and_ingest
from core.ingestion.indexer import global_index
from core.search.vectorizer import get_vectorizer
from core.search.ranker import search as ranker_search

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_test_data() -> Tuple[list, list, Dict[str, Set[str]]]:
    """Load corpus, queries, qrels từ thư mục tests/."""
    with open(os.path.join(TESTS_DIR, "corpus.json"), encoding="utf-8") as f:
        corpus = json.load(f)
    with open(os.path.join(TESTS_DIR, "queries.json"), encoding="utf-8") as f:
        queries = json.load(f)
    with open(os.path.join(TESTS_DIR, "qrels.json"), encoding="utf-8") as f:
        qrels_list = json.load(f)

    qrels: Dict[str, Set[str]] = {}
    for item in qrels_list:
        qrels[item["query_id"]] = set(item["relevant_docs"])

    return corpus, queries, qrels


def ingest_corpus(corpus: list) -> None:
    """Nạp toàn bộ corpus vào index."""
    requests = []
    for doc in corpus:
        text = f"{doc['title']} {doc['description']}"
        requests.append(UpsertRequest(doc_id=doc["doc_id"], content=text))
    process_and_ingest(requests)


def run_query(query_text: str, top_k: int = 10) -> List[str]:
    """Chạy search và trả về list doc_id."""
    vectorizer = get_vectorizer("manual")
    vectorizer.build_vectors(global_index)
    tokens = query_text.lower().split()
    results = ranker_search(vectorizer, tokens, top_k=top_k)
    return [doc_id for doc_id, _score in results]


def compute_metrics(
    retrieved: Set[str], relevant: Set[str]
) -> Tuple[float, float, float]:
    """Tính Precision, Recall, F1."""
    if not retrieved and not relevant:
        return 1.0, 1.0, 1.0
    if not retrieved:
        return 0.0, 0.0, 0.0

    true_pos = len(retrieved & relevant)
    precision = true_pos / len(retrieved) if retrieved else 0.0
    recall = true_pos / len(relevant) if relevant else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def evaluate(top_k: int = 10) -> None:
    """Chạy toàn bộ evaluation pipeline."""
    print("=" * 60)
    print("  TNKV-DB Evaluation: Precision & Recall")
    print("=" * 60)

    # Load data
    corpus, queries, qrels = load_test_data()
    print(f"\nCorpus: {len(corpus)} docs | Queries: {len(queries)} | Qrels: {len(qrels)}")

    # Ingest
    ingest_corpus(corpus)
    print(f"Ingested {global_index.total_documents} documents, {len(global_index.index)} terms\n")

    # Evaluate từng query
    total_p, total_r, total_f1 = 0.0, 0.0, 0.0
    print(f"{'Query':<8} {'Text':<30} {'Retrieved':<15} {'Relevant':<15} {'Prec':>8} {'Recall':>8} {'F1':>8}")
    print("-" * 92)

    for q in queries:
        qid = q["query_id"]
        query_text = q["query"]
        relevant = qrels.get(qid, set())

        start = time.time()
        retrieved_list = run_query(query_text, top_k=top_k)
        elapsed = (time.time() - start) * 1000

        retrieved = set(retrieved_list)
        precision, recall, f1 = compute_metrics(retrieved, relevant)
        total_p += precision
        total_r += recall
        total_f1 += f1

        ret_str = ",".join(sorted(retrieved)) if retrieved else "∅"
        rel_str = ",".join(sorted(relevant)) if relevant else "∅"
        print(f"{qid:<8} {query_text:<30} {ret_str:<15} {rel_str:<15} {precision:>8.4f} {recall:>8.4f} {f1:>8.4f}  ({elapsed:.1f}ms)")

    # Average
    n = len(queries)
    print("-" * 92)
    print(f"{'AVERAGE':<8} {'':<30} {'':<15} {'':<15} {total_p/n:>8.4f} {total_r/n:>8.4f} {total_f1/n:>8.4f}")
    print("=" * 60)


if __name__ == "__main__":
    evaluate(top_k=10)
