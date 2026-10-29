# ANWB File

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=vinnie1234&repository=HomeAssisantANWBFile&category=integration)
[![Open your Home Assistant instance](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=anwb_file)

Live traffic information from **ANWB**: traffic jams (files), speed cameras (flitsers) and roadworks, as sensors and as markers on the Home Assistant map.

## Setup options

When adding the integration (and later via **Configure**) you choose:

| Option | Choices |
|---|---|
| Refresh interval | 1 - 60 minutes (default 5) |
| Road types | A roads only / A and N roads / all roads (incl. city ring roads) |
| Roads | All roads, or specific roads (pick from the list or type e.g. `A2`, `N201`) |
| Incidents | Traffic jams, speed cameras, roadworks and closures (default: jams and speed cameras) |
| Show on map | Which of those get a marker on the map (default: jams and speed cameras). The card list always shows everything you track |

Changing the options reloads the integration.

## Sensors

| Sensor | Description |
|---|---|
| `sensor.anwb_file_traffic_jams` | Number of jams, with a `jams` attribute listing them |
| `sensor.anwb_file_traffic_jam_length` | Total jam length (km) |
| `sensor.anwb_file_traffic_jam_delay` | Total delay (minutes) |
| `sensor.anwb_file_roadworks` | Number of roadworks / closures, with a `roadworks` attribute |
| `sensor.anwb_file_speed_cameras` | Number of speed cameras, with a `radars` attribute |
| `sensor.anwb_file_traffic_jams_<road>` | Only when specific roads are selected: jams per road |

Sensors only exist for the incident types you selected.

## ANWB File card

A dashboard card that works like anwb.nl/verkeer: a list grouped per road next to a map.

```yaml
type: custom:anwb-file-map-card
radius_km: 20   # initial map view: your Home Assistant location + this radius (default 20)
height: 640     # card height in px on wide screens (default 640)
```

- **List per road** with a road badge (A red, N yellow), number of jams / roadworks / speed cameras, total delay and length. Click a road to expand it: per direction you see the stretch, delay, length, the situation text and the period for roadworks.
- **Bekijk op kaart** zooms the map to that incident and opens its details.
- **Search** on road, place or situation text, and **filter chips** for jams, roadworks and speed cameras. The map follows the search and filters.
- **Map** with jams drawn as a coloured line along the road (yellow = slow, orange = queueing, red = stationary or closed) and a round icon marker per incident: car (jam), roadworker (roadworks), flash (speed camera). The map starts zoomed on your Home Assistant location; buttons jump back there or to all of the Netherlands.
- Follows the light/dark theme and switches to a stacked layout on narrow screens.

The card is added automatically by the integration; if it is not found after setup, refresh the browser (Ctrl+F5). Which incidents are drawn on the map is set in the integration options (**Show on the map**). Incidents you track but do not put on the map stay in the list, and "Bekijk op kaart" still shows them.

## Standard Map card

When at least one category is set to show on the map, those incidents are also `geo_location` entities (source `anwb_file`) with a coloured icon badge, so Home Assistant's own Map card can show them too:

```yaml
type: map
geo_location_sources:
  - anwb_file
```

The map in the ANWB File card uses OpenStreetMap tiles (Leaflet is bundled, see `www/LEAFLET-LICENSE.txt`).

## Installation

1. HACS → three dots → **Custom repositories** → `https://github.com/vinnie1234/HomeAssisantANWBFile`, category **Integration**
2. Download **ANWB File** and restart Home Assistant
3. **Settings → Devices & Services → + Add Integration → ANWB File**

## Notes

- Data comes from the public ANWB incident feed (`api.anwb.nl/routing/v1/incidents/incidents-desktop`); it is an unofficial API and may change.
- Be considerate with the refresh interval; the feed updates roughly every minute.

## License

MIT
