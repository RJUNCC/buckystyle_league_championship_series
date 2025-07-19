FROM python:3.12-slim

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

# 192.9.200(network) .23(host) :22(port [22 is standrd service port for ssh]) for v4 IP address
# tels docker that container should listen to traffic on this port
# so docker will listen for on port 8080 for TCP connections since TCP is default
EXPOSE 8080 

# Run the dashboard
CMD ["python", "main.py"]