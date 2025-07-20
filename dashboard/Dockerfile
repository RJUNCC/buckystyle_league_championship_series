FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY dashboard/pyproject.toml ./
COPY dashboard/uv.lock ./

# Install dependencies using --system flag for Docker
RUN uv pip sync pyproject.toml --no-cache --system

# Copy the dashboard and shared code into the container
COPY ./dashboard /app
COPY ./shared /app/shared

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

# Run the dashboard
CMD ["python", "main.py"]