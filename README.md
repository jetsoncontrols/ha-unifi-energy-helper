# UniFi Energy Helper for Home Assistant

A Home Assistant custom component that automatically creates synthetic Energy (kWh) entities for UniFi Network devices with PoE ports and PDU outlets. This helper accumulates energy consumption from power wattage entities and displays them alongside the UniFi Network device.

## Features

- 🔌 **Automatic Discovery**: Automatically finds all UniFi PoE power sensors and PDU outlet sensors
- ⚡ **Per-Port/Outlet Energy Tracking**: Creates individual energy (kWh) sensors for each PoE port or PDU outlet
- 📊 **Device Integration**: Energy sensors and reset buttons appear under the same device as the UniFi Network switch or PDU
- 🔄 **Real-time Tracking**: Updates energy consumption instantly when power changes (event-driven)
- 🔘 **Reset Buttons**: Each energy sensor has an associated reset button to zero the accumulation
- 📈 **State Preservation**: Tracks total energy consumption as a monotonically increasing value, persists across restarts
- 🆕 **Dynamic Discovery**: Automatically detects newly added or enabled PoE ports and PDU outlets

## Requirements

- Home Assistant 2023.1 or later
- UniFi Network integration configured with:
  - PoE-capable switches, and/or
  - UniFi PDUs (Power Distribution Units)
- Power wattage entities enabled in the UniFi integration

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

1. **Discovery**: On startup, the integration scans the entity registry for UniFi power sensors (PoE ports and PDU outlets)
2. **Sensor Creation**: Creates one energy accumulation sensor **per PoE port or PDU outlet**
3. **Button Creation**: Creates a reset button for each energy sensor
4. **Device Linking**: Links all sensors and buttons to the same device as the UniFi switch or PDU
5. **Real-time Energy Calculation**: When power changes on any port/outlet:
   - Detects the power state change immediately via event listener
   - Calculates the time elapsed since the last change
   - Computes energy consumed: Energy = Power × Time
   - Adds it to the accumulated total for that port/outlet
6. **Dynamic Updates**: Automatically creates new energy sensors and buttons when:
   - New PoE ports or PDU outlets are detected
   - Previously disabled power entities are enabled
7. **Display**: Energy sensors and reset buttons appear under the same device as the switch or PDU in the Home Assistant UI

## Example

### PoE Switch Example
If you have a UniFi switch with 8 PoE ports, and ports 1, 3, and 5 have devices connected drawing 15W, 30W, and 10W respectively:

**Created Entities:**
- `sensor.switch_port_1_energy` - Energy sensor for Port 1 (tracks 15W device)
- `button.switch_port_1_reset_energy` - Reset button for Port 1
- `sensor.switch_port_3_energy` - Energy sensor for Port 3 (tracks 30W device)
- `button.switch_port_3_reset_energy` - Reset button for Port 3
- `sensor.switch_port_5_energy` - Energy sensor for Port 5 (tracks 10W device)
- `button.switch_port_5_reset_energy` - Reset button for Port 5

### PDU Example
If you have a UniFi PDU with outlets 1, 3, and 5 drawing 25W, 40W, and 18W respectively:

**Created Entities:**
- `sensor.unifi_pdu_outlet_1_energy` - Energy sensor for Outlet 1 (tracks 25W device)
- `button.unifi_pdu_outlet_1_reset_energy` - Reset button for Outlet 1
- `sensor.unifi_pdu_outlet_3_energy` - Energy sensor for Outlet 3 (tracks 40W device)
- `button.unifi_pdu_outlet_3_reset_energy` - Reset button for Outlet 3
- `sensor.unifi_pdu_outlet_5_energy` - Energy sensor for Outlet 5 (tracks 18W device)
- `button.unifi_pdu_outlet_5_reset_energy` - Reset button for Outlet 5

**Energy Tracking:**
- PoE Port 1: After 1 hour at 15W → 0.015 kWh added
- PoE Port 3: After 1 hour at 30W → 0.030 kWh added
- PoE Port 5: After 1 hour at 10W → 0.010 kWh added
- PDU Outlet 1: After 1 hour at 25W → 0.025 kWh added
- PDU Outlet 3: After 1 hour at 40W → 0.040 kWh added
- PDU Outlet 5: After 1 hour at 18W → 0.018 kWh added
- Each sensor shows its cumulative total independently

**Resetting Energy:**
- Press the reset button for any port/outlet to zero its energy accumulation
- Other ports/outlets continue tracking independently

## Energy Dashboard Integration

The created energy sensors are compatible with Home Assistant's Energy Dashboard:

1. Go to Settings → Dashboards → Energy
2. Under "Device consumption", click "Add Consumption"
3. Select individual port energy sensors (e.g., "Port 1 Energy", "Port 3 Energy")
4. Add multiple ports to track total switch consumption or monitor high-power devices
5. Save and view your PoE power consumption over time!

**Tip**: You can add all port energy sensors to get a complete view of your switch's PoE consumption.

## Troubleshooting

**No energy sensors created**
- Ensure the UniFi Network integration is set up and working
- Verify that you have PoE-capable switches or PDUs configured
- Check that power entities are enabled:
  - PoE ports: `sensor.switch_port_X_poe_power` or similar
  - PDU outlets: `sensor.unifi_pdu_outlet_X_outlet_power` or similar
- Some power entities may be disabled by default - enable them in the entity settings

**Energy not accumulating**
- Verify PoE port sensors are reporting valid power values (not "unknown" or "unavailable")
- Check the Home Assistant logs for any errors from `unifi_energy_helper`
- Energy only accumulates when power values change or time elapses

**Reset button doesn't appear**
- Reset buttons are created after energy sensors are initialized
- Check if the button entity is disabled in entity settings
- Restart Home Assistant if buttons don't appear after initial setup

**Energy sensor not showing under the correct device**
- This should happen automatically; if not, check the device ID in the sensor attributes
- The sensor links to the same device as the corresponding PoE power sensor

**Newly added PoE port or PDU outlet not detected**
- The integration listens for entity registry changes
- If a new port/outlet isn't detected, try restarting Home Assistant
- Check that the new power entity is enabled (not disabled)

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