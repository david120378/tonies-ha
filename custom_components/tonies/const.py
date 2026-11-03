"""Constants for the tonies integration."""

DOMAIN = "tonies"

TOKEN_URL = "https://login.tonies.com/auth/realms/tonies/protocol/openid-connect/token"
API_BASE = "https://api.prod.tcs.toys/v2"
CLIENT_ID = "my-tonies"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL_MINUTES = 15
MIN_SCAN_INTERVAL_MINUTES = 5

VOLUME_OPTIONS = ["25", "50", "75", "100"]
LED_OPTIONS = ["off", "dimmed", "on"]
TAP_OPTIONS = ["left", "right"]
