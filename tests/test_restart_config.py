import os
import subprocess
import sys
import unittest
from unittest.mock import patch
from tests import test_workflow
from backend.config import settings, Settings
from pydantic import ValidationError
from backend.database import initialize, connection
from backend.repositories import complaints as repo


class RestartConfigTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_database_survives_separate_interpreter_processes(self):
        env = {**os.environ, "DATABASE_PATH":settings.database_path, "USE_MOCK_AGENTS":"true"}
        first = subprocess.run([sys.executable,"-B","-c",
            "from backend.database import initialize; from backend.repositories.complaints import create; initialize(); print(create('Synthetic persisted restart complaint',None)[0]['tracking_id'])"],
            env=env, capture_output=True, text=True, check=True)
        tracking = first.stdout.strip()
        second = subprocess.run([sys.executable,"-B","-c",
            "from backend.database import initialize; from backend.repositories.complaints import track; import sys; initialize(); print(track(sys.argv[1])['status'])", tracking],
            env=env, capture_output=True, text=True, check=True)
        self.assertEqual(second.stdout.strip(), "submitted")

    def test_configuration_bounds_and_sdk_retry_options(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, jwt_secret="test", provider_max_retries=99)
        from google.genai import types
        options = types.HttpOptions(timeout=20000, retry_options=types.HttpRetryOptions(attempts=2))
        self.assertEqual(options.retry_options.attempts, 2)

    def test_additive_migration_keeps_existing_case_and_idempotency(self):
        case,_ = repo.create("Synthetic existing record before migration", None, "migration-idempotency")
        with connection() as db:
            for column in ["clarification_answers", "review_urgency", "area", "processing_mode"]:
                db.execute("ALTER TABLE complaints DROP COLUMN " + column)
            db.execute("PRAGMA user_version=1")
            db.execute("UPDATE complaints SET request_hash='legacy-fingerprint'")
        initialize()
        retained = repo.get(case["id"])
        self.assertEqual(retained["text"], case["text"])
        self.assertEqual(retained["processing_mode"], "unknown")
        repeated,created = repo.create(case["text"], None, "migration-idempotency")
        self.assertFalse(created)
        self.assertEqual(repeated["id"], case["id"])
