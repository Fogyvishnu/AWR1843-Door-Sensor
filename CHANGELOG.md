# Changelog

All notable changes to the **TI AWR1843BOOST Standalone Door Sensor** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-10-03

### Added
- **Production C Unit Test Suite**: `firmware/tests/test_door_detector.c` covering boundary validation, CFAR clutter rejection, debounce hysteresis, and VT100 buffer safety.
- **Home Assistant MQTT Bridge**: `python_gui/door_mqtt_bridge.py` featuring MQTT Auto-Discovery for binary contact sensors, cycle counters, distance, and signal strength.
- **Automated CI/CD Pipeline**: GitHub Actions workflow testing Python 3.8–3.12 and GCC C firmware compilation on push and PR.
- **PEP 517 / 621 Packaging**: Added `pyproject.toml` with console script entry points (`awr1843-door-gui`, `awr1843-door-cli`, `awr1843-door-vt100`, `awr1843-door-mqtt`).
- **Defensive Firmware API**: Added `DoorResult_e` return codes, `DoorDiagnostics_t` health metrics, and parameter validation in `door_detector.c`.
- **Engineering Documentation**:
  - `docs/SYSTEM_ARCHITECTURE.md`: Complete subsystem memory budget, timing analysis, and data path flow.
  - `docs/COMMUNICATION_PROTOCOL.md`: Protocol specification for UART CLI and MQTT JSON schemas.
  - `docs/ENCLOSURE_DESIGN.md`: 77 GHz half-wavelength radome thickness math and 3D printing guidelines.
  - `docs/POWER_MANAGEMENT.md`: Power rail consumption breakdown and battery sizing calculations.
  - `docs/COMMISSIONING_GUIDE.md`: Field installation checklist and door material reflection characteristics.

### Changed
- Enforced strict CFAR minimum SNR gating (`minSnr`) during 3D point cloud spatial filtering.
- Implemented resilient auto-reconnect handling across all Python terminal and logging utilities.

---

## [1.2.0] - 2026-09-29

### Added
- **Live Running UART VT100 Console**: On-chip firmware VT100 dashboard formatting with dynamic ASCII door graphics, real-time gauges, and event transition tables.
- **Python VT100 Terminal Monitor**: `python_gui/door_vt100.py` with cross-platform ANSI support and optional audible door open bell.
- **CLI Commands**: Added `vt100 [0|1]` to switch between full-screen console and raw one-line logs.

---

## [1.1.0] - 2026-09-28

### Added
- **Mathematical Foundations Guide**: Authored `docs/learning.md` with complete derivations for FMCW beat frequency, 2D Doppler FFT, TDM-MIMO virtual array, CA-CFAR, and FSM debounce math.
- Added 1-click automated firmware compilation batch script: `firmware/build/build_firmware.bat`.

---

## [1.0.0] - 2026-09-28

### Added
- Initial standalone door open/close detector firmware for TI AWR1843BOOST.
- Onboard execution of 3D spatial gating, hysteresis debouncing, and cycle counting (No DCA1000 required).
- Hardware LED DS3 indicator drive.
- Autonomous 3-second auto-boot task.
- Python companion GUI and headless serial logger.
