from fastapi import FastAPI

app = FastAPI(title="Tablr Menu Service")


@app.get("/health")
def health():
    return {"service": "menu", "status": "ok"}
