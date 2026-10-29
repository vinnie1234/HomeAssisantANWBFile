"""Route planning: travel time, delay and arrival for the routes set up in the options."""

from __future__ import annotations

from datetime import timedelta
import logging
import re

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_ROUTE_URL,
    CONF_ROUTES,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import HEADERS, REQUEST_TIMEOUT, decode_polyline, simplify_path

_LOGGER = logging.getLogger(__name__)

ROUTE_HEADERS = {**HEADERS, "x-anwb-caller-id": "routing/routeplanner-web"}
# The API also lists European (E35) and city (s112) route numbers; keep A and N roads
MOTORWAY_PATTERN = re.compile(r"^[AN]\d+$")


def parse_routes(raw: dict) -> list[dict]:
    """The fastest route first, followed by the alternatives, as the API orders them."""
    routes = []
    for item in raw.get("value", []):
        summary = item["summary"]
        polyline = "".join(leg.get("polyline", "") for leg in item.get("legs", []))
        via = [road for road in summary.get("roadNumbers", []) if MOTORWAY_PATTERN.match(road)]
        routes.append(
            {
                "distance_km": round(summary["distanceInMeters"] / 1000, 1),
                "duration_min": round(summary["durationInSeconds"] / 60, 1),
                "delay_min": round(summary["delayInSeconds"] / 60, 1),
                "difference_min": round(summary.get("difference", {}).get("durationInSeconds", 0) / 60, 1),
                "departure": summary["departure"],
                "arrival": summary["arrival"],
                "via": list(dict.fromkeys(via)),
                "toll": bool(summary.get("tollRoads")),
                "path": simplify_path(decode_polyline(polyline)) if polyline else [],
                "incidents": [
                    {
                        "category": incident.get("simpleCategory"),
                        "delay_min": round(incident.get("delayInSeconds", 0) / 60, 1),
                        "path": simplify_path(decode_polyline(incident["polyline"]))
                        if incident.get("polyline")
                        else [],
                    }
                    for incident in item.get("incidents", [])
                ],
            }
        )
    return routes


class ANWBRoutesCoordinator(DataUpdateCoordinator[dict[str, dict | None]]):
    """Data per route id: {"origin", "destination", "best", "alternatives"}, or None if it failed."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        options = {**entry.data, **entry.options}
        self.routes: list[dict] = options.get(CONF_ROUTES, [])
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_routes",
            # Without routes there is nothing to refresh
            update_interval=timedelta(minutes=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
            if self.routes
            else None,
        )

    def payload(self) -> list[dict]:
        """What the ANWB File card receives over the websocket."""
        payload = []
        for route in self.routes:
            result = (self.data or {}).get(route["id"])
            payload.append({"id": route["id"], "name": route["name"], **(result or {"error": True})})
        return payload

    async def _async_update_data(self) -> dict[str, dict | None]:
        if not self.routes:
            return {}
        results = {route["id"]: await self._async_fetch(route) for route in self.routes}
        if not any(results.values()):
            raise UpdateFailed("None of the ANWB routes could be fetched")
        return results

    async def _async_fetch(self, route: dict) -> dict | None:
        origin = self._coordinates(route["origin"])
        destination = self._coordinates(route["destination"])
        if origin is None or destination is None:
            _LOGGER.debug("Route %s has an end without a known location", route["name"])
            return None

        params = {
            "locations": f"{origin[0]},{origin[1]}:{destination[0]},{destination[1]}",
            "tollInfo": "true",
            "traffic": "true",
            "routeType": "fastest",
            "includeAlternatives": "true",
        }
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                API_ROUTE_URL, params=params, headers=ROUTE_HEADERS, timeout=REQUEST_TIMEOUT
            ) as response:
                response.raise_for_status()
                routes = parse_routes(await response.json())
        except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as err:
            _LOGGER.warning("Could not fetch ANWB route %s: %s", route["name"], err)
            return None
        if not routes:
            return None

        return {
            "origin": list(origin),
            "destination": list(destination),
            "best": routes[0],
            "alternatives": routes[1:],
        }

    def _coordinates(self, end: dict) -> tuple[float, float] | None:
        """A fixed point, or the live position of a zone/person/device tracker."""
        if entity_id := end.get("entity_id"):
            state = self.hass.states.get(entity_id)
            attributes = state.attributes if state else {}
            latitude, longitude = attributes.get("latitude"), attributes.get("longitude")
            return (latitude, longitude) if latitude is not None and longitude is not None else None
        return end["latitude"], end["longitude"]
