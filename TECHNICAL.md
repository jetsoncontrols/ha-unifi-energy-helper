# Technical Documentation - UniFi Energy Helper

## Architecture Overview

UniFi Energy Helper is a Home Assistant custom component that extends the built-in UniFi Network integration by creating synthetic energy accumulation sensors for PoE-capable network switches.

## Component Structure

```
custom_components/unifi_energy_helper/
├── __init__.py         # Component initialization and platform setup coordination
├── button.py          # Reset button entities
├── config_flow.py     # UI-based configuration flow
├── const.py           # Constants and configuration defaults
├── manifest.json      # Component metadata and dependencies
├── sensor.py          # Energy accumulation sensors with state restoration
└── strings.json       # UI strings and translations
```

## How It Works

### 1. Discovery Phase

When Home Assistant loads the integration (via config flow), the sensor platform performs entity discovery:

```python
# In sensor.py - async_setup_entry()
entity_registry = er.async_get(hass)

for entity_id, entry in entity_registry.entities.items():
    if _is_poe_power_entity(entry):
        # Found a PoE power sensor!
        poe_entities.append((entity_id, entry))
```

**Discovery Criteria (_is_poe_power_entity):**
- Entity platform must be `unifi`
- Must start with `sensor.`
- Device class must be `POWER`
- Unit of measurement must be `WATT`
- Entity ID or unique ID contains "port" or "poe"
- Entity must have a `device_id` (linked to a device)
- Entity must not be disabled (`disabled_by is None`)

### 2. Per-Port Sensor Creation

For each discovered PoE power sensor, an individual energy sensor is created:

```python
for poe_entity_id, poe_entry in poe_entities:
    energy_sensor = UniFiEnergyAccumulationSensor(
        hass=hass,
        device_id=poe_entry.device_id,
        poe_entity_id=poe_entity_id,
        poe_entity_entry=poe_entry,
        config_entry_id=config_entry.entry_id,
    )
    energy_sensors.append(energy_sensor)
```

This creates **one energy sensor per PoE port**, allowing granular tracking of individual port consumption.

### 3. Energy Sensor Properties

Each `UniFiEnergyAccumulationSensor` has these properties:

```python
class UniFiEnergyAccumulationSensor(RestoreSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_should_poll = False  # Event-driven, no polling
    _attr_entity_category = EntityCategory.DIAGNOSTIC
```

**Key Properties:**
- **Device Class**: `ENERGY` - Tells HA this is an energy sensor
- **State Class**: `TOTAL_INCREASING` - Enables Energy Dashboard integration
- **Unit**: `kWh` - Standard energy unit
- **Should Poll**: `False` - Uses event listeners instead of polling
- **Entity Category**: `DIAGNOSTIC` - Marks as diagnostic/utility entity
- **Restoration**: Inherits from `RestoreSensor` to preserve state across restarts

### 4. Device Linking

Both energy sensors and reset buttons link to the existing UniFi device:

```python
# In sensor.py and button.py
async def async_added_to_hass(self):
    # Link to the existing UniFi device
    entity_registry = er.async_get(self.hass)
    
    @callback
    def _async_update_device():
        if self.entity_id:
            entity_registry.async_update_entity(
                self.entity_id,
                device_id=self._device_id,
            )
    
    _async_update_device()
```

This ensures all entities appear grouped under the UniFi switch device in the UI.

### 5. Event-Driven Energy Accumulation

Energy accumulation happens **immediately** when power changes, using event listeners:

```python
# Set up state change listener
self._unsub_update = async_track_state_change_event(
    self.hass,
    [self._poe_entity_id],
    self._async_power_changed,
)

@callback
def _async_power_changed(self, event) -> None:
    new_state = event.data.get("new_state")
    new_power_watts = float(new_state.state)
    current_time = dt_util.utcnow()
    
    # Calculate energy increment since last update
    self._calculate_energy_increment(current_time, new_power_watts)
    self.async_write_ha_state()
```

**Energy Calculation (Riemann Sum - Left Endpoint):**
```python
def _calculate_energy_increment(self, current_time, new_power_watts):
    if self._last_update_time and self._last_power_watts:
        time_delta_seconds = (current_time - self._last_update_time).total_seconds()
        
        # Use previous power for the elapsed time period
        energy_increment_kwh = (
            self._last_power_watts *
            time_delta_seconds *
            SECONDS_TO_HOURS *
            WATTS_TO_KILOWATTS
        )
        
        self._total_energy_kwh += energy_increment_kwh
    
    # Update tracking variables
    self._last_power_watts = new_power_watts
    self._last_update_time = current_time
```

**Example:**
- Port drawing 15W for 1 hour
- Energy: 15W × 3600s × (1/3600) × (1/1000) = 0.015 kWh
- Updates happen in real-time as power changes, not on a schedule

### 6. State Restoration

When Home Assistant restarts, the sensor restores its previous value:

```python
async def async_added_to_hass(self):
    await super().async_added_to_hass()
    
    last_sensor_data = await self.async_get_last_sensor_data()
    
    if last_sensor_data and last_sensor_data.native_value is not None:
        try:
            self._total_energy_kwh = float(last_sensor_data.native_value)
            _LOGGER.info(
                "Restored energy state for %s: %.3f kWh",
                self._poe_entity_id,
                self._total_energy_kwh,
            )
        except (ValueError, TypeError):
            _LOGGER.warning("Could not restore energy state, starting from 0")
```

This ensures energy accumulation continues seamlessly across restarts.

### 7. Reset Button Integration

Each energy sensor has an associated reset button:

```python
class UniFiEnergyResetButton(ButtonEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    async def async_press(self) -> None:
        # Call reset method directly on the sensor
        if hasattr(self._energy_sensor, "_reset_energy"):
            self._energy_sensor._reset_energy()
```

The reset button calls the sensor's reset method:

```python
@callback
def _reset_energy(self) -> None:
    _LOGGER.info("Resetting energy for %s from %.3f kWh to 0")
    self._total_energy_kwh = 0.0
    self._last_update_time = dt_util.utcnow()
    # Keep last power reading to continue tracking
    self.async_write_ha_state()
```

### 8. Dynamic Entity Creation

The integration listens for new or enabled PoE entities:

```python
@callback
def _async_entity_registry_updated(event) -> None:
    action = event.data["action"]
    
    if action == "create" or (action == "update" and entity_was_enabled):
        entity_id = event.data["entity_id"]
        
        if _is_poe_power_entity(entry) and not already_tracked:
            # Create new energy sensor and button
            energy_sensor = UniFiEnergyAccumulationSensor(...)
            async_add_entities([energy_sensor], True)
            
            reset_button = UniFiEnergyResetButton(...)
            button_add_entities([reset_button], True)
```

This allows automatic detection of:
- Newly discovered PoE ports
- Previously disabled PoE entities that are enabled

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ loads integration (config flow)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              UniFi Energy Helper Integration                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Discovery: Scan entity registry for PoE sensors  │   │
│  │    - Find all enabled UniFi PoE power entities      │   │
│  └──────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 2. Create energy sensor for EACH PoE port          │   │
│  │    - One sensor per port, not per device           │   │
│  └──────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 3. Create reset button for each energy sensor      │   │
│  └──────────────────────────────────────────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 4. Set up entity registry listener                 │   │
│  │    - Detect new/enabled PoE entities dynamically   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      UniFi Energy Accumulation Sensor (per port)            │
│                                                              │
│  On state change event (real-time):                         │
│  ┌────────────────────────────────────────────────┐         │
│  │ 1. Power state changes for PoE port            │         │
│  │    Event: sensor.switch_port_1_poe_power       │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 2. Calculate time delta since last change     │         │
│  │    Δt = current_time - last_update_time        │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 3. Calculate energy using PREVIOUS power      │         │
│  │    E = P_previous × Δt / 3600 / 1000           │         │
│  │    (Riemann sum - left endpoint)               │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 4. Add increment to total energy              │         │
│  │    total_kwh += energy_increment_kwh           │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 5. Update tracking variables                  │         │
│  │    last_power = new_power                      │         │
│  │    last_update_time = current_time             │         │
│  └────────────────────────────────────────────────┘         │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐         │
│  │ 6. Write state to Home Assistant              │         │
│  │    sensor.switch_port_1_energy = X.XXX kWh     │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Reset Button (per sensor)                   │
│  ┌────────────────────────────────────────────────┐         │
│  │ When pressed:                                  │         │
│  │ • Call sensor._reset_energy()                  │         │
│  │ • Set total_energy_kwh = 0.0                   │         │
│  │ • Keep tracking current power                  │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│            Home Assistant Energy Dashboard                   │
│  • Visualizes per-port energy consumption                   │
│  • Shows cost calculations (if configured)                  │
│  • Can track multiple ports individually                    │
│  • Add all ports for total switch consumption               │
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
  "codeowners": ["@jetsoncontrols"],
  "config_flow": true,
  "dependencies": ["unifi"],
  "integration_type": "helper",
  "iot_class": "local_polling",
  "requirements": [],
  "version": "2.0.0"
}
```

**Key Fields:**
- `config_flow`: `true` - Uses UI-based configuration
- `dependencies`: Ensures UniFi integration loads first
- `integration_type`: "helper" - Provides helper functionality
- `iot_class`: "local_polling" - Monitors local entity state changes
- `version`: "2.0.0" - Current version with per-port tracking

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
  - Reference to one PoE entity ID
  - Tracking variables (power, time)
  - Total: ~1-2KB per port sensor

- **Per Reset Button**:
  - ~500 bytes for button state
  - Reference to energy sensor
  - Total: ~500 bytes per button

### CPU Usage

- **Event-driven (on power change)**:
  - State change event handler: <0.5ms
  - Calculate time delta: <0.1ms
  - Calculate energy increment: <0.1ms
  - Update state: ~1ms
  - **Total**: ~2ms per power change per port

- **Idle**: No CPU usage when power is stable

### Database Impact

- **State updates**: Only when power changes (variable frequency)
- **Size**: ~100 bytes per state update
- **Daily estimate**: Depends on device power fluctuations
  - Stable device (few changes): ~50 updates/day = ~5KB
  - Variable device (frequent changes): ~500 updates/day = ~50KB

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
| Home Assistant restart | Energy values restored from previous state |
| UniFi integration removed | Energy sensors become unavailable |
| Multiple switches | One energy sensor per PoE port per switch |
| Reset button pressed | Energy resets to 0, tracking continues |
| New PoE port enabled | Sensor and button created dynamically |
| PoE port disabled | Energy sensor becomes unavailable |
| Power changes frequently | Each change accumulates correctly |

## Future Enhancements

Potential improvements for future versions:

1. **Aggregated sensors**: Option to create device-level total energy sensors
2. **Statistics**: Add min/max/avg power attributes to energy sensors
3. **Notifications**: Alert when power or energy exceeds thresholds
4. **Cost calculation**: Built-in cost per kWh tracking per port
5. **Historical data**: Export energy data to CSV
6. **Auto-reset**: Schedule automatic resets (daily, weekly, monthly)
7. **Power factor**: Support for apparent vs real power calculations
8. **Comparison views**: Built-in comparisons between ports

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
