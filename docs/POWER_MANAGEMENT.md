# Power Management & Battery Life Engineering Guide

## TI AWR1843BOOST Standalone Door Sensor
**Document Version:** 1.3.0  
**Classification:** Electrical & Power Specification

---

## 1. Power Supply Requirements

The TI AWR1843BOOST requires a regulated **5.0V DC** power supply capable of delivering instantaneous transient currents during the RF chirp ramps:

- **Input Voltage**: $5.0\text{ V} \pm 5\%$ ($4.75\text{ V}$ to $5.25\text{ V}$)
- **Peak Current Requirement**: **$2.5\text{ A}$** (during concurrent 3-TX chirp ramps)
- **Nominal Continuous Current**: $320\text{ mA} - 420\text{ mA}$ (@ 5.0V, 10 Hz frame rate)
- **Power Connector Options**:
  1. Micro-USB (J8): Powered directly from standard USB 3.0 port, 5V power bank, or 5V wall adapter.
  2. 5V DC Barrel Jack (2.1mm center positive).

> [!WARNING]
> **Brownout Prevention**: Standard USB 2.0 ports are limited to 500 mA. When transmitting chirps, voltage sag below 4.5V on a weak USB 2.0 port will trigger the board's internal PMIC power-on reset (POR). Always use a USB 3.0 port (900 mA), dedicated 5V/2A power adapter, or high-capacity power bank.

---

## 2. Onboard Power Rail Distribution

```
                +---------------------+
                | 5.0V DC Input (USB) |
                +---------------------+
                           |
         +-----------------+-----------------+
         |                 |                 |
         v                 v                 v
   +-----------+     +-----------+     +-----------+
   | 1.2V Buck |     | 1.8V LDO  |     | 3.3V Buck |
   | (LP87524) |     | (LP87524) |     | (TPS62130)|
   +-----------+     +-----------+     +-----------+
         |                 |                 |
         v                 v                 v
   - RF LO & Synth   - Analog PLL      - Digital I/O
   - DSP Core        - Baseband ADC    - QSPI Flash
   - ARM Cortex-R4F  - Clock Tree      - XDS110 Debug
   (Peak: 1.4 A)     (Peak: 350 mA)    (Peak: 250 mA)
```

---

## 3. Power Consumption vs Frame Rate

Because mmWave radar operation is inherently periodic, power consumption scales directly with the **frame periodicity** ($T_{\text{frame}}$):

```math
P_{\text{avg}} = P_{\text{active}} \times D + P_{\text{idle}} \times (1 - D)
```

where duty cycle $D = \frac{T_{\text{active}}}{T_{\text{frame}}}$. With active acquisition and processing time $T_{\text{active}} \approx 47.3\text{ ms}$:

| Frame Rate | Period ($T_{\text{frame}}$) | Active Duty Cycle ($D$) | Average Power (@ 5V) | Average Current (@ 5V) |
|---|---|---|---|---|
| **10.0 Hz (Default)** | $100\text{ ms}$ | $47.3\%$ | **$1.42\text{ W}$** | $284\text{ mA}$ |
| **5.0 Hz (Balanced)** | $200\text{ ms}$ | $23.6\%$ | **$0.86\text{ W}$** | $172\text{ mA}$ |
| **2.0 Hz (Low Power)** | $500\text{ ms}$ | $9.5\%$ | **$0.48\text{ W}$** | $96\text{ mA}$ |
| **1.0 Hz (Ultra Low)** | $1000\text{ ms}$ | $4.7\%$ | **$0.34\text{ W}$** | $68\text{ mA}$ |

---

## 4. Battery Life Projections

For untethered or battery-backed installations, projected operating times are calculated below for common power storage configurations (assuming 85% DC-DC boost conversion efficiency):

| Battery Pack Configuration | Usable Energy | 10 Hz Frame Rate (Default) | 5 Hz Frame Rate | 2 Hz Frame Rate |
|---|---|---|---|---|
| **10,000 mAh 5V Power Bank** | $37.0\text{ Wh}$ | **$26.0\text{ hours}$** | **$43.0\text{ hours}$** | **$77.0\text{ hours}$ (3.2 days)** |
| **20,000 mAh 5V Power Bank** | $74.0\text{ Wh}$ | **$52.1\text{ hours}$** | **$86.0\text{ hours}$** | **$154.2\text{ hours}$ (6.4 days)** |
| **Single 18650 Li-Ion (3500mAh)** | $10.8\text{ Wh}$ | **$7.6\text{ hours}$** | **$12.5\text{ hours}$** | **$22.5\text{ hours}$** |
| **Solar + 12V 7Ah SLA Battery** | $71.4\text{ Wh}$ | **Continuous (Indefinite with 10W panel)** | **Continuous** | **Continuous** |

---

## 5. Low-Power Optimization Settings

To maximize battery life in low-activity commercial environments:

1. **Enable Deep Idle Power-Down**:
   In `door_sensor_profile.cfg`, configure:
   ```
   lowPower 1 1
   ```
   This gates the RF synthesizer, turns off the ADC baseband, and puts the C674x DSP into low-leakage standby during the inter-frame idle window.

2. **Adjust Frame Period for Low-Traffic Doors**:
   For residential doors or storage vaults where rapid transitions are infrequent, changing the frame period from 100 ms to 250 ms (4 frames/sec):
   ```
   frameCfg 0 1 32 0 250 1 0
   ```
   Reduces power consumption by **54%** with zero degradation in detection reliability.
