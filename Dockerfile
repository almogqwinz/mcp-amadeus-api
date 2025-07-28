# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies directly with pip
RUN pip install --no-cache-dir amadeus mcp

# Set environment variables for MCP deployment
ENV MCP_TRANSPORT=http
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose port
EXPOSE 8000

# Simple startup command
CMD ["python", "src/server.py"]
