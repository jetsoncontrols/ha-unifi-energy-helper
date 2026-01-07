# Contributing to UniFi Energy Helper

Thank you for your interest in contributing to UniFi Energy Helper! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ha-unifi-energy-helper.git
   cd ha-unifi-energy-helper
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Home Assistant 2023.1 or later
- A UniFi Controller with PoE-capable switches (for testing)

### Local Development

1. **Install in Development Mode**:
   ```bash
   # Link to your Home Assistant config directory
   ln -s $(pwd)/custom_components/unifi_energy_helper ~/.homeassistant/custom_components/unifi_energy_helper
   ```

2. **Enable Debug Logging** in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.unifi_energy_helper: debug
   ```

3. **Restart Home Assistant** to load your changes

## Making Changes

### Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for all function parameters and return values
- Add docstrings to all functions, classes, and modules
- Keep lines under 100 characters when possible
- Use meaningful variable names

### Example:

```python
async def calculate_energy(
    power_watts: float, 
    time_seconds: float
) -> float:
    """Calculate energy in kWh from power and time.
    
    Args:
        power_watts: Power consumption in watts
        time_seconds: Time duration in seconds
        
    Returns:
        Energy consumption in kilowatt-hours
    """
    return power_watts * time_seconds / 3600 / 1000
```

### File Organization

- `__init__.py`: Component initialization and platform coordination
- `button.py`: Reset button entities implementation
- `config_flow.py`: UI-based configuration flow
- `const.py`: All constants and configuration defaults
- `sensor.py`: Energy sensor platform with event-driven tracking
- `strings.json`: UI text for config flow
- `manifest.json`: Metadata (update version on changes)

### Testing Your Changes

Before submitting:

1. **Syntax Check**:
   ```bash
   python3 -m py_compile custom_components/unifi_energy_helper/*.py
   ```

2. **Manual Testing**:
   - Install in a test Home Assistant instance via config flow
   - Verify per-port/outlet energy sensors are created for both PoE and PDU devices
   - Verify reset buttons are created for each sensor
   - Check real-time energy accumulation when power changes
   - Test reset button functionality
   - Test Home Assistant restart (state restoration)
   - Enable a previously disabled PoE port or PDU outlet and verify sensor creation
   - Monitor logs for errors

3. **Test Edge Cases**:
   - No PoE or PDU sensors present
   - Power sensors become unavailable
   - Multiple UniFi switches with different port counts
   - Multiple UniFi PDUs
   - Mixed environment with both PoE switches and PDUs
   - UniFi integration disabled/removed
   - Dynamic port/outlet addition/removal
   - Reset button pressed during active tracking
   - Rapid power changes on ports/outlets

## Submitting Changes

### Commit Messages

Use clear, descriptive commit messages:

```
Add per-port energy sensor option

- Add configuration option for per-port sensors
- Update discovery logic to create individual sensors
- Add documentation for new option
```

### Pull Request Process

1. **Update documentation** if needed (README, INSTALL, TECHNICAL)
2. **Update CHANGELOG.md** with your changes
3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
4. **Create a Pull Request** on GitHub
5. **Fill out the PR template** completely
6. **Wait for review** - be patient and responsive to feedback

### Pull Request Checklist

- [ ] Code follows the style guidelines
- [ ] All Python files pass syntax check
- [ ] Changes have been tested manually
- [ ] Documentation has been updated
- [ ] CHANGELOG.md has been updated
- [ ] Commit messages are clear and descriptive
- [ ] No unnecessary files are included (no `__pycache__`, etc.)

## Reporting Issues

### Bug Reports

When reporting bugs, include:

- Home Assistant version
- UniFi Energy Helper version
- UniFi Controller version
- Switch model
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (with debug logging enabled)
- Screenshots if applicable

See [bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md) template.

### Feature Requests

When requesting features, include:

- Problem you're trying to solve
- Proposed solution
- Alternative solutions considered
- Use case and who would benefit
- Willingness to help test

See [feature_request.md](.github/ISSUE_TEMPLATE/feature_request.md) template.

## Development Guidelines

### Adding New Features

1. **Discuss first**: Open an issue to discuss major changes
2. **Keep it simple**: Follow the principle of least surprise
3. **Maintain compatibility**: Don't break existing functionality
4. **Document thoroughly**: Update all relevant documentation
5. **Test extensively**: Cover edge cases and error conditions

### Code Review

All submissions require review. We aim to:

- Respond to PRs within 48 hours
- Provide constructive feedback
- Help you improve your contribution
- Merge quality contributions promptly

### Areas for Contribution

Good first contributions:

- Documentation improvements
- Bug fixes
- Test coverage
- Code cleanup and refactoring
- Adding debug logging
- Improving error messages
- Enhancing config flow UI text

More advanced contributions:

- New features (aggregated device sensors, statistics, auto-reset, etc.)
- Performance optimizations
- Event listener efficiency improvements
- Integration with other HA components
- Configuration options UI
- Cost tracking per port
- Power factor calculations

## Home Assistant Integration Standards

When contributing, follow Home Assistant's:

- [Developer Documentation](https://developers.home-assistant.io/)
- [Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index)
- [Code Review Guidelines](https://developers.home-assistant.io/docs/review-process)

## Questions?

- **Documentation**: Read [README.md](README.md), [INSTALL.md](INSTALL.md), [TECHNICAL.md](TECHNICAL.md)
- **Issues**: Search [existing issues](https://github.com/jetsoncontrols/ha-unifi-energy-helper/issues)
- **Discussion**: Start a [GitHub Discussion](https://github.com/jetsoncontrols/ha-unifi-energy-helper/discussions)

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers this project.

## Recognition

Contributors will be:
- Listed in release notes
- Credited in CHANGELOG.md
- Appreciated by the community!

Thank you for contributing to UniFi Energy Helper!
