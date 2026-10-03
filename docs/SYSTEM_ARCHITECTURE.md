# System Architecture & Technical Specification

## TI AWR1843BOOST Standalone Door Sensor & Event Counter
**Document Version:** 1.3.0  
**Classification:** Engineering Specification

---

## 1. System Overview

The **TI AWR1843BOOST Standalone Door Sensor** is an industrial-grade, edge-AI sensing solution designed to detect door state transitions (**OPEN** vs **CLOSED**) and maintain accurate cycle counts directly on-chip. Unlike traditional mmWave development pipelines that require an external capture card (e.g. DCA1000EVM) and host computer processing, this system executes 100% of the radar processing and decision logic within the AWR1843 SoC.

```
+-----------------------------------------------------------------------------------+
|                           TI AWR1843 mmWave Radar SoC                             |
|                                                                                   |
|  +------------------+    +-----------------------+    +------------------------+  |
|  |  BSS (Radar SS)  |    |     DSS (DSP Core)    |    |     MSS (ARM MCU Core) |  |
|  |                  |    |                       |    |                        |  |
|  | - 77GHz Chirp Gen|--->| - 1D Range FFT (HWA)  |--->| - 3D Spatial Gating    |  |
|  | - 3 TX, 4 RX     |    | - 2D Doppler FFT (DSP)|    | - Debounced FSM        |  |
|  | - ADC Sampling   |    | - CA-CFAR Detection   |    | - Open/Close Counters  |  |
|  | - 7200 ksps      |    | - AoA Azimuth Engine  |    | - LED Driver (DS3)     |  |
|  +------------------+    +-----------------------+    | - Live VT100 Console   |  |
|                                                       | - UART Telemetry Stream|  |
|                                                       +------------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
                         +-------------------------------+
                         | Hardware Outputs & Interfaces |
                         |                               |
                         | - LED DS3: ON (Open)/OFF(Shut)|
                         | - Header J5 Pin 19: 3.3V Logic|
                         | - USB UART: VT100 & MQTT Stream|
                         +-------------------------------+
```

---

## 2. Hardware Architecture & Multi-Core Subsystems

The TI AWR1843 SoC contains three heterogeneous processor subsystems operating in tandem:

### 2.1 BSS (Radar Subsystem)
- **Processor**: Dedicated ARM Cortex-R4F core managing the RF analog front-end.
- **RF Configuration**: 3 Transmit (TX) channels, 4 Receive (RX) channels operating across the 76–81 GHz band.
- **Synthesizer**: Fractional-N PLL generating linear frequency sweeps (chirps) at $100\text{ MHz}/\mu\text{s}$.
- **Data Capture**: 4-channel high-speed ADC sampling intermediate frequency (IF) beat signals at $7.2\text{ Msps}$.

### 2.2 DSS (DSP Subsystem)
- **Processor**: TI C674x 32-bit floating-point DSP operating at 600 MHz.
- **Hardware Accelerators**: High-Speed Hardware Accelerator (HWA) offloading FFT computations.
- **Data Processing Responsibilities**:
  1. Windowing and 1D Range FFT over 256 ADC samples per chirp.
  2. Range-Doppler Matrix generation via 2D FFT across 32 chirps.
  3. Constant False Alarm Rate (CA-CFAR) detection across range and Doppler domains.
  4. Angle of Arrival (AoA) estimation across the 8-element virtual antenna array.
  5. 3D Cartesian point cloud transformation $(x, y, z, v, \text{SNR})$.

### 2.3 MSS (Master Subsystem)
- **Processor**: ARM Cortex-R4F MCU operating at 200 MHz under TI-RTOS.
- **Application Responsibilities**:
  1. Boot-time autonomous chirp configuration dispatch.
  2. Mailbox inter-processor communication (IPC) reception from DSS.
  3. **Door Detector Engine** (`door_detector.c`):
     - 3D spatial bounding box gating.
     - Reflection SNR verification and clutter suppression.
     - Hysteresis debounce state machine (500 ms filter).
     - Cycle counting (Total Opens, Total Closes, Duration timers).
  4. Physical indicator actuation (LED DS3 via GPIO_2).
  5. Real-time VT100 console formatting and streaming over User UART.

---

## 3. Memory Allocation & Budget

| Memory Region | Physical Size | Allocated Usage | Margin / Headroom | Purpose |
|---|---|---|---|---|
| **L3 Shared RAM** | 768 KB | 512 KB | 256 KB (33%) | Radar ADC buffer, Range-Doppler matrix, CFAR list |
| **MSS TCMA (RAM)** | 512 KB | 312 KB | 200 KB (39%) | MSS application executable, TI-RTOS kernel, Door Detector |
| **MSS TCMB (RAM)** | 192 KB | 78 KB | 114 KB (59%) | Stack, global variables, VT100 render buffers |
| **DSS L2 SRAM** | 256 KB | 164 KB | 92 KB (36%) | DSP scratchpad, Twiddle factors, AoA matrix |
| **DSS L1P / L1D** | 32 KB + 32 KB | 32 KB + 32 KB | 0 KB (Cache) | DSP direct L1 instruction & data cache |
| **Onboard QSPI Flash** | 4 MB | 334 KB | 3,762 KB (91%) | Multi-core MetaImage firmware storage |

---

## 4. Real-Time Timing Budget & Frame Deadlines

The sensor operates at a nominal frame rate of **10.0 Hz** ($T_{\text{frame}} = 100.0\text{ ms}$).

```
0 ms                       20.2 ms            32.0 ms      40.0 ms  41.5 ms              100.0 ms
+--------------------------+------------------+------------+--------+---------------------+
| Chirp Active Transmission| 1D Range FFT     | 2D Doppler | Door   | Low-Power Standby / |
| & ADC Sampling (32 chirps| Processing (HWA) | & CFAR/AoA | FSM &  | Inter-Frame Idle    |
| @ 630 us chirp interval) |                  | (DSP)      | UART   |                     |
+--------------------------+------------------+------------+--------+---------------------+
|<------ Active RF ------->|<------------ Processing Stage -------->|<----- Idle Margin ->|
```

| Pipeline Stage | Max Execution Time | Hardware Unit | Description |
|---|---|---|---|
| **Chirp Acquisition** | 20.16 ms | BSS Front-End | 32 chirps $\times$ 630 $\mu\text{s}$ chirp interval |
| **1D Range FFT** | 11.80 ms | Hardware Accelerator | Windowing + FFT on 256 samples $\times$ 4 RX |
| **2D Doppler & CFAR** | 8.20 ms | C674x DSP Core | Doppler matrix generation & peak detection |
| **AoA Estimation** | 4.10 ms | C674x DSP Core | Virtual array phase angle solve |
| **Door Detector FSM** | 1.20 ms | Cortex-R4F MSS | 3D gating, debounce filter, counter updates |
| **VT100 UART Output** | 1.80 ms | Cortex-R4F MSS | String formatting & DMA/UART buffer transfer |
| **Total Active Time** | **47.26 ms** | — | **47.3% Duty Cycle** |
| **Idle / Margin** | **52.74 ms** | Power Management | Available for low-power standby |

---

## 5. Fail-Safe & Watchdog Management

1. **Autonomous Auto-Start**: If no serial CLI commands are received within 3.0 seconds of power-on, the MSS automatically executes the embedded chirp configuration from internal flash table `gDoorSensorProfileTable`.
2. **Defensive Point Cloud Validation**:
   - `points == NULL` or `numPoints == 0` is safely treated as an empty frame (no reflection).
   - Any coordinates $(x, y, z)$ containing IEEE-754 `NaN` or `Inf` are rejected prior to distance math.
3. **Clutter Suppression**: Stationary room reflections (walls, ceiling, floor) are rejected by the 3D bounding box gate before reaching the state machine.
4. **Hysteresis Debouncing**: An intentional door transition requires **5 consecutive frames** (500 ms) of consistent state candidate confirmation, eliminating false alarms caused by airborne dust, insects, or momentary multipath reflections.
