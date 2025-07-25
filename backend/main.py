from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "Welcome to the Tax API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Tax API is running"}
