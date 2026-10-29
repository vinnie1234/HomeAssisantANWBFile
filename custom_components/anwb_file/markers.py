"""Colour and icon for an incident, shared by the map markers and the map card."""

from __future__ import annotations

from urllib.parse import quote

from .const import CATEGORY_JAMS, CATEGORY_RADARS, CATEGORY_ROADWORKS

COLOR_YELLOW = "#fbc02d"
COLOR_ORANGE = "#f57c00"
COLOR_RED = "#d32f2f"
COLOR_RADAR = "#1976d2"
COLOR_ROADWORKS = "#607d8b"

# Jams get yellow/orange/red by how bad the ANWB says the traffic is
JAM_COLORS = {
    "slow-traffic": COLOR_YELLOW,
    "queing-traffic": COLOR_ORANGE,  # sic: ANWB's spelling
    "stationary-traffic": COLOR_RED,
    "road-closed": COLOR_RED,
}

# Material Design Icons (24x24): car-multiple, camera-wireless, account-hard-hat
_MDI_CAR = (
    "M8,11L9.5,6.5H18.5L20,11M18.5,16A1.5,1.5 0 0,1 17,14.5A1.5,1.5 0 0,1 18.5,13A1.5,1.5 0 0,1 20,14.5A1.5,1.5 0 0,1 18.5,16M9.5,16A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 9.5,13A1.5,1.5 0 0,1 11,14.5A1.5,1.5 0 0,1 9.5,16M19.92,6C19.71,5.4 19.14,5 18.5,5H9.5C8.86,5 8.29,5.4 8.08,6L6,12V20A1,1 0 0,0 7,21H8A1,1 0 0,0 9,20V19H19V20A1,1 0 0,0 20,21H21A1,1 0 0,0 22,20V12L19.92,6M14.92,3C14.71,2.4 14.14,2 13.5,2H4.5C3.86,2 3.29,2.4 3.08,3L1,9V17A1,1 0 0,0 2,18H3A1,1 0 0,0 4,17V12.91C3.22,12.63 2.82,11.77 3.1,11C3.32,10.4 3.87,10 4.5,10H4.57L5.27,8H3L4.5,3.5H15.09L14.92,3Z"
)
_MDI_CAMERA = "M12,10.8A3.2,3.2 0 0,1 15.2,14A3.2,3.2 0 0,1 12,17.2A3.2,3.2 0 0,1 8.8,14A3.2,3.2 0 0,1 12,10.8M16,3.33V2A6,6 0 0,1 22,8H20.67C20.67,5.42 18.58,3.33 16,3.33M16,6V4.67C17.84,4.67 19.33,6.16 19.33,8H18C18,6.89 17.11,6 16,6M17,9H22V20A2,2 0 0,1 20,22H4A2,2 0 0,1 2,20V8A2,2 0 0,1 4,6H7.17L9,4H15V7C16.11,7 17,7.89 17,9M12,19A5,5 0 0,0 17,14A5,5 0 0,0 12,9A5,5 0 0,0 7,14A5,5 0 0,0 12,19Z"
_MDI_WORKER = (
    "M12,15C7.58,15 4,16.79 4,19V21H20V19C20,16.79 16.42,15 12,15M8,9A4,4 0 0,0 12,13A4,4 0 0,0 16,9M11.5,2C11.2,2 11,2.21 11,2.5V5.5H10V3C10,3 7.75,3.86 7.75,6.75C7.75,6.75 7,6.89 7,8H17C16.95,6.89 16.25,6.75 16.25,6.75C16.25,3.86 14,3 14,3V5.5H13V2.5C13,2.21 12.81,2 12.5,2H11.5Z"
)
_ICON_PATHS = {
    CATEGORY_JAMS: _MDI_CAR,
    CATEGORY_RADARS: _MDI_CAMERA,
    CATEGORY_ROADWORKS: _MDI_WORKER,
}


def incident_color(category: str, incident_type: str | None) -> str:
    if category == CATEGORY_JAMS:
        return JAM_COLORS.get(incident_type, COLOR_ORANGE)
    if category == CATEGORY_RADARS:
        return COLOR_RADAR
    return COLOR_ROADWORKS


def marker_picture(category: str, color: str) -> str:
    """A round coloured badge with a white icon, as an inline SVG data URI."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<circle cx="12" cy="12" r="11.5" fill="{color}" stroke="#fff" stroke-width="1"/>'
        f'<path transform="translate(4.8 4.8) scale(.6)" fill="#fff" d="{_ICON_PATHS[category]}"/>'
        "</svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)
