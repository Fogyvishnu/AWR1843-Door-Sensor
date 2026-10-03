"""
TI AWR1843BOOST - Live Running UART VT100 Terminal Monitor
===========================================================
Displays a real-time, flicker-free VT100/ANSI console dashboard for
the standalone AWR1843 door open/close detector and cycle counter.

Usage:
    python door_vt100.py [--port COM3] [--baud 115200] [--csv door_events.csv]
"""

import sys
import os
import time
import argparse
import csv
from datetime import datetime

# Windows ANSI terminal escape sequence support
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # STD_OUTPUT_HANDLE = -11
    h_stdout = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode))
    # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    mode.value |= 0x0004
    kernel32.SetConsoleMode(h_stdout, mode)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial is required. Install it using: pip install pyserial")
    sys.exit(1)


# ANSI / VT100 Color and Formatting Codes
ESC = "\033"
C_RESET = f"{ESC}[0m"
C_BOLD = f"{ESC}[1m"
C_RED = f"{ESC}[1;31m"
C_GREEN = f"{ESC}[1;32m"
C_YELLOW = f"{ESC}[1;33m"
C_BLUE = f"{ESC}[1;34m"
C_MAGENTA = f"{ESC}[1;35m"
C_CYAN = f"{ESC}[1;36m"
C_WHITE = f"{ESC}[1;37m"
C_BG_RED = f"{ESC}[41;1;37m"
C_BG_GREEN = f"{ESC}[42;1;37m"
CLEAR_SCREEN = f"{ESC}[2J"
CURSOR_HOME = f"{ESC}[H"
CURSOR_HIDE = f"{ESC}[?25l"
CURSOR_SHOW = f"{ESC}[?25h"
ERASE_LINE = f"{ESC}[K"


def auto_detect_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = p.description or ""
        if "Application" in desc or "User UART" in desc or "XDS110" in desc:
            return p.device
    if ports:
        return ports[0].device
    return None


def get_non_blocking_key():
    """Reads a single keypress without waiting (cross-platform)."""
    if sys.platform == "win32":
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            try:
                return ch.decode("utf-8").lower()
            except Exception:
                return ""
    else:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            return sys.stdin.read(1).lower()
    return None


def make_gauge(val, max_val, length=16, fill_char="=", head_char=">"):
    """Generates an ASCII meter bar [========>       ]"""
    val = max(0.0, min(float(val), float(max_val)))
    ratio = val / float(max_val)
    filled = int(ratio * length)
    bar = fill_char * max(0, filled - 1)
    if filled > 0:
        bar += head_char
    bar = bar.ljust(length, " ")
    return f"[{bar}]"


class DoorVT100Monitor:
    def __init__(self, port, baud, csv_path=None, beep_on_open=True):
        self.port = port
        self.baud = baud
        self.csv_path = csv_path
        self.beep_on_open = beep_on_open

        # Telemetry State
        self.door_state = "UNKNOWN"
        self.total_opens = 0
        self.total_closes = 0
        self.door_distance = 0.0
        self.peak_snr = 0.0
        self.points_in_roi = 0
        self.is_calibrated = False
        self.state_start_time = time.time()
        self.start_time = time.time()
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.fps = 0.0

        # Event History (Last 5 transitions)
        self.history = []

        # Serial Connection
        self.ser = None
        self.csv_file = None
        self.csv_writer = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
            self.ser.reset_input_buffer()
        except Exception as e:
            print(f"{C_RED}[!] Error: Failed to open serial port {self.port}: {e}{C_RESET}")
            sys.exit(1)

        if self.csv_path:
            file_exists = os.path.exists(self.csv_path)
            self.csv_file = open(self.csv_path, "a", newline="", buffering=1)
            self.csv_writer = csv.writer(self.csv_file)
            if not file_exists:
                self.csv_writer.writerow(["Timestamp", "Event", "Current State", "Total Opens", "Total Closes", "Distance (m)", "SNR (dB)"])

    def record_transition(self, new_state, increment=True):
        if new_state == self.door_state:
            return

        old_state = self.door_state
        self.door_state = new_state
        self.state_start_time = time.time()

        if new_state == "OPEN":
            if increment:
                self.total_opens += 1
            event_name = "DOOR OPENED"
            if self.beep_on_open:
                # Terminal audible bell
                sys.stdout.write("\a")
                sys.stdout.flush()
        elif new_state == "CLOSED":
            if increment:
                self.total_closes += 1
            event_name = "DOOR CLOSED"
        else:
            event_name = f"STATE -> {new_state}"

        timestamp = datetime.now().strftime("%H:%M:%S")
        record = {
            "time": timestamp,
            "event": event_name,
            "trans": f"{old_state}->{new_state}",
            "opens": self.total_opens,
            "closes": self.total_closes,
            "dist": self.door_distance,
            "snr": self.peak_snr,
        }
        self.history.insert(0, record)
        if len(self.history) > 5:
            self.history.pop()

        if self.csv_writer:
            self.csv_writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_name,
                self.door_state,
                self.total_opens,
                self.total_closes,
                f"{self.door_distance:.2f}" if self.door_state == "CLOSED" else "",
                f"{self.peak_snr:.1f}",
            ])

    def parse_line(self, line):
        line = line.strip()
        if not line:
            return

        # Check for instant event messages
        if "EVENT: Door Opened" in line or "EVENT] DOOR OPEN" in line:
            if "Total Opens:" in line:
                try:
                    self.total_opens = int(line.split("Total Opens:")[1].split("|")[0].strip())
                except (ValueError, IndexError):
                    pass
            if "Total Closes:" in line:
                try:
                    self.total_closes = int(line.split("Total Closes:")[1].split(")")[0].strip())
                except (ValueError, IndexError):
                    pass
            self.record_transition("OPEN", increment=("Total Opens:" not in line))
            return
        elif "EVENT: Door Closed" in line or "EVENT] DOOR CLOSE" in line:
            if "Total Opens:" in line:
                try:
                    self.total_opens = int(line.split("Total Opens:")[1].split("|")[0].strip())
                except (ValueError, IndexError):
                    pass
            if "Total Closes:" in line:
                try:
                    self.total_closes = int(line.split("Total Closes:")[1].split(")")[0].strip())
                except (ValueError, IndexError):
                    pass
            self.record_transition("CLOSED", increment=("Total Closes:" not in line))
            return

        # Check for periodic telemetry lines:
        # [DOOR] State: CLOSED | Opens: 0 | Closes: 0 | Dist: 1.15m | Pts: 5 | SNR: 18.2dB
        if "[DOOR]" in line or "State:" in line:
            self.frame_count += 1
            now = time.time()
            dt = now - self.last_frame_time
            if dt > 0:
                self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)
            self.last_frame_time = now

            parts = line.split("|")
            for p in parts:
                p = p.strip()
                if "Opens:" in p:
                    try:
                        self.total_opens = int(p.split("Opens:")[1].strip())
                    except ValueError:
                        pass
                elif "Closes:" in p:
                    try:
                        self.total_closes = int(p.split("Closes:")[1].strip())
                    except ValueError:
                        pass
                elif "Dist:" in p:
                    try:
                        self.door_distance = float(p.split("Dist:")[1].strip().replace("m", ""))
                    except ValueError:
                        pass
                elif "Pts:" in p:
                    try:
                        self.points_in_roi = int(p.split("Pts:")[1].strip())
                    except ValueError:
                        pass
                elif "SNR:" in p:
                    try:
                        self.peak_snr = float(p.split("SNR:")[1].strip().replace("dB", ""))
                    except ValueError:
                        pass

            for p in parts:
                p = p.strip()
                if "State:" in p:
                    st = p.split("State:")[1].strip().upper()
                    if st in ["OPEN", "CLOSED", "UNKNOWN"]:
                        if st != self.door_state:
                            self.record_transition(st, increment=False)

    def render_dashboard(self):
        elapsed_total = int(time.time() - self.start_time)
        m_tot, s_tot = divmod(elapsed_total, 60)
        h_tot, m_tot = divmod(m_tot, 60)

        elapsed_state = int(time.time() - self.state_start_time)
        m_st, s_st = divmod(elapsed_state, 60)
        h_st, m_st = divmod(m_st, 60)

        dist_gauge = make_gauge(self.door_distance, 2.5, 14)
        snr_gauge = make_gauge(self.peak_snr, 30.0, 14)

        # Status Banner Styling
        if self.door_state == "CLOSED":
            status_banner = f"{C_GREEN}{C_BOLD}[   DOOR CLOSED   ]     LED DS3: OFF (Secure)                 {C_RESET}"
            door_color = C_GREEN
            art = [
                "  +-----------+  ",
                "  |   |   |   |  ",
                "  |   | . |   |  ",
                "  |   |   |   |  ",
                "  +-----------+  ",
                "  [DOOR CLOSED]  ",
            ]
        elif self.door_state == "OPEN":
            status_banner = f"{C_RED}{C_BOLD}[    DOOR OPEN    ]     LED DS3: ON  (Passage Active!)        {C_RESET}"
            door_color = C_RED
            art = [
                "  +           +  ",
                "   \\         /   ",
                "    \\   .   /    ",
                "     \\     /     ",
                "  +           +  ",
                "   [DOOR OPEN]   ",
            ]
        else:
            status_banner = f"{C_YELLOW}{C_BOLD}[     UNKNOWN     ]     Awaiting radar detection...           {C_RESET}"
            door_color = C_YELLOW
            art = [
                "  + - - - - - +  ",
                "  |     ?     |  ",
                "  |     .     |  ",
                "  |     ?     |  ",
                "  + - - - - - +  ",
                "   [SCANNING]    ",
            ]

        beep_str = f"{C_GREEN}ON{C_RESET}" if self.beep_on_open else f"{C_RED}OFF{C_RESET}"

        buf = []
        buf.append(f"{CURSOR_HOME}{CURSOR_HIDE}")
        buf.append(f"{C_CYAN}+-----------------------------------------------------------------------------+{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}|        TI AWR1843BOOST mmWave Radar - Live VT100 Console Monitor            |{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}|    77 GHz FMCW | Standalone On-Chip Event Counter | Port: {self.port:<6}        |{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}+-----------------------------------------------------------------------------+{C_RESET}{ERASE_LINE}")
        buf.append(f"| STATUS: {status_banner}|{ERASE_LINE}")
        buf.append(f"{C_CYAN}+-------------------+---------------------------------------------------------+{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}| DOOR VISUAL       | RADAR SENSING METRICS & PASSAGE STATISTICS              |{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}+-------------------+---------------------------------------------------------+{C_RESET}{ERASE_LINE}")

        # Metrics rows side-by-side with Door Art
        d_str = f"{self.door_distance:5.2f} m" if self.door_state == "CLOSED" else "  --- m "
        buf.append(f"| {door_color}{art[0]}{C_RESET} | Target Distance : {d_str}    | Total Openings : {C_BOLD}{self.total_opens:<8}{C_RESET} |{ERASE_LINE}")
        buf.append(f"| {door_color}{art[1]}{C_RESET} | Distance Gauge  : {dist_gauge} | Total Closings : {C_BOLD}{self.total_closes:<8}{C_RESET} |{ERASE_LINE}")
        buf.append(f"| {door_color}{art[2]}{C_RESET} | Peak Reflection : {self.peak_snr:5.1f} dB   | Time In State  : {h_st:02d}:{m_st:02d}:{s_st:02d}   |{ERASE_LINE}")
        buf.append(f"| {door_color}{art[3]}{C_RESET} | Reflection SNR  : {snr_gauge} | Debounce Filter: 500 ms (5f) |{ERASE_LINE}")
        buf.append(f"| {door_color}{art[4]}{C_RESET} | Points in ROI   : {self.points_in_roi:3d} points   | Uptime Session : {h_tot:02d}:{m_tot:02d}:{s_tot:02d}   |{ERASE_LINE}")
        buf.append(f"| {door_color}{art[5]}{C_RESET} | Data Stream FPS : {self.fps:5.1f} Hz     | Audio Beep     : {beep_str:<12} |{ERASE_LINE}")

        # Event History Table
        buf.append(f"{C_CYAN}+-------------------+---------------------------------------------------------+{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}| RECENT EVENT TRANSITION HISTORY                                             |{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}+----+----------+-------------+--------------+--------+--------+--------------+{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}| #  | Time     | Event       | Transition   | Opens  | Closes | Distance     |{C_RESET}{ERASE_LINE}")
        buf.append(f"{C_CYAN}+----+----------+-------------+--------------+--------+--------+--------------+{C_RESET}{ERASE_LINE}")

        if not self.history:
            buf.append(f"| -- | --:--:-- | MONITORING  | Awaiting door activity transitions...         |{ERASE_LINE}")
        else:
            for i, rec in enumerate(self.history):
                c_evt = C_RED if "OPEN" in rec['event'] else C_GREEN
                d_val = f"{rec['dist']:.2f} m" if rec['dist'] > 0.05 and "CLOSED" in rec['event'] else "  --- m "
                buf.append(
                    f"| {i+1:<2} | {rec['time']} | {c_evt}{rec['event']:<11}{C_RESET} | "
                    f"{rec['trans']:<12} | {rec['opens']:<6} | {rec['closes']:<6} | {d_val:<12} |{ERASE_LINE}"
                )

        buf.append(f"{C_CYAN}+----+----------+-------------+--------------+--------+--------+--------------+{C_RESET}{ERASE_LINE}")
        buf.append(f"| COMMANDS: {C_BOLD}[r]{C_RESET} Reset  {C_BOLD}[c]{C_RESET} Calibrate  {C_BOLD}[b]{C_RESET} Beep  {C_BOLD}[t]{C_RESET} Firmware VT100  {C_BOLD}[q]{C_RESET} Quit |{ERASE_LINE}")
        buf.append(f"{C_CYAN}+-----------------------------------------------------------------------------+{C_RESET}{ERASE_LINE}")

        sys.stdout.write("\n".join(buf) + "\n")
        sys.stdout.flush()

    def run(self):
        self.connect()

        # Clear terminal screen and hide cursor on start
        sys.stdout.write(f"{CLEAR_SCREEN}{CURSOR_HOME}{CURSOR_HIDE}")
        sys.stdout.flush()

        line_buffer = ""
        last_render = 0

        # Check if incoming data is already raw firmware VT100 stream
        is_direct_vt100 = False

        try:
            while True:
                # Handle user keyboard shortcuts
                key = get_non_blocking_key()
                if key == 'q':
                    break
                elif key == 'r':
                    if self.ser and self.ser.is_open:
                        self.ser.write(b"resetCounters\n")
                    self.total_opens = 0
                    self.total_closes = 0
                elif key == 'c':
                    if self.ser and self.ser.is_open:
                        self.ser.write(b"calibrate\n")
                elif key == 'b':
                    self.beep_on_open = not self.beep_on_open
                elif key == 't':
                    if self.ser and self.ser.is_open:
                        self.ser.write(b"vt100\n")

                # Read UART bytes with auto-reconnection on disconnect
                try:
                    if self.ser and self.ser.is_open:
                        if self.ser.in_waiting > 0:
                            raw_bytes = self.ser.read(self.ser.in_waiting)
                            text = raw_bytes.decode("utf-8", errors="replace")

                            # If firmware is already emitting VT100 escape codes directly
                            if "\x1b[H" in text or "\x1b[2J" in text or is_direct_vt100:
                                is_direct_vt100 = True
                                sys.stdout.write(text)
                                sys.stdout.flush()
                                # Extract event logging to CSV if any
                                if "EVENT" in text:
                                    if "DOOR OPEN" in text:
                                        self.record_transition("OPEN")
                                    elif "DOOR CLOSED" in text:
                                        self.record_transition("CLOSED")
                                time.sleep(0.01)
                                continue

                            line_buffer += text
                            while "\n" in line_buffer:
                                line, line_buffer = line_buffer.split("\n", 1)
                                self.parse_line(line)
                    else:
                        # Attempt reconnection
                        time.sleep(1.0)
                        self.connect()
                except Exception as e:
                    # Connection lost, retry
                    if self.ser:
                        try:
                            self.ser.close()
                        except Exception:
                            pass
                        self.ser = None
                    self.door_state = "RECONNECTING"
                    self.render_dashboard()
                    time.sleep(1.5)
                    detected = auto_detect_port()
                    if detected:
                        self.port = detected
                    try:
                        self.connect()
                    except Exception:
                        pass
                    continue

                # Render dashboard at up to 10 Hz when parsing line stream
                if not is_direct_vt100 and (time.time() - last_render) >= 0.10:
                    self.render_dashboard()
                    last_render = time.time()

                time.sleep(0.01)

        except KeyboardInterrupt:
            pass
        finally:
            # Restore cursor and clean terminal
            sys.stdout.write(f"{CURSOR_SHOW}{C_RESET}\n")
            sys.stdout.flush()
            if self.ser:
                self.ser.close()
            if self.csv_file:
                self.csv_file.close()
            print(f"[+] VT100 Session ended. Total events recorded: Opens={self.total_opens}, Closes={self.total_closes}")


def main():
    parser = argparse.ArgumentParser(description="AWR1843 Live VT100 UART Terminal Monitor")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (auto-detected if omitted)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--csv", type=str, default="door_events_log.csv", help="CSV log filename")
    parser.add_argument("--no-beep", action="store_true", help="Disable audible beep on door open")
    args = parser.parse_args()

    port = args.port or auto_detect_port()
    if not port:
        print("[!] Error: No serial port found. Connect your TI AWR1843BOOST and retry.")
        sys.exit(1)

    monitor = DoorVT100Monitor(
        port=port,
        baud=args.baud,
        csv_path=args.csv,
        beep_on_open=(not args.no_beep)
    )
    monitor.run()


if __name__ == "__main__":
    main()
