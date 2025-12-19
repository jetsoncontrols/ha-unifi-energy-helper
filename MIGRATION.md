# Migration Guide: v1.x to v2.0.0

## Overview

Version 2.0.0 introduces **config flow** (UI-based configuration), replacing the previous YAML-based setup. This is a **breaking change** that requires user action to migrate.

## What Changed

### Before (v1.x) - YAML Configuration
```yaml
# configuration.yaml
unifi_energy_helper:
```

### After (v2.0.0) - UI Configuration
No YAML configuration needed! Setup through the UI instead.

## Migration Steps

### 1. Update the Integration

Update UniFi Energy Helper to version 2.0.0 through HACS or by replacing the files manually.

### 2. Remove YAML Configuration

Remove the `unifi_energy_helper:` entry from your `configuration.yaml`:

```yaml
# Remove this line:
unifi_energy_helper:
```

### 3. Restart Home Assistant

Restart Home Assistant to apply the changes.

### 4. Set Up Through UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration** (bottom right corner)
3. Search for **"UniFi Energy Helper"**
4. Click on it and follow the setup wizard
5. Click **Submit** to complete the setup

### 5. Verify

After setup:
- Your existing energy data should be preserved (state restoration)
- Energy sensors will continue accumulating from where they left off
- All PoE devices should be detected automatically

## What Stays the Same

✅ Energy accumulation continues from previous values  
✅ All entities keep their entity IDs  
✅ Energy Dashboard integration still works  
✅ Same device linking behavior  
✅ Same 60-second update interval  

## What's New

✨ UI-based setup - no YAML editing required  
✨ Automatic validation during setup  
✨ Better error messages when UniFi PoE devices aren't found  
✨ Single instance enforcement  

## Troubleshooting

### "No UniFi PoE devices found" error

**Solution**: Ensure you have:
- UniFi Network integration configured
- At least one PoE-capable switch
- PoE port power monitoring enabled
- PoE power entities visible in Developer Tools → States

### Integration won't appear in Add Integration list

**Solution**:
1. Clear your browser cache
2. Force refresh (Ctrl+F5 or Cmd+Shift+R)
3. Restart Home Assistant
4. Check that `config_flow: true` is in `manifest.json`

### Energy data reset to zero

**Solution**: This shouldn't happen, but if it does:
1. Check Home Assistant logs for errors
2. Verify state restoration is working: Developer Tools → States → look for your energy sensors
3. Report as an issue with logs

## Need Help?

- **Documentation**: [README.md](README.md) | [INSTALL.md](INSTALL.md)
- **Issues**: [GitHub Issues](https://github.com/jetsoncontrols/ha-unifi-helper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jetsoncontrols/ha-unifi-helper/discussions)

## Rolling Back

If you need to roll back to v1.x:

1. Downgrade to v1.0.0 through HACS or manually
2. Add `unifi_energy_helper:` back to `configuration.yaml`
3. Restart Home Assistant

Note: This is not recommended unless you encounter critical issues.
