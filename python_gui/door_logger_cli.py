"""
TI AWR1843BOOST - Headless Door Activity Logger & Event Counter
===============================================================
Usage:
    python door_logger_cli.py --port COM3 --baud 115200 --csv door_log.csv
"""

import sys
import os
import time
import argparse
import csv
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial is required. Install it using: pip install pyserial")
    sys.exit(1)


def auto_detect_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = p.description or ""
        if "Application" in desc or "User UART" in desc or "XDS110" in desc:
            return p.device
    if ports:
        return ports[0].device
    return None


def main():
    parser = argparse.ArgumentParser(description="AWR1843 Door Activity Serial Logger")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (e.g. COM3 or /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--csv", type=str, default="door_events_log.csv", help="CSV log filename")
    parser.add_argument("--cfg", type=str, default=None, help="Optional .cfg file to send on connect")
    args = parser.parse_args()

    port = args.port or auto_detect_port()
    if not port:
        print("[!] Error: No serial port found. Connect your AWR1843BOOST and retry.")
        sys.exit(1)

    print("=" * 65)
    print("  TI AWR1843BOOST STANDALONE DOOR SENSOR LOGGER")
    print(f"  Port: {port} | Baud: {args.baud}")
    print(f"  CSV Output: {args.csv}")
    print("=" * 65)

    # Initialize CSV file if not exists
    file_exists = os.path.exists(args.csv)
    csv_file = open(args.csv, "a", newline="", buffering=1)
    csv_writer = csv.writer(csv_file)
    if not file_exists:
        csv_writer.writerow(["Timestamp", "Event", "Current State", "Total Opens", "Total Closes", "Distance (m)"])

    try:
        ser = serial.Serial(port, args.baud, timeout=0.1)
    except Exception as e:
        print(f"[!] Failed to open serial port {port}: {e}")
        sys.exit(1)

    # Send configuration profile if provided
    if args.cfg and os.path.exists(args.cfg):
        print(f"[*] Uploading chirp profile: {args.cfg}...")
        with open(args.cfg, "r") as cf:
            for line in cf:
                line = line.strip()
                if line and not line.startswith("%"):
                    ser.write((line + "\n").encode())
                    time.sleep(0.05)
        print("[+] Profile sent. Sensor started.")

    door_state = "UNKNOWN"
    total_opens = 0
    total_closes = 0

    print("[*] Listening for door events... Press Ctrl+C to exit.\n")

    try:
        line_buf = ""
        while True:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                line_buf += chunk

                while "\n" in line_buf:
                    line, line_buf = line_buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    # Print raw line if debug desired
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if "[DOOR]" in line or "DOOR STATUS" in line:
                        print(f"[{now_str}] {line}")
                        # Extract metrics
                        parts = line.split("|")
                        dist = 0.0
                        for p in parts:
                            p = p.strip()
                            if "State:" in p:
                                door_state = p.split("State:")[1].strip().upper()
                            elif "Opens:" in p:
                                try:
                                    total_opens = int(p.split("Opens:")[1].strip())
                                except ValueError:
                                    pass
                            elif "Closes:" in p:
                                try:
                                    total_closes = int(p.split("Closes:")[1].strip())
                                except ValueError:
                                    pass
                            elif "Dist:" in p:
                                try:
                                    dist = float(p.split("Dist:")[1].strip().replace("m", ""))
                                except ValueError:
                                    pass

                    elif "EVENT: Door Opened" in line or "DOOR OPENED" in line:
                        total_opens += 1
                        door_state = "OPEN"
                        print(f"\n>>> [{now_str}] EVENT: DOOR OPENED! (Total Opens: {total_opens}) <<<\n")
                        csv_writer.writerow([now_str, "DOOR_OPENED", door_state, total_opens, total_closes, ""])

                    elif "EVENT: Door Closed" in line or "DOOR CLOSED" in line:
                        total_closes += 1
                        door_state = "CLOSED"
                        print(f"\n>>> [{now_str}] EVENT: DOOR CLOSED! (Total Closes: {total_closes}) <<<\n")
                        csv_writer.writerow([now_str, "DOOR_CLOSED", door_state, total_opens, total_closes, ""])

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[*] Exiting logger...")
    finally:
        ser.close()
        csv_file.close()
        print("[+] Log file closed successfully.")


if __name__ == "__main__":
    main()
