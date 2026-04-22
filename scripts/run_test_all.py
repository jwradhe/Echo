from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlunparse


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


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _replace_url_port(base_url: str, port: int) -> str:
    parsed = urlparse(base_url)
    hostname = parsed.hostname or "127.0.0.1"
    scheme = parsed.scheme or "http"
    netloc = f"{hostname}:{port}"
    return urlunparse((scheme, netloc, parsed.path or "", parsed.params, parsed.query, parsed.fragment))


def _run(cmd: list[str], env: dict[str, str] | None = None) -> int:
    result = subprocess.run(cmd, cwd=ROOT, check=False, env=env)
    return result.returncode


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
HEALTH_URL = f"{BASE_URL}/dashboard"
NPM_CMD = "npm.cmd" if os.name == "nt" else "npm"

server_process = None
server_started = False
test_base_url = BASE_URL
test_health_url = HEALTH_URL
parsed_base_url = urlparse(BASE_URL)
base_host = parsed_base_url.hostname or "127.0.0.1"
base_port = parsed_base_url.port or 5001
reuse_existing = os.environ.get("TEST_USE_EXISTING_SERVER", "").lower() in {"1", "true", "yes"}

try:
    if not (reuse_existing and _wait_for_server(HEALTH_URL, timeout=2)):
        port = base_port
        if _wait_for_server(HEALTH_URL, timeout=2):
            port = _find_free_port(base_host)
            test_base_url = _replace_url_port(BASE_URL, port)
            test_health_url = f"{test_base_url}/dashboard"

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
                str(port),
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        server_started = True

        if not _wait_for_server(test_health_url, timeout=30):
            raise RuntimeError("Flask server did not start for test:all")

    exit_code = _run([sys.executable, "-m", "pytest", "tests/api"])
    if exit_code != 0:
        sys.exit(exit_code)

    exit_code = _run(
        [NPM_CMD, "run", "api-test", "--", "--env-var", f"baseUrl={test_base_url}"],
        env=os.environ.copy(),
    )
    if exit_code != 0:
        sys.exit(exit_code)

    e2e_env = os.environ.copy()
    e2e_env["BASE_URL"] = test_base_url
    e2e_env["E2E_USE_EXISTING_SERVER"] = "1"

    exit_code = _run([sys.executable, "-m", "pytest", "tests/e2e"], env=e2e_env)
    if exit_code != 0:
        sys.exit(exit_code)
finally:
    if server_process and server_started:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except Exception:
            server_process.kill()
