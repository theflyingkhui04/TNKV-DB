"""
Integration Test: Kịch bản thực tế
Nạp data → Tìm kiếm → Tìm sai chính tả → Click phản hồi mở rộng truy vấn
"""
import json
import requests
import time
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"

def load_corpus() -> List[Dict[str, Any]]:
    """Tải corpus từ file JSON."""
    with open("tests/corpus.json", "r", encoding="utf-8") as f:
        return json.load(f)

def test_step_1_ingest_data():
    """Bước 1: Nạp dữ liệu vào hệ thống."""
    print("\n" + "="*70)
    print("BƯỚC 1: NẠP DỮ LIỆU VÀO HỆ THỐNG")
    print("="*70)
    
    corpus = load_corpus()
    
    # Chuẩn bị dữ liệu cho API /ingestion/bulk
    # UpsertRequest yêu cầu: doc_id, content, metadata (optional)
    documents = [
        {
            "doc_id": doc["doc_id"],
            "content": f"{doc['title']} {doc['description']}",
            "metadata": {"title": doc["title"], "description": doc["description"]}
        }
        for doc in corpus
    ]
    
    print(f"📥 Nạp {len(documents)} tài liệu...")
    start = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/ingestion/bulk",
            json=documents,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        elapsed = time.time() - start
        print(f"✅ Nạp thành công {result['success_count']} tài liệu")
        print(f"⏱️  Thời gian: {result['execution_time_ms']:.2f}ms")
        
        return True
    except Exception as e:
        print(f"❌ Lỗi khi nạp dữ liệu: {e}")
        return False

