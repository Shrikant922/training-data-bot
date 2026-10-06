"""
Launcher script for Training Data Bot Studio.
Runs the FastAPI server with Uvicorn.
"""

import sys
import os
import webbrowser
from pathlib import Path
import uvicorn

def main():
    """Run the FastAPI web server."""
    port = int(os.environ.get("PORT", 8000))
    host = "127.0.0.1"
    
    print("=" * 60)
    print("  Training Data Bot Studio")
    print(f"  Local Server: http://localhost:{port}")
    print("=" * 60)
    
    uvicorn.run("web.server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
