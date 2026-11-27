"""Run the API tests against the synthetic storylines in a throwaway database.

The tests rely on named storyline patients (Aarav Mehta, Zoya Farooqui), so they pin
DATA_SOURCE to "synthetic" and never touch the developer's real seeded database.
"""

import os
import tempfile

_db_dir = tempfile.mkdtemp(prefix="medvault-tests-")
os.environ["DATA_SOURCE"] = "synthetic"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
