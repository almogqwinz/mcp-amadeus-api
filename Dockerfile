# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv for dependency management
RUN pip install uv

# Install dependencies
RUN uv sync --frozen

# Copy source code
COPY src/ ./src/

# Set environment variables for MCP deployment
ENV MCP_TRANSPORT=http
ENV HOST=0.0.0.0
ENV MCP_PATH=/mcp

# Expose port (will be set by Smithery via PORT env var)
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/mcp/health || exit 1

# Start the server
# Smithery will pass configuration via query parameters
# The server will listen on PORT environment variable
CMD ["sh", "-c", "uv run python src/server.py"]
