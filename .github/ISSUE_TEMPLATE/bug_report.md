---
name: Bug Report
about: Create a report to help us improve UniFi Energy Helper
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of what the bug is.

## Environment
- **Home Assistant Version**: [e.g., 2024.1.0]
- **UniFi Energy Helper Version**: [e.g., 1.0.0]
- **UniFi Integration Version**: [e.g., built-in]
- **UniFi Controller Version**: [e.g., 7.5.176]
- **Switch Model**: [e.g., USW-24-POE]

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
A clear and concise description of what you expected to happen.

## Actual Behavior
A clear and concise description of what actually happened.

## Screenshots
If applicable, add screenshots to help explain your problem.

## Logs
Please include relevant logs with debug logging enabled:

```yaml
logger:
  logs:
    custom_components.unifi_energy_helper: debug
```

```
Paste logs here
```

## Configuration
```yaml
# Your configuration.yaml entry for unifi_energy_helper
unifi_energy_helper:
```

## Additional Context
Add any other context about the problem here.

## Checklist
- [ ] I have enabled debug logging
- [ ] I have included the full error message/stack trace
- [ ] I have included my Home Assistant and UniFi versions
- [ ] I have checked existing issues for duplicates
