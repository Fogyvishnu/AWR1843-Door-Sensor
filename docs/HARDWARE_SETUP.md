# Hardware Setup & Placement Guide

## 1. Overview
The AWR1843BOOST operates at 77 GHz to 81 GHz FMCW radar frequencies. It does not require any cameras, optical sensors, or line-of-sight lighting. It can see through darkness, smoke, fog, and thin enclosures (like 3D-printed plastic cases).

---

## 2. Mounting Configurations

### Placement Option A: Wall / Ceiling Facing the Door (Recommended)
```
          [ Wall / Stand ]
          [ AWR1843BOOST ]
                |
                |  Radar Boresight Beam (77 GHz)
                |  Distance: 0.5m - 1.5m
                v
       +-------------------+
       |     DOOR LEAF     | (CLOSED: High reflected energy)
       +-------------------+
               /
              /  (OPEN: Beam shoots through into room beyond)
             v
```
- Mount the sensor facing the door surface at a height of 1.0m to 1.5m.
- Keep the distance between sensor and closed door between **0.4m and 1.8m**.
- **When Door is CLOSED**:
  - The door slab reflects strong radar echoes in the specified range gate.
  - The onboard detector registers the door reflection, counts it as **CLOSED**, and turns **LED DS3 OFF**.
- **When Door is OPEN**:
  - The door swings or slides away. The radar beam travels past the doorway into empty space or a distant wall (> 2m).
  - The absence of reflections in the closed zone confirms the door is **OPEN**, increments the **Total Opens** counter, and turns **LED DS3 ON**.

### Placement Option B: Top of Door Frame Looking Down / Across Threshold
- Mount the sensor on the top door frame angled downwards 45° across the swing threshold.
- Distance to door when closed is ~0.3m - 0.7m.

---

## 3. Onboard Indicators & Pinout

### Onboard LEDs:
- **DS4 (Green)**: 5V Power Indicator
- **DS3 (Orange User LED / GPIO_2)**:
  - **OFF**: Door is **CLOSED** (Secure)
  - **SOLID ON**: Door is **OPEN** (Alert)
- **DS2 (Red)**: Hardware NERROR indicator (should remain off under normal operation)

### External GPIO Pin (BoosterPack 40-Pin Header):
If you wish to trigger an external buzzer, relay, or connect to an ESP32 / Arduino / Home Assistant:
- **Header J5, Pin 19** (GPIO_1 / DSS output):
  - Logic **HIGH (3.3V)**: Door OPEN
  - Logic **LOW (0V)**: Door CLOSED

---

## 4. Power Supply Options
1. **Option 1 (Standalone Wall Outlet / Power Bank)**:
   - Connect a standard 5V / 2.5A USB wall charger to the micro-USB port or barrel jack.
   - The board runs 100% standalone without any computer attached!
2. **Option 2 (PC Connected)**:
   - Connect micro-USB to a PC to view live GUI animation, counter statistics, and CSV logs.
