"""Entry point for Cloudflare Redirect Manager.
Delegates directly to src.main:main().
Allows running directly from root directory with:
    py main.py
    python main.py
"""

import sys
import os

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
