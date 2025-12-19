# Technical Documentation - UniFi Energy Helper

## Architecture Overview

UniFi Energy Helper is a Home Assistant custom component that extends the built-in UniFi Network integration by creating synthetic energy accumulation sensors for PoE-capable network switches.

## Component Structure

```
custom_components/unifi_energy_helper/
├── __init__.py         # Component initialization and setup
├── const.py           # Constants and configuration defaults
├── manifest.json      # Component metadata and dependencies
├── sensor.py          # Energy sensor implementation
└── strings.json       # UI strings and translations
```

## How It Works

### 1. Discovery Phase

When Home Assistant loads the integration (via `configuration.yaml`), the sensor platform performs entity discovery:

```python
# In sensor.py - async_setup_platform()
entity_registry = er.async_get(hass)

for entity_id, entry in entity_registry.entities.items():
    if (entry.platform == "unifi" and 
        entry.device_class == SensorDeviceClass.POWER and
        entry.unit_of_measurement == UnitOfPower.WATT and
        ("port" in entity_id.lower() or "poe" in entity_id.lower())):
        # Found a PoE power sensor!
```

**Discovery Criteria:**
- Entity platform must be `unifi`
- Device class must be `POWER`
- Unit of measurement must be `WATT`
- Entity ID or unique ID contains "port" or "poe"
- Entity must have a `device_id` (linked to a device)

### 2. Grouping Phase

PoE power sensors are grouped by their parent device (the UniFi switch):

```python
device_poe_map = {}  # device_id → [entity_id, entity_id, ...]

for entity_id, entry in poe_entities:
    if entry.device_id not in device_poe_map:
        device_poe_map[entry.device_id] = []
    device_poe_map[entry.device_id].append(entity_id)
```

This ensures one energy sensor per switch device, regardless of how many PoE ports it has.

### 3. Sensor Creation

For each device with PoE ports, an `UniFiEnergyAccumulationSensor` is created:

```python
class UniFiEnergyAccumulationSensor(RestoreSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
```

**Key Properties:**
- **Device Class**: `ENERGY` - Tells HA this is an energy sensor
- **State Class**: `TOTAL_INCREASING` - Enables Energy Dashboard integration
- **Unit**: `kWh` - Standard energy unit
- **Restoration**: Inherits from `RestoreSensor` to preserve state across restarts

### 4. Device Linking

To make the energy sensor appear under the same device as the switch:

```python
async def async_added_to_hass(self):
    # Link to the existing UniFi device
    entity_registry = er.async_get(self.hass)
    entity_registry.async_update_entity(
        self.entity_id,
        device_id=self._device_id,
    )
```

This updates the entity registry to associate the energy sensor with the UniFi device, making it appear in the same device card in the UI.

### 5. Energy Accumulation

Every 60 seconds (configurable via `DEFAULT_SCAN_INTERVAL`), the sensor updates:

```python
@callback
async def _async_update(self, now: datetime | None = None):
    current_time = dt_util.utcnow()
    time_delta_seconds = (current_time - self._last_update).total_seconds()
    
    # Sum power from all PoE ports
    total_power_watts = sum([
        float(self.hass.states.get(entity_id).state)
        for entity_id in self._poe_entity_ids
        if state is valid
    ])
    
    # Calculate energy: P (W) × t (s) / 3600 / 1000 = E (kWh)
    energy_increment_kwh = (
        total_power_watts * 
        time_delta_seconds * 
        SECONDS_TO_HOURS * 
        WATTS_TO_KILOWATTS
    )
    
    self._total_energy_kwh += energy_increment_kwh
```

**Energy Calculation:**
```
Energy (kWh) = Power (W) × Time (s) × (1/3600 s/h) × (1/1000 W/kW)
```

Example:
- Power: 55W (from 3 PoE ports: 15W + 30W + 10W)
- Time: 60 seconds
- Energy: 55 × 60 × (1/3600) × (1/1000) = 0.000917 kWh
- After 1 hour: ~0.055 kWh

### 6. State Restoration

When Home Assistant restarts, the sensor restores its previous value:

```python
async def async_added_to_hass(self):
    last_sensor_data = await self.async_get_last_sensor_data()
    
    if last_sensor_data and last_sensor_data.native_value:
        self._total_energy_kwh = float(last_sensor_data.native_value)
```

This ensures energy accumulation continues seamlessly across restarts.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ loads integration
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              UniFi Energy Helper Integration                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Discovery: Scan entity registry for PoE sensors  │   │
│  └──────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 2. Grouping: Group sensors by device_id             │   │
│  └──────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 3. Create energy sensor for each device             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           UniFi Energy Accumulation Sensor                   │
│                                                              │
│  Every 60 seconds:                                           │
│  ┌────────────────────────────────────────────────┐         │
│  │ 1. Read power from all PoE port sensors       │         │
│  │    (sensor.switch_port_1_poe_power, etc.)     │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 2. Calculate time delta since last update     │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 3. Calculate energy increment                 │         │
│  │    E = P × Δt / 3600 / 1000                   │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 4. Add to total accumulated energy            │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 5. Update state in Home Assistant             │         │
│  │    sensor.switch_poe_energy = X.XXX kWh       │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│            Home Assistant Energy Dashboard                   │
│  • Visualizes energy consumption over time                  │
│  • Shows cost calculations (if configured)                  │
│  • Compares with other energy sources                       │
└─────────────────────────────────────────────────────────────┘
```

## Dependencies

### Hard Dependencies

- **homeassistant.components.sensor**: Core sensor platform
- **homeassistant.helpers.entity_registry**: Entity discovery and management
- **homeassistant.helpers.event**: Periodic update scheduling

### Soft Dependencies

- **unifi**: The integration depends on the UniFi integration being configured
  - Specified in `manifest.json`: `"dependencies": ["unifi"]`
  - Home Assistant ensures UniFi loads before UniFi Energy Helper

## Configuration

### manifest.json

```json
{
  "domain": "unifi_energy_helper",
  "name": "UniFi Energy Helper",
  "dependencies": ["unifi"],
  "integration_type": "device",
  "iot_class": "local_polling",
  "version": "1.0.0"
}
```

**Key Fields:**
- `dependencies`: Ensures UniFi integration loads first
- `integration_type`: "device" - associates with devices
- `iot_class`: "local_polling" - reads data periodically from local entities

### Constants (const.py)

```python
DOMAIN = "unifi_energy_helper"
UNIFI_DOMAIN = "unifi"
DEFAULT_SCAN_INTERVAL = 60  # seconds
WATTS_TO_KILOWATTS = 0.001
SECONDS_TO_HOURS = 1 / 3600
```

## Entity Registry Integration

The component heavily relies on Home Assistant's entity registry:

1. **Discovery**: Scans registry to find existing UniFi PoE sensors
2. **Device Linking**: Updates registry to link energy sensors to devices
3. **State Restoration**: Uses registry to restore previous energy values

## Performance Considerations

### Memory Usage

- **Per Energy Sensor**:
  - ~1KB for sensor state
  - List of PoE entity IDs (8-16 entities typically)
  - Total: ~2-3KB per device

### CPU Usage

- **Every 60 seconds per sensor**:
  - Read 8-16 entity states: ~1ms
  - Calculate energy increment: <0.1ms
  - Update state: ~1ms
  - **Total**: ~2-3ms per sensor per minute

### Database Impact

- **State updates**: Once per 60 seconds per sensor
- **Size**: ~100 bytes per state update
- **Daily**: 1,440 updates × 100 bytes = ~140KB per sensor per day

## Security Considerations

1. **Read-only**: Component only reads existing sensor states
2. **No network access**: No external connections
3. **No user data**: No personal information stored
4. **Local only**: All processing is local to Home Assistant

## Testing Approach

### Manual Testing

1. **Setup**: Configure UniFi integration with PoE switch
2. **Install**: Add unifi_energy_helper to configuration
3. **Verify**: Check energy sensor appears under device
4. **Monitor**: Observe energy accumulation over time
5. **Restart**: Verify state restoration works

### Test Scenarios

| Scenario | Expected Behavior |
|----------|------------------|
| No PoE sensors | Warning logged, no sensors created |
| PoE sensors unavailable | Energy accumulation pauses, no errors |
| Home Assistant restart | Energy value restored from previous state |
| UniFi integration removed | Energy sensor becomes unavailable |
| Multiple switches | One energy sensor per switch |

## Future Enhancements

Potential improvements for future versions:

1. **Configurable scan interval**: Allow users to customize update frequency
2. **Per-port energy**: Option to create energy sensors per port
3. **Statistics**: Add min/max/avg power attributes
4. **Notifications**: Alert when power exceeds thresholds
5. **Cost calculation**: Built-in cost per kWh tracking
6. **Historical data**: Export energy data to CSV

## Contributing

When contributing to this component:

1. Follow [Home Assistant development guidelines](https://developers.home-assistant.io/)
2. Maintain Python 3.11+ compatibility
3. Use type hints throughout
4. Add docstrings to all functions/classes
5. Test with multiple UniFi switch models
6. Update this documentation for any architectural changes

## References

- [Home Assistant Sensor Platform](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [Energy Dashboard Integration](https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics)
- [Entity Registry](https://developers.home-assistant.io/docs/core/entity-registry/)
- [RestoreSensor](https://developers.home-assistant.io/docs/core/entity/sensor/#restoring-sensor-states)
