FROM python:3.11-slim

WORKDIR /app
COPY requirements-lite.txt .
RUN pip install --no-cache-dir -r requirements-lite.txt
COPY hermes_lite.py .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "hermes_lite.py"]
