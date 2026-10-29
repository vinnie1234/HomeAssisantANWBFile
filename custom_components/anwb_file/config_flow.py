from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CATEGORIES,
    CONF_CATEGORIES,
    CONF_ROAD_SELECTION,
    CONF_ROAD_TYPE,
    CONF_ROADS,
    CONF_ROUTE_NAME,
    CONF_ROUTES,
    CONF_MAP_CATEGORIES,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAP_CATEGORIES,
    DEFAULT_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    ROAD_SELECTION_ALL,
    ROAD_SELECTION_SPECIFIC,
    ROAD_TYPE_A,
    ROAD_TYPE_FILTER,
    ROUTE_ENDS,
    ROUTE_ENTITY_DOMAINS,
    ROUTE_SOURCE_ENTITY,
    ROUTE_SOURCE_LOCATION,
)
from .coordinator import async_fetch_incidents, available_roads, normalize_road

_LOGGER = logging.getLogger(__name__)


def _settings_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    unit_of_measurement="min",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_ROAD_TYPE, default=defaults.get(CONF_ROAD_TYPE, ROAD_TYPE_A)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(ROAD_TYPE_FILTER),
                    translation_key=CONF_ROAD_TYPE,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_ROAD_SELECTION,
                default=defaults.get(CONF_ROAD_SELECTION, ROAD_SELECTION_ALL),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[ROAD_SELECTION_ALL, ROAD_SELECTION_SPECIFIC],
                    translation_key=CONF_ROAD_SELECTION,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_CATEGORIES, default=defaults.get(CONF_CATEGORIES, DEFAULT_MAP_CATEGORIES)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=CATEGORIES,
                    translation_key=CONF_CATEGORIES,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_MAP_CATEGORIES,
                default=defaults.get(CONF_MAP_CATEGORIES, DEFAULT_MAP_CATEGORIES),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=CATEGORIES,
                    translation_key=CONF_CATEGORIES,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        }
    )


