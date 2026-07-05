from fastapi import FastAPI

app = FastAPI(title="Tablr Orders Service")


@app.get("/health")
def health():
    return {"service": "orders", "status": "ok"}
