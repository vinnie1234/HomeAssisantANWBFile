"""Websocket feed for the ANWB File card.

The card needs every incident (with its path) regardless of which ones are
exposed as map entities, so it subscribes here instead of reading entity states.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_READY
from .runtime import ANWBFileRuntime


def _loaded_runtime(hass: HomeAssistant) -> ANWBFileRuntime | None:
    # SETUP_IN_PROGRESS: SIGNAL_READY is sent before Home Assistant marks the entry LOADED
    active = (ConfigEntryState.LOADED, ConfigEntryState.SETUP_IN_PROGRESS)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state in active:
            return getattr(entry, "runtime_data", None)
    return None


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    unsubscribe_runtime = None

    @callback
    def _attach() -> None:
        # Also runs when the integration is reloaded (options changed): the old
        # runtime is gone, so move this subscription to the new one.
        nonlocal unsubscribe_runtime
        if unsubscribe_runtime:
            unsubscribe_runtime()
            unsubscribe_runtime = None
        runtime = _loaded_runtime(hass)
        if runtime is None:
            return

        @callback
        def _send() -> None:
            connection.send_message(websocket_api.event_message(msg["id"], runtime.payload()))

        unsubscribe_runtime = runtime.async_add_listener(_send)
        _send()

    unsubscribe_signal = async_dispatcher_connect(hass, SIGNAL_READY, _attach)

    @callback
    def _unsubscribe() -> None:
        unsubscribe_signal()
        if unsubscribe_runtime:
            unsubscribe_runtime()

    connection.subscriptions[msg["id"]] = _unsubscribe
    connection.send_result(msg["id"])
    _attach()
