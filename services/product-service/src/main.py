from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Product Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "ok", "service": "product-service"}

# TODO: add routers
# from .routers import products
# app.include_router(products.router, prefix="/api/products", tags=["products"])
