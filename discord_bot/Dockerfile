FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy pyproject.toml
COPY pyproject.toml ./

# Install dependencies with uv without requiring lock file
# RUN uv pip install --system -r pyproject.toml
RUN uv pip install --system --no-deps -e .

# Copy app code
COPY . ./

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8080

# Run the bot
CMD ["uv", "run", "bot.py"]