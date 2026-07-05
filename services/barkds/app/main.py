from fastapi import FastAPI

app = FastAPI(title="Tablr Barkds Service")


@app.get("/health")
def health():
    return {"service": "barkds", "status": "ok"}
