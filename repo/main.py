import os
import sys
from pathlib import Path

# Add the current directory to sys.path so 'core' and 'plugins' are found
# This MUST be done before importing core or plugins
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import logging
import argparse
import uvicorn

from core.app import create_app

# Optional Import Tracing (Stufe 3 Optimization)
if os.environ.get("SHERATAN_IMPORT_TRACE") == "1":
    try:
        from tools.import_trace import install_import_tracer
        install_import_tracer()
    except ImportError:
        pass

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

def main():
    parser = argparse.ArgumentParser(description="Sheratan Core Evolution")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8001)), help="Port to run on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("main")
    logger.info(f"Starting Sheratan Core Evolution on {args.host}:{args.port}")

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
