FROM python:3.11-slim

LABEL maintainer="AI Email Agent"
LABEL description="AI-powered email importance classifier and dashboard"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/   /app/backend/
COPY frontend/  /app/frontend/
COPY data/      /app/data/

# Create volume mount point for DB
RUN mkdir -p /app/db

# Streamlit config
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Python path so backend modules are importable from frontend
ENV PYTHONPATH=/app/backend

EXPOSE 8501

# Entrypoint: run the Streamlit dashboard (which also runs the agent inline)
CMD ["streamlit", "run", "/app/frontend/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
