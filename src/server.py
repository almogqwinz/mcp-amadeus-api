import os
import json
from amadeus import Client, ResponseError
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

@dataclass
class AppContext:
    amadeus_client: Client

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage Amadeus client lifecycle"""
    # Support both old and new environment variable names for backward compatibility
    api_key = os.environ.get("AMADEUS_CLIENT_ID") or os.environ.get("AMADEUS_API_KEY")
    api_secret = os.environ.get("AMADEUS_CLIENT_SECRET") or os.environ.get("AMADEUS_API_SECRET")
    hostname = os.environ.get("AMADEUS_HOSTNAME", "test")

    if not api_key or not api_secret:
        raise ValueError("AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET must be set as environment variables")

    amadeus_client = Client(
        client_id=api_key,
        client_secret=api_secret,
        hostname=hostname
    )

    try:
        yield AppContext(amadeus_client=amadeus_client)
    finally:
        pass

mcp = FastMCP("Amadeus API", dependencies=["amadeus"], lifespan=app_lifespan)

# Add a simple health check endpoint for container deployments
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for container deployments"""
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "amadeus-mcp-api"})

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
    if adults and not (1 <= adults <= 9):
        return json.dumps({"error": "Adults must be between 1 and 9"})

    if children and infants and adults and (adults + children > 9):
        return json.dumps({"error": "Total number of seated travelers (adults + children) cannot exceed 9"})

    if infants and adults and (infants > adults):
        return json.dumps({"error": "Number of infants cannot exceed number of adults"})

    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    params = {}
    params["originLocationCode"] = originLocationCode
    params["destinationLocationCode"] = destinationLocationCode
    params["departureDate"] = departureDate
    params["adults"] = adults

    if returnDate:
        params["returnDate"] = returnDate
    if children is not None:
        params["children"] = children
    if infants is not None:
        params["infants"] = infants
    if travelClass:
        params["travelClass"] = travelClass
    if includedAirlineCodes:
        params["includedAirlineCodes"] = includedAirlineCodes
    if excludedAirlineCodes:
        params["excludedAirlineCodes"] = excludedAirlineCodes
    if nonStop is not None:
        params["nonStop"] = nonStop
    if currencyCode:
        params["currencyCode"] = currencyCode
    if maxPrice is not None:
        params["maxPrice"] = maxPrice
    if max is not None:
        params["max"] = max

    try:
        ctx.info(f"Searching flights from {originLocationCode} to {destinationLocationCode}")
        ctx.info(f"API parameters: {json.dumps(params)}")

        response = amadeus_client.shopping.flight_offers_search.get(**params)
        return json.dumps(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
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
    
    # Check if we should run with HTTP transport (for streamable HTTP)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "http":
        # Run with streamable HTTP transport
        # Use PORT environment variable (set by Smithery) or default to 8000
        port = int(os.environ.get("PORT", 8000))
        host = os.environ.get("HOST", "0.0.0.0")  # Use 0.0.0.0 for container deployments
        log_level = os.environ.get("LOG_LEVEL", "info")
        path = os.environ.get("MCP_PATH", "/mcp")
        
        print(f"Starting Amadeus MCP server on {host}:{port}{path}")
        print(f"Configuration: HOST={host}, AMADEUS_HOSTNAME={os.environ.get('AMADEUS_HOSTNAME', 'test')}")
        
        async def run_http():
            # Note: The MCP SDK's run_streamable_http_async doesn't accept custom parameters
            # It uses default settings, but we can override via environment if needed
            await mcp.run_streamable_http_async()
        
        asyncio.run(run_http())
    else:
        # Default to stdio transport
        mcp.run()
