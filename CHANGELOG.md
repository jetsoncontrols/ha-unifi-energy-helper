# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-17

### Added
- Initial release of UniFi Helper custom component
- Automatic discovery of UniFi PoE power sensors
- Energy accumulation sensor for each UniFi device with PoE ports
- Device integration - energy sensors appear under the same device as UniFi switches
- State restoration - energy values persist across Home Assistant restarts
- Energy Dashboard compatibility with TOTAL_INCREASING state class
- Real-time energy accumulation with 60-second update interval
- Comprehensive documentation (README, INSTALL, TECHNICAL)
- HACS support for easy installation
- Debug logging support for troubleshooting
- Example configuration file

### Features
- Monitors all PoE ports on a switch and creates a single cumulative energy sensor per device
- Calculates energy consumption: Power (W) × Time (s) / 3600 / 1000 = Energy (kWh)
- Handles unavailable sensors gracefully - pauses accumulation when sensors are unavailable
- Supports multiple UniFi switches simultaneously
- Zero configuration required after adding to configuration.yaml

### Technical
- Built on Home Assistant 2023.1+ APIs
- Uses RestoreSensor for state persistence
- Leverages entity registry for device linking and discovery
- Efficient polling with configurable scan interval
- Type-hinted Python code for better IDE support
- Follows Home Assistant coding standards

## [Unreleased]

### Planned
- Configurable scan interval via options
- Per-port energy sensors (optional)
- Power statistics (min/max/average)
- Threshold-based notifications
- Cost calculation features
- Historical data export

[1.0.0]: https://github.com/jetsoncontrols/ha-unifi-helper/releases/tag/v1.0.0
