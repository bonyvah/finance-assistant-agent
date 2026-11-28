from fastapi import FastAPI

from app.routers import chat, invoices

app = FastAPI()
app.include_router(invoices.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
