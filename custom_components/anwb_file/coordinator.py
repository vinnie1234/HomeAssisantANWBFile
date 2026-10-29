from __future__ import annotations

from datetime import timedelta
import logging
import math

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_URL,
    CATEGORIES,
    CATEGORY_RADARS,
    CONF_CATEGORIES,
    CONF_MAP_CATEGORIES,
    CONF_ROAD_SELECTION,
    CONF_ROAD_TYPE,
    CONF_ROADS,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAP_CATEGORIES,
    DEFAULT_SCAN_INTERVAL,
    ROAD_SELECTION_SPECIFIC,
    ROAD_TYPE_A,
    ROAD_TYPE_FILTER,
)

from .markers import incident_color

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "accept": "application/json",
    "accept-language": "nl,en;q=0.9",
    "origin": "https://www.anwb.nl",
    "referer": "https://www.anwb.nl/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    ),
}

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


async def async_fetch_incidents(hass: HomeAssistant) -> dict:
    """Fetch the raw ANWB incident feed (all roads, all categories)."""
    session = async_get_clientsession(hass)
    async with session.get(API_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT) as response:
        response.raise_for_status()
        raw = await response.json()
    if not raw.get("success", False):
        raise UpdateFailed("ANWB incident feed returned success=false")
    return raw


def available_roads(raw: dict, road_type: str) -> list[str]:
    """Road names in the feed that match the road type, in ANWB's order."""
    allowed = ROAD_TYPE_FILTER[road_type]
    return [road["road"] for road in raw.get("roads", []) if road.get("type") in allowed]


def normalize_road(road: str) -> str:
    """'a 2 ' -> 'A2', so user input matches the API's road names."""
    return road.replace(" ", "").upper()


def decode_polyline(encoded: str) -> list[list[float]]:
    """Decode a Google encoded polyline (precision 5) into [[lat, lon], ...]."""
    points = []
    index = lat = lon = 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append([lat / 1e5, lon / 1e5])
    return points


def simplify_path(points: list[list[float]], tolerance: float = 0.0001) -> list[list[float]]:
    """Ramer-Douglas-Peucker; ~11 m tolerance keeps the road shape but cuts ~80% of the points."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        (ax, ay), (bx, by) = points[first], points[last]
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        farthest, farthest_distance = -1, 0.0
        for i in range(first + 1, last):
            px, py = points[i]
            t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > farthest_distance:
                farthest, farthest_distance = i, d
        if farthest_distance > tolerance:
            keep[farthest] = True
            stack += [(first, farthest), (farthest, last)]
    return [point for point, kept in zip(points, keep) if kept]


class ANWBFileCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        options = {**entry.data, **entry.options}
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self._road_types = ROAD_TYPE_FILTER[options.get(CONF_ROAD_TYPE, ROAD_TYPE_A)]
        self.categories = set(options.get(CONF_CATEGORIES, CATEGORIES))
        # Only these are drawn as markers on the map; the list always shows all
        self.map_categories = self.categories & set(
            options.get(CONF_MAP_CATEGORIES, DEFAULT_MAP_CATEGORIES)
        )
        self.roads: list[str] | None = (
            [normalize_road(road) for road in options.get(CONF_ROADS, [])]
            if options.get(CONF_ROAD_SELECTION) == ROAD_SELECTION_SPECIFIC
            else None
        )

    async def _async_update_data(self) -> dict:
        try:
            raw = await async_fetch_incidents(self.hass)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error fetching ANWB traffic information: {err}") from err

        return {
            "updated": raw.get("dateTime"),
            "incidents": self._parse(raw),
        }

    def payload(self) -> dict:
        """What the ANWB File card receives over the websocket."""
        data = self.data or {"updated": None, "incidents": []}
        return {
            "updated": data["updated"],
            "incidents": data["incidents"],
            "categories": sorted(self.categories),
            "map_categories": sorted(self.map_categories),
        }

    def _parse(self, raw: dict) -> list[dict]:
        incidents = []
        for road in raw.get("roads", []):
            if road.get("type") not in self._road_types:
                continue
            if self.roads is not None and normalize_road(road["road"]) not in self.roads:
                continue
            for segment in road.get("segments", []):
                for category in self.categories:
                    for item in segment.get(category, []):
                        incidents.append(self._incident(item, category, segment))
        return incidents

    @staticmethod
    def _incident(item: dict, category: str, segment: dict) -> dict:
        path = simplify_path(decode_polyline(item["polyline"])) if item.get("polyline") else []

        # Radars are a single point; for jams/roadworks the polyline runs in the
        # driving direction, so its first point is where you hit the tail.
        if category == CATEGORY_RADARS and item.get("loc"):
            location = item["loc"]
            latitude, longitude = location["lat"], location["lon"]
        elif path:
            latitude, longitude = path[0]
        else:
            location = item.get("fromLoc") or {}
            latitude, longitude = location.get("lat"), location.get("lon")

        distance = item.get("distance")
        delay = item.get("delay")
        return {
            "id": f"{category}_{item['id']}",
            "category": category,
            "road": normalize_road(item.get("road", "")),
            "direction": f"{segment.get('start')} - {segment.get('end')}",
            "incident_type": item.get("incidentType"),
            "color": incident_color(category, item.get("incidentType")),
            "from": item.get("from"),
            "to": item.get("to"),
            "reason": item.get("reason"),
            "length_km": round(distance / 1000, 1) if distance is not None else None,
            "delay_min": round(delay / 60) if delay is not None else None,
            "start": item.get("start"),
            "stop": item.get("stop"),
            "latitude": latitude,
            "longitude": longitude,
            "path": path,
        }
