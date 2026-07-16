# ===========================================================================
# Dockerfile — Network Automation Platform
# ===========================================================================
FROM python:3.11-slim

LABEL maintainer="network-engineering@example.com"
LABEL description="Network Automation Platform — bots and automation engine"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Install project in editable mode
RUN pip install --no-cache-dir -e .

# Default port (overridden per bot in docker-compose)
EXPOSE 8000

# Default command (overridden per service)
CMD ["python", "-m", "uvicorn", "bots.firewall_bot.firewall_bot:FirewallBot", "--host", "0.0.0.0", "--port", "8000"]
