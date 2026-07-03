# Backend Dockerfile, hardened for production review.
#
# - Pinned base image (full tag, not `latest`). To pin by digest
#   instead (strongest reproducibility), run:
#     docker pull python:3.11.9-slim-bookworm
#     docker images --digests
#   then replace the FROM line with the `python:...@sha256:...` form.
# - Multi-stage: build deps live in a builder stage that does not
#   ship in the final image.
# - Non-root user. The image runs as UID 10001 (no shell login, no
#   home directory).
# - No secrets in the image. All configuration comes through env
#   vars at runtime.
# - No `apt` cache, no `pip` cache, no build tools in the final image.
# - Healthcheck that hits the local readiness probe.

# ---- builder --------------------------------------------------------
FROM python:3.11.9-slim-bookworm AS builder

WORKDIR /build

# Install build deps for any wheels that need a compiler. Remove
# them at the end of the stage so they don't end up in the runtime
# image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libffi-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime --------------------------------------------------------
FROM python:3.11.9-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="thirsty-ai-builder-backend" \
      org.opencontainers.image.description="ThirstyAI Builder backend (FastAPI)" \
      org.opencontainers.image.source="https://github.com/thirsty-ai/builder" \
      org.opencontainers.image.licenses="Proprietary"

# Create the unprivileged user. UID 10001 avoids collisions with
# host users and most containers.
RUN groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Pull the installed Python packages from the builder stage.
COPY --from=builder /install /usr/local

# Application code. --chown ensures the runtime user owns the files.
COPY --chown=app:app server.py ./
COPY --chown=app:app thirsty_ai_builder_backend ./thirsty_ai_builder_backend

# Writable temp dir for the app. /tmp is OK; we do not write to /app.
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8001

USER app:app

EXPOSE 8001

# Healthcheck hits the liveness probe. Uses Python instead of curl
# to keep the image minimal (no extra package).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8001/api/health',timeout=3); sys.exit(0 if r.status==200 else 1)"

CMD ["python", "server.py"]
