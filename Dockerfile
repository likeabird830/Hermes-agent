# Ultra-lightweight Hermes Discord Bot for Render Free Tier
# Only 3 Python packages + bot script = ~80MB RAM usage

FROM python:3.11-slim

WORKDIR /app

COPY requirements-lite.txt .
RUN pip install --no-cache-dir -r requirements-lite.txt

COPY hermes_lite.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["python", "hermes_lite.py"]
