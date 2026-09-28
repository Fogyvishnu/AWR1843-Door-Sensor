# TI AWR1843BOOST Flashing Guide (No DCA1000 Required)

This guide walks you through flashing the prebuilt door sensor firmware directly onto the onboard QSPI Flash of the **AWR1843BOOST** EVM using standard micro-USB and **TI UniFlash**.

---

## 1. What You Need
1. **TI AWR1843BOOST** Evaluation Board
2. Micro-USB Cable (connects the onboard XDS110 debugger to your PC)
3. 5V 2.5A Power Supply (barrel jack or micro-USB)
4. **TI UniFlash**:
   - **Option A (Recommended, Zero Install)**: Use the Cloud Web Tool directly in Chrome or Edge: [https://dev.ti.com/uniflash](https://dev.ti.com/uniflash)
   - **Option B (Desktop Installer)**: Download from [ti.com/tool/UNIFLASH](https://www.ti.com/tool/UNIFLASH)
5. Firmware file: `firmware/prebuilt_binaries/awr1843_door_sensor.bin`

---

## 2. Setting SOP Jumpers to Flashing Mode

On the AWR1843BOOST board, locate the **SOP (Sense on Power)** jumpers (marked SOP2, SOP1, SOP0):

| Jumper | Pin Header | Flashing Mode (Flash QSPI) | Functional Mode (Run Firmware) |
|---|---|---|---|
| **SOP2** | J5 / Header | **CLOSED (Jumper ON)** | **OPEN (Jumper OFF)** |
| **SOP1** | J6 / Header | **OPEN (Jumper OFF)**  | **OPEN (Jumper OFF)** |
| **SOP0** | J7 / Header | **CLOSED (Jumper ON)** | **CLOSED (Jumper ON)** |

> [!IMPORTANT]
> To enter Flashing Mode, set **SOP2 = ON, SOP1 = OFF, SOP0 = ON** (Mode 1-0-1), then press the **SW2 (RESET)** button or power cycle the board.

---

## 3. Identify the COM Port

1. Connect the micro-USB cable from your PC to the AWR1843BOOST.
2. Open **Device Manager** on Windows and expand **Ports (COM & LPT)**.
3. You will see two XDS110 ports:
   - `XDS110 Class Application/User UART (COM_A)` -> **Used for Flashing and Telemetry (115200 baud)**
   - `XDS110 Class Auxiliary Data Port (COM_D)` -> Used for high-speed radar data (921600 baud)
4. Note down the COM number for the **Application/User UART**.

---

## 4. Flash Using UniFlash

1. Launch **UniFlash** (or open [dev.ti.com/uniflash](https://dev.ti.com/uniflash)).
2. In the search box, type: **`AWR1843BOOST`** and select it.
3. Click **Start**.
4. In the **Settings & Utilities** tab:
   - Under **COM Port**, enter your **Application/User UART COM port** (e.g. `COM3`).
5. In the **Program** tab:
   - Under **Meta Image 1**, click **Browse**.
   - Navigate to:
     ```
     DOOR SENSOR\firmware\prebuilt_binaries\awr1843_door_sensor.bin
     ```
6. Click the blue **Load Image** button.
7. Wait ~15-30 seconds for the flashing process to finish. The progress bar will turn green with:
   ```
   [SUCCESS] Program Load completed successfully
   ```

---

## 5. Switch to Functional Run Mode

1. Disconnect power or remove the micro-USB cable.
2. Change the jumpers to **Functional Mode (Run Mode)**:
   - **SOP2 = OFF (Open)**
   - **SOP1 = OFF (Open)**
   - **SOP0 = ON (Closed)**
3. Power the board back on (via 5V power adapter, USB power bank, or PC USB).
4. The board will automatically boot into standalone door sensor mode!
   - 3 seconds after boot, the radar starts chirping automatically.
   - User LED **DS3** reflects the door state:
     - **LED OFF**: Door is **CLOSED**
     - **LED ON**: Door is **OPEN**
