FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies with uv
RUN uv pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8080

# Run the bot
CMD ["uv", "run", "discord_bot/bot.py"]