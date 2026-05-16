FROM python:3.11-slim

WORKDIR /app

COPY common/src /app/common
COPY inference-service/pyproject.toml .
RUN pip install --no-cache-dir .

COPY inference-service/src/ /app/src/
COPY inference-service/artifacts/ /app/artifacts/

ENV PYTHONPATH=/app:/app/common
CMD ["python", "-m", "src.main"]
