# Lightweight Hermes Gateway - Discord only
# Designed for Render Free tier (512MB RAM)

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies only (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy project files first (layer caching)
COPY pyproject.toml setup-hermes.sh ./

# Install Python dependencies - only messaging (Discord), no browser/Playwright
RUN pip install --no-cache-dir "uv>=0.4" && \
    uv pip install --system --no-cache-dir \
        "openai>=2.21.0,<3" \
        "anthropic>=0.39.0,<1" \
        "python-dotenv>=1.2.1,<2" \
        "fire>=0.7.1,<1" \
        "discord.py[voice]>=2.7.1,<3" \
        "aiohttp>=3.13.3,<4" \
        "rich>=13.0,<14" \
        "prompt_toolkit>=3.0,<4" && \
    rm -rf /root/.cache/pip

# Copy source code
COPY . .

# Create required directories
RUN mkdir -p /opt/data/{cron,sessions,logs,hooks,memories,skills,skins,plans,workspace,home}

ENV PYTHONUNBUFFERED=1
ENV HERMES_HOME=/opt/data
ENV HERMES_INTERACTIVE=0

EXPOSE 8080

# Run gateway mode only (no interactive TUI)
CMD ["python", "-m", "cli", "--gateway"]
