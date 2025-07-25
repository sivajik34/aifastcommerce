from fastapi import FastAPI
from modules.assistant.routes import router as assistant_router

app = FastAPI()

app.include_router(assistant_router)


@app.get("/health")
def health_check():
    return {"status": "Magento AI Commerce backend is running 🚀"}
