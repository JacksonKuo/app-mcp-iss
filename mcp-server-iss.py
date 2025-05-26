from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("iss")

API_BASE = "http://api.open-notify.org"

async def make_iss_request(url: str) -> dict[str, Any] | None:
    """Make a request to the ISS API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers={}, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_response(json: dict) -> str:
    """Format an json into a readable string."""
    return f"""
        Timestamp: {json.get('timestamp')}
        Message: {json.get('message')}
        Latitude: {json.get('iss_position').get('latitude')}
        Longitude: {json.get('iss_position').get('longitude')}
        """

@mcp.tool()
async def get_position() -> str:
    """Get ISS geolocation.

    Args:

    """
    url = f"{API_BASE}/iss-now.json"
    data = await make_iss_request(url)

    if not data:
        return "Unable to fetch data or no data found."

    if not data["message"]:
        return "Malformed response"

    return data

if __name__ == "__main__":
    print("running")
    mcp.run(transport='stdio')