# Use official Python 3.13 slim image
FROM python:3.13-slim

# Set a non-root user (optional) and working directory
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy only dependency specification first (small layer)
COPY pyproject.toml /app/

# Install pip and build dependencies, then install runtime dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install google-genai==1.12.1 python-dotenv==1.1.0

# Copy application code
COPY . /app

# Expose nothing by default; this container runs CLI script

# Default entrypoint: run main.py
CMD ["python", "main.py"]
