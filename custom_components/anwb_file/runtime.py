from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.core import callback

from .coordinator import ANWBFileCoordinator
from .routing import ANWBRoutesCoordinator


@dataclass
class ANWBFileRuntime:
    """Everything a config entry runs: the incident feed and the routes."""

    incidents: ANWBFileCoordinator
    routes: ANWBRoutesCoordinator

    def payload(self) -> dict:
        return {**self.incidents.payload(), "routes": self.routes.payload()}

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        unsubscribe = [
            self.incidents.async_add_listener(update),
            self.routes.async_add_listener(update),
        ]

        @callback
        def _remove() -> None:
            for remove in unsubscribe:
                remove()

        return _remove
