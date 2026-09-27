# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git is required for git diff/history analysis, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ backend/
COPY frontend/ frontend/
COPY .streamlit/ .streamlit/
COPY entrypoint.sh .

# Ensure entrypoint is executable
RUN chmod +x entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8501

EXPOSE 8501 8000

ENTRYPOINT ["./entrypoint.sh"]
