import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Aviationstack MCP")

API_BASE_URL = "https://api.aviationstack.com/v1"

@mcp.tool(name="list_airports")
def list_airports(limit: int = 10, offset: int = 0, search: str = ""):
    api_key = os.getenv("AVIATION_STACK_API_KEY")
    params = {
        "access_key": api_key,
        "limit": min(max(1, limit), 100),
        "offset": max(0, offset)
    }
    if search:
        params["search"] = search
    
    try:
        response = requests.get(f"{API_BASE_URL}/airports", params=params, timeout=15)
        if response.status_code != 200:
            return {"ok": False, "error": f"API error: {response.status_code}", "data": []}
        data = response.json()
        airports = []
        for airport in data.get("data", []):
            airports.append({
                "airport_name": airport.get("airport_name"),
                "iata_code": airport.get("iata_code"),
                "icao_code": airport.get("icao_code"),
                "city_iata_code": airport.get("city_iata_code"),
                "country_name": airport.get("country_name"),
                "country_iso2": airport.get("country_iso2"),
                "timezone": airport.get("timezone"),
                "gmt": airport.get("gmt"),
            })
        return {"ok": True, "count": len(airports), "data": airports}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}

@mcp.tool(name="list_airlines")
def list_airlines(limit: int = 10, offset: int = 0, search: str = ""):
    api_key = os.getenv("AVIATION_STACK_API_KEY")
    params = {
        "access_key": api_key,
        "limit": min(max(1, limit), 100),
        "offset": max(0, offset)
    }
    if search:
        params["search"] = search
    
    try:
        response = requests.get(f"{API_BASE_URL}/airlines", params=params, timeout=15)
        if response.status_code != 200:
            return {"ok": False, "error": f"API error: {response.status_code}", "data": []}
        data = response.json()
        airlines = []
        for airline in data.get("data", []):
            airlines.append({
                "airline_name": airline.get("airline_name"),
                "iata_code": airline.get("iata_code"),
                "icao_code": airline.get("icao_code"),
                "callsign": airline.get("callsign"),
                "status": airline.get("status"),
                "country_name": airline.get("country_name"),
                "country_iso2": airline.get("country_iso2"),
            })
        return {"ok": True, "count": len(airlines), "data": airlines}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}

if __name__ == "__main__":
    mcp.run()
