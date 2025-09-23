FROM python:3.10-slim

WORKDIR /app

# Install system deps (needed for lxml, newspaper3k)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    pkg-config \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Run the main script directly (no web server needed)
CMD ["python", "main.py"]
