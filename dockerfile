# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Add these lines before installing dependencies
RUN mkdir -p /app/images /app/data/parquet && \
    chmod -R 777 /app/images /app/data

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libatspi2.0-0 libwayland-client0 fonts-liberation \
    libappindicator3-1 xdg-utils

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set the working directory in the container
WORKDIR /app
COPY . .

RUN uv sync --frozen

# Install Playwright browsers
RUN playwright install chromium && chmod -R a+rwx /app/images

# Run the bot
CMD ["uv", "run", "discord_bot/bot.py"]
