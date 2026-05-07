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
</style>
""", unsafe_allow_html=True)

st.title("✨ TNKV-DB Smart Search")
st.markdown("Hệ thống Vector Database thưa tích hợp Auto-correct & Rocchio Expansion.")

if 'relevant_docs' not in st.session_state:
    st.session_state.relevant_docs = set()

tab_search, tab_ingest = st.tabs(["🔍 Tìm Kiếm", "📂 Nạp Dữ Liệu"])

with tab_search:
    col_search, col_settings = st.columns([3, 1])
    
    with col_search:
        query = st.text_input("Nhập từ khóa tìm kiếm...", placeholder="Ví dụ: máy học, trí tuệ nhân tạo...", key="query_input")
        
    with col_settings:
        st.markdown("<br>", unsafe_allow_html=True) # padding
        use_spellcheck = st.checkbox("Tự sửa chính tả", value=True)
        use_rocchio = st.checkbox("Bật Rocchio", value=True)

    if st.button("Tìm kiếm ngay 🚀", use_container_width=True):
        if not query:
            st.warning("Vui lòng nhập từ khóa!")
        else:
            with st.spinner("Đang tìm kiếm..."):
                payload = {
                    "query": query,
                    "top_k": 10,
                    "use_spell_check": use_spellcheck,
                    "use_rocchio": use_rocchio,
                    "positive_feedback_ids": list(st.session_state.relevant_docs) if use_rocchio else []
                }
                
                try:
                    res = requests.post(f"{API_URL}/smart/search", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        
                        # Thông báo sửa lỗi chính tả
                        if data.get("corrected_query") and data["corrected_query"] != query:
                            st.info(f"💡 Đã sửa lỗi chính tả: **{query}** ➔ **{data['corrected_query']}**")
                            
                        # Hiển thị thống kê
                        st.success(f"Tìm thấy {data['total_found']} kết quả trong {data['execution_time_ms']} ms.")
                        
                        # Hiển thị kết quả
                        for item in data['results']:
                            # Kiểm tra xem doc này có đang được đánh dấu phù hợp không
                            is_relevant = item['doc_id'] in st.session_state.relevant_docs
                            
                            st.markdown(f"""
                            <div class="result-card">
                                <h4 style="margin-top: 0; color: #f8fafc;">
                                    📄 {item['doc_id']} 
                                    <span class="score-badge">Score: {item['score']}</span>
                                </h4>
                                <p style="color: #cbd5e1; margin-bottom: 0;">{item['content']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Nút đánh dấu Rocchio Feedback
                            if use_rocchio:
                                if st.checkbox(f"✅ Đánh dấu là Phù hợp", value=is_relevant, key=f"check_{item['doc_id']}"):
                                    st.session_state.relevant_docs.add(item['doc_id'])
                                else:
                                    st.session_state.relevant_docs.discard(item['doc_id'])
                                    
                    else:
                        st.error(f"Lỗi từ server: {res.text}")
                except Exception as e:
                    st.error(f"Không thể kết nối đến server API. Hãy chắc chắn uvicorn đang chạy! Lỗi: {e}")

with tab_ingest:
    st.subheader("Thêm tài liệu mới vào Database")
    
    st.markdown("##### 1. Nạp thủ công")
    col1, col2 = st.columns([1, 3])
    with col1:
        doc_id = st.text_input("Mã tài liệu (Doc ID)")
    with col2:
        doc_content = st.text_area("Nội dung tài liệu")
        
    if st.button("Nạp dữ liệu 💾"):
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
    
    st.markdown("##### 2. Nạp hàng loạt (Upload File JSON)")
    st.info("Định dạng file: `[{\"doc_id\": \"1\", \"content\": \"...\", \"metadata\": {}}]`")
    uploaded_file = st.file_uploader("Chọn file dữ liệu (.json)", type=["json"])
    
    if uploaded_file is not None:
        try:
            import json
            data = json.load(uploaded_file)
            st.write(f"📄 Đã đọc được **{len(data)}** tài liệu từ file.")
            
            if st.button("Nạp toàn bộ file JSON 🚀", type="primary"):
                with st.spinner("Đang nạp dữ liệu..."):
                    try:
                        res = requests.post(f"{API_URL}/ingestion/bulk", json=data)
                        if res.status_code == 200:
                            st.success(f"Nạp thành công {len(data)} tài liệu!")
                            st.balloons()
                        else:
                            st.error(f"Lỗi từ server: {res.text}")
                    except Exception as e:
                        st.error("Không thể kết nối API.")
        except Exception as e:
            st.error(f"File JSON không hợp lệ! Vui lòng kiểm tra lại cấu trúc file. Lỗi: {e}")
