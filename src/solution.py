"""F1 capstone solution entry point for Suryaa Sales Investigation.

This module provides the main() function that starts the FastAPI application
exposing the POST /ask endpoint required by the assignment contract.

Usage:
    python -m src.solution
"""
import os
import uvicorn
from src.app import app


def main() -> None:
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()