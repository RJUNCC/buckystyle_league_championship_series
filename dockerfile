FROM python:3.14-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies with uv
RUN uv pip install --system -r requirements.txt

# Copy app code
COPY . .

# Run the bot
CMD ["uv", "run", "discord_bot/bot.py"]