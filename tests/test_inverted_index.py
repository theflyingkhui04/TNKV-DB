"""
tests/test_inverted_index.py

Unit test cho HashMapInvertedIndex — bao phủ:
  - add_document / get_postings / get_document_frequency
  - sorted order của linked list
  - TF lookup, merge AND/OR
  - save_to_disk / load_from_disk round-trip
  - thread safety (concurrent add)
  - edge cases: duplicate doc_id, term không tồn tại
"""

import os
import tempfile
import threading

import pytest

from contracts import Document
from inverted_index import HashMapInvertedIndex, PostingsListNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(doc_id: str, tokens: list[str]) -> Document:
    """Tạo Document đơn giản từ danh sách token."""
    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    return Document(
        doc_id=doc_id,
        content=" ".join(tokens),
        tokenized_content=tokens,
        term_frequencies=tf,
    )


@pytest.fixture
def idx() -> HashMapInvertedIndex:
    return HashMapInvertedIndex()


@pytest.fixture
def populated_idx() -> HashMapInvertedIndex:
    """Index có sẵn 3 document."""
    index = HashMapInvertedIndex()
    index.add_document(make_doc("doc1", ["python", "học", "máy", "học"]))
    index.add_document(make_doc("doc2", ["python", "web", "django"]))
    index.add_document(make_doc("doc3", ["học", "sâu", "mạng", "nơ-ron"]))
    return index


# ===========================================================================
# add_document
# ===========================================================================

class TestAddDocument:
    def test_total_documents_increases(self, idx):
        idx.add_document(make_doc("d1", ["hello", "world"]))
        assert idx.get_total_documents() == 1
        idx.add_document(make_doc("d2", ["foo"]))
        assert idx.get_total_documents() == 2

    def test_term_in_vocabulary(self, idx):
        idx.add_document(make_doc("d1", ["tiếng", "việt"]))
        vocab = idx.get_vocabulary()
        assert "tiếng" in vocab
        assert "việt" in vocab

    def test_duplicate_doc_id_raises(self, idx):
        idx.add_document(make_doc("d1", ["hello"]))
        with pytest.raises(ValueError, match="đã tồn tại"):
            idx.add_document(make_doc("d1", ["world"]))

    def test_document_stored(self, idx):
        doc = make_doc("d1", ["xin", "chào"])
        idx.add_document(doc)
        assert idx.get_document("d1") is not None
        assert idx.get_document("d1").content == doc.content

    def test_term_frequency_correct(self, idx):
        idx.add_document(make_doc("d1", ["a", "b", "a", "a"]))
        assert idx.get_term_frequency("a", "d1") == 3
        assert idx.get_term_frequency("b", "d1") == 1

    def test_positions_recorded(self, idx):
        idx.add_document(make_doc("d1", ["x", "y", "x"]))
        pl = idx.get_postings("x")
        assert pl is not None
        assert pl.postings[0].positions == [0, 2]


# ===========================================================================
# get_postings
# ===========================================================================

class TestGetPostings:
    def test_returns_none_for_unknown_term(self, idx):
        assert idx.get_postings("không_tồn_tại") is None

    def test_returns_postings_list(self, populated_idx):
        pl = populated_idx.get_postings("python")
        assert pl is not None
        assert pl.term == "python"
        assert pl.document_frequency == 2

    def test_postings_sorted_by_doc_id(self, idx):
        # Thêm doc theo thứ tự ngược — linked list phải vẫn sorted
        idx.add_document(make_doc("doc_z", ["term"]))
        idx.add_document(make_doc("doc_a", ["term"]))
        idx.add_document(make_doc("doc_m", ["term"]))
        pl = idx.get_postings("term")
        doc_ids = [p.doc_id for p in pl.postings]
        assert doc_ids == sorted(doc_ids)

    def test_postings_contain_correct_doc_ids(self, populated_idx):
        pl = populated_idx.get_postings("học")
        doc_ids = {p.doc_id for p in pl.postings}
        assert doc_ids == {"doc1", "doc3"}

    def test_single_occurrence_df(self, populated_idx):
        pl = populated_idx.get_postings("django")
        assert pl.document_frequency == 1
        assert pl.postings[0].doc_id == "doc2"

    def test_frequency_aggregated_within_doc(self, populated_idx):
        # "học" xuất hiện 2 lần trong doc1
        pl = populated_idx.get_postings("học")
        doc1_posting = next(p for p in pl.postings if p.doc_id == "doc1")
        assert doc1_posting.frequency == 2


# ===========================================================================
# get_document_frequency
# ===========================================================================

class TestGetDocumentFrequency:
    def test_zero_for_unknown_term(self, idx):
        assert idx.get_document_frequency("xyz") == 0

    def test_correct_df(self, populated_idx):
        assert populated_idx.get_document_frequency("python") == 2
        assert populated_idx.get_document_frequency("học") == 2
        assert populated_idx.get_document_frequency("django") == 1

    def test_df_increases_after_add(self, idx):
        idx.add_document(make_doc("d1", ["cat"]))
        assert idx.get_document_frequency("cat") == 1
        idx.add_document(make_doc("d2", ["cat", "dog"]))
        assert idx.get_document_frequency("cat") == 2


# ===========================================================================
# get_vocabulary
# ===========================================================================

class TestGetVocabulary:
    def test_empty_index_has_empty_vocab(self, idx):
        assert idx.get_vocabulary() == []

    def test_vocab_contains_all_terms(self, idx):
        idx.add_document(make_doc("d1", ["alpha", "beta"]))
        idx.add_document(make_doc("d2", ["gamma"]))
        vocab = set(idx.get_vocabulary())
        assert {"alpha", "beta", "gamma"}.issubset(vocab)

    def test_vocab_no_duplicates(self, idx):
        idx.add_document(make_doc("d1", ["a", "a", "b"]))
        idx.add_document(make_doc("d2", ["a", "c"]))
        vocab = idx.get_vocabulary()
        assert len(vocab) == len(set(vocab))


# ===========================================================================
# merge (AND / OR)
# ===========================================================================

class TestMerge:
    def test_and_common_docs(self, populated_idx):
        result = populated_idx.merge("python", "học", mode="AND")
        # doc1 có cả "python" và "học"
        assert result == ["doc1"]

    def test_and_no_common_docs(self, populated_idx):
        result = populated_idx.merge("django", "sâu", mode="AND")
        assert result == []

    def test_and_missing_term(self, populated_idx):
        result = populated_idx.merge("python", "không_có", mode="AND")
        assert result == []

    def test_or_union(self, populated_idx):
        result = populated_idx.merge("django", "sâu", mode="OR")
        assert set(result) == {"doc2", "doc3"}

    def test_or_result_sorted(self, idx):
        idx.add_document(make_doc("doc_c", ["x"]))
        idx.add_document(make_doc("doc_a", ["y"]))
        idx.add_document(make_doc("doc_b", ["x", "y"]))
        result = idx.merge("x", "y", mode="OR")
        assert result == sorted(result)

    def test_invalid_mode_raises(self, populated_idx):
        with pytest.raises(ValueError, match="mode không hợp lệ"):
            populated_idx.merge("python", "học", mode="XOR")


# ===========================================================================
# get_term_frequency
# ===========================================================================

class TestGetTermFrequency:
    def test_tf_zero_unknown_term(self, idx):
        idx.add_document(make_doc("d1", ["hello"]))
        assert idx.get_term_frequency("unknown", "d1") == 0

    def test_tf_zero_unknown_doc(self, idx):
        idx.add_document(make_doc("d1", ["hello"]))
        assert idx.get_term_frequency("hello", "d9999") == 0

    def test_tf_correct_value(self, idx):
        idx.add_document(make_doc("d1", ["go", "go", "go", "python"]))
        assert idx.get_term_frequency("go", "d1") == 3
        assert idx.get_term_frequency("python", "d1") == 1


# ===========================================================================
# get_stats
# ===========================================================================

class TestGetStats:
    def test_stats_empty(self, idx):
        s = idx.get_stats()
        assert s["total_documents"] == 0
        assert s["vocabulary_size"] == 0

    def test_stats_after_add(self, populated_idx):
        s = populated_idx.get_stats()
        assert s["total_documents"] == 3
        assert s["vocabulary_size"] > 0


# ===========================================================================
# save_to_disk / load_from_disk
# ===========================================================================

class TestPersistence:
    def test_round_trip(self, populated_idx):
        with tempfile.TemporaryDirectory() as tmpdir:
            populated_idx.save_to_disk(tmpdir)

            # Kiểm tra file tồn tại
            assert os.path.exists(os.path.join(tmpdir, "dictionary.json"))
            assert os.path.exists(os.path.join(tmpdir, "postings.json"))
            assert os.path.exists(os.path.join(tmpdir, "documents.json"))

            # Load vào index mới
            idx2 = HashMapInvertedIndex()
            idx2.load_from_disk(tmpdir)

            # Kiểm tra số liệu cơ bản
            assert idx2.get_total_documents() == populated_idx.get_total_documents()
            assert set(idx2.get_vocabulary()) == set(populated_idx.get_vocabulary())

    def test_postings_preserved_after_load(self, populated_idx):
        with tempfile.TemporaryDirectory() as tmpdir:
            populated_idx.save_to_disk(tmpdir)
            idx2 = HashMapInvertedIndex()
            idx2.load_from_disk(tmpdir)

            pl_orig = populated_idx.get_postings("python")
            pl_load = idx2.get_postings("python")

            assert pl_load is not None
            assert pl_load.document_frequency == pl_orig.document_frequency
            orig_ids = {p.doc_id for p in pl_orig.postings}
            load_ids = {p.doc_id for p in pl_load.postings}
            assert orig_ids == load_ids

    def test_load_resets_old_data(self, idx):
        idx.add_document(make_doc("old_doc", ["old_term"]))
        with tempfile.TemporaryDirectory() as tmpdir:
            # Lưu index rỗng (mới)
            empty_idx = HashMapInvertedIndex()
            empty_idx.save_to_disk(tmpdir)
            # Load đè lên idx đang có data
            idx.load_from_disk(tmpdir)
            assert idx.get_total_documents() == 0
            assert idx.get_postings("old_term") is None

    def test_sorted_order_preserved_after_load(self):
        index = HashMapInvertedIndex()
        # Thêm theo thứ tự ngược
        for i in range(9, -1, -1):
            index.add_document(make_doc(f"doc_{i:02d}", ["shared_term"]))
        with tempfile.TemporaryDirectory() as tmpdir:
            index.save_to_disk(tmpdir)
            idx2 = HashMapInvertedIndex()
            idx2.load_from_disk(tmpdir)
            pl = idx2.get_postings("shared_term")
            doc_ids = [p.doc_id for p in pl.postings]
            assert doc_ids == sorted(doc_ids)


# ===========================================================================
# Thread safety
# ===========================================================================

class TestThreadSafety:
    def test_concurrent_add_documents(self, idx):
        """50 thread đồng thời add document — không race condition."""
        errors: list[Exception] = []

        def add(i: int) -> None:
            try:
                idx.add_document(make_doc(f"thread_doc_{i}", ["shared", f"term_{i}"]))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Có lỗi trong thread: {errors}"
        assert idx.get_total_documents() == 50
        pl = idx.get_postings("shared")
        assert pl.document_frequency == 50