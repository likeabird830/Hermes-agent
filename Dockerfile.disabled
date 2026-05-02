FROM python:3.11-slim

WORKDIR /app

# Install only what we need
RUN pip install --no-cache-dir discord.py aiohttp

COPY hermes_lite.py .

# Unbuffered output
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "hermes_lite.py"]
