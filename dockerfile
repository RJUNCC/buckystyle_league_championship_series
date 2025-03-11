# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD . /app

# Set the working directory in the container
WORKDIR /app
RUN uv sync --frozen

# Run app.py when the container launches
CMD ["uv", "run", "discord_bot/bot.py"]