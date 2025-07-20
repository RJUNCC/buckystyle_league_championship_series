FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker caching
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the dashboard and shared code into the container
COPY ./dashboard /app
COPY ./shared /app/shared

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

# Run the dashboard
CMD ["python", "main.py"]