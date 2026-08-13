"""Constants for the GIF Creator integration."""

DOMAIN = "gif"

SERVICE_CREATE_GIF = "create_gif"

ATTR_IMAGES = "images"
ATTR_CAMERA = "camera"
ATTR_COUNT = "count"
ATTR_INTERVAL = "interval"
ATTR_FPS = "fps"
ATTR_OUTPUT_PATH = "output_path"
ATTR_URL = "url"
ATTR_LOOP = "loop"

CAMERA_DOMAIN = "camera"

DEFAULT_FPS = 10
DEFAULT_LOOP = True
DEFAULT_COUNT = 10
DEFAULT_INTERVAL = 0.5
DEFAULT_IMAGES_PREFIX = "images"
WWW_DIRNAME = "www"
WWW_GIF_DIRNAME = "gif"
MIN_FPS = 1
MAX_FPS = 60
MIN_IMAGES = 2
MIN_COUNT = MIN_IMAGES
MAX_COUNT = 60
MIN_INTERVAL = 0.1
MAX_INTERVAL = 10.0

STATE_UNAVAILABLE = "unavailable"
STATE_UNKNOWN = "unknown"
