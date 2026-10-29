"""Incidents as geo_location entities, so they show up on the Home Assistant map.

Incidents come and go, so entities are created and removed on every refresh
instead of being registered once. They deliberately have no unique_id: that
keeps hundreds of short-lived incidents out of the entity registry.
"""

from __future__ import annotations

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.location import distance

from .const import DOMAIN, CATEGORY_JAMS, CATEGORY_RADARS
from .coordinator import ANWBFileCoordinator
from .markers import marker_picture

ICONS = {
    CATEGORY_JAMS: "mdi:car-multiple",
    CATEGORY_RADARS: "mdi:camera-wireless",
}
DEFAULT_ICON = "mdi:account-hard-hat"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ANWBFileCoordinator = entry.runtime_data
    entities: dict[str, ANWBFileIncident] = {}

    @callback
    def _sync() -> None:
        incidents = {
            incident["id"]: incident
            for incident in (coordinator.data or {}).get("incidents", [])
            if incident["category"] in coordinator.map_categories
            and incident["latitude"] is not None
            and incident["longitude"] is not None
        }

        for incident_id in entities.keys() - incidents.keys():
            hass.async_create_task(entities.pop(incident_id).async_remove())

        new = []
        for incident_id, incident in incidents.items():
            if incident_id in entities:
                entities[incident_id].update_incident(incident)
            else:
                entities[incident_id] = ANWBFileIncident(incident)
                new.append(entities[incident_id])
        if new:
            async_add_entities(new)

    entry.async_on_unload(coordinator.async_add_listener(_sync))
    _sync()


class ANWBFileIncident(GeolocationEvent):
    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS
    # The polyline is only useful live (for map cards), not in history
    _unrecorded_attributes = frozenset({"path"})

    def __init__(self, incident: dict) -> None:
        self._attr_icon = ICONS.get(incident["category"], DEFAULT_ICON)
        self._set_incident(incident)

    def _set_incident(self, incident: dict) -> None:
        self._incident = incident
        self._color = incident["color"]
        # The map card shows the entity picture instead of the first letters of the name
        self._attr_entity_picture = marker_picture(incident["category"], self._color)

    @callback
    def update_incident(self, incident: dict) -> None:
        self._set_incident(incident)
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        incident = self._incident
        if incident["category"] == CATEGORY_RADARS:
            return f"{incident['road']} flitser {incident['from']}"
        return f"{incident['road']} {incident['from']} - {incident['to']}"

    @property
    def latitude(self) -> float:
        return self._incident["latitude"]

    @property
    def longitude(self) -> float:
        return self._incident["longitude"]

    @property
    def distance(self) -> float | None:
        meters = distance(
            self.hass.config.latitude,
            self.hass.config.longitude,
            self.latitude,
            self.longitude,
        )
        return round(meters / 1000, 1) if meters is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        incident = self._incident
        return {
            "category": incident["category"],
            "road": incident["road"],
            "direction": incident["direction"],
            "incident_type": incident["incident_type"],
            "from": incident["from"],
            "to": incident["to"],
            "reason": incident["reason"],
            "length_km": incident["length_km"],
            "delay_min": incident["delay_min"],
            "start": incident["start"],
            "stop": incident["stop"],
            "color": self._color,
            "path": incident["path"],
        }
