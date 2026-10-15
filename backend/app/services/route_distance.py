"""
Route distances for trips. Google Maps distances are route estimates, not GPS-measured travel.
The server-side key (GOOGLE_MAPS_API_KEY) is used; it never reaches clients.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, Tuple

import httpx

from app.core.config import settings

LatLng = Tuple[float, float]


class RouteUnavailable(Exception):
    pass


@dataclass
class RouteResult:
    stop_legs_km: List[Decimal]   # origin->stop1, stop1->stop2, ...
    return_leg_km: Decimal        # last stop -> origin
    provider_data: Dict[str, Any]


class RouteDistanceProvider(Protocol):
    async def route(self, origin: LatLng, stops: List[LatLng]) -> RouteResult: ...


class GoogleDirectionsProvider:
    """Directions API with the admin-defined stop order (optimize:false), returning to the kitchen."""
    URL = "https://maps.googleapis.com/maps/api/directions/json"

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout

    async def route(self, origin: LatLng, stops: List[LatLng]) -> RouteResult:
        if not stops:
            raise RouteUnavailable("No stops to route")
        fmt = lambda p: f"{p[0]},{p[1]}"  # noqa: E731
        params = {
            "origin": fmt(origin),
            "destination": fmt(origin),
            "waypoints": "optimize:false|" + "|".join(fmt(s) for s in stops),
            "mode": "driving",
            "key": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                body = (await client.get(self.URL, params=params)).json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RouteUnavailable(f"Google Maps request failed: {exc}") from exc
        if body.get("status") != "OK" or not body.get("routes"):
            raise RouteUnavailable(f"Google Maps returned {body.get('status')}")
        legs = body["routes"][0]["legs"]
        if len(legs) != len(stops) + 1:
            raise RouteUnavailable("Google Maps returned an unexpected number of legs")
        km = [Decimal(leg["distance"]["value"]) / Decimal(1000) for leg in legs]
        return RouteResult(km[:-1], km[-1], {
            "provider": "google_directions",
            "legs_m": [leg["distance"]["value"] for leg in legs],
        })


def default_provider() -> Optional[RouteDistanceProvider]:
    if settings.google_maps_api_key:
        return GoogleDirectionsProvider(settings.google_maps_api_key)
    return None
