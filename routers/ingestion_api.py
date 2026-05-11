from fastapi import APIRouter
from typing import List
import time

from core.contracts import UpsertRequest
from core.ingestion.pipeline import process_and_ingest
from pydantic import BaseModel

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

class IngestionResponse(BaseModel):
    success_count: int
    execution_time_ms: float
    message: str

@router.post("/bulk", response_model=IngestionResponse)
def bulk_ingest(documents: List[UpsertRequest]):
    start_time = time.time()
    success_count = process_and_ingest(documents)
    execution_time = (time.time() - start_time) * 1000  # Đổi ra milliseconds
    return IngestionResponse(
        success_count=success_count,
        execution_time_ms=execution_time,
        message="Dữ liệu đã được nạp và lập chỉ mục thành công."
    )

@router.delete("/clear", response_model=IngestionResponse)
def clear_database():
    start_time = time.time()
    
    # Reset in-memory structures
    from core.ingestion.indexer import global_index
    global_index.clear()
    
    # Remove files from disk (optional but good for completely dropping DB)
    import os
    storage_dir = "storage"
    if os.path.exists(storage_dir):
        for filename in os.listdir(storage_dir):
            file_path = os.path.join(storage_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                pass
                
    execution_time = (time.time() - start_time) * 1000
    return IngestionResponse(
        success_count=0,
        execution_time_ms=execution_time,
        message="Toàn bộ Database đã được dọn sạch thành công."
    )
