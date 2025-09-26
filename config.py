import os


WPP_SECRET_KEY = os.getenv("WPP_SECRET_KEY", "your_token_here")
WPP_HOST_PORT = os.getenv("WPP_HOST_PORT", "http://localhost:8081")

try:
    from local_config import * # type: ignore
except ImportError:
    print("No local_config.py found, using default settings.")
