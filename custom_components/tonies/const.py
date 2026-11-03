"""Constants for the tonies integration."""

from datetime import timedelta

DOMAIN = "tonies"

TOKEN_URL = "https://login.tonies.com/auth/realms/tonies/protocol/openid-connect/token"
API_BASE = "https://api.prod.tcs.toys/v2"
CLIENT_ID = "my-tonies"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

VOLUME_OPTIONS = ["25", "50", "75", "100"]
LED_OPTIONS = ["off", "dimmed", "on"]
TAP_OPTIONS = ["left", "right"]