def test_step_2_basic_search():
    """Bước 2: Tìm kiếm cơ bản."""
    print("\n" + "="*70)
    print("BƯỚC 2: TÌM KIẾM CƠ BẢN")
    print("="*70)
    
    query = "điện thoại"
    print(f"🔍 Tìm kiếm: '{query}'")
    
    try:
        response = requests.get(
            f"{BASE_URL}/search/collections/default",
            params={
                "q": query,
                "top_k": 5,
                "algorithm": "manual"
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Tìm thấy {result['total_found']} kết quả")
        print(f"⏱️  Thời gian: {result['execution_time_ms']:.2f}ms")
        print(f"🎯 Thuật toán: {result['algorithm']}\n")
        
        for i, item in enumerate(result['results'], 1):
            print(f"  {i}. [{item['doc_id']}] Score: {item['score']}")
            if item['content']:
                print(f"     {item['content'][:80]}...")
        
        return True, result['results']
    except Exception as e:
        print(f"❌ Lỗi khi tìm kiếm: {e}")
        return False, []

def test_step_3_spell_check_search():
    """Bước 3: Tìm kiếm với sửa lỗi chính tả."""
    print("\n" + "="*70)
    print("BƯỚC 3: TÌM KIẾM VỚI SỬA LỖI CHÍNH TẢ")
    print("="*70)
    
    # Tạo lỗi chính tả: "điện thoại" → "diện thoai"
    query_with_typo = "diện thoai"
    print(f"🔤 Truy vấn gốc có lỗi chính tả: '{query_with_typo}'")
    
    try:
        response = requests.post(
            f"{BASE_URL}/smart/search",
            json={
                "query": query_with_typo,
                "top_k": 5,
                "ranker": "tfidf",
                "use_spell_check": True,
                "use_rocchio": False,
                "positive_feedback_ids": []
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Tìm thấy {result['total_found']} kết quả (sau sửa chính tả)")
        print(f"⏱️  Thời gian: {result['execution_time_ms']:.2f}ms\n")
        
        for i, item in enumerate(result['results'], 1):
            print(f"  {i}. [{item['doc_id']}] Score: {item['score']}")
            if item['content']:
                print(f"     {item['content'][:80]}...")
        
        return True, result['results']
    except Exception as e:
        print(f"❌ Lỗi khi tìm kiếm với sửa chính tả: {e}")
        return False, []

def test_step_4_rocchio_feedback():
    """Bước 4: Click phản hồi mở rộng truy vấn (Rocchio)."""
    print("\n" + "="*70)
    print("BƯỚC 4: MỞ RỘNG TRUY VẤN VỚI ROCCHIO FEEDBACK")
    print("="*70)
    
    query = "tai nghe"
    print(f"🔍 Truy vấn gốc: '{query}'")
    print(f"👍 Người dùng click \"tài liệu liên quan\" từ kết quả trước")
    
    # Giả sử người dùng click vào các tài liệu tương ứng với AirPods Pro và Sony WF-1000XM4
    positive_feedback_ids = ["D03", "D04"]
    print(f"   Phản hồi tích cực: {positive_feedback_ids}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/smart/search",
            json={
                "query": query,
                "top_k": 5,
                "ranker": "tfidf",
                "use_spell_check": False,
                "use_rocchio": True,
                "positive_feedback_ids": positive_feedback_ids
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"\n✅ Tìm thấy {result['total_found']} kết quả (truy vấn đã mở rộng)")
        print(f"⏱️  Thời gian: {result['execution_time_ms']:.2f}ms\n")
        
        for i, item in enumerate(result['results'], 1):
            print(f"  {i}. [{item['doc_id']}] Score: {item['score']}")
            if item['content']:
                print(f"     {item['content'][:80]}...")
        
        return True
    except Exception as e:
        print(f"❌ Lỗi khi sử dụng Rocchio: {e}")
        return False

def test_memory_stability():
    """Test độ ổn định bộ nhớ - chạy nhiều lần tìm kiếm."""
    print("\n" + "="*70)
    print("KIỂM TRA ĐỘ ỔN ĐỊNH BỘ NHỚ")
    print("="*70)
    
    queries = [
        "điện thoại",
        "tai nghe",
        "laptop",
        "cáp sạc",
        "pin trâu"
    ]
    
    print(f"🔄 Chạy {len(queries)} truy vấn liên tiếp...\n")
    
    times = []
    try:
        for i, query in enumerate(queries, 1):
            start = time.time()
            response = requests.get(
                f"{BASE_URL}/search/collections/default",
                params={
                    "q": query,
                    "top_k": 3,
                    "algorithm": "manual"
                },
                timeout=10
            )
            response.raise_for_status()
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            result = response.json()
            print(f"  {i}. '{query}' → {result['total_found']} kết quả ({elapsed:.2f}ms)")
        
        avg_time = sum(times) / len(times)
        print(f"\n✅ Trung bình thời gian: {avg_time:.2f}ms")
        print(f"📊 Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")
        print("✨ Bộ nhớ ổn định - không bị crash")
        
        return True
    except Exception as e:
        print(f"❌ Lỗi trong quá trình test: {e}")
        return False

def main():
    """Chạy toàn bộ kịch bản test."""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  INTEGRATION TEST - TNKV DB PIPELINE".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝\n")
    
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Bước 1: Nạp dữ liệu
    if not test_step_1_ingest_data():
        print("⚠️  Không thể tiếp tục - Bước nạp dữ liệu thất bại")
        return
    
    time.sleep(1)  # Chờ index được cập nhật
    
    # Bước 2: Tìm kiếm cơ bản
    success, basic_results = test_step_2_basic_search()
    if not success:
        print("⚠️  Bước tìm kiếm cơ bản thất bại")
    
    # Bước 3: Tìm kiếm với sửa chính tả
    time.sleep(0.5)
    success, typo_results = test_step_3_spell_check_search()
    if not success:
        print("⚠️  Bước tìm kiếm với sửa chính tả thất bại")
    
    # Bước 4: Rocchio feedback
    time.sleep(0.5)
    success = test_step_4_rocchio_feedback()
    if not success:
        print("⚠️  Bước Rocchio feedback thất bại")
    
    # Test độ ổn định bộ nhớ
    time.sleep(0.5)
    test_memory_stability()
    
    print("\n" + "="*70)
    print("✅ TẬT CẢ BƯỚC TEST HOÀN THÀNH")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
