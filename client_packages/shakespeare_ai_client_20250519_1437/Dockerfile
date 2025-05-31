FROM python:3.10-bookworm

# Set environment variables for better Python & Streamlit behavior in Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install spaCy model
RUN python -m spacy download en_core_web_sm

# Copy the application
COPY . .

# Create necessary directories for mounted volumes
RUN mkdir -p /app/embeddings/chromadb_vectors \
    /app/outputs \
    /app/logs \
    /app/translation_sessions

# Create empty .env file (will be populated by environment variables)
RUN echo "OPENAI_API_KEY=" > /app/.env && \
    echo "ANTHROPIC_API_KEY=" >> /app/.env

# Create and set up the entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# Expose Streamlit port
EXPOSE 8501

# Add healthcheck to verify application is running
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/ || exit 1

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]