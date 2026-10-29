DOMAIN = "anwb_file"

API_URL = "https://api.anwb.nl/routing/v1/incidents/incidents-desktop"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_ROAD_TYPE = "road_type"
CONF_ROAD_SELECTION = "road_selection"
CONF_ROADS = "roads"
CONF_CATEGORIES = "categories"
CONF_MAP_CATEGORIES = "map_categories"

DEFAULT_SCAN_INTERVAL = 5  # minutes
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 60

# Road types as used by the ANWB API ("other" are city ring roads like "Arnhem")
ROAD_TYPE_A = "a"
ROAD_TYPE_A_N = "a_n"
ROAD_TYPE_ALL = "all"
ROAD_TYPE_FILTER = {
    ROAD_TYPE_A: {"a"},
    ROAD_TYPE_A_N: {"a", "n"},
    ROAD_TYPE_ALL: {"a", "n", "other"},
}

ROAD_SELECTION_ALL = "all"
ROAD_SELECTION_SPECIFIC = "specific"

# Incident categories as used by the ANWB API
CATEGORY_JAMS = "jams"
CATEGORY_ROADWORKS = "roadworks"
CATEGORY_RADARS = "radars"
CATEGORIES = [CATEGORY_JAMS, CATEGORY_ROADWORKS, CATEGORY_RADARS]

# Shown on the map by default; roadworks/closures are numerous and clutter it
DEFAULT_MAP_CATEGORIES = [CATEGORY_JAMS, CATEGORY_RADARS]

SIGNAL_READY = f"{DOMAIN}_ready"

API_ROUTE_URL = "https://api.anwb.nl/routing/route/v1/route/car"

# Routes live in the entry options as a list of
# {"id", "name", "origin", "destination"}; an end is {"entity_id"} or {"latitude", "longitude"}
CONF_ROUTES = "routes"
CONF_ROUTE_NAME = "name"
ROUTE_ENDS = ("origin", "destination")
ROUTE_ENTITY_DOMAINS = ["zone", "person", "device_tracker"]
ROUTE_SOURCE_LOCATION = "location"
ROUTE_SOURCE_ENTITY = "entity"
