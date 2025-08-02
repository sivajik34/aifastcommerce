from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import logging

from assistant.routes import router as assistant_router

from utils.log import Logger

logger = Logger(name="main", log_file="Logs/app.log", level=logging.DEBUG)

# FastAPI app with metadata
app = FastAPI(
    title="Magento AI Commerce Assistant",
    description="LangGraph-powered assistant backend for Magento-based ecommerce automation.",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend domain in production (e.g., ["https://yourdomain.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include assistant module routes
app.include_router(assistant_router)


@app.get("/health", tags=["Health"], response_class=JSONResponse)
def health_check() -> dict:
    """
    Health check endpoint to confirm backend status.
    """
    return {
        "status": "Magento AI Commerce backend is running 🚀",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }




