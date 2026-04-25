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
    # Em produção, use HOST=127.0.0.1 e coloque um reverse proxy (nginx/caddy) na frente.
    # O valor padrão 0.0.0.0 é aceitável apenas para desenvolvimento local.
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(
        "api.routes:app",
        host=host,
        port=8000,
        reload=os.getenv("ENV") == "development"
    )