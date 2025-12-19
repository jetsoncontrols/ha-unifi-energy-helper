# UniFi Energy Helper for Home Assistant

A Home Assistant custom component that automatically creates synthetic Energy (kWh) entities for UniFi Network devices with PoE ports. This helper accumulates energy consumption from PoE port wattage entities and displays them alongside the UniFi Network device.

## Features

- 🔌 **Automatic Discovery**: Automatically finds all UniFi PoE power sensors
- ⚡ **Energy Accumulation**: Creates energy (kWh) sensors that accumulate power consumption over time
- 📊 **Device Integration**: Energy sensors appear under the same device as the UniFi Network switch
- 🔄 **Real-time Tracking**: Updates energy consumption every 60 seconds
- 📈 **State Preservation**: Tracks total energy consumption as a monotonically increasing value

## Requirements

- Home Assistant 2023.1 or later
- UniFi Network integration configured with PoE-capable switches
- PoE port wattage entities enabled in the UniFi integration

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/jetsoncontrols/ha-unifi-helper` as a custom repository with category "Integration"
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/unifi_energy_helper` folder from this repository
2. Copy it to your Home Assistant `custom_components` directory:
   ```
   <config_directory>/custom_components/unifi_energy_helper/
   ```
3. Restart Home Assistant

## Configuration

After installation, add the integration through the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "UniFi Energy Helper"
4. Click on it and follow the setup wizard

No YAML configuration needed! The integration will automatically discover all UniFi PoE power entities and create corresponding energy sensors.

## How It Works

1. **Discovery**: On startup, the integration scans the entity registry for UniFi power sensors (PoE ports)
2. **Grouping**: Groups PoE port sensors by their parent device (the UniFi switch)
3. **Energy Sensor Creation**: Creates one energy accumulation sensor per device with PoE ports
4. **Energy Calculation**: Every 60 seconds, it:
   - Reads the current power consumption from all PoE ports on the device
   - Calculates the energy consumed since the last update (Power × Time)
   - Adds it to the total accumulated energy
5. **Display**: The energy sensor appears under the same device as the switch in the Home Assistant UI

## Example

If you have a UniFi switch with 8 PoE ports, and ports 1, 3, and 5 have devices connected drawing 15W, 30W, and 10W respectively:

- Total power: 55W
- After 1 hour: 55Wh = 0.055 kWh added to the total
- Energy sensor shows cumulative total (e.g., 1.234 kWh after several days)

## Energy Dashboard Integration

The created energy sensors are compatible with Home Assistant's Energy Dashboard:

1. Go to Settings → Dashboards → Energy
2. Under "Device consumption", click "Add Consumption"
3. Select your UniFi device's "PoE Energy" sensor
4. Save and view your PoE power consumption over time!

## Troubleshooting

**No energy sensors created**
- Ensure the UniFi Network integration is set up and working
- Verify that you have PoE-capable switches configured
- Check that PoE port power entities are enabled (look for `sensor.switch_port_X_poe_power` entities)

**Energy not accumulating**
- Verify PoE port sensors are reporting valid power values (not "unknown" or "unavailable")
- Check the Home Assistant logs for any errors from `unifi_energy_helper`

**Energy sensor not showing under the correct device**
- This should happen automatically; if not, check the device ID in the sensor attributes

## Debug Logging

To enable debug logging for troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.unifi_energy_helper: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter issues or have questions:
- Check the [Issues](https://github.com/jetsoncontrols/ha-unifi-helper/issues) page
- Create a new issue with detailed information about your setup and the problem