import os
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlparse, urlunparse
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


@pytest.fixture(scope="session", autouse=True)
def e2e_server():
    """Ensure the Flask app is running for E2E tests."""
    original_base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    base_url = original_base_url
    health_url = f"{base_url}/dashboard"
    parsed_base_url = urlparse(base_url)
    host = parsed_base_url.hostname or "127.0.0.1"
    port = parsed_base_url.port or 5001
    reuse_existing = os.environ.get("E2E_USE_EXISTING_SERVER", "").lower() in {"1", "true", "yes"}

    if reuse_existing and _wait_for_server(health_url, timeout=2):
        yield
        return

    if not reuse_existing and _wait_for_server(health_url, timeout=2):
        port = _find_free_port(host)
        base_url = _replace_url_port(base_url, port)
        health_url = f"{base_url}/dashboard"
        os.environ["BASE_URL"] = base_url

    env = os.environ.copy()
    env.setdefault("FLASK_ENV", "testing")
    env.setdefault("MYSQL_HOST", "localhost")
    env.setdefault("MYSQL_PORT", "3306")
    env.setdefault("MYSQL_USER", "root")
    env.setdefault("MYSQL_PASSWORD", "changemeCHANGEME123")
    env.setdefault("MYSQL_DATABASE", "EchoDB")
    env.setdefault("PORT", str(port))

    process = subprocess.Popen(
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
        if os.environ.get("BASE_URL") == base_url and base_url != original_base_url:
            os.environ["BASE_URL"] = original_base_url
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
