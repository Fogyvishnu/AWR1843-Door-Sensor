# Site Survey, Commissioning & Field Tuning Guide

## TI AWR1843BOOST Standalone Door Sensor
**Document Version:** 1.3.0  
**Classification:** Standard Operating Procedure (SOP)

---

## 1. Pre-Installation Site Survey

Before permanently mounting the sensor, evaluate the doorway environment against the checklist below:

| Parameter | Recommended Specification | Field Verification Note |
|---|---|---|
| **Mounting Distance** | $0.5\text{ m} - 1.5\text{ m}$ from closed door surface | Distances $>2.5\text{ m}$ reduce reflection SNR |
| **Door Material** | Wood, Metal, Composite, Glass | Verify radar cross section (RCS) per Section 2 |
| **Clearance Cone** | $\pm 45^\circ$ Azimuth, $\pm 20^\circ$ Elevation | Keep moving curtains/plants outside this zone |
| **Vibration** | Rigid door frame or wall surface | Do not mount on flexible drywall that flexes on door slam |
| **Power Source** | 5V / 2.0A dedicated USB power | Avoid unpowered USB hub extensions |

---

## 2. Door Material Reflection Characteristics

Different door materials exhibit distinct reflection signatures at 77 GHz:

```
+-------------------------------------------------------------------------------+
| Material               | RCS (@ 77 GHz) | Expected SNR | Tuning Tip           |
+-------------------------------------------------------------------------------+
| Solid Metal / Steel    | Very High      | 28 - 35 dB   | Increase minSnr to   |
| (Commercial fire door) |                |              | 15dB to cut multipath|
+-------------------------------------------------------------------------------+
| Solid Wood / Timber    | High           | 20 - 28 dB   | Factory default      |
| (Residential exterior) |                |              | settings optimal     |
+-------------------------------------------------------------------------------+
| Hollow Core Composite  | Medium         | 14 - 22 dB   | Factory default      |
| (Interior bedroom/bath)|                |              | settings optimal     |
+-------------------------------------------------------------------------------+
| Tempered Glass         | Medium-High    | 16 - 24 dB   | Normal incidence     |
| (Retail storefront)    |                |              | required; avoid angle|
+-------------------------------------------------------------------------------+
```

---

## 3. Physical Installation Procedure

1. **Mounting Location**:
   - For standard interior/exterior swinging doors, mount the sensor on the adjacent wall facing the closed door leaf at a height of **$1.1\text{ m} - 1.3\text{ m}$** above the finished floor level.
   - Alternatively, mount directly above the doorway header tilted downwards at a $35^\circ$ pitch angle.

2. **Alignment**:
   - Ensure the radar front-end antennas are oriented horizontally (parallel to the floor) to maintain the wide $\pm 45^\circ$ azimuth coverage across the door sweep arc.

3. **Power On & Automatic Baseline Calibration**:
   - Ensure the door is **completely closed**.
   - Connect 5V power to the AWR1843BOOST board.
   - The green LED DS3 will remain OFF while the MCU samples 20 frames ($\approx 2.0\text{ s}$) to automatically measure the exact closed-door distance and establish the spatial range gate $[R_{\min}, R_{\max}]$.
   - Once calibrated, the sensor immediately enters active monitoring.

---

## 4. Commissioning Verification Checklist

Perform the following operational acceptance tests (OAT):

- [ ] **Baseline Check**: With door closed, run CLI command `doorStatus` or view VT100 console. Confirm:
  - `State: CLOSED`
  - `Calibrated: YES`
  - `Points in ROI >= 2`
  - `LED DS3: OFF`
- [ ] **Open Transition Test**: Swing the door open by at least 15 cm.
  - Confirm: Within 500 ms, `LED DS3 turns ON`.
  - Confirm: `Total Opens` counter increments by exactly 1.
  - Confirm: VT100 dashboard switches to RED `[ DOOR OPEN ]`.
- [ ] **Close Transition Test**: Swing the door fully closed.
  - Confirm: Within 500 ms, `LED DS3 turns OFF`.
  - Confirm: `Total Closes` counter increments by exactly 1.
  - Confirm: VT100 dashboard switches to GREEN `[ DOOR CLOSED ]`.
- [ ] **Glitch Rejection Test**: Quickly wave your hand or momentarily crack the door for $<300\text{ ms}$ and let it snap shut.
  - Confirm: State remains CLOSED and counters do NOT increment (transient debounce rejection verified).

---

## 5. Troubleshooting & Parameter Tuning

| Symptom | Root Cause | Corrective Action |
|---|---|---|
| **Door shows OPEN when physically closed** | Range gate too narrow or door was open during boot calibration | Close door and run CLI command `calibrate`, or widen range with `doorCfg 0.3 2.0 5` |
| **Door shows CLOSED when cracked open** | Side wall or door frame reflection inside ROI | Narrow lateral boundaries or decrease `doorCfg` max range |
| **False trigger when person walks outside room** | Deep points passing through doorway | Tighten `rangeMax` to door face distance $+ 20\text{ cm}$ |
| **LED DS3 flickers during opening** | Debounce frame count too low | Increase debounce frames from 5 to 7 via `doorCfg` |
