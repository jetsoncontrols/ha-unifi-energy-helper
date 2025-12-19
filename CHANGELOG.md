# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-17

### Changed - BREAKING CHANGES
- **BREAKING**: Changed from device-level aggregated energy tracking to **per-port energy tracking**
  - Old: One energy sensor per switch (aggregated all ports)
  - New: One energy sensor per PoE port (individual tracking)
  - Entity IDs changed from `sensor.switch_poe_energy` to `sensor.switch_port_X_energy`
- **BREAKING**: Migrated from YAML-based configuration to config flow (UI-based setup)
  - Integration now set up through Settings → Devices & Services → Add Integration
  - No longer requires `unifi_energy_helper:` in configuration.yaml
- **BREAKING**: Changed from polling-based to event-driven energy accumulation
  - Old: 60-second polling interval
  - New: Real-time updates when power changes

### Added
- **Reset buttons** for each energy sensor (`button.switch_port_X_reset_energy`)
  - Allows zeroing energy accumulation for individual ports
  - Appears as diagnostic entity under the same device
- **Dynamic entity creation** - Automatically detects and creates sensors for:
  - Newly discovered PoE ports
  - Previously disabled PoE entities that are enabled
- **Entity registry listener** for real-time detection of new PoE entities
- **Button platform** with UniFiEnergyResetButton entities
- Config flow implementation for UI-based setup
- Automatic detection of UniFi PoE devices during setup
- Single instance enforcement to prevent duplicate configurations
- Better error messaging when no PoE devices are found
- Comprehensive state restoration for per-port sensors

### Improved
- **Event-driven tracking**: Uses `async_track_state_change_event` for instant updates
- **Better device organization**: All per-port sensors and buttons grouped under switch device
- **More accurate energy calculation**: Uses Riemann sum (left endpoint) approach
- **Diagnostic entity categorization**: All helper entities marked as diagnostic
- **Enhanced logging**: More detailed debug information for troubleshooting
- **Improved state persistence**: More robust restoration logic

### Technical
- Added `button.py` for reset button implementation
- Added `config_flow.py` for UI-based configuration
- Completely rewrote `sensor.py`:
  - Changed to per-port tracking architecture
  - Implemented event-driven state change listeners
  - Added dynamic entity creation via registry listener
  - Enhanced state restoration with error handling
  - Removed polling, added `_attr_should_poll = False`
- Updated `__init__.py`:
  - Changed to use `async_setup_entry` instead of `async_setup`
  - Added coordinated setup of sensor and button platforms
- Updated `const.py` with additional constants
- Added `config_flow: true` to manifest.json
- Changed `integration_type` to "helper" in manifest.json
- Updated version to "2.0.0" in manifest.json
- Enhanced strings.json with config flow steps and abort messages

## [1.0.0] - 2024-12-17

### Added
- Initial release of UniFi Energy Helper custom component
- Automatic discovery of UniFi PoE power sensors
- Energy accumulation sensor for each UniFi device with PoE ports
- Device integration - energy sensors appear under the same device as UniFi switches
- State restoration - energy values persist across Home Assistant restarts
- Energy Dashboard compatibility with TOTAL_INCREASING state class
- Real-time energy accumulation with 60-second update interval
- Comprehensive documentation (README, INSTALL, TECHNICAL)
- HACS support for easy installation
- Debug logging support for troubleshooting

### Features (Deprecated in v2.0.0)
- Monitored all PoE ports on a switch and created a single cumulative energy sensor per device
- Calculated energy consumption: Power (W) × Time (s) / 3600 / 1000 = Energy (kWh)
- Handled unavailable sensors gracefully - paused accumulation when sensors were unavailable
- Supported multiple UniFi switches simultaneously
- Zero configuration required after adding to configuration.yaml
- Used 60-second polling interval for updates

### Technical
- Built on Home Assistant 2023.1+ APIs
- Uses RestoreSensor for state persistence
- Leverages entity registry for device linking and discovery
- Efficient polling with configurable scan interval
- Type-hinted Python code for better IDE support
- Follows Home Assistant coding standards

## [Unreleased]

### Added
- Support for UniFi PDU (Power Distribution Unit) outlet power sensors
- Automatic detection and energy tracking for PDU outlets alongside PoE ports
- Smart naming logic to handle PDU outlet naming patterns (e.g., "Outlet 5 Outlet Power" → "Outlet 5 Energy")

### Planned
- ✅ ~~Per-port energy sensors~~ (Implemented in v2.0.0)
- ✅ ~~Reset functionality~~ (Implemented in v2.0.0 via reset buttons)
- Device-level aggregated sensors (optional, in addition to per-port)
- Power statistics (min/max/average) as attributes
- Threshold-based notifications
- Cost calculation features per port
- Historical data export to CSV
- Scheduled auto-reset (daily/weekly/monthly)
- Power factor support for apparent vs real power

[1.0.0]: https://github.com/jetsoncontrols/ha-unifi-helper/releases/tag/v1.0.0
