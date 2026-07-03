FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY source ./source
COPY deploy/example-config.json ./deploy/example-config.json
RUN pip install --no-cache-dir .
EXPOSE 8080 50051
CMD ["constitutional-builder-api", "--config", "deploy/example-config.json", "--host", "0.0.0.0", "--port", "8080"]
