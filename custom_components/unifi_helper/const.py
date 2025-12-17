"""Constants for the UniFi Helper integration."""

DOMAIN = "unifi_helper"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # seconds

# UniFi integration constants
UNIFI_DOMAIN = "unifi"

# Entity attributes
ATTR_DEVICE_ID = "device_id"
ATTR_PORT_IDX = "port_idx"

# Sensor types
SENSOR_TYPE_POE_POWER = "poe_power"
SENSOR_TYPE_ENERGY = "energy"

# Unit conversions
WATTS_TO_KILOWATTS = 0.001
SECONDS_TO_HOURS = 1 / 3600
