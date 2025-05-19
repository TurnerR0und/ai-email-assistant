# Dockerfile

# 1. Use the official Python base image (choose your version)
FROM python:3.12-slim

# 2. Set the working directory in the container
WORKDIR /code

# 3. Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your code into the container
COPY . .

# 5. Expose the port your app runs on
EXPOSE 8000

# At the end of your Dockerfile (before CMD)
RUN mkdir -p /code/logs

# 6. Set the default command to run your app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
