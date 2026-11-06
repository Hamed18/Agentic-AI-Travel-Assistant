import os
import sys
import logging
import httpx
from langchain_core.tools import tool
from config import (
    AVIATION_STACK_API_KEY,
    OPENWEATHER_API_KEY,
    TAVILY_API_KEY,
)

logger = logging.getLogger("mcp_client")
DEFAULT_TIMEOUT = 7.0
TAVILY_TIMEOUT = 10.0

# ------------------------
# Direct Resilient HTTP Implementations
# ------------------------

async def tavily_search(query: str):
    """Direct search using Tavily REST API with timeout and error resilience."""
    if not TAVILY_API_KEY:
        return "Tavily search API key not configured."
    try:
        async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": 5,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                if data.get("answer"):
                    results.append(f"Summary: {data['answer']}")
                for r in data.get("results", []):
                    results.append(f"- {r.get('title')}: {r.get('content')}")
                return "\n".join(results) if results else "No specific hotel or travel results found."
            return f"Tavily search returned status {resp.status_code}"
    except Exception as e:
        logger.warning(f"Tavily search error: {e}")
        return f"Hotel search temporarily unavailable: {e}"


async def list_airports(search: str = "", limit: int = 10):
    """Direct AviationStack airport lookup with timeout and error resilience."""
    if not AVIATION_STACK_API_KEY:
        return {"ok": False, "note": "AviationStack key not configured", "data": []}
    try:
        params = {
            "access_key": AVIATION_STACK_API_KEY,
            "limit": min(max(1, limit), 20),
            "offset": 0,
        }
        if search:
            params["search"] = search
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get("https://api.aviationstack.com/v1/airports", params=params)
            if resp.status_code == 200:
                data = resp.json()
                airports = []
                for a in data.get("data", []):
                    airports.append({
                        "airport_name": a.get("airport_name"),
                        "iata_code": a.get("iata_code"),
                        "city_iata_code": a.get("city_iata_code"),
                        "country_name": a.get("country_name"),
                    })
                return {"ok": True, "count": len(airports), "data": airports}
            return {"ok": False, "note": f"Aviation API returned {resp.status_code}", "data": []}
    except Exception as e:
        logger.warning(f"Airport lookup error: {e}")
        return {"ok": False, "note": str(e), "data": []}


async def list_airlines(search: str = "", limit: int = 10):
    """Direct AviationStack airline lookup with timeout and error resilience."""
    if not AVIATION_STACK_API_KEY:
        return {"ok": False, "note": "AviationStack key not configured", "data": []}
    try:
        params = {
            "access_key": AVIATION_STACK_API_KEY,
            "limit": min(max(1, limit), 20),
            "offset": 0,
        }
        if search:
            params["search"] = search
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get("https://api.aviationstack.com/v1/airlines", params=params)
            if resp.status_code == 200:
                data = resp.json()
                airlines = []
                for a in data.get("data", []):
                    airlines.append({
                        "airline_name": a.get("airline_name"),
                        "iata_code": a.get("iata_code"),
                        "callsign": a.get("callsign"),
                        "country_name": a.get("country_name"),
                    })
                return {"ok": True, "count": len(airlines), "data": airlines}
            return {"ok": False, "note": f"Aviation API returned {resp.status_code}", "data": []}
    except Exception as e:
        logger.warning(f"Airline lookup error: {e}")
        return {"ok": False, "note": str(e), "data": []}


async def current_weather(city: str):
    """Direct OpenWeatherMap current weather lookup."""
    if not OPENWEATHER_API_KEY:
        return {"error": "OpenWeather API key not configured"}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "city": data.get("name", city),
                    "temperature_c": data.get("main", {}).get("temp"),
                    "feels_like_c": data.get("main", {}).get("feels_like"),
                    "humidity": data.get("main", {}).get("humidity"),
                    "condition": data.get("weather", [{}])[0].get("description", "clear"),
                    "wind_speed": data.get("wind", {}).get("speed")
                }
            return {"city": city, "error": f"Weather API returned {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Weather lookup error: {e}")
        return {"city": city, "error": str(e)}


async def forecast(city: str):
    """Direct OpenWeatherMap forecast lookup."""
    if not OPENWEATHER_API_KEY:
        return {"error": "OpenWeather API key not configured"}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
            )
            if resp.status_code == 200:
                data = resp.json()
                forecast_items = []
                for item in data.get("list", [])[:5]:
                    forecast_items.append({
                        "datetime": item.get("dt_txt"),
                        "temperature": item.get("main", {}).get("temp"),
                        "weather": item.get("weather", [{}])[0].get("description")
                    })
                return {"city": city, "forecast": forecast_items}
            return {"city": city, "error": f"Forecast API returned {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Forecast lookup error: {e}")
        return {"city": city, "error": str(e)}


# ------------------------
# LangChain Tool compatibility layer
# ------------------------

@tool
async def tool_tavily_search(query: str) -> str:
    """Search web for hotel accommodations and travel tips."""
    return await tavily_search(query)

@tool
async def tool_list_airports(search: str = "", limit: int = 10) -> dict:
    """Find airports near destination or origin."""
    return await list_airports(search=search, limit=limit)

@tool
async def tool_list_airlines(search: str = "", limit: int = 10) -> dict:
    """Find airlines operating at destination or origin."""
    return await list_airlines(search=search, limit=limit)

@tool
async def tool_current_weather(city: str) -> dict:
    """Get current weather conditions for a destination."""
    return await current_weather(city)

@tool
async def tool_forecast(city: str) -> dict:
    """Get 5-day weather forecast for a destination."""
    return await forecast(city)

_tools_list = [
    tool_tavily_search,
    tool_list_airports,
    tool_list_airlines,
    tool_current_weather,
    tool_forecast,
]

async def get_tools():
    return _tools_list

async def call_tool(tool_name: str, args: dict = None):
    args = args or {}
    tool_map = {
        "tavily_search": tavily_search,
        "list_airports": list_airports,
        "list_airlines": list_airlines,
        "get_current_weather": current_weather,
        "current_weather": current_weather,
        "get_forecast": forecast,
        "forecast": forecast,
    }
    func = tool_map.get(tool_name)
    if not func:
        raise ValueError(f"Tool '{tool_name}' not found")
    return await func(**args)
