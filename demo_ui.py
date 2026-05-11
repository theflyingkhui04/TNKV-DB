import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="TNKV-DB Smart Search", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Làm đẹp nút bấm với Gradient và Hover effect */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 8px;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(168, 85, 247, 0.4);
        color: white;
    }
    
    /* Thẻ kết quả tìm kiếm (Glassmorphism mờ) */
    .result-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        transition: all 0.2s ease-in-out;
    }
    .result-card:hover {
        transform: translateY(-3px);
        border-color: rgba(168, 85, 247, 0.5);
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    
    .score-badge {
        background: rgba(168, 85, 247, 0.2);
        color: #d8b4fe;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    mark {
        background: rgba(168, 85, 247, 0.3);
        color: #f8fafc;
        padding: 0 4px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("TNKV-DB Smart Search")
st.markdown("Hệ thống Vector Database thưa tích hợp Auto-correct & Rocchio Expansion.")

if 'relevant_docs' not in st.session_state:
    st.session_state.relevant_docs = set()

tab_search, tab_ingest, tab_debug = st.tabs(["Tìm Kiếm", "Nạp Dữ Liệu", "Khám Phá DB"])

with tab_search:
    col_search, col_settings = st.columns([3, 1])
    
    with col_search:
        query = st.text_input("Nhập từ khóa tìm kiếm...", placeholder="Ví dụ: máy học, trí tuệ nhân tạo...", key="query_input")
        
    with col_settings:
        st.markdown("<br>", unsafe_allow_html=True) # padding
        ranker_algo = st.selectbox("Thuật toán", options=["TF-IDF", "L2-norm TF-IDF", "BM25", "BM25+"], index=0)
        use_spellcheck = st.checkbox("Tự sửa chính tả", value=True)
        use_rocchio = st.checkbox("Bật Rocchio", value=True)

    # Hàm callback cho checkbox
    def toggle_relevance(doc_id):
        if doc_id in st.session_state.relevant_docs:
            st.session_state.relevant_docs.discard(doc_id)
        else:
            st.session_state.relevant_docs.add(doc_id)

    if st.button("Tìm kiếm ngay", use_container_width=True):
        if not query:
            st.warning("Vui lòng nhập từ khóa!")
        else:
            with st.spinner("Đang tìm kiếm..."):
                ranker_map = {
                    "TF-IDF": "manual",
                    "L2-norm TF-IDF": "sklearn",
                    "BM25": "bm25",
                    "BM25+": "bm25+"
                }
                payload = {
                    "query": query,
                    "top_k": 10,
                    "ranker": ranker_map[ranker_algo],
                    "use_spell_check": use_spellcheck,
                    "use_rocchio": use_rocchio,
                    "positive_feedback_ids": list(st.session_state.relevant_docs) if use_rocchio else []
                }
                
                try:
                    res = requests.post(f"{API_URL}/smart/search", json=payload)
                    if res.status_code == 200:
                        st.session_state.search_results = res.json()
                        st.session_state.last_query = query
                    else:
                        st.error(f"Lỗi từ server: {res.text}")
                except Exception as e:
                    st.error(f"Không thể kết nối đến server API. Hãy chắc chắn uvicorn đang chạy! Lỗi: {e}")

    # Hiển thị kết quả tìm kiếm độc lập với nút bấm
    if "search_results" in st.session_state:
        data = st.session_state.search_results
        last_query = st.session_state.last_query
        
        # Thông báo sửa lỗi chính tả
        if data.get("corrected_query") and data["corrected_query"] != last_query:
            st.info(f"Đã sửa lỗi chính tả: **{last_query}** ➔ **{data['corrected_query']}**")
            
        # Hiển thị thống kê
        st.success(f"Tìm thấy {data['total_found']} kết quả trong {data['execution_time_ms']} ms.")
        
        # Hiển thị kết quả
        for item in data['results']:
            display_text = item.get('snippet') or item.get('content', '')
            st.markdown(f"""
            <div class="result-card">
                <h4 style="margin-top: 0; color: #f8fafc;">
                    {item['doc_id']} 
                    <span class="score-badge">Score: {item['score']}</span>
                </h4>
                <p style="color: #cbd5e1; margin-bottom: 0;">{display_text}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Nút đánh dấu Rocchio Feedback
            if use_rocchio:
                st.checkbox(
                    "Đánh dấu là Phù hợp", 
                    value=(item['doc_id'] in st.session_state.relevant_docs), 
                    key=f"check_{item['doc_id']}",
                    on_change=toggle_relevance,
                    args=(item['doc_id'],)
                )

with tab_ingest:
    st.subheader("Thêm tài liệu mới vào Database")
    
    st.markdown("##### 1. Nạp thủ công")
    col1, col2 = st.columns([1, 3])
    with col1:
        doc_id = st.text_input("Mã tài liệu (Doc ID)")
    with col2:
        doc_content = st.text_area("Nội dung tài liệu")
        
    if st.button("Nạp dữ liệu"):
        if doc_id and doc_content:
            payload = [{"doc_id": doc_id, "content": doc_content, "metadata": {}}]
            try:
                res = requests.post(f"{API_URL}/ingestion/bulk", json=payload)
                if res.status_code == 200:
                    st.success("Nạp thành công!")
                    st.balloons()
                else:
                    st.error("Có lỗi xảy ra!")
            except Exception as e:
                st.error("Không thể kết nối API.")
        else:
            st.warning("Vui lòng điền đủ ID và Nội dung!")
            
    st.divider()
    
    st.markdown("##### 2. Nạp hàng loạt (Hỗ trợ JSON / JSONL)")
    st.info("Hệ thống sẽ đọc các cột trong file và cho phép bạn tự chọn trường dữ liệu thích hợp.")
    uploaded_file = st.file_uploader("Chọn file dữ liệu (.json, .jsonl)", type=["json", "jsonl"])
    
    if uploaded_file is not None:
        try:
            import json
            records = []
            
            # Đọc JSONL hoặc JSON
            if uploaded_file.name.endswith('.jsonl'):
                for line in uploaded_file:
                    if line.strip():
                        records.append(json.loads(line))
            else:
                raw_data = json.load(uploaded_file)
                if isinstance(raw_data, dict):
                    # Tìm xem có key nào chứa list of dicts không
                    for k, v in raw_data.items():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            records = v
                            break
                    else:
                        records = [raw_data]
                elif isinstance(raw_data, list):
                    records = raw_data
                    
            if not records or not isinstance(records, list):
                st.error("Không tìm thấy danh sách dữ liệu hợp lệ trong file.")
            else:
                first = records[0]
                if not isinstance(first, dict):
                    st.error("Định dạng không hỗ trợ (Cần Object/Dict).")
                else:
                    st.success(f"Đã tải thành công **{len(records)}** tài liệu. Vui lòng ánh xạ dữ liệu:")
                    
                    keys = list(first.keys())
                    keys.insert(0, "-- Tự động tạo ID ảo --")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        # Thử đoán ID để pre-select
                        id_idx = 0
                        id_cands = ['doc_id', 'id', '_id', 'uuid', 'key', 'item_id', 'review_id']
                        match_id = next((c for c in id_cands if c in first), None)
                        if match_id: id_idx = keys.index(match_id)
                        selected_id_key = st.selectbox("Chọn cột làm Doc ID:", options=keys, index=id_idx)
                        
                    with col2:
                        # Thử đoán Content để pre-select
                        content_keys = [k for k in first.keys()]
                        content_idx = 0
                        content_cands = ['content', 'text', 'body', 'review', 'comment', 'description', 'title']
                        match_c = next((c for c in content_cands if c in first), None)
                        if match_c: content_idx = content_keys.index(match_c)
                        selected_content_key = st.selectbox("Chọn cột làm Nội dung (Content):", options=content_keys, index=content_idx)
                    
                    if st.button("Nạp toàn bộ dữ liệu", type="primary"):
                        with st.spinner("Đang chuyển đổi dữ liệu và nạp..."):
                            try:
                                payload = []
                                for i, r in enumerate(records):
                                    d_id = str(r.get(selected_id_key)) if selected_id_key != "-- Tự động tạo ID ảo --" else str(i)
                                    c_text = str(r.get(selected_content_key, ""))
                                    
                                    # Lấy metadata
                                    exclude_keys = [selected_content_key]
                                    if selected_id_key != "-- Tự động tạo ID ảo --":
                                        exclude_keys.append(selected_id_key)
                                    meta = {k: v for k, v in r.items() if k not in exclude_keys}
                                    
                                    payload.append({
                                        "doc_id": d_id,
                                        "content": c_text,
                                        "metadata": meta
                                    })
                                res = requests.post(f"{API_URL}/ingestion/bulk", json=payload)
                                if res.status_code == 200:
                                    st.success(f"Nạp thành công {len(records)} tài liệu!")
                                    st.balloons()
                                else:
                                    st.error(f"Lỗi từ server: {res.text}")
                            except Exception as e:
                                st.error(f"Không thể kết nối API. Lỗi: {e}")
        except Exception as e:
            st.error(f"File tải lên bị lỗi hoặc sai định dạng. Lỗi chi tiết: {e}")

    st.divider()
    
    st.markdown("##### 3. Vùng Nguy Hiểm (Danger Zone)")
    st.warning("Hành động này sẽ xoá TOÀN BỘ dữ liệu và Inverted Index trong bộ nhớ và ổ cứng. KHÔNG THỂ KHÔI PHỤC!")
    
    col_empty, col_btn = st.columns([3, 1])
    with col_btn:
        if st.button("Xóa sạch Database", type="secondary"):
            with st.spinner("Đang xóa dữ liệu..."):
                try:
                    res = requests.delete(f"{API_URL}/ingestion/clear")
                    if res.status_code == 200:
                        st.success("Đã xóa sạch Database!")
                        st.session_state.relevant_docs.clear()
                    else:
                        st.error("Có lỗi xảy ra khi xóa.")
                except Exception as e:
                    st.error("Không thể kết nối API.")

with tab_debug:
    st.subheader("Khám phá Kiến trúc Inverted Index")
    st.markdown("Tại đây bạn có thể 'nhìn xuyên thấu' vào bên trong Database để xem dữ liệu thực sự được tổ chức như thế nào.")
    
    if st.button("Làm mới Thống kê", key="refresh_stats"):
        pass
        
    try:
        res = requests.get(f"{API_URL}/search/debug/stats")
        if res.status_code == 200:
            stats = res.json()
            col1, col2 = st.columns(2)
            col1.metric("Tổng số Tài liệu (Documents)", stats['total_documents'])
            col2.metric("Kích thước Từ vựng (Vocabulary Size)", stats['vocabulary_size'])
            
            with st.expander("Xem thử 50 từ vựng đầu tiên trong Dictionary"):
                st.write(stats['vocabulary_sample'])
        else:
            st.error("Chưa có dữ liệu thống kê.")
    except Exception:
        st.warning("Vui lòng khởi động server API.")

    st.divider()
    st.markdown("##### Tra cứu Postings List")
    st.info("Nhập một từ khóa (vd: 'điện', 'thoại', 'ngon') để xem danh sách Postings của nó.")
    
    debug_term = st.text_input("Từ khóa cần tra cứu")
    if st.button("Tra cứu Postings"):
        if debug_term:
            try:
                res = requests.get(f"{API_URL}/search/debug/postings/{debug_term}")
                if res.status_code == 200:
                    data = res.json()
                    st.success(f"Tìm thấy **{data['document_frequency']}** tài liệu chứa từ '{data['term']}'")
                    
                    if data.get('disk_storage'):
                        st.code(f"Lưu trữ trên ổ đĩa (Block Offset):\n- Offset: {data['disk_storage']['offset']} byte\n- Kích thước nén: {data['disk_storage']['length_bytes']} byte", language="yaml")
                    
                    st.write("Chi tiết Postings List:")
                    st.json(data['postings'])
                else:
                    st.error(f"Từ khóa '{debug_term}' không tồn tại trong từ điển (Dictionary)!")
            except Exception:
                st.error("Lỗi kết nối API.")
        else:
            st.warning("Vui lòng nhập từ khóa.")
