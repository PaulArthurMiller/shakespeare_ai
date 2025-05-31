#!/bin/bash
set -e

# Create .env file from environment variables
echo "OPENAI_API_KEY=${OPENAI_API_KEY:-}" > /app/.env
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}" >> /app/.env

# Print startup message (only show first 5 chars of keys for security)
echo "=== Shakespeare AI Initialization ==="
if [ -n "$OPENAI_API_KEY" ]; then
    echo "OpenAI API key: ${OPENAI_API_KEY:0:5}... [detected]" 
else
    echo "OpenAI API key: [not provided]"
fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "Anthropic API key: ${ANTHROPIC_API_KEY:0:5}... [detected]"
else
    echo "Anthropic API key: [not provided]"
fi

# Check database
if [ ! -d "/app/embeddings/chromadb_vectors" ] || [ -z "$(ls -A /app/embeddings/chromadb_vectors)" ]; then
    echo "ERROR: Database not found in /app/embeddings/chromadb_vectors"
    echo "Please make sure to mount the database volume correctly."
    exit 1
fi

echo "Database: [detected]"
echo "=== Startup Complete ==="
echo "Starting Streamlit server..."

# Start the application
exec streamlit run streamlit_ui.py