# 🚀 Complete Guide: Streamable HTTP Transport for MCP with Smithery

This guide shows how to implement streamable HTTP transport for Model Context Protocol (MCP) servers with Smithery platform integration.

## 📋 Table of Contents
- [Overview](#overview)
- [Basic Setup](#basic-setup)
- [Smithery Integration](#smithery-integration)
- [Configuration Handling](#configuration-handling)
- [Production Deployment](#production-deployment)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

### What is Streamable HTTP Transport?
- Allows MCP servers to run over HTTP instead of stdio
- Enables web-based deployments and cloud hosting
- Perfect for platforms like Smithery that need HTTP endpoints

### Key Benefits
- ✅ Cloud deployment ready
- ✅ Better for containerized environments
- ✅ Supports query parameter configuration
- ✅ Health check endpoints
- ✅ Production-ready logging

## Basic Setup

### 1. Project Structure
```
your-mcp-project/
├── src/
│   └── server.py          # Main MCP server
├── pyproject.toml         # Dependencies
├── Dockerfile            # Container setup
└── smithery.yaml         # Smithery configuration
```

### 2. Dependencies (`pyproject.toml`)
```toml
[project]
name = "your-mcp-server"
dependencies = [
    "mcp",
    "fastmcp",
    "uvicorn",
    "starlette",
]

[project.scripts]
server = "src.server:main"
```

### 3. Basic Server Setup (`src/server.py`)
```python
import os
import json
import asyncio
from mcp.server.fastmcp import FastMCP

# Create MCP server with HTTP support
mcp = FastMCP("Your MCP Server", stateless_http=True)

@mcp.tool()
def your_tool() -> str:
    """Your MCP tool implementation"""
    return "Hello from MCP!"

# Health check endpoint for container deployments
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "healthy", 
        "service": "your-mcp-server"
    })

if __name__ == "__main__":
    # Check transport mode
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "http":
        # Run with HTTP transport
        asyncio.run(run_http_server())
    else:
        # Run with stdio transport
        mcp.run()
```

## Smithery Integration

### 1. Smithery Configuration (`smithery.yaml`)
```yaml
version: "1.0"
name: "Your MCP Server"
description: "Description of your MCP server"

# Server configuration
server:
  # Entry point script
  command: "python src/server.py"
  
  # Environment variables
  env:
    MCP_TRANSPORT: "http"
    PORT: "8000"
    HOST: "0.0.0.0"

# Configuration schema for Smithery UI
config:
  - name: "apiKey"
    type: "string"
    description: "Your API Key"
    required: true
    
  - name: "apiSecret" 
    type: "password"
    description: "Your API Secret"
    required: true
    
  - name: "environment"
    type: "select"
    description: "API Environment"
    options: ["test", "production"]
    default: "test"

# Container settings
container:
  port: 8000
  healthcheck: "/health"
```

### 2. HTTP Server Implementation
```python
async def run_http_server():
    """Run the MCP server with HTTP transport"""
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting MCP server in HTTP mode on {host}:{port}")
    
    # Create the HTTP app
    app = mcp.streamable_http_app()
    
    # Add configuration middleware for Smithery
    @app.middleware("http")
    async def config_middleware(request, call_next):
        await handle_smithery_config(request)
        response = await call_next(request)
        return response
    
    # Start the server
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
```

## Configuration Handling

### 1. Smithery Config Middleware
```python
async def handle_smithery_config(request):
    """Handle Smithery configuration from query parameters"""
    query_params = dict(request.query_params)
    
    print(f"🔍 Request path: {request.url.path}")
    print(f"🔍 Query parameters: {list(query_params.keys())}")
    
    # Check for Smithery's base64-encoded config
    if 'config' in query_params:
        try:
            import base64
            
            # Decode the base64-encoded JSON config
            config_b64 = query_params['config']
            decoded_bytes = base64.b64decode(config_b64)
            decoded_string = decoded_bytes.decode('utf-8')
            config_data = json.loads(decoded_string)
            
            print(f"✅ Decoded Smithery config")
            print(f"🔍 Config keys: {list(config_data.keys())}")
            
            # Apply configuration to environment variables
            apply_config_to_env(config_data)
            
        except Exception as e:
            print(f"❌ Error parsing Smithery config: {e}")
    
    # Fallback: Check for individual query parameters
    else:
        print("🔍 Checking individual query parameters...")
        apply_individual_params_to_env(query_params)

def apply_config_to_env(config_data):
    """Apply Smithery config to environment variables"""
    # Map Smithery config keys to environment variables
    config_mapping = {
        'apiKey': 'YOUR_API_KEY',
        'apiSecret': 'YOUR_API_SECRET', 
        'environment': 'YOUR_ENVIRONMENT',
    }
    
    for config_key, env_var in config_mapping.items():
        if config_key in config_data:
            os.environ[env_var] = config_data[config_key]
            print(f"✅ Applied {env_var} from Smithery config")

def apply_individual_params_to_env(query_params):
    """Apply individual query parameters to environment variables"""
    param_mapping = {
        'apiKey': 'YOUR_API_KEY',
        'apiSecret': 'YOUR_API_SECRET',
        'environment': 'YOUR_ENVIRONMENT',
    }
    
    for param_key, env_var in param_mapping.items():
        if param_key in query_params:
            os.environ[env_var] = query_params[param_key]
            print(f"✅ Applied {env_var} from query params")
```

### 2. Debug Endpoint
```python
@mcp.custom_route("/debug", methods=["GET"])
async def debug_endpoint(request):
    """Debug endpoint to inspect configuration"""
    from starlette.responses import JSONResponse
    
    query_params = dict(request.query_params)
    
    # Show environment variables (mask secrets)
    env_vars = {}
    for key in ['YOUR_API_KEY', 'YOUR_API_SECRET', 'YOUR_ENVIRONMENT']:
        value = os.environ.get(key, "NOT_SET")
        if 'SECRET' in key or 'KEY' in key:
            env_vars[key] = "SET" if value != "NOT_SET" else "NOT_SET"
        else:
            env_vars[key] = value
    
    return JSONResponse({
        "message": "Debug info for Your MCP Server",
        "query_parameters": list(query_params.keys()),
        "environment_variables": env_vars,
        "server_status": "running"
    })
```

## Production Deployment

### 1. Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install -e .

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["python", "src/server.py"]
```

### 2. Complete Main Function
```python
if __name__ == "__main__":
    print("=== Your MCP Server Starting ===")
    print(f"Python version: {os.sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Show environment info
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    print(f"Transport mode: {transport}")
    
    if transport == "http":
        port = int(os.environ.get("PORT", 8000))
        host = os.environ.get("HOST", "0.0.0.0")
        
        print(f"Starting HTTP server on {host}:{port}")
        print("Available endpoints:")
        print("  - /health (GET) - Health check")
        print("  - /debug (GET) - Debug info")
        
        try:
            asyncio.run(run_http_server())
        except Exception as e:
            print(f"ERROR: Failed to start HTTP server: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Starting in STDIO mode")
        try:
            mcp.run()
        except Exception as e:
            print(f"ERROR: Failed to start STDIO server: {e}")
            import traceback
            traceback.print_exc()
```

## Best Practices

### 1. Error Handling
```python
def get_your_api_client():
    """Create API client with proper error handling"""
    api_key = os.environ.get("YOUR_API_KEY")
    api_secret = os.environ.get("YOUR_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError(
            "API credentials not configured. "
            "Please provide your API credentials when connecting to this server."
        )
    
    try:
        # Initialize your API client
        client = YourAPIClient(api_key=api_key, api_secret=api_secret)
        return client
    except Exception as e:
        raise ValueError(f"Failed to initialize API client: {str(e)}")
```

### 2. Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@mcp.tool()
def your_tool_with_logging():
    """Tool with proper logging"""
    logger.info("Tool called")
    try:
        # Your tool logic here
        result = "success"
        logger.info(f"Tool completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return json.dumps({"error": str(e)})
```

### 3. Parameter Validation
```python
@mcp.tool()
def validated_tool(param1: str, param2: int = None) -> str:
    """Tool with parameter validation"""
    
    # Validate required parameters
    if not param1 or not param1.strip():
        return json.dumps({"error": "param1 is required and cannot be empty"})
    
    # Validate optional parameters
    if param2 is not None and param2 <= 0:
        return json.dumps({"error": "param2 must be positive if provided"})
    
    # Filter out empty/invalid values before API calls
    api_params = {"param1": param1}
    if param2 is not None and param2 > 0:
        api_params["param2"] = param2
    
    # Make API call with filtered parameters
    try:
        result = your_api_call(**api_params)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
```

## Troubleshooting

### Common Issues

1. **Server won't start**
   - Check `MCP_TRANSPORT=http` is set
   - Verify port is not in use
   - Check Python dependencies are installed

2. **Configuration not working**
   - Add debug logging to middleware
   - Use `/debug` endpoint to inspect config
   - Check base64 decoding of Smithery config

3. **API calls failing**
   - Verify credentials are being set correctly
   - Check parameter filtering logic
   - Use proper error handling

### Debug Commands
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test debug endpoint  
curl http://localhost:8000/debug

# Test with Smithery config
curl "http://localhost:8000/debug?config=eyJ0ZXN0IjoidmFsdWUifQ=="
```

## 🎉 Summary

This guide provides everything you need to create robust MCP servers with streamable HTTP transport and Smithery integration:

- ✅ HTTP transport setup
- ✅ Smithery configuration handling
- ✅ Production deployment ready
- ✅ Proper error handling and logging
- ✅ Parameter validation patterns
- ✅ Debug capabilities

Your MCP server will be ready for cloud deployment and seamless integration with platforms like Smithery! 🚀 