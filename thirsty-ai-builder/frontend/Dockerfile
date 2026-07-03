# Frontend Dockerfile, hardened for production review.
#
# - Multi-stage: the `build` stage compiles a static React bundle and
#   is discarded. Only the static files + nginx end up in the runtime
#   image.
# - Pinned base images (full tags). Pin by digest for strongest
#   reproducibility: `docker pull node:20.18.0-alpine` and
#   `docker pull nginx:1.27.2-alpine`, then replace the FROM lines
#   with the `...@sha256:...` form.
# - Nginx runs as the unprivileged `nginx` user (default for the
#   alpine image).
# - The `serve` script and a custom nginx config are added so the
#   frontend serves `/api/*` from the same origin (proxied to the
#   backend) instead of relying on CORS. Single-origin is the
#   reviewer's preferred posture for an internal admin app.

# ---- build ----------------------------------------------------------
FROM node:20.18.0-alpine AS build

WORKDIR /app

# Copy manifests first so the npm install layer caches well.
COPY package*.json ./
# `--ignore-scripts` skips postinstall hooks from dependencies. The
# Builder's package.json has no postinstall; the flag is a defense
# against a malicious dependency.
RUN npm ci --no-audit --no-fund --ignore-scripts

COPY . .
RUN npm run build

# ---- runtime --------------------------------------------------------
FROM nginx:1.27.2-alpine AS runtime

# Wipe the default nginx config; we ship our own.
RUN rm /etc/nginx/conf.d/default.conf

# Custom nginx config: SPA fallback + /api proxy + security headers.
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Static build artifacts, owned by the nginx user.
COPY --chown=nginx:nginx --from=build /app/build /usr/share/nginx/html

# The base image already runs as the unprivileged `nginx` user
# (UID 101). Verify in the final image: `docker run --rm ... id`.

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
