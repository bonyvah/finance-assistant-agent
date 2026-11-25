from fastapi import FastAPI

from app.routers import invoices

app = FastAPI()
app.include_router(invoices.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
