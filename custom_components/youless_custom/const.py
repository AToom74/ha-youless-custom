"""Constants for the YouLess (custom) integration."""

from __future__ import annotations

import logging

DOMAIN = "youless_custom"
LOGGER = logging.getLogger(__package__)

# Config / options keys
CONF_HOST = "host"
CONF_NAME = "name"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "YouLess"
# The YouLess device itself uses a 2s HTTP timeout, so keep the interval
# comfortably above that. 10s matches the behaviour of the built-in integration.
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 3600
