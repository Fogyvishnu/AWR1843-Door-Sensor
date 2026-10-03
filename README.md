# TI AWR1843BOOST Standalone Door Sensor & Event Counter

[![CI](https://github.com/Fogyvishnu/AWR1843-Door-Sensor/actions/workflows/ci.yml/badge.svg)](https://github.com/Fogyvishnu/AWR1843-Door-Sensor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![TI mmWave SDK](https://img.shields.io/badge/TI%20mmWave%20SDK-03.06.02.00--LTS-red.svg)](https://www.ti.com/tool/MMWAVE-SDK)
[![Hardware](https://img.shields.io/badge/Hardware-AWR1843BOOST-brightgreen.svg)](https://www.ti.com/tool/AWR1843BOOST)

An industrial-grade, edge-AI mmWave radar solution that monitors door status (**OPEN** vs **CLOSED**), counts cumulative open/close cycles, and operates **100% standalone directly on the TI AWR1843BOOST evaluation board without requiring a DCA1000 capture card or a PC connection**.

---

## 🌟 Highlights

- **Edge Processing On-Chip**: The FMCW Range FFT, Doppler, CFAR detection, 3D Spatial Gating, and Debounced State Machine execute entirely on the onboard TI C674x DSP and ARM Cortex-R4F MCU.
- **Zero DCA1000 Hardware Required**: Operates using internal radar processing buffers, HWA accelerator, and on-chip QSPI flash.
- **Autonomous Auto-Boot**: The board boots up autonomously within 3.0 seconds of connecting 5V power, configures the 77 GHz radar chirps from internal flash, and begins monitoring without any computer or manual CLI commands.
- **Visual Hardware Feedback**:
  - **LED DS3 ON**: Door is **OPEN** (Passage active)
  - **LED DS3 OFF**: Door is **CLOSED** (Secured)
- **Live On-Chip VT100 Console**: Transmits a real-time, flicker-free ANSI/VT100 dashboard directly over serial UART for instant viewing in PuTTY, Tera Term, minicom, or Windows Terminal.
- **Smart Home Integration**: Includes a production **Home Assistant MQTT Bridge** with MQTT Auto-Discovery for seamless zero-config smart building integration.
- **Comprehensive Production Engineering**: Includes 77 GHz radome CAD math, power budget & battery sizing, memory/timing specifications, and field commissioning SOPs.

---

## 📂 Project Structure

```
AWR1843-Door-Sensor/
├── ci/
│   └── github_actions_ci.yml         # Automated CI/CD workflow configuration (Python & C)
├── config/
│   ├── door_sensor_profile.cfg       # 77GHz FMCW chirp profile (~4.2cm range resolution)
│   └── default_settings.json         # Physical boundary constraints and GPIO mappings
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md        # Technical spec: memory budget, timing, & data flow
│   ├── COMMUNICATION_PROTOCOL.md     # UART framing, CLI syntax, & MQTT JSON schema
│   ├── ENCLOSURE_DESIGN.md           # 77 GHz radome physics, wall thickness math, & 3D print specs
│   ├── POWER_MANAGEMENT.md           # Current draw breakdown, duty cycles, & battery sizing
│   ├── COMMISSIONING_GUIDE.md        # Site survey, door material characteristics, & field tuning
│   ├── FLASHING_GUIDE.md             # SOP jumper setup & UniFlash step-by-step flashing
│   ├── HARDWARE_SETUP.md             # Sensor placement, mounting & wiring guide
│   └── learning.md                   # In-depth math: FMCW, Doppler FFT, AoA MIMO, CFAR, FSM
├── firmware/
│   ├── build/
│   │   └── build_firmware.bat        # 1-Click automated TI CGT compiler batch script
│   ├── prebuilt_binaries/
│   │   └── awr1843_door_sensor.bin   # Production-ready flashable MetaImage (CRC32 verified)
│   ├── src/
│   │   ├── door_detector.c           # Production door detector FSM & VT100 console engine
│   │   ├── door_detector.h           # Data structures, validation limits & public APIs
│   │   ├── mmw_cli.c                 # CLI commands & Standalone Auto-Boot task
│   │   └── mss_main.c                # MSS driver integrating DoorDetector & LED control
│   └── tests/
│       ├── test_door_detector.c      # Standalone C unit test suite (10 test cases)
│       ├── Makefile                  # GCC / Clang build configuration for CI/CD
│       └── run_c_tests.py            # Cross-platform automated C test runner
├── python_gui/
│   ├── door_monitor_gui.py           # Animated desktop GUI visualizer & event logger
│   ├── door_vt100.py                 # Live running UART VT100 terminal dashboard
│   ├── door_mqtt_bridge.py           # Home Assistant MQTT Auto-Discovery bridge
│   ├── door_logger_cli.py            # Headless command-line serial logger
│   ├── requirements.txt              # Production Python dependencies
│   └── requirements-dev.txt          # Developer testing & linting dependencies
├── tests/
│   ├── test_door_parser.py           # Unit tests for UART telemetry parser
│   ├── test_config_validation.py     # Unit tests for chirp profile & JSON schema
│   ├── test_mqtt_bridge.py           # Unit tests for MQTT bridge and Home Assistant payloads
│   └── run_tests.py                  # Master automated test suite runner
├── pyproject.toml                    # PEP 517 / 621 package metadata & entry points
├── CHANGELOG.md                      # Semantic versioning release history
├── CONTRIBUTING.md                   # Pull request workflow and coding standards
├── CODE_OF_CONDUCT.md                # Contributor Covenant standard
├── LICENSE                           # MIT License
└── README.md                         # Project documentation
```

---

## 🚀 Quick Start Guide

### Step 1: Flash Prebuilt Binary to AWR1843BOOST
1. Set the **SOP jumpers** on the AWR1843BOOST to **Flashing Mode (1-0-1)**:
   - **SOP2**: CLOSED (Jumper ON)
   - **SOP1**: OPEN (Jumper OFF)
   - **SOP0**: CLOSED (Jumper ON)
2. Connect the AWR1843BOOST to your PC using a micro-USB cable.
3. Open **TI UniFlash** ([dev.ti.com/uniflash](https://dev.ti.com/uniflash)).
4. Select device: **`AWR1843BOOST`** and configure your **Application/User UART COM port** (e.g. `COM3`).
5. In **Meta Image 1**, load:
   ```
   firmware/prebuilt_binaries/awr1843_door_sensor.bin
   ```
6. Click **Load Image** and wait for completion.

*(For detailed flashing steps with screenshots, see [docs/FLASHING_GUIDE.md](docs/FLASHING_GUIDE.md)).*

---

### Step 2: Standalone Operation
1. Disconnect USB power.
2. Change the **SOP jumpers** to **Functional Mode (0-0-1)**:
   - **SOP2**: OPEN (Jumper OFF)
   - **SOP1**: OPEN (Jumper OFF)
   - **SOP0**: CLOSED (Jumper ON)
3. Mount the sensor facing the doorway ($0.5\text{ m} - 1.5\text{ m}$ away). Keep the door closed.
4. Power the board using any standard **5V / 2.0A USB wall adapter, power bank, or PC USB port**.
5. **Operation begins automatically**:
   - The sensor auto-calibrates the closed door distance for 2.0 seconds.
   - Open the door -> **LED DS3 turns ON** and open count increments.
   - Close the door -> **LED DS3 turns OFF** and close count increments.

---

## 📺 Live Running UART VT100 Console

The firmware features an on-chip **VT100/ANSI terminal dashboard** that transforms your serial terminal into an interactive, real-time radar console:

```
+-----------------------------------------------------------------------------+
|        TI AWR1843BOOST mmWave Radar - Live VT100 Console Monitor            |
|    77 GHz FMCW | Standalone On-Chip Event Counter | Port: COM3              |
+-----------------------------------------------------------------------------+
| STATUS: [   DOOR CLOSED   ]     LED DS3: OFF (Secure)                       |
+-------------------+---------------------------------------------------------+
| DOOR VISUAL       | RADAR SENSING METRICS & PASSAGE STATISTICS              |
+-------------------+---------------------------------------------------------+
|   +-----------+   | Target Distance :  1.18 m    | Total Openings : 14      |
|   |   |   |   |   | Distance Gauge  : [=====>        ] | Total Closings : 14      |
|   |   | . |   |   | Peak Reflection :  22.4 dB   | Time In State  : 00:03:15|
|   |   |   |   |   | Reflection SNR  : [=========>    ] | Debounce Filter: 500 ms  |
|   +-----------+   | Points in ROI   :   7 points   | Frame Count    : 4520    |
|   [DOOR CLOSED]   | Auto-Baseline   : LOCKED (OK)  | Radar State    : ACTIVE  |
+-------------------+---------------------------------------------------------+
| RECENT EVENT TRANSITION HISTORY                                             |
+----+----------+-------------+--------------+--------+--------+--------------+
| #  | Time     | Event       | Transition   | Opens  | Closes | Distance     |
+----+----------+-------------+--------------+--------+--------+--------------+
| 1  | 21:00:15 | DOOR CLOSED | OPEN->CLOSED | 14     | 14     | 1.18 m       |
| 2  | 20:58:30 | DOOR OPENED | CLOSED->OPEN | 14     | 13     |   --- m      |
+----+----------+-------------+--------------+--------+--------+--------------+
| COMMANDS: [r] Reset  [c] Calibrate  [b] Beep  [t] Firmware VT100  [q] Quit |
+-----------------------------------------------------------------------------+
```

### Option A: Direct Hardware Serial Terminal (No Python Required)
Connect directly via **PuTTY**, **Tera Term**, **minicom**, or **Windows Terminal**:
- **Port**: XDS110 Application/User UART (e.g., `COM3` or `/dev/ttyACM0`)
- **Baud Rate**: `115200`
- **Emulation**: `VT100` / `ANSI`

### Option B: Python VT100 Terminal Monitor
```bash
pip install -e .
awr1843-door-vt100
# Or: python python_gui/door_vt100.py
```

**Hotkeys:**
- <kbd>r</kbd> : Reset counters to 0
- <kbd>c</kbd> : Recalibrate closed-door distance
- <kbd>b</kbd> : Toggle audible door opening bell
- <kbd>t</kbd> : Toggle firmware VT100 / raw log mode
- <kbd>q</kbd> : Exit cleanly

---

## 🏡 Home Assistant & MQTT Integration

The production **MQTT Bridge** connects the sensor to any MQTT broker with native **Home Assistant MQTT Auto-Discovery**:

```bash
# Launch MQTT Bridge
python python_gui/door_mqtt_bridge.py --mqtt-host 192.168.1.100 --port COM3
# Or via entry point: awr1843-door-mqtt --mqtt-host 192.168.1.100
```

**Automatically Discovered Entities in Home Assistant:**
- `binary_sensor.awr1843_door`: Door open/closed state (device class: `door`)
- `sensor.awr1843_door_open_count`: Total open cycles (state class: `total_increasing`)
- `sensor.awr1843_door_close_count`: Total close cycles (state class: `total_increasing`)
- `sensor.awr1843_door_distance`: Live distance in meters
- `sensor.awr1843_door_snr`: Reflection strength in dB

---

## 🖥️ Companion Desktop Visualizer GUI

For lab demonstrations, testing, and real-time radar data visualization:

```bash
python python_gui/door_monitor_gui.py
# Or: awr1843-door-gui
```

- **Animated Door View**: 2D door graphics swing dynamically with radar state.
- **Large Digital Counters**: Total Opens, Closes, Duration timers, and SNR meters.
- **Event Log & CSV Export**: One-click CSV recording of all door activities.

---

## 🛠️ CLI Commands (115200 Baud)

| Command | Syntax | Description |
|---|---|---|
| `vt100` | `vt100 [0\|1]` | Toggle between live VT100 full-screen dashboard (1) and raw one-line logs (0) |
| `doorStatus` | `doorStatus` | Prints door state, total opens, closes, distance, SNR, and calibration flag |
| `resetCounters` | `resetCounters` | Resets cumulative open and close cycle counters back to 0 |
| `calibrate` | `calibrate` | Re-triggers the 2.0-second closed door distance calibration |
| `doorCfg` | `doorCfg <rMin> <rMax> [debounce]` | Sets custom door zone boundaries in meters (e.g. `doorCfg 0.5 1.5 5`) |

---

## 📚 Technical & Engineering Documentation

- [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md): Multi-core subsystem allocation, memory budget, and timing diagrams.
- [docs/COMMUNICATION_PROTOCOL.md](docs/COMMUNICATION_PROTOCOL.md): Interface Control Document (ICD) covering UART framing and MQTT JSON schemas.
- [docs/ENCLOSURE_DESIGN.md](docs/ENCLOSURE_DESIGN.md): 77 GHz half-wavelength radome thickness math, 3D printing parameters, and thermal design.
- [docs/POWER_MANAGEMENT.md](docs/POWER_MANAGEMENT.md): Power rail consumption profiles, duty-cycling analysis, and battery sizing.
- [docs/COMMISSIONING_GUIDE.md](docs/COMMISSIONING_GUIDE.md): Door material reflection characteristics (wood vs glass vs metal) and field tuning SOP.
- [docs/learning.md](docs/learning.md): Comprehensive mathematical foundations (FMCW, Doppler FFT, AoA MIMO, CA-CFAR, FSM debouncing).

---

## 🧪 Testing & Quality Assurance

### Run Python Test Suite
```bash
python tests/run_tests.py
```

### Run Firmware C Unit Tests
```bash
cd firmware/tests
make
```

---

## 🔨 Compiling Firmware from Source

To compile the embedded multi-core MetaImage:
1. Ensure **TI mmWave SDK 03.06.02.00-LTS** is installed in `C:\ti`.
2. Run the 1-click batch script:
   ```cmd
   firmware\build\build_firmware.bat
   ```
3. The script compiles both ARM Cortex-R4F MSS and C674x DSP binaries, generates the multicore MetaImage with CRC32 checksum, and copies `awr1843_door_sensor.bin` to `firmware/prebuilt_binaries/`.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
