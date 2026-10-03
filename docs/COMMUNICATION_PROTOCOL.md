# Communication Protocol & Interface Specification

## TI AWR1843BOOST Standalone Door Sensor
**Document Version:** 1.3.0  
**Classification:** Interface Control Document (ICD)

---

## 1. Physical Layer (UART)

The primary external communication link is the **Application/User UART** interface exposed via the onboard TI XDS110 debug probe or direct header pins:

- **Baud Rate**: `115200`
- **Data Bits**: `8`
- **Parity**: `None`
- **Stop Bits**: `1`
- **Flow Control**: `None`
- **Connector**: Micro-USB (J8) or Expansion Header J5 (Pin 3: TX, Pin 4: RX, 3.3V TTL logic levels)

---

## 2. Interactive CLI Commands

When the sensor is connected to a serial terminal, commands can be submitted as newline-terminated ASCII strings (`\n` or `\r\n`):

| Command | Arguments | Example | Description | Response |
|---|---|---|---|---|
| `doorStatus` | None | `doorStatus` | Queries live door state, counts, distance, SNR | Multi-line status block |
| `resetCounters` | None | `resetCounters` | Resets total open and close counters to 0 | `"Door open/close counters reset to 0\n"` |
| `calibrate` | None | `calibrate` | Starts 20-frame closed-door distance calibration | `"Door calibration triggered...\n"` |
| `vt100` | `<0\|1>` | `vt100 1` | Enables (1) or disables (0) live VT100 dashboard | `"VT100 mode: ENABLED\n"` |
| `doorCfg` | `<rMin> <rMax> [debounce]` | `doorCfg 0.5 1.5 5` | Updates door ROI boundaries and debounce window | `"Door Zone updated: [0.50m to 1.50m]\n"` |
| `version` | None | `version` | Prints firmware version and build date | Version information block |

---

## 3. Telemetry Stream Formats

The sensor transmits three distinct telemetry streams depending on the active operational mode:

### 3.1 Raw Periodic Telemetry (Mode: `vt100 0`)
Transmitted every 10 frames (1.0 second) during continuous operation:

```
[DOOR] State: <STATE> | Opens: <NUM> | Closes: <NUM> | Dist: <FLOAT>m | Pts: <NUM> | SNR: <FLOAT>dB\r\n
```

**Field Breakdown:**
- `<STATE>`: `CLOSED`, `OPEN`, or `UNKNOWN`
- `<NUM>` Opens: Total confirmed door opening cycles
- `<NUM>` Closes: Total confirmed door closing cycles
- `<FLOAT>` Dist: Mean Euclidean distance to door reflection (e.g. `1.18m`)
- `<NUM>` Pts: Number of radar points inside the 3D door ROI
- `<FLOAT>` SNR: Peak reflection signal-to-noise ratio in decibels (e.g. `22.4dB`)

### 3.2 Instant Event Notification (Mode: `vt100 0`)
Transmitted immediately upon a confirmed state transition (debounced):

```
\r\n>>> [EVENT] DOOR <STATE>! (Total Opens: <U32> | Total Closes: <U32>) <<<\r\n
```

### 3.3 Live VT100 Dashboard (Mode: `vt100 1`, Default)
Transmitted every 500 ms (2 Hz) and immediately upon state transition. Formatted with ANSI/VT100 terminal escape sequences:
- `\x1B[H`: Cursor home (row 1, col 1)
- `\x1B[?25l`: Hide cursor
- `\x1B[1;32m`: Green color (Door Closed)
- `\x1B[1;31m`: Red color (Door Open)
- `\x1B[1;36m`: Cyan color (Panels and borders)
- `\x1B[K`: Erase line to end (eliminates redraw artifacts)

---

## 4. MQTT & Home Assistant JSON Schema

When utilizing `door_mqtt_bridge.py`, telemetry is parsed and published to standard MQTT topics.

### 4.1 State Topic: `awr1843/door/state`
Published on every state transition and periodically every 5.0 seconds:

```json
{
  "state": "CLOSED",
  "opens": 14,
  "closes": 14,
  "distance": 1.18,
  "snr": 22.4,
  "points": 7,
  "uptime_seconds": 3840,
  "timestamp": "2026-10-03T21:00:00.000000"
}
```

### 4.2 Control Topic: `awr1843/door/set`
Accepts commands from Home Assistant or external automation platforms:

```json
{"command": "resetCounters"}
```
or simple text payloads:
- `"reset"`
- `"calibrate"`
- `"vt100 1"`

### 4.3 Availability Topic: `awr1843/door/availability`
- Payload: `"online"` (retained on startup)
- Payload: `"offline"` (sent upon graceful shutdown or MQTT Last Will and Testament)
