FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY thirsty_ai_builder_backend ./thirsty_ai_builder_backend

ENV PYTHONPATH=/app
EXPOSE 8001

CMD ["python", "server.py"]
