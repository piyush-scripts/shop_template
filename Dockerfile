# Use Python 3.9 slim image as the base
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better cache utilization
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application code
COPY . .

# Create a non-root user and switch to it for security
RUN useradd -m appuser
USER appuser

# Expose the port the app runs on
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
