# Vercel Serverless Function entrypoint
# Routes all incoming web requests to the FastAPI application instance
import sys
import os
from pathlib import Path

# Add project root to sys.path so 'backend' package imports resolve on Vercel
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app
