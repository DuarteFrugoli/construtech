"""
Server module for running the house plan generator API.
"""
import os
import uvicorn
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from api.routes import app

if __name__ == "__main__":
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV") == "development"
    )