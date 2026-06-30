import os
import tempfile
from pathlib import Path


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="chess-coach-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATA_DIR / 'test.db'}"
