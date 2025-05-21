# Dockerfile

# 1. Use an updated official Python base image (slim version)
# Consider python:3.13-alpine for a significantly smaller image and potentially fewer vulnerabilities,
# but be aware of potential compatibility issues with complex C extensions in your dependencies (e.g., torch, scipy, nvidia packages).
# Thorough testing would be required if switching to Alpine.
FROM python:3.13-slim

# Optional: Set environment variables for Python using the recommended key=value format
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. Set the working directory in the container
WORKDIR /code

# 3. Copy requirements.txt and install dependencies
# This layer is cached and only rebuilds if requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app_cache/hf_cache && chmod 777 /app_cache/hf_cache

# 4. Copy only the necessary application code into the container
# Be specific here. If your application code is primarily in the 'app' directory,
# and you might have other top-level scripts or utility modules, copy them explicitly.
# Copy Alembic configuration and scripts
COPY alembic.ini /code/alembic.ini
COPY ./alembic /code/alembic


COPY ./app /code/app
# If you have other essential directories or files at the root level that your app needs:
# Example: COPY ./my_utils_module /code/my_utils_module
# Example: COPY ./run_script.py /code/run_script.py
# Avoid `COPY . .` if possible to prevent unnecessary cache invalidation.

# 5. Expose the port your app runs on (good for documentation, though docker-compose handles publishing)
EXPOSE 8000

# 6. Create logs directory (ensure 'logs/' is in .dockerignore if you don't want local logs copied)
# This layer is small and quick.
RUN mkdir -p /code/logs

# 7. Set the default command to run your app
# This will be overridden by the `command` in docker-compose.yml for the fastapi service,
# but it's good practice to have a default.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
