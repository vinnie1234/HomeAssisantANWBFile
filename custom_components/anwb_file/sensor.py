from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CATEGORY_JAMS,
    CATEGORY_RADARS,
    CATEGORY_ROADWORKS,
)
from .coordinator import ANWBFileCoordinator
from .routing import ANWBRoutesCoordinator

# Attributes listed without the polyline path, which only the map needs
_LIST_KEYS = ("road", "direction", "from", "to", "reason", "length_km", "delay_min", "start", "stop")


def _summary(incidents: list[dict]) -> list[dict]:
    return [{key: incident[key] for key in _LIST_KEYS} for incident in incidents]


def _of(incidents: list[dict], category: str) -> list[dict]:
    return [incident for incident in incidents if incident["category"] == category]


def _total_length(jams: list[dict]) -> float:
    return round(sum(jam["length_km"] or 0 for jam in jams), 1)


def _total_delay(jams: list[dict]) -> int:
    return sum(jam["delay_min"] or 0 for jam in jams)


@dataclass(frozen=True, kw_only=True)
class ANWBFileSensorDescription(SensorEntityDescription):
    category: str
    value_fn: Callable[[list[dict]], float | int]
    list_attribute: str | None = None


SENSORS: tuple[ANWBFileSensorDescription, ...] = (
    ANWBFileSensorDescription(
        key="jams",
        translation_key="jams",
        category=CATEGORY_JAMS,
        icon="mdi:car-multiple",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=len,
        list_attribute="jams",
    ),
    ANWBFileSensorDescription(
        key="jam_length",
        translation_key="jam_length",
        category=CATEGORY_JAMS,
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:map-marker-distance",
        value_fn=_total_length,
    ),
    ANWBFileSensorDescription(
        key="jam_delay",
        translation_key="jam_delay",
        category=CATEGORY_JAMS,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-sand",
        value_fn=_total_delay,
    ),
    ANWBFileSensorDescription(
        key="roadworks",
        translation_key="roadworks",
        category=CATEGORY_ROADWORKS,
        icon="mdi:cone",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=len,
        list_attribute="roadworks",
    ),
    ANWBFileSensorDescription(
        key="radars",
        translation_key="radars",
        category=CATEGORY_RADARS,
        icon="mdi:camera-wireless",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=len,
        list_attribute="radars",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ANWBFileCoordinator = entry.runtime_data.incidents
    routes: ANWBRoutesCoordinator = entry.runtime_data.routes
    entities: list[SensorEntity] = [
        ANWBFileSensor(coordinator, entry, description)
        for description in SENSORS
        if description.category in coordinator.categories
    ]
    if coordinator.roads is not None and CATEGORY_JAMS in coordinator.categories:
        entities += [ANWBFileRoadSensor(coordinator, entry, road) for road in coordinator.roads]
    for route in routes.routes:
        entities += [
            ANWBFileRouteSensor(routes, entry, route, description) for description in ROUTE_SENSORS
        ]
    async_add_entities(entities)


class _ANWBFileEntity(CoordinatorEntity[ANWBFileCoordinator], SensorEntity):
    _attr_has_entity_name = True
    # The incident lists can exceed the recorder's attribute size limit
    _unrecorded_attributes = frozenset({"jams", "roadworks", "radars"})

    def __init__(self, coordinator: ANWBFileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ANWB File",
            manufacturer="ANWB",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.anwb.nl/verkeer",
        )

    @property
    def _incidents(self) -> list[dict]:
        return self.coordinator.data["incidents"] if self.coordinator.data else []


class ANWBFileSensor(_ANWBFileEntity):
    entity_description: ANWBFileSensorDescription

    def __init__(
        self,
        coordinator: ANWBFileCoordinator,
        entry: ConfigEntry,
        description: ANWBFileSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> float | int | None:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(_of(self._incidents, self.entity_description.category))

    @property
    def extra_state_attributes(self) -> dict | None:
        if not self.coordinator.data:
            return None
        attrs = {"updated": self.coordinator.data["updated"]}
        if self.entity_description.list_attribute:
            attrs[self.entity_description.list_attribute] = _summary(
                _of(self._incidents, self.entity_description.category)
            )
        return attrs


class ANWBFileRoadSensor(_ANWBFileEntity):
    """Number of jams on one selected road, with length and delay as attributes."""

    _attr_icon = "mdi:road-variant"
    _attr_native_unit_of_measurement = "files"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "road"

    def __init__(self, coordinator: ANWBFileCoordinator, entry: ConfigEntry, road: str) -> None:
        super().__init__(coordinator, entry)
        self._road = road
        self._attr_unique_id = f"{entry.entry_id}_road_{road.lower()}"
        self._attr_translation_placeholders = {"road": road}

    @property
    def _jams(self) -> list[dict]:
        return [jam for jam in _of(self._incidents, CATEGORY_JAMS) if jam["road"] == self._road]

    @property
    def native_value(self) -> int | None:
        return len(self._jams) if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict | None:
        if not self.coordinator.data:
            return None
        jams = self._jams
        return {
            "road": self._road,
            "length_km": _total_length(jams),
            "delay_min": _total_delay(jams),
            "jams": _summary(jams),
            "updated": self.coordinator.data["updated"],
        }


def _route_attributes(result: dict) -> dict:
    best = result["best"]
    return {
        "via": best["via"],
        "toll": best["toll"],
        "departure": best["departure"],
        "origin": result["origin"],
        "destination": result["destination"],
        "incidents": [
            {"category": i["category"], "delay_min": i["delay_min"]} for i in best["incidents"]
        ],
        "alternatives": [
            {
                key: alternative[key]
                for key in ("via", "duration_min", "delay_min", "distance_km", "arrival", "difference_min")
            }
            for alternative in result["alternatives"]
        ],
    }


@dataclass(frozen=True, kw_only=True)
class ANWBFileRouteSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], float | str | datetime | None]
    attributes_fn: Callable[[dict], dict] | None = None


ROUTE_SENSORS: tuple[ANWBFileRouteSensorDescription, ...] = (
    ANWBFileRouteSensorDescription(
        key="duration",
        translation_key="route_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda result: result["best"]["duration_min"],
        attributes_fn=lambda result: {
            "normal_duration_min": round(result["best"]["duration_min"] - result["best"]["delay_min"], 1)
        },
    ),
    ANWBFileRouteSensorDescription(
        key="delay",
        translation_key="route_delay",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:timer-sand",
        value_fn=lambda result: result["best"]["delay_min"],
    ),
    ANWBFileRouteSensorDescription(
        key="arrival",
        translation_key="route_arrival",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda result: dt_util.parse_datetime(result["best"]["arrival"]),
    ),
    ANWBFileRouteSensorDescription(
        key="distance",
        translation_key="route_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda result: result["best"]["distance_km"],
    ),
    ANWBFileRouteSensorDescription(
        key="via",
        translation_key="route_via",
        icon="mdi:routes",
        value_fn=lambda result: " · ".join(result["best"]["via"]) or None,
        attributes_fn=_route_attributes,
    ),
)


class ANWBFileRouteSensor(CoordinatorEntity[ANWBRoutesCoordinator], SensorEntity):
    """One value of the fastest route between two places, with traffic."""

    entity_description: ANWBFileRouteSensorDescription
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"alternatives", "incidents"})

    def __init__(
        self,
        coordinator: ANWBRoutesCoordinator,
        entry: ConfigEntry,
        route: dict,
        description: ANWBFileRouteSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._route_id = route["id"]
        self._attr_unique_id = f"{entry.entry_id}_route_{route['id']}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_route_{route['id']}")},
            name=f"ANWB Route {route['name']}",
            manufacturer="ANWB",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, entry.entry_id),
            configuration_url="https://www.anwb.nl/verkeer/routeplanner",
        )

    @property
    def _result(self) -> dict | None:
        return (self.coordinator.data or {}).get(self._route_id)

    @property
    def available(self) -> bool:
        # A single route can fail (e.g. a tracker without position) while the others work
        return super().available and self._result is not None

    @property
    def native_value(self):
        result = self._result
        return self.entity_description.value_fn(result) if result else None

    @property
    def extra_state_attributes(self) -> dict | None:
        result = self._result
        if not result:
            return None
        attributes = self.entity_description.attributes_fn(result) if self.entity_description.attributes_fn else {}
        if result.get("person"):
            attributes["person"] = result["person"]
        return attributes or None

