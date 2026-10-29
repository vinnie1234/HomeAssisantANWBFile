from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SHOW_ON_MAP, DOMAIN
from .coordinator import ANWBFileCoordinator

CARD_URL = f"/{DOMAIN}/anwb-file-map-card.js"
CARD_PATH = Path(__file__).parent / "www" / "anwb-file-map-card.js"


def _platforms(entry: ConfigEntry) -> list[str]:
    options = {**entry.data, **entry.options}
    platforms = ["sensor"]
    if options.get(CONF_SHOW_ON_MAP, True):
        platforms.append("geo_location")
    return platforms


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the map card and load it in the frontend, once per Home Assistant run."""
    if hass.data.get(f"{DOMAIN}_card_registered"):
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    add_extra_js_url(hass, CARD_URL)
    hass.data[f"{DOMAIN}_card_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ANWBFileCoordinator(hass, entry)

    # A failed first fetch must not block setup: the sensors stay registered
    # (unavailable) and the coordinator retries at the configured interval.
    await coordinator.async_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    platforms = _platforms(entry)
    if "geo_location" in platforms:
        await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, _platforms(entry))


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
