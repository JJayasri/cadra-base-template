"""F1 capstone solution entry point for Suryaa Sales Investigation.

This module provides the main() function that starts the FastAPI application
exposing the POST /ask endpoint required by the assignment contract.

Usage:
    python -m src.solution
"""
import uvicorn
from src.app import app


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()