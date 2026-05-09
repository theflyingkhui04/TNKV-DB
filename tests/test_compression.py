"""
tests/test_compression.py

Unit & Integration tests cho Index Compression (Gap Encoding + Variable Byte).

Test scenarios:
  1. Kiểm tra Gap Encoding/Decoding
  2. Kiểm tra Variable Byte Encoding/Decoding
  3. Kiểm tra full compression pipeline
  4. Kiểm tra integration với Inverted Index (save/load)
  5. Kiểm tra compression ratio
"""

import json
import os
import tempfile
import sys
from pathlib import Path

# Add parent to path để import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ingestion.compression import (
    gap_encode,
    gap_decode,
    vb_encode,
    vb_decode,
    compress_postings,
    decompress_postings,
    compression_ratio,
)
from core.contracts import Document
from core.ingestion.inverted_index import HashMapInvertedIndex


def test_gap_encoding():
    """Test Gap Encoding & Decoding."""
    print("\n" + "="*70)
    print("TEST 1: Gap Encoding & Decoding")
    print("="*70)

    # Test case 1: Basic sequence
    doc_ids = [100, 105, 115, 125, 130]
    gaps = gap_encode(doc_ids)
    decoded = gap_decode(gaps)

    print(f"Original:  {doc_ids}")
    print(f"Gaps:      {gaps}")
    print(f"Decoded:   {decoded}")

    assert decoded == doc_ids, f"Gap encoding failed: {decoded} != {doc_ids}"
    print("✅ Basic sequence OK")

    # Test case 2: Single element
    single = [42]
    gaps = gap_encode(single)
    decoded = gap_decode(gaps)
    assert decoded == single
    print("✅ Single element OK")

    # Test case 3: Empty list
    empty = []
    gaps = gap_encode(empty)
    decoded = gap_decode(gaps)
    assert decoded == empty
    print("✅ Empty list OK")

    # Test case 4: Large gaps
    large_gaps = [1, 1000000, 2000000]
    gaps = gap_encode(large_gaps)
    decoded = gap_decode(gaps)
    assert decoded == large_gaps
    print("✅ Large gaps OK")

    print("✅ All Gap Encoding tests passed!")


def test_vb_encoding():
    """Test Variable Byte Encoding & Decoding."""
    print("\n" + "="*70)
    print("TEST 2: Variable Byte Encoding & Decoding")
    print("="*70)

    test_cases = [
        ([5], "Single small number"),
        ([127], "Max 1-byte number"),
        ([128], "Min 2-byte number"),
        ([255], "2-byte number"),
        ([300], "Mid 2-byte number"),
        ([16383], "Max 2-byte number"),
        ([16384], "Min 3-byte number"),
        ([1000000], "Large number"),
        ([5, 100, 300, 2000, 1000000], "Mixed sizes"),
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "Sequential small numbers"),
    ]

    for numbers, description in test_cases:
        encoded = vb_encode(numbers)
        decoded = vb_decode(encoded)

        print(f"  {description:.<40} ", end="")
        if decoded == numbers:
            print(f"✅ ({len(encoded)} bytes)")
        else:
            print(f"❌ Got {decoded}, expected {numbers}")
            raise AssertionError(f"VB encoding failed for {description}")

    print("✅ All Variable Byte Encoding tests passed!")


def test_full_compression_pipeline():
    """Test full compression pipeline."""
    print("\n" + "="*70)
    print("TEST 3: Full Compression Pipeline")
    print("="*70)

    # Generate realistic doc_ids
    doc_ids = [1 + i*7 for i in range(100)]  # [1, 8, 15, ..., 694]
    print(f"Testing with {len(doc_ids)} doc_ids")

    # Compress
    compressed, count = compress_postings(doc_ids)
    original_size = len(doc_ids) * 4  # 4 bytes per int32

    print(f"Original size: {original_size} bytes")
    print(f"Compressed size: {len(compressed)} bytes")

    ratio = compression_ratio(original_size, len(compressed))
    print(f"Compression ratio: {ratio:.1%}")

    assert len(compressed) < original_size, "Compression didn't reduce size!"
    assert count == len(doc_ids), f"Count mismatch: {count} != {len(doc_ids)}"

    # Decompress
    decompressed = decompress_postings(compressed, count)

    print(f"Decompressed: {len(decompressed)} items")
    assert decompressed == doc_ids, "Decompression failed!"

    print("✅ Full compression pipeline OK!")


def test_inverted_index_compression():
    """Test integration with Inverted Index save/load."""
    print("\n" + "="*70)
    print("TEST 4: Inverted Index with Compression")
    print("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create index with sample documents
        index = HashMapInvertedIndex()

        documents = [
            Document(
                doc_id="D01",
                content="python programming language",
                tokenized_content=["python", "programming", "language"],
                term_frequencies={"python": 1, "programming": 1, "language": 1},
                metadata={}
            ),
            Document(
                doc_id="D02",
                content="java programming language",
                tokenized_content=["java", "programming", "language"],
                term_frequencies={"java": 1, "programming": 1, "language": 1},
                metadata={}
            ),
            Document(
                doc_id="D03",
                content="python python code",
                tokenized_content=["python", "python", "code"],
                term_frequencies={"python": 2, "code": 1},
                metadata={}
            ),
        ]

        print(f"Adding {len(documents)} documents...")
        for doc in documents:
            index.add_document(doc)

        print(f"Index stats: {index.get_stats()}")

        # Save to disk
        print(f"\nSaving index to {tmpdir}...")
        index.save_to_disk(tmpdir)

        # Check file sizes
        postings_path = os.path.join(tmpdir, "postings.json")
        if os.path.exists(postings_path):
            postings_size = os.path.getsize(postings_path)
            print(f"Postings file size: {postings_size} bytes")

        # Load from disk
        print("Loading index from disk...")
        index2 = HashMapInvertedIndex()
        index2.load_from_disk(tmpdir)

        print(f"Loaded index stats: {index2.get_stats()}")

        # Verify postings are correct
        for term in index.get_vocabulary():
            orig_postings = index.get_postings(term)
            loaded_postings = index2.get_postings(term)

            assert orig_postings is not None, f"Original postings missing for {term}"
            assert loaded_postings is not None, f"Loaded postings missing for {term}"

            assert orig_postings.document_frequency == loaded_postings.document_frequency, \
                f"DF mismatch for {term}"

            assert len(orig_postings.postings) == len(loaded_postings.postings), \
                f"Postings count mismatch for {term}"

            print(f"  ✅ {term}: {loaded_postings.document_frequency} docs, "
                  f"{len(loaded_postings.postings)} postings")

        print("✅ Inverted Index compression integration OK!")


def test_compression_statistics():
    """Test compression ratio statistics."""
    print("\n" + "="*70)
    print("TEST 5: Compression Ratio Statistics")
    print("="*70)

    # Realistic scenario: 10000 doc_ids with varying gaps
    import random
    doc_ids = sorted([random.randint(1, 1000000) for _ in range(10000)])

    compressed, count = compress_postings(doc_ids)
    original_size = len(doc_ids) * 4

    ratio = compression_ratio(original_size, len(compressed))
    savings = original_size - len(compressed)

    print(f"Document count: {len(doc_ids):,}")
    print(f"Original size: {original_size:,} bytes")
    print(f"Compressed size: {len(compressed):,} bytes")
    print(f"Compression ratio: {ratio:.1%}")
    print(f"Bytes saved: {savings:,} bytes")
    print(f"Average bytes per doc_id: {len(compressed)/len(doc_ids):.2f} bytes")

    assert ratio > 0, "Should have positive compression ratio"
    print("✅ Compression statistics OK!")


def run_all_tests():
    """Run all tests."""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  INDEX COMPRESSION TEST SUITE".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    try:
        test_gap_encoding()
        test_vb_encoding()
        test_full_compression_pipeline()
        test_inverted_index_compression()
        test_compression_statistics()

        print("\n" + "="*70)
        print("✨ ALL TESTS PASSED!")
        print("="*70 + "\n")

        return True
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
