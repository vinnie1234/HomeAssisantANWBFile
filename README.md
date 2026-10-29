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
| Show on map | Create map markers and load the map card (default on) |

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

With **Show on map** enabled, every incident is a `geo_location` entity (source `anwb_file`), so the standard Map card shows it. Each marker has a coloured badge with an icon:

| Incident | Icon | Colour |
|---|---|---|
| Traffic jam | car | yellow = slow, orange = queueing, red = stationary or closed |
| Speed camera | flash | blue |
| Roadworks / closure | roadworker | grey |

```yaml
type: map
geo_location_sources:
  - anwb_file
```

### ANWB File card (coloured roads + text list)

The integration also ships its own card, which draws each jam as a **coloured line along the road** and lists everything in text underneath (sorted by delay):

```yaml
type: custom:anwb-file-map-card
show_list: true   # text list below the map (default true)
show_map: true    # set to false for a list only (default true)
height: 450       # map height in px (default 450)
```

The card is loaded automatically; if it is not found after setup, refresh the browser (Ctrl+F5). Without map markers you can still get a text list from the `jams` attribute of `sensor.anwb_file_traffic_jams`:

```yaml
type: markdown
content: >
  {% for j in state_attr('sensor.anwb_file_traffic_jams', 'jams') %}
  **{{ j.road }}** {{ j.from }} - {{ j.to }}: {{ j.length_km }} km, {{ j.delay_min }} min
  {% else %}Geen files{% endfor %}
```

## Installation

1. HACS → three dots → **Custom repositories** → `https://github.com/vinnie1234/HomeAssisantANWBFile`, category **Integration**
2. Download **ANWB File** and restart Home Assistant
3. **Settings → Devices & Services → + Add Integration → ANWB File**

## Notes

- Data comes from the public ANWB incident feed (`api.anwb.nl/routing/v1/incidents/incidents-desktop`); it is an unofficial API and may change.
- Be considerate with the refresh interval; the feed updates roughly every minute.

## License

MIT
