import os
import json
from amadeus import Client, ResponseError

from mcp.server.fastmcp import FastMCP, Context

def get_amadeus_client() -> Client:
    """Create Amadeus client with credentials from environment"""
    # Support both old and new environment variable names for backward compatibility
    api_key = os.environ.get("AMADEUS_CLIENT_ID") or os.environ.get("AMADEUS_API_KEY")
    api_secret = os.environ.get("AMADEUS_CLIENT_SECRET") or os.environ.get("AMADEUS_API_SECRET")
    hostname = os.environ.get("AMADEUS_HOSTNAME", "test")

    if not api_key or not api_secret:
        raise ValueError(
            "Amadeus API credentials not configured. "
            "Please provide your Amadeus API credentials when connecting to this server."
        )

    try:
        # Create the client
        amadeus_client = Client(
            client_id=api_key,
            client_secret=api_secret,
            hostname=hostname
        )
        
        return amadeus_client
    except Exception as e:
        raise ValueError(f"Failed to initialize Amadeus client: {str(e)}")

mcp = FastMCP("Amadeus API", stateless_http=True)

# Simple debug tool that doesn't require any credentials
@mcp.tool()
def ping() -> str:
    """Simple ping tool to test server connectivity"""
    return "pong"

# Add a simple health check endpoint for container deployments
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for container deployments"""
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "amadeus-mcp-api"})

# Add debug endpoint to see what parameters we're receiving
@mcp.custom_route("/debug", methods=["GET"])
async def debug_endpoint(request):
    """Debug endpoint to see what parameters are being received"""
    from starlette.responses import JSONResponse
    
    query_params = dict(request.query_params)
    headers = dict(request.headers)
    
    # Get current environment variables
    env_vars = {
        "AMADEUS_CLIENT_ID": os.environ.get("AMADEUS_CLIENT_ID", "NOT_SET"),
        "AMADEUS_CLIENT_SECRET": "SET" if os.environ.get("AMADEUS_CLIENT_SECRET") else "NOT_SET",
        "AMADEUS_HOSTNAME": os.environ.get("AMADEUS_HOSTNAME", "NOT_SET"),
    }
    
    return JSONResponse({
        "message": "Debug info for Amadeus MCP Server",
        "query_parameters": query_params,
        "environment_variables": env_vars,
        "headers": {k: v for k, v in headers.items() if k.lower() in ['host', 'user-agent', 'referer', 'authorization']},
        "server_status": "running"
    })


@mcp.tool()
def search_flight_offers(
    originLocationCode: str,
    destinationLocationCode: str,
    departureDate: str,
    adults: int,
    ctx: Context,
    returnDate: str = None,
    children: int = None,
    infants: int = None,
    travelClass: str = None,
    includedAirlineCodes: str = None,
    excludedAirlineCodes: str = None,
    nonStop: bool = None,
    currencyCode: str = None,
    maxPrice: int = None,
    max: int = 250
) -> str:
    """
    Search for flight offers using the Amadeus API

    Args:
        originLocationCode: IATA code of the departure city/airport (e.g., SYD for Sydney)
        destinationLocationCode: IATA code of the destination city/airport (e.g., BKK for Bangkok)
        departureDate: Departure date in ISO 8601 format (YYYY-MM-DD, e.g., 2023-05-02)
        adults: Number of adult travelers (age 12+), must be 1-9
        returnDate: Return date in ISO 8601 format (YYYY-MM-DD), if round-trip is desired
        children: Number of child travelers (age 2-11)
        infants: Number of infant travelers (age <= 2)
        travelClass: Travel class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
        includedAirlineCodes: Comma-separated IATA airline codes to include (e.g., '6X,7X')
        excludedAirlineCodes: Comma-separated IATA airline codes to exclude (e.g., '6X,7X')
        nonStop: If true, only non-stop flights are returned
        currencyCode: ISO 4217 currency code (e.g., EUR for Euro)
        maxPrice: Maximum price per traveler, positive integer with no decimals
        max: Maximum number of flight offers to return
    """
    # Validate input parameters before attempting to get credentials
    if adults and not (1 <= adults <= 9):
        return json.dumps({"error": "Adults must be between 1 and 9"})

    if children and infants and adults and (adults + children > 9):
        return json.dumps({"error": "Total number of seated travelers (adults + children) cannot exceed 9"})

    if infants and adults and (infants > adults):
        return json.dumps({"error": "Number of infants cannot exceed number of adults"})

    # Try to get the Amadeus client - this is where credentials are validated
    try:
        amadeus_client = get_amadeus_client()
    except ValueError as e:
        # Return a user-friendly error if credentials are not configured
        return json.dumps({
            "error": "Configuration required",
            "message": str(e),
            "details": "Please ensure your Amadeus API credentials are properly configured."
        })
    except Exception as e:
        # Handle any other initialization errors
        return json.dumps({
            "error": "Service initialization failed", 
            "message": str(e)
        })

    # Build API parameters with proper filtering to avoid Amadeus API 400 errors
    params = {}
    params["originLocationCode"] = originLocationCode
    params["destinationLocationCode"] = destinationLocationCode
    params["departureDate"] = departureDate
    params["adults"] = adults

    # Only include optional parameters when they have meaningful values
    if returnDate:
        params["returnDate"] = returnDate
    
    # Don't send children/infants if they are 0 - Amadeus API rejects these
    if children is not None and children > 0:
        params["children"] = children
    if infants is not None and infants > 0:
        params["infants"] = infants
    
    if travelClass:
        params["travelClass"] = travelClass
    
    # Don't send empty airline codes - Amadeus API rejects empty strings
    if includedAirlineCodes and includedAirlineCodes.strip():
        params["includedAirlineCodes"] = includedAirlineCodes
    if excludedAirlineCodes and excludedAirlineCodes.strip():
        params["excludedAirlineCodes"] = excludedAirlineCodes
    
    # Only send nonStop when it's True - Amadeus API rejects nonStop: false
    if nonStop is True:
        params["nonStop"] = nonStop
    
    if currencyCode:
        params["currencyCode"] = currencyCode
    if maxPrice is not None and maxPrice > 0:
        params["maxPrice"] = maxPrice
    if max is not None and max > 0:
        params["max"] = max

    # Make the actual API call
    try:
        print(f"Searching flights from {originLocationCode} to {destinationLocationCode}")
        print(f"API parameters: {json.dumps(params)}")

        response = amadeus_client.shopping.flight_offers_search.get(**params)
        return json.dumps(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        print(f"Error: {error_msg}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Error: {error_msg}")
        return json.dumps({"error": error_msg})

@mcp.prompt()
def flight_search_prompt(origin: str, destination: str, date: str) -> str:
    """Create a flight search prompt"""
    return f"""
    Please search for flights from {origin} to {destination} on {date}.

    I'd like to see options sorted by price, with information about the airlines,
    departure/arrival times, and any layovers.
    """

if __name__ == "__main__":
    import os
    import asyncio
    
    print("=== Amadeus MCP Server Starting ===")
    print(f"Python version: {os.sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Environment variables:")
    for key in ['MCP_TRANSPORT', 'PORT', 'HOST', 'AMADEUS_CLIENT_ID', 'AMADEUS_CLIENT_SECRET']:
        value = os.environ.get(key, 'NOT_SET')
        if 'SECRET' in key:
            value = 'SET' if value != 'NOT_SET' else 'NOT_SET'
        print(f"  {key}={value}")
    
    # Check if we should run with HTTP transport (for streamable HTTP)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "http":
        # Run with streamable HTTP transport
        # Use PORT environment variable (set by Smithery) or default to 8000
        port = int(os.environ.get("PORT", 8000))
        host = os.environ.get("HOST", "0.0.0.0")  # Use 0.0.0.0 for container deployments
        
        print(f"Starting Amadeus MCP server in HTTP mode")
        print(f"Server will bind to: {host}:{port}")
        print("Available tools: ping, search_flight_offers")
        
        try:
            async def run_http():
                print("Creating HTTP app with middleware...")
                
                # Create the HTTP app and add middleware for query parameter parsing
                app = mcp.streamable_http_app()
                
                # Add middleware to parse query parameters and set environment variables
                @app.middleware("http")
                async def config_middleware(request, call_next):
                    # Extract configuration from query parameters
                    query_params = dict(request.query_params)
                    
                    # Debug logging - show ALL query parameters received
                    print(f"🔍 DEBUG: Request path: {request.url.path}")
                    print(f"🔍 DEBUG: Query parameters received: {query_params}")
                    
                    # Check for Smithery's base64-encoded config parameter
                    if 'config' in query_params:
                        try:
                            import base64
                            import json
                            
                            # Decode the base64-encoded JSON config
                            config_b64 = query_params['config']
                            decoded_bytes = base64.b64decode(config_b64)
                            decoded_string = decoded_bytes.decode('utf-8')
                            config_data = json.loads(decoded_string)
                            
                            print(f"✅ Decoded Smithery config parameter")
                            print(f"🔍 Config contains: {list(config_data.keys())}")
                            
                            # Apply Amadeus configuration from decoded config
                            if 'amadeusClientId' in config_data:
                                os.environ['AMADEUS_CLIENT_ID'] = config_data['amadeusClientId']
                                print(f"✅ Applied AMADEUS_CLIENT_ID from Smithery config")
                            
                            if 'amadeusClientSecret' in config_data:
                                os.environ['AMADEUS_CLIENT_SECRET'] = config_data['amadeusClientSecret']
                                print(f"✅ Applied AMADEUS_CLIENT_SECRET from Smithery config")
                            
                            if 'amadeusHostname' in config_data:
                                os.environ['AMADEUS_HOSTNAME'] = config_data['amadeusHostname']
                                print(f"✅ Applied AMADEUS_HOSTNAME: {config_data['amadeusHostname']}")
                            else:
                                # Default to test environment if not specified
                                os.environ['AMADEUS_HOSTNAME'] = 'test'
                                print(f"ℹ️ Using default AMADEUS_HOSTNAME: test")
                                
                        except Exception as e:
                            print(f"❌ Error parsing Smithery config: {e}")
                    
                    # Fallback: Check for individual query parameters (for backwards compatibility)
                    else:
                        print(f"🔍 No 'config' parameter found, checking individual parameters...")
                        
                        if 'amadeusClientId' in query_params:
                            os.environ['AMADEUS_CLIENT_ID'] = query_params['amadeusClientId']
                            print(f"✅ Applied AMADEUS_CLIENT_ID from individual query params")
                        else:
                            print(f"❌ amadeusClientId NOT found in query params")
                            
                        if 'amadeusClientSecret' in query_params:
                            os.environ['AMADEUS_CLIENT_SECRET'] = query_params['amadeusClientSecret']
                            print(f"✅ Applied AMADEUS_CLIENT_SECRET from individual query params")
                        else:
                            print(f"❌ amadeusClientSecret NOT found in query params")
                            
                        if 'amadeusHostname' in query_params:
                            os.environ['AMADEUS_HOSTNAME'] = query_params['amadeusHostname']
                            print(f"✅ Applied AMADEUS_HOSTNAME: {query_params['amadeusHostname']}")
                        else:
                            print(f"ℹ️ amadeusHostname not specified, using default: test")
                            os.environ['AMADEUS_HOSTNAME'] = 'test'
                    
                    # Continue processing the request
                    response = await call_next(request)
                    return response
                
                # Start the server with uvicorn
                import uvicorn
                config = uvicorn.Config(app, host=host, port=port, log_level="info")
                server = uvicorn.Server(config)
                print("Starting HTTP server with query parameter support...")
                await server.serve()
            
            asyncio.run(run_http())
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
