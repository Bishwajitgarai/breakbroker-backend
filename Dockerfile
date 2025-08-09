# Use official Python image with slim base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (optional) or use requirements.txt
# COPY pyproject.toml poetry.lock ./
# RUN pip install poetry && poetry install --no-root

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY ./app ./app
COPY ./migrate.py .
COPY .env .

# Expose port
EXPOSE 8000
