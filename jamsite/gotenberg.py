"""Find a Gotenberg server for document conversion.

On the server, Gotenberg runs as a docker compose service. On a dev machine,
a temporary container is started on first use (Docker if it is running,
otherwise the Apple container CLI) and stopped when the process exits.
"""
import atexit
import json
import os
import subprocess
import time

import requests

COMPOSE_URL = "http://gotenberg:3000"
LOCAL_PORT = 3002
CONTAINER_NAME = "jamsite-gotenberg"
IMAGE = "gotenberg/gotenberg:8"

_url = None


def get_url():
    global _url
    if _url is None:
        _url = os.getenv("GOTENBERG_URL")
    if _url is None and _is_healthy(COMPOSE_URL):
        _url = COMPOSE_URL
    if _url is None:
        _url = _start_local()
    return _url


def _is_healthy(url):
    try:
        return requests.get(url + "/health", timeout=2).status_code == 200
    except requests.exceptions.RequestException:
        return False


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _detect_runtime():
    try:
        if _run(["docker", "info"]).returncode == 0:
            return "docker"
    except FileNotFoundError:
        pass
    try:
        status = _run(["container", "system", "status", "--format", "json"])
    except FileNotFoundError:
        raise SystemExit(
            "No container runtime found for Gotenberg. "
            "Start Docker Desktop, or run: brew install container"
        )
    try:
        running = json.loads(status.stdout).get("status") == "running"
    except json.JSONDecodeError:
        running = False
    if not running:
        raise SystemExit(
            "Apple container service is not running. "
            "Run: container system start --enable-kernel-install"
        )
    return "container"


def _remove(runtime):
    _run([runtime, "stop", CONTAINER_NAME])
    _run([runtime, "rm", CONTAINER_NAME])


def _start_local():
    runtime = _detect_runtime()
    print(f"Starting Gotenberg container (using '{runtime}')...")
    _remove(runtime)
    result = _run([
        runtime, "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{LOCAL_PORT}:3000",
        IMAGE,
    ])
    if result.returncode != 0:
        raise SystemExit(f"Failed to start Gotenberg: {result.stderr.strip()}")
    atexit.register(_stop_local, runtime)

    url = f"http://localhost:{LOCAL_PORT}"
    for _ in range(30):
        if _is_healthy(url):
            print("Gotenberg is ready")
            return url
        time.sleep(2)
    raise SystemExit("Gotenberg container did not become ready after 60 seconds")


def _stop_local(runtime):
    print("Stopping Gotenberg container...")
    _remove(runtime)
