from __future__ import annotations

import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    from .release_config import LOCAL_IMAGE_TAG, RELEASE_IMAGE_TAG
except ImportError:  # pragma: no cover - direct script execution
    from release_config import LOCAL_IMAGE_TAG, RELEASE_IMAGE_TAG


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    failures.extend(static_manifest_checks())

    docker = shutil.which("docker")
    if docker and docker_daemon_available(docker):
        completed = subprocess.run(
            [docker, "build", "-f", "deploy/Dockerfile", "-t", LOCAL_IMAGE_TAG, "."],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if completed.returncode != 0:
            failures.append("docker build failed")
            print(completed.stdout)
        else:
            print("PASS: docker image build completed")
            smoke = subprocess.run(
                [docker, "run", "--rm", LOCAL_IMAGE_TAG, "constitutional-builder", "--help"],
                cwd=ROOT,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            if smoke.returncode != 0:
                failures.append("docker image CLI smoke failed")
                print(smoke.stdout)
            else:
                print("PASS: docker image CLI smoke completed")
            live_failure = docker_api_smoke(docker)
            if live_failure:
                failures.append(live_failure)
            tag = subprocess.run(
                [docker, "tag", LOCAL_IMAGE_TAG, RELEASE_IMAGE_TAG],
                cwd=ROOT,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if tag.returncode != 0:
                failures.append(f"docker image tag for Kubernetes smoke failed: {tag.stdout}")
    elif docker:
        print("WARN: docker CLI available but daemon is not reachable; static Dockerfile checks only")
    else:
        print("WARN: docker not available; static Dockerfile checks only")

    kubectl = shutil.which("kubectl")
    if kubectl and kubernetes_cluster_available(kubectl):
        completed = subprocess.run(
            [kubectl, "apply", "--dry-run=client", "--validate=false", "-f", "deploy/kubernetes.yaml"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if completed.returncode != 0:
            failures.append("kubectl client dry-run failed")
            print(completed.stdout)
        else:
            print("PASS: kubectl client dry-run completed")
            live_failure = import_image_to_kind_node(docker) if docker else "docker required for Kubernetes image import"
            if live_failure:
                failures.append(live_failure)
            live_failure = kubernetes_apply_smoke(kubectl) if not live_failure else None
            if live_failure:
                failures.append(live_failure)
    elif kubectl:
        print("WARN: kubectl CLI available but no cluster API is reachable; static Kubernetes checks only")
    else:
        print("WARN: kubectl not available; static Kubernetes checks only")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: deployment validation completed")
    return 0


def static_manifest_checks() -> list[str]:
    failures: list[str] = []
    dockerfile = (ROOT / "deploy" / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    kubernetes = (ROOT / "deploy" / "kubernetes.yaml").read_text(encoding="utf-8")

    required_docker = ["FROM python:3.12-slim", "COPY source ./source", "EXPOSE 8080"]
    for token in required_docker:
        if token not in dockerfile:
            failures.append(f"Dockerfile missing {token!r}")

    if "constitutional-builder" not in compose or "8080:8080" not in compose:
        failures.append("docker-compose.yml missing service or port mapping")

    for token in ["kind: Deployment", "kind: Service", "containerPort: 8080"]:
        if token not in kubernetes:
            failures.append(f"kubernetes.yaml missing {token!r}")

    return failures


def docker_daemon_available(docker: str) -> bool:
    completed = subprocess.run(
        [docker, "info"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )
    return completed.returncode == 0


def kubernetes_cluster_available(kubectl: str) -> bool:
    completed = subprocess.run(
        [kubectl, "cluster-info"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )
    return completed.returncode == 0


def docker_api_smoke(docker: str) -> str | None:
    container_name = f"constitutional-builder-smoke-{int(time.time())}"
    run = subprocess.run(
        [
            docker,
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            "127.0.0.1::8080",
            LOCAL_IMAGE_TAG,
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if run.returncode != 0:
        return f"docker API smoke container failed to start: {run.stdout}"

    try:
        port_result = subprocess.run(
            [docker, "port", container_name, "8080/tcp"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if port_result.returncode != 0:
            return f"docker API smoke port lookup failed: {port_result.stdout}"
        endpoint = port_result.stdout.strip().replace("0.0.0.0", "127.0.0.1")
        if not endpoint:
            return "docker API smoke port lookup returned empty endpoint"
        url = f"http://{endpoint}/health"
        deadline = time.time() + 60
        last_error = ""
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    if response.status == 200 and '"status": "ok"' in body:
                        print("PASS: docker container API health smoke completed")
                        return None
                    last_error = f"unexpected response {response.status}: {body}"
            except Exception as exc:  # noqa: BLE001 - retry until container is ready.
                last_error = str(exc)
            time.sleep(2)
        return f"docker API smoke health check failed: {last_error}"
    finally:
        subprocess.run(
            [docker, "rm", "-f", container_name],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )


def kubernetes_apply_smoke(kubectl: str) -> str | None:
    namespace = f"cb-smoke-{int(time.time())}"
    created_namespace = False
    try:
        create = subprocess.run(
            [kubectl, "create", "namespace", namespace],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if create.returncode != 0:
            return f"kubernetes smoke namespace creation failed: {create.stdout}"
        created_namespace = True
        apply = subprocess.run(
            [kubectl, "apply", "-n", namespace, "-f", "deploy/kubernetes.yaml"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if apply.returncode != 0:
            return f"kubernetes smoke apply failed: {apply.stdout}"
        wait = subprocess.run(
            [
                kubectl,
                "wait",
                "-n",
                namespace,
                "--for=condition=available",
                "deployment/constitutional-builder",
                "--timeout=120s",
            ],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=150,
        )
        if wait.returncode != 0:
            return f"kubernetes smoke deployment wait failed: {wait.stdout}"
        print("PASS: kubernetes apply/wait smoke completed")
        return None
    finally:
        if created_namespace:
            subprocess.run(
                [kubectl, "delete", "namespace", namespace, "--wait=false"],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )


def import_image_to_kind_node(docker: str) -> str | None:
    nodes = subprocess.run(
        [docker, "ps", "--format", "{{.Names}}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if nodes.returncode != 0:
        return f"docker node lookup failed: {nodes.stdout}"
    node_name = next((name for name in nodes.stdout.splitlines() if name == "desktop-control-plane"), None)
    if node_name is None:
        print("WARN: desktop-control-plane node container not found; skipping image import")
        return None
    export = subprocess.Popen(
        [docker, "save", RELEASE_IMAGE_TAG],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    import_cmd = subprocess.run(
        [docker, "exec", "-i", node_name, "ctr", "-n", "k8s.io", "images", "import", "-"],
        cwd=ROOT,
        stdin=export.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if export.stdout:
        export.stdout.close()
    export_stderr = export.stderr.read().decode("utf-8", errors="replace") if export.stderr else ""
    export_return = export.wait(timeout=30)
    if export_return != 0:
        return f"docker image export failed: {export_stderr}"
    if import_cmd.returncode != 0:
        return f"kubernetes node image import failed: {import_cmd.stdout}"
    print("PASS: kubernetes node image import completed")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
