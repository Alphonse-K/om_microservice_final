FROM python:3.11-slim

WORKDIR /app

# Copy requirements from project root, not from docker/celery folder
COPY ../../requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from project root
COPY ../../src ./src

CMD ["celery", "-A", "src.worker_app", "worker", "--loglevel=info"]
