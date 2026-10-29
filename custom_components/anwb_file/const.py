DOMAIN = "anwb_file"

API_URL = "https://api.anwb.nl/routing/v1/incidents/incidents-desktop"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_ROAD_TYPE = "road_type"
CONF_ROAD_SELECTION = "road_selection"
CONF_ROADS = "roads"
CONF_CATEGORIES = "categories"

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
