FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY start.py .

# Create data/models directory if it doesn't exist
RUN mkdir -p data/models

# Expose port (Railway sets the actual port dynamically via PORT env var)
EXPOSE 8000

# Run the application using the startup script
CMD ["python", "start.py"]
