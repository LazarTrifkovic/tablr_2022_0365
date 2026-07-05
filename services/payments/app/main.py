from fastapi import FastAPI

app = FastAPI(title="Tablr Payments Service")


@app.get("/health")
def health():
    return {"service": "payments", "status": "ok"}
