from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "thirsty-ai-builder"
BACKEND_IMAGE = "thirsty-ai-builder-backend:local-verify"
FRONTEND_IMAGE = "thirsty-ai-builder-frontend:local-verify"
COMPOSE_PROJECT = f"thirsty-ai-builder-verify-{os.getpid()}"
STRONG_TOKEN = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd,
        env=merged_env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_ok(name: str, completed: subprocess.CompletedProcess[str]) -> None:
    if completed.returncode != 0:
        raise RuntimeError(f"{name} failed with {completed.returncode}\n{completed.stdout}")
    print(f"PASS: {name}")


def require_fail_contains(name: str, completed: subprocess.CompletedProcess[str], needle: str) -> None:
    if completed.returncode == 0:
        raise RuntimeError(f"{name} unexpectedly succeeded")
    if needle not in completed.stdout:
        raise RuntimeError(f"{name} did not mention {needle!r}\n{completed.stdout}")
    print(f"PASS: {name}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def fetch(url: str, *, token: str | None = None, attempts: int = 30) -> str:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"could not fetch {url}: {last_error}")


def validate_compose_runtime() -> None:
    port = free_port()
    env = {
        "CB_API_KEY": STRONG_TOKEN,
        "THIRSTY_AI_FRONTEND_PORT": str(port),
    }
    compose = ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(APP / "docker-compose.yml")]
    try:
        require_ok("thirsty compose runtime up", run([*compose, "up", "-d", "--build", "--wait"], env=env))
        healthz = fetch(f"http://127.0.0.1:{port}/healthz")
        if "ok" not in healthz:
            raise RuntimeError(f"frontend healthz returned unexpected body: {healthz!r}")
        api_health = fetch(f"http://127.0.0.1:{port}/api/health")
        if "ThirstyAi Builder" not in api_health or "database_backend" not in api_health:
            raise RuntimeError(f"proxied api health returned unexpected body: {api_health!r}")
        protected = fetch(
            f"http://127.0.0.1:{port}/api/appstore/tools",
            token=STRONG_TOKEN,
        )
        if "tools" not in protected:
            raise RuntimeError(f"authenticated proxied API returned unexpected body: {protected!r}")
        print("PASS: thirsty compose runtime smoke")
    finally:
        down = run([*compose, "down", "-v", "--remove-orphans"], env=env)
        if down.returncode != 0:
            print(f"WARN: thirsty compose cleanup failed\n{down.stdout}")


def main() -> int:
    try:
        require_ok(
            "thirsty compose config",
            run(
                ["docker", "compose", "-f", str(APP / "docker-compose.yml"), "config"],
                env={"CB_API_KEY": STRONG_TOKEN},
            ),
        )
        require_ok(
            "thirsty backend image build",
            run(["docker", "build", "-t", BACKEND_IMAGE, "."], cwd=APP / "backend"),
        )
        require_ok(
            "thirsty frontend image build",
            run(["docker", "build", "-t", FRONTEND_IMAGE, "."], cwd=APP / "frontend"),
        )
        require_fail_contains(
            "thirsty backend fails closed without CB_API_KEY",
            run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-e",
                    "THIRSTY_AI_REQUIRE_AUTH=1",
                    BACKEND_IMAGE,
                    "python",
                    "-c",
                    "import server",
                ]
            ),
            "requires CB_API_KEY",
        )
        require_fail_contains(
            "thirsty backend fails closed without MONGO_URL",
            run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-e",
                    f"CB_API_KEY={STRONG_TOKEN}",
                    "-e",
                    "THIRSTY_AI_REQUIRE_MONGO=1",
                    BACKEND_IMAGE,
                    "python",
                    "-c",
                    "import server",
                ]
            ),
            "requires MONGO_URL",
        )
        require_ok(
            "thirsty backend production preflight",
            run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-e",
                    f"CB_API_KEY={STRONG_TOKEN}",
                    "-e",
                    "THIRSTY_AI_REQUIRE_AUTH=1",
                    "-e",
                    "MONGO_URL=mongodb://mongo:27017/thirsty_ai_builder",
                    "-e",
                    "THIRSTY_AI_REQUIRE_MONGO=1",
                    "-e",
                    "CORS_ORIGINS=https://builder.example.com",
                    "-e",
                    "OLLAMA_HOST=http://127.0.0.1:11434",
                    BACKEND_IMAGE,
                    "python",
                    "-m",
                    "thirsty_ai_builder_backend.preflight",
                ]
            ),
        )
        validate_compose_runtime()
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: thirsty-ai-builder deployment validation completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
