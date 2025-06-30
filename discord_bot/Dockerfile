FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]