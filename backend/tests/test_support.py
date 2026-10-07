"""Central, deterministic configuration for the backend test suite."""
import os
import tempfile
from pathlib import Path


TEST_DATABASE = Path(tempfile.gettempdir()) / "acxiomcrm-test-suite.db"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DATABASE.as_posix()}"
os.environ["AUTH_SECRET_KEY"] = "unit-test-secret-not-for-production-123456"
os.environ["COOKIE_SECURE"] = "false"
os.environ["LOCKOUT_MAX_ATTEMPTS"] = "2"
os.environ["LOCKOUT_DURATION_MINUTES"] = "15"
