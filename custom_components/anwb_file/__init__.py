from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import ANWBFileCoordinator

PLATFORMS = ["sensor", "geo_location"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ANWBFileCoordinator(hass, entry)

    # A failed first fetch must not block setup: the sensors stay registered
    # (unavailable) and the coordinator retries at the configured interval.
    await coordinator.async_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
