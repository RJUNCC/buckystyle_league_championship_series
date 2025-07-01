FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker caching
COPY discord_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot and shared code into the container
COPY ./discord_bot /app
COPY ./shared /app/shared

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]