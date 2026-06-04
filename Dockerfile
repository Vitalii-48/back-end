# Use the official lightweight Python image
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Install curl and clear the apt cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the dependency file to the working directory
COPY requirements.txt .

# Upgrade pip and install the project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project layout into the container
COPY . .

# Command to run the FastAPI application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
