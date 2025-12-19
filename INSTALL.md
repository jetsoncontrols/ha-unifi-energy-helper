# Installation Guide - UniFi Energy Helper

## Prerequisites

Before installing UniFi Energy Helper, ensure you have:

1. **Home Assistant** 2023.1 or later
2. **UniFi Network Integration** configured and working
   - Available at Settings → Devices & Services → Add Integration → UniFi Network
   - Must have at least one UniFi switch with PoE capabilities
3. **PoE Port Sensors** enabled in the UniFi integration
   - These appear as entities like `sensor.switch_port_1_poe_power`

## Installation Methods

### Method 1: HACS (Recommended)

HACS (Home Assistant Community Store) is the easiest way to install and manage custom components.

#### First-time HACS Setup (if not already installed)

1. Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)
2. Restart Home Assistant after HACS installation

#### Installing UniFi Energy Helper via HACS

1. Open Home Assistant
2. Navigate to **HACS** in the sidebar
3. Click on **Integrations**
4. Click the **⋮** (three dots) in the top right corner
5. Select **Custom repositories**
6. Add the repository:
   - **URL**: `https://github.com/jetsoncontrols/ha-unifi-helper`
   - **Category**: Integration
7. Click **Add**
8. Close the custom repositories dialog
9. Click the **+ Explore & Download Repositories** button
10. Search for "UniFi Energy Helper"
11. Click on **UniFi Energy Helper**
12. Click **Download**
13. Select the latest version
14. Restart Home Assistant

### Method 2: Manual Installation

If you prefer not to use HACS, you can install manually:

1. Download the latest release from the [releases page](https://github.com/jetsoncontrols/ha-unifi-helper/releases)
2. Unzip the downloaded file
3. Copy the `custom_components/unifi_energy_helper` folder to your Home Assistant configuration directory:
   ```
   <config_directory>/custom_components/unifi_energy_helper/
   ```
   
   Your directory structure should look like:
   ```
   homeassistant/
   ├── configuration.yaml
   ├── custom_components/
   │   └── unifi_energy_helper/
   │       ├── __init__.py
   │       ├── const.py
   │       ├── manifest.json
   │       ├── sensor.py
   │       └── strings.json
   ```

4. Restart Home Assistant

### Method 3: Git Clone (For Development)

If you want to contribute or test the latest development version:

```bash
cd /config/custom_components
git clone https://github.com/jetsoncontrols/ha-unifi-helper.git unifi_energy_helper
```

Restart Home Assistant after cloning.

## Configuration

After installation, set up the integration through the Home Assistant UI:

1. **Restart Home Assistant** (if you just installed the integration)
2. Go to **Settings** → **Devices & Services**
3. Click the **+ Add Integration** button in the bottom right
4. Search for **"UniFi Energy Helper"**
5. Click on **UniFi Energy Helper** in the search results
6. The integration will automatically check for UniFi PoE devices
7. Click **Submit** to complete the setup

**Note**: No YAML configuration needed! The integration uses config flow (UI-based setup).

### Optional: Debug Logging

If you want to see detailed logs during setup or troubleshooting, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.unifi_energy_helper: debug
```

## Verification

After setting up through the UI:

1. The integration will appear in **Settings** → **Devices & Services**
2. Find your UniFi devices in the integration
3. Click on a device that has PoE ports
4. You should see a new entity: **PoE Energy** with unit kWh
5. The sensor will start accumulating energy from all PoE ports on that device

## What Gets Created

For each PoE port or PDU outlet on your UniFi devices, the integration creates:

- **1 Energy Sensor** per PoE port or PDU outlet
  - Entity ID format: 
    - PoE: `sensor.<device_name>_port_X_energy`
    - PDU: `sensor.<device_name>_outlet_X_energy`
  - Unit: kWh (kilowatt-hours)
  - Device Class: Energy
  - State Class: Total Increasing (for Energy Dashboard compatibility)
  - Tracks energy consumption for that specific port/outlet

- **1 Reset Button** per energy sensor
  - Entity ID format:
    - PoE: `button.<device_name>_port_X_reset_energy`
    - PDU: `button.<device_name>_outlet_X_reset_energy`
  - Allows you to zero the energy accumulation for that port/outlet
  - Appears as a diagnostic entity under the same device

**Examples**: 
- A UniFi switch with 24 PoE ports will have 24 energy sensors and 24 reset buttons, all grouped under the switch device.
- A UniFi PDU with 6 outlets will have 6 energy sensors and 6 reset buttons, all grouped under the PDU device.

## Using with Energy Dashboard

To track PoE energy consumption in Home Assistant's Energy Dashboard:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Under **Device consumption**, click **Add Consumption**
3. Select individual port energy sensors (e.g., "Port 1 Energy", "Port 5 Energy")
   - You can add multiple sensors to track different devices or ports
   - Add all ports to see total switch consumption
4. Configure the cost per kWh (optional)
5. Click **Save**

The Energy Dashboard will now track and visualize your per-port PoE power consumption!

## Troubleshooting

### No energy sensors appear

**Check**: Do you have PoE port or PDU outlet power sensors?
```
Developer Tools → States → Filter by "poe_power" or "port" or "outlet" and "power"
```

If no sensors appear:
1. Verify your UniFi integration is working
2. Ensure you have PoE-capable switches or PDUs
3. Check that power monitoring is enabled in the UniFi controller
4. **Important**: Many power sensors are disabled by default
   - Go to Settings → Devices & Services → UniFi → Devices
   - Click on your switch or PDU
   - Look for disabled entities and enable the ones you want to track

**Check**: Are the PoE sensors from the UniFi integration?
- Entity IDs should start with `sensor.`
- Platform should be `unifi`
- Look in the entity attributes

### Reset buttons don't appear

1. Reset buttons are created automatically for each energy sensor
2. They are marked as diagnostic entities (may be hidden by default)
3. Check Settings → Devices & Services → UniFi Energy Helper → Your Device
4. Look for "Show disabled entities" or filter to show diagnostic entities

### Energy not accumulating

**Check**: Are PoE port sensors reporting values?
1. Go to Developer Tools → States
2. Find your PoE power sensors
3. Verify they show numeric values (not "unknown" or "unavailable")

**Check**: Are devices connected to PoE ports?
- PoE ports with no connected devices will report 0W
- At least one port needs to have a powered device

### Energy resets to zero

The energy sensor uses state restoration and should persist across restarts.

**If it resets:**
1. Check Home Assistant logs for errors
2. Verify the `home-assistant_v2.db` file has write permissions
3. Enable debug logging to see restoration attempts

### Sensor not under correct device

The sensor should automatically appear under the same device as the UniFi switch.

**If it doesn't:**
1. Check the entity's device_id in Developer Tools → States → Attributes
2. Compare with the device_id of the PoE port sensors
3. Report as an issue with device IDs included

## Uninstallation

To remove UniFi Energy Helper:

1. Remove `unifi_energy_helper:` from your `configuration.yaml`
2. Restart Home Assistant
3. (Optional) Remove the `custom_components/unifi_energy_helper` directory
4. (Optional) If using HACS, go to HACS → Integrations → UniFi Energy Helper → Remove

## Getting Help

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/jetsoncontrols/ha-unifi-helper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jetsoncontrols/ha-unifi-helper/discussions)

When reporting issues, please include:
- Home Assistant version
- UniFi integration version
- UniFi controller version
- Switch model
- Debug logs (see Optional: Debug Logging above)
- Screenshots of the issue
