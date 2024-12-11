"""
Simulate running uvicorn to start the FastAPI server.

Usage:
- Run from the root directory.
- To start in development mode: `python run.py --dev`
- To start in production mode: `python run.py --prod`
- To start in testing mode: `python run.py --test`
"""

import argparse
import os
from dotenv import load_dotenv
import uvicorn


def run_server():
    """
    Start FastAPI server in different modes.

    Modes:
    - --prod: Loads .env.prod for production.
    - --test: Loads .env.test for testing.
    - --dev: Loads .env.dev for development.

    Environment Variables:
    - PORT: Server port.
    - RELOAD: Enable/disable auto-reload in development.
    """
    parser = argparse.ArgumentParser(description="Run the server in different modes.")
    parser.add_argument(
        "--prod", action="store_true", help="Run the server in production mode."
    )
    parser.add_argument(
        "--test", action="store_true", help="Run the server in test mode."
    )
    parser.add_argument(
        "--dev", action="store_true", help="Run the server in development mode."
    )

    args = parser.parse_args()

    # 讀取環境變數
    if args.prod:
        load_dotenv("env/.env.prod")
    elif args.test:
        load_dotenv("env/.env.test")
    else:
        load_dotenv("env/.env.dev")

    # 執行指令
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT")),
        reload=bool(os.getenv("RELOAD")),
        reload_dirs="app/",
        timeout_graceful_shutdown=5,
    )


if __name__ == "__main__":
    run_server()
