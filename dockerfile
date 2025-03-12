# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# ADD . /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app
COPY . .

RUN uv sync --frozen

# install playwright browsers
RUN playwright install chromium

# Run app.py when the container launches
CMD ["uv", "run", "discord_bot/bot.py"]