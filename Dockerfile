FROM python:3.11-slim

WORKDIR /app


# Install system dependencies required for building Python packages
# pycairo needs pkg-config and libcairo2-dev
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "core.web.app:app", "--host", "0.0.0.0", "--port", "8001"]
