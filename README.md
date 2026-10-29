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

## Map

Every incident is also a `geo_location` entity (source `anwb_file`) with latitude and longitude, so the standard **Map** card and dashboard panel draw it. Jams and roadworks sit at the start of the incident (where you meet the tail). The `path` attribute holds the full route as `[lat, lon]` points.

```yaml
type: map
geo_location_sources:
  - anwb_file
```

Entities appear and disappear as ANWB reports and clears incidents. Their `icon`s differ per type (cars for jams, camera for speed cameras, cone for roadworks).

## Installation

1. HACS → three dots → **Custom repositories** → `https://github.com/vinnie1234/HomeAssisantANWBFile`, category **Integration**
2. Download **ANWB File** and restart Home Assistant
3. **Settings → Devices & Services → + Add Integration → ANWB File**

## Notes

- Data comes from the public ANWB incident feed (`api.anwb.nl/routing/v1/incidents/incidents-desktop`); it is an unofficial API and may change.
- Be considerate with the refresh interval; the feed updates roughly every minute.

## License

MIT
