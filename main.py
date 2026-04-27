from fastapi import FastAPI
from routers import ingestion_api, search_api, smart_api

app = FastAPI(
    title="TNKV DB", 
    description="The Lightweight Sparse Vector Database for IR Purists",
    version="1.0.0"
)

# Đăng ký các module routers
app.include_router(ingestion_api.router)
app.include_router(search_api.router)
app.include_router(smart_api.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to TNKV DB API! Access /docs for Swagger UI."}
