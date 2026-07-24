"""
Test configuration: points the app at a throwaway SQLite database
*before* backend.app.config is imported anywhere, so tests never touch
real chat history.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "data" / "test_saamai.db"
os.environ["SAAMAI_DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()
