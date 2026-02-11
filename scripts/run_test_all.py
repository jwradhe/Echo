from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


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


def _run(cmd: list[str]) -> int:
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    return result.returncode


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
HEALTH_URL = f"{BASE_URL}/dashboard"
NPM_CMD = "npm.cmd" if os.name == "nt" else "npm"

server_process = None
server_started = False

try:
    if not _wait_for_server(HEALTH_URL, timeout=2):
        env = os.environ.copy()
        env.setdefault("FLASK_ENV", "testing")
        env.setdefault("MYSQL_HOST", "localhost")
        env.setdefault("MYSQL_PORT", "3306")
        env.setdefault("MYSQL_USER", "root")
        env.setdefault("MYSQL_PASSWORD", "changemeCHANGEME123")
        env.setdefault("MYSQL_DATABASE", "EchoDB")

        server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "flask",
                "--app",
                "app:create_app",
                "run",
                "--port",
                "5001",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        server_started = True

        if not _wait_for_server(HEALTH_URL, timeout=30):
            raise RuntimeError("Flask server did not start for test:all")

    exit_code = _run([sys.executable, "-m", "pytest", "tests/api"])
    if exit_code != 0:
        sys.exit(exit_code)

    exit_code = _run([NPM_CMD, "run", "api-test"])
    if exit_code != 0:
        sys.exit(exit_code)

    exit_code = _run([sys.executable, "-m", "pytest", "tests/e2e"])
    if exit_code != 0:
        sys.exit(exit_code)
finally:
    if server_process and server_started:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except Exception:
            server_process.kill()
