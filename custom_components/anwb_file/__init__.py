from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_READY
from .coordinator import ANWBFileCoordinator
from .websocket import async_register_websocket

WWW_URL = f"/{DOMAIN}"
WWW_PATH = Path(__file__).parent / "www"
CARD_FILE = "anwb-file-map-card.js"
FRONTEND_REGISTERED = f"{DOMAIN}_frontend_registered"


def _platforms(coordinator: ANWBFileCoordinator) -> list[str]:
    platforms = ["sensor"]
    if coordinator.map_categories:
        platforms.append("geo_location")
    return platforms


def _card_version() -> int:
    return int((WWW_PATH / CARD_FILE).stat().st_mtime)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card (and Leaflet) and load it in the frontend, once per run."""
    if hass.data.get(FRONTEND_REGISTERED):
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(WWW_URL, str(WWW_PATH), cache_headers=False)]
    )
    version = await hass.async_add_executor_job(_card_version)
    # The version in the URL makes browsers pick up a new card after an update
    add_extra_js_url(hass, f"{WWW_URL}/{CARD_FILE}?v={version}")
    async_register_websocket(hass)
    hass.data[FRONTEND_REGISTERED] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ANWBFileCoordinator(hass, entry)

    # A failed first fetch must not block setup: the sensors stay registered
    # (unavailable) and the coordinator retries at the configured interval.
    await coordinator.async_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await _async_register_frontend(hass)
    await hass.config_entries.async_forward_entry_setups(entry, _platforms(coordinator))
    async_dispatcher_send(hass, SIGNAL_READY)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(
        entry, _platforms(entry.runtime_data)
    )


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