class _ANWBFileFlowMixin:
    """Steps shared by the config flow and the options flow.

    Step 1 picks interval, road type, all/specific roads and categories;
    step 2 ("roads") only runs when specific roads were chosen.
    """

    _settings: dict[str, Any]

    def _defaults(self) -> dict:
        return {}

    def _finish(self, data: dict) -> FlowResult:
        raise NotImplementedError

    def _show_settings(self, step_id: str, errors: dict | None = None) -> FlowResult:
        return self.async_show_form(
            step_id=step_id,
            data_schema=_settings_schema(self._defaults()),
            errors=errors,
        )

    async def _handle_settings(self, step_id: str, user_input: dict | None) -> FlowResult:
        if user_input is None:
            return self._show_settings(step_id)

        if not user_input.get(CONF_CATEGORIES):
            return self._show_settings(step_id, {"base": "at_least_one_category"})

        self._settings = {
            **user_input,
            CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
            # Only categories that are tracked at all can be drawn on the map
            CONF_MAP_CATEGORIES: [
                c for c in user_input[CONF_MAP_CATEGORIES] if c in user_input[CONF_CATEGORIES]
            ],
        }
        if self._settings[CONF_ROAD_SELECTION] == ROAD_SELECTION_SPECIFIC:
            return await self.async_step_roads()
        return self._finish({**self._settings, CONF_ROADS: []})

    async def async_step_roads(self, user_input: dict | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            roads = list(dict.fromkeys(normalize_road(r) for r in user_input[CONF_ROADS] if r.strip()))
            if roads:
                return self._finish({**self._settings, CONF_ROADS: roads})
            errors["base"] = "at_least_one_road"

        selected = self._defaults().get(CONF_ROADS, [])
        try:
            raw = await async_fetch_incidents(self.hass)
            suggestions = available_roads(raw, self._settings[CONF_ROAD_TYPE])
        except Exception as err:  # noqa: BLE001 - suggestions are optional, typing roads still works
            _LOGGER.debug("Could not fetch ANWB roads for suggestions: %s", err)
            suggestions = []

        return self.async_show_form(
            step_id="roads",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROADS, default=selected): SelectSelector(
                        SelectSelectorConfig(
                            options=list(dict.fromkeys([*selected, *suggestions])),
                            multiple=True,
                            custom_value=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )


class ANWBFileConfigFlow(_ANWBFileFlowMixin, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self._handle_settings("user", user_input)

    def _finish(self, data: dict) -> FlowResult:
        return self.async_create_entry(title="ANWB File", data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ANWBFileOptionsFlow()


def _source_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[ROUTE_SOURCE_LOCATION, ROUTE_SOURCE_ENTITY],
            translation_key="route_source",
            mode=SelectSelectorMode.LIST,
        )
    )


class ANWBFileOptionsFlow(_ANWBFileFlowMixin, config_entries.OptionsFlow):
    _new_route: dict[str, Any]

    async def async_step_init(self, user_input=None) -> FlowResult:
        menu = ["settings", "add_route"]
        if self._routes():
            menu.append("remove_route")
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_settings(self, user_input=None) -> FlowResult:
        return await self._handle_settings("settings", user_input)

    async def async_step_add_route(self, user_input=None) -> FlowResult:
        """Name the route and choose how each end is given; the ends follow in the next steps."""
        if user_input is not None:
            self._new_route = {
                "id": uuid4().hex[:8],
                CONF_ROUTE_NAME: user_input[CONF_ROUTE_NAME].strip(),
                "sources": {end: user_input[f"{end}_source"] for end in ROUTE_ENDS},
            }
            return await self.async_step_origin()

        return self.async_show_form(
            step_id="add_route",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROUTE_NAME): str,
                    vol.Required("origin_source", default=ROUTE_SOURCE_LOCATION): _source_selector(),
                    vol.Required("destination_source", default=ROUTE_SOURCE_LOCATION): _source_selector(),
                }
            ),
        )

    async def async_step_origin(self, user_input=None) -> FlowResult:
        return await self._async_route_end("origin", user_input)

    async def async_step_destination(self, user_input=None) -> FlowResult:
        return await self._async_route_end("destination", user_input)

    async def _async_route_end(self, end: str, user_input: dict | None) -> FlowResult:
        """One end of the new route: a pinned location, or a zone/person/device tracker."""
        by_location = self._new_route["sources"][end] == ROUTE_SOURCE_LOCATION
        if user_input is not None:
            if by_location:
                location = user_input["location"]
                self._new_route[end] = {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                }
            else:
                self._new_route[end] = {"entity_id": user_input["entity"]}

            if end == "origin":
                return await self.async_step_destination()
            route = {k: v for k, v in self._new_route.items() if k != "sources"}
            return self._save_routes([*self._routes(), route])

        if by_location:
            home = {"latitude": self.hass.config.latitude, "longitude": self.hass.config.longitude}
            field = {vol.Required("location", default=home): LocationSelector()}
        else:
            field = {
                vol.Required("entity"): EntitySelector(EntitySelectorConfig(domain=ROUTE_ENTITY_DOMAINS))
            }
        return self.async_show_form(
            step_id=end,
            data_schema=vol.Schema(field),
            description_placeholders={"name": self._new_route[CONF_ROUTE_NAME]},
        )

    async def async_step_remove_route(self, user_input=None) -> FlowResult:
        if user_input is not None:
            removed = set(user_input[CONF_ROUTES])
            return self._save_routes([r for r in self._routes() if r["id"] not in removed])

        options = [SelectOptionDict(value=r["id"], label=r["name"]) for r in self._routes()]
        return self.async_show_form(
            step_id="remove_route",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROUTES): SelectSelector(
                        SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    def _defaults(self) -> dict:
        return {**self.config_entry.data, **self.config_entry.options}

    def _routes(self) -> list[dict]:
        return self._defaults().get(CONF_ROUTES, [])

    def _save_routes(self, routes: list[dict]) -> FlowResult:
        return self.async_create_entry(data={**self._defaults(), CONF_ROUTES: routes})

    def _finish(self, data: dict) -> FlowResult:
        # Saving the settings must keep the routes
        return self.async_create_entry(data={**data, CONF_ROUTES: self._routes()})
