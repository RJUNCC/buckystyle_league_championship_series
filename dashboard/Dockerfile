# Use a consistent Python version
FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency definition files first
COPY dashboard/pyproject.toml ./
COPY dashboard/uv.lock ./

# Install dependencies using uv. This layer is cached as long as the lockfile doesn't change.
RUN uv pip sync pyproject.toml --no-cache

# Copy the rest of the application code
COPY . .

# Expose the port the app will run on
EXPOSE 8080

# Run the dashboard. The script is now at /app/dashboard/main.py
CMD ["python", "dashboard/main.py"]
