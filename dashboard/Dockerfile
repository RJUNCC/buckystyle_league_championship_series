# Use a consistent Python version
FROM python:3.11-slim

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy only the files needed for dependency installation first to leverage caching
COPY dashboard/pyproject.toml dashboard/uv.lock ./dashboard/
COPY shared/config/conf/dashboard_config.yaml ./shared/config/conf/

# Install dependencies using uv
RUN uv pip sync dashboard/pyproject.toml --no-cache

# Copy the rest of the application code
COPY ./dashboard /app/dashboard
COPY ./shared /app/shared

# Set the host to 0.0.0.0 so it's accessible outside the container
ENV TAIPY_GUI_HOST=0.0.0.0

# Expose the port the app will run on
EXPOSE 8080

# Run the dashboard using the correct entrypoint
CMD ["python", "dashboard/main.py"]
