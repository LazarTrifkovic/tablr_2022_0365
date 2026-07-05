from fastapi import FastAPI

app = FastAPI(title="Tablr Auth Service")


@app.get("/health")
def health():
    return {"service": "auth", "status": "ok"}
