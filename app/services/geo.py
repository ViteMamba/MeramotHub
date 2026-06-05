import math
import httpx
import asyncio

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in kilometers.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371
    return c * r

async def road_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """
    Get road distance using OSRM API. Returns {"km": float, "method": "road"|"straight"}.
    Falls back to haversine if OSRM fails.
    """
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            km = data["routes"][0]["distance"] / 1000
            return {"km": km, "method": "road"}
    except Exception:
        pass
    km = haversine_distance(lat1, lon1, lat2, lon2)
    return {"km": km, "method": "straight"}
