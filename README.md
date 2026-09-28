# TI AWR1843BOOST Standalone Door Sensor & Event Counter

A complete edge-AI mmWave radar solution that monitors door status (**OPEN** vs **CLOSED**), counts cumulative open/close cycles, and operates **100% standalone directly on the TI AWR1843BOOST evaluation board without requiring a DCA1000 capture card or a PC connection**.

---

## 🌟 Highlights

- **Edge Processing On-Chip**: The FMCW Range FFT, Doppler, CFAR detection, and Door State Machine execute directly on the onboard TI C674x DSP and ARM Cortex-R4F MCU.
- **No DCA1000 Required**: Operates using the onboard radar processing pipeline and QSPI flash.
- **Auto-Boot Standalone Mode**: Once flashed, the board boots up autonomously within 3 seconds of connecting power, configures the 77GHz radar chirps, and starts detecting without requiring any computer or manual CLI commands.
- **Visual Hardware Feedback**:
  - **LED DS3 ON**: Door is **OPEN**
  - **LED DS3 OFF**: Door is **CLOSED**
- **Robust Debounced FSM**: Employs hysteresis and multi-frame debouncing to eliminate false triggers from noise, curtains, or quick transients.
- **Rich Telemetry & Companion Tools**:
  - Live serial logging over the XDS110 Application UART (115200 baud).
  - Modern Python GUI visualizer with smooth animated door graphics, real-time counters, duration timers, and CSV export.

---

## 📂 Project Structure

```
DOOR SENSOR/
├── firmware/
│   ├── prebuilt_binaries/
│   │   └── awr1843_door_sensor.bin   # Flashable MetaImage ready for UniFlash!
│   ├── src/
│   │   ├── door_detector.c           # Door detection FSM, hysteresis & counting logic
│   │   ├── door_detector.h           # Data structures, thresholds & API definitions
│   │   ├── mss_main.c                # Modified MSS driver with DoorDetector & LED control
│   │   └── mmw_cli.c                 # CLI commands & Standalone Auto-Boot task
│   └── build/
│       └── build_firmware.bat        # 1-Click automated compiler batch script
├── python_gui/
│   ├── door_monitor_gui.py           # Animated desktop GUI visualizer & event logger
│   ├── door_logger_cli.py            # Headless command-line logger for CSV recording
│   └── requirements.txt              # Python dependencies (pyserial)
├── config/
│   ├── door_sensor_profile.cfg       # 77GHz FMCW chirp profile optimized for doors (~4.2cm resolution)
│   └── default_settings.json         # Configurable parameters & pin mappings
├── docs/
│   ├── FLASHING_GUIDE.md             # SOP jumper setup & UniFlash step-by-step guide
│   └── HARDWARE_SETUP.md             # Sensor placement, mounting & wiring guide
└── README.md                         # This documentation file
```

---

## 🚀 Quick Start Guide

### Step 1: Flash the Firmware to AWR1843BOOST
1. Set the **SOP jumpers** on the AWR1843BOOST to **Flashing Mode (1-0-1)**:
   - **SOP2**: CLOSED (Jumper ON)
   - **SOP1**: OPEN (Jumper OFF)
   - **SOP0**: CLOSED (Jumper ON)
2. Connect the AWR1843BOOST to your PC using a micro-USB cable.
3. Open **TI UniFlash** (either desktop version or web version at [dev.ti.com/uniflash](https://dev.ti.com/uniflash)).
4. Select device: **`AWR1843BOOST`**.
5. Set your **Application/User UART COM port** (e.g. `COM3`).
6. In **Meta Image 1**, load:
   ```
   firmware/prebuilt_binaries/awr1843_door_sensor.bin
   ```
7. Click **Load Image** and wait for completion.

*(For detailed flashing steps with screenshots and troubleshooting, see [docs/FLASHING_GUIDE.md](docs/FLASHING_GUIDE.md)).*

---

### Step 2: Run in Standalone Mode
1. Disconnect the USB cable or power.
2. Change the **SOP jumpers** to **Functional Mode (0-0-1)**:
   - **SOP2**: OPEN (Jumper OFF)
   - **SOP1**: OPEN (Jumper OFF)
   - **SOP0**: CLOSED (Jumper ON)
3. Mount the sensor facing your door (between 0.5m and 1.5m away).
4. Power the board using any standard **5V / 2.5A USB adapter, power bank, or PC USB port**.
5. **That's it!** The sensor auto-calibrates to your door distance and begins monitoring:
   - Open the door -> **LED DS3 turns ON** and open count increments.
   - Close the door -> **LED DS3 turns OFF** and close count increments.

---

### Step 3: (Optional) Monitor with Python GUI

If connected to a computer, you can run the live animated visualizer:

```bash
# 1. Install pyserial
pip install -r python_gui/requirements.txt

# 2. Launch the GUI
python python_gui/door_monitor_gui.py
```

**GUI Features:**
- **Animated Door**: Smoothly swings open and closed following the radar's real-time detection.
- **Big Digital Counters**: Displays live Total Opens, Total Closes, Current State, and Duration.
- **Event Log Table**: Logs every open/close transition with timestamp, duration, and measured distance.
- **CSV Export**: Save your event history to a CSV file with one click.
- **Live Controls**: Auto-calibrate distance or adjust range gates dynamically.

For headless recording on a Raspberry Pi or server, run:
```bash
python python_gui/door_logger_cli.py --port COM3 --csv door_activity_log.csv
```

---

## 🛠️ Custom CLI Commands

When connected to any serial terminal (e.g., PuTTY, Tera Term, minicom) at **115200 baud**, the firmware supports custom interactive commands:

| Command | Syntax | Description |
|---|---|---|
| `doorStatus` | `doorStatus` | Prints current door state, total opens, closes, distance, SNR |
| `resetCounters` | `resetCounters` | Resets the cumulative open and close counters back to 0 |
| `calibrate` | `calibrate` | Re-runs the closed door distance calibration |
| `doorCfg` | `doorCfg <rMin> <rMax> [debounce]` | Sets custom door zone range in meters (e.g. `doorCfg 0.5 1.4 5`) |

---

## 🔨 Rebuilding the Firmware from Source

To modify the code or rebuild the `.bin` binary:
1. Edit any source files in `firmware/src/`.
2. Double-click or execute the build script:
   ```cmd
   firmware\build\build_firmware.bat
   ```
3. The script will automatically invoke the TI ARM & C674x compilers, link the binaries, package the multicore image with CRC32, and save the updated `awr1843_door_sensor.bin` to `firmware/prebuilt_binaries/`.
