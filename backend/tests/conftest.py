"""Test configuration: isolated temp database, deterministic offline engine.

Real models are disabled here so the suite runs in seconds; they are tested
separately in test_models.py (run with:  pytest -m models).
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="mindbridge-test-")
os.environ["MINDBRIDGE_DATA_DIR"] = _tmp
os.environ["MINDBRIDGE_DB"] = os.path.join(_tmp, "test.db")
os.environ.setdefault("MINDBRIDGE_ENABLE_MODELS", "0")
os.environ["LLM_PROVIDER"] = "offline"


def pytest_configure(config):
    config.addinivalue_line("markers", "models: tests that load the real AI models (slow)")
