FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user
RUN useradd -m -s /bin/bash deepseek
USER deepseek
WORKDIR /home/deepseek

# Copy requirements and install
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set Python path
ENV PATH="/home/deepseek/.local/bin:${PATH}"
ENV PYTHONPATH="/home/deepseek:${PYTHONPATH}"

CMD ["python", "test.py"]