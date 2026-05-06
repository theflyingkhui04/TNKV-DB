from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers import ingestion_api, search_api, smart_api
from core.ingestion.indexer import global_index

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Đang khởi động TNKV DB...")
    print("Đang nạp dữ liệu Inverted Index từ ổ cứng lên RAM...")
    global_index.load_from_disk("storage")
    print(f"Đã tải thành công {global_index.total_documents} tài liệu vào bộ nhớ.")
    
    yield
    
    # --- Sự kiện Shutdown ---
    print("Đang tắt TNKV DB. Đang lưu trạng thái cuối cùng xuống đĩa...")
    global_index.save_to_disk("storage")
    print("Đã lưu thành công.")

app = FastAPI(
    title="TNKV DB", 
    description="Vector Database thưa do nhóm của Khôi, Nhật, Tùng làm trong môn IR",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(ingestion_api.router)
app.include_router(search_api.router)
app.include_router(smart_api.router)


@app.get("/")
def read_root():
    return {"message": "Xin chào!"}
