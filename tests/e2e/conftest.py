import os
import subprocess
import sys
import time
import urllib.request
import pytest


def _wait_for_server(url: str, timeout: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session", autouse=True)
def e2e_server():
    """Ensure the Flask app is running for E2E tests."""
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    health_url = f"{base_url}/dashboard"

    # If server is already running (e.g., via start-server-and-test), use it.
    if _wait_for_server(health_url, timeout=2):
        yield
        return

    env = os.environ.copy()
    env.setdefault("FLASK_ENV", "testing")

    process = subprocess.Popen(
        [sys.executable, "-m", "app"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.getcwd(),
    )

    try:
        if not _wait_for_server(health_url, timeout=30):
            raise RuntimeError("Flask server did not start for E2E tests.")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
