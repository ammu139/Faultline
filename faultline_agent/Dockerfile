# Faultline: AI-Powered System Resilience Agent
# Deployment container for Cloud Run / Docker
#
# Build:  docker build -t faultline .
# Run:    docker run -p 8501:8501 --env-file .env faultline
# Deploy: gcloud run deploy faultline --source .

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default: run Streamlit UI
# Override with: docker run faultline python -m app.runner --interactive
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]