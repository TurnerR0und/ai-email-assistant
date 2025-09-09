"""Test configuration to ensure project root is importable.

Adds the repository root to sys.path so `import app` works
regardless of the working directory pytest uses in CI.
"""
import os
import sys
from pathlib import Path

# Resolve repo root (parent of tests/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure default env flags for CI if not set
os.environ.setdefault("APP_MOCK_AI", "1")
