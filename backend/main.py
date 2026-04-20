"""
FastAPI main application.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models.database import init_db
from backend.api import workflow, history, execute, plugins

# Initialize database
init_db()

app = FastAPI(
    title="Batch Workflow API",
    description="Web management interface for Batch Workflow Framework",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflow.router)
app.include_router(history.router)
app.include_router(execute.router)
app.include_router(plugins.router)


@app.get("/")
def root():
    return {
        "name": "Batch Workflow API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
