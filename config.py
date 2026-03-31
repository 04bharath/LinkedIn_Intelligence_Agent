import os

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

GOOGLE_CREDS_FILE = "creds.json"
GOOGLE_SHEET_NAME = "LinkedIn Jobs"

LYZR_API_KEY = os.getenv("LYZR_API_KEY", "dummy")
