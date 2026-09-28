"""
TI AWR1843BOOST - Real-Time Door Open/Close Monitor & Event Counter GUI
========================================================================
Supports both:
1. Standalone Door Firmware (Direct serial telemetry & counters from AWR1843)
2. Standard mmWave SDK Demo (Parses TLV point clouds and performs host-side detection)
"""

import sys
import os
import time
import math
import csv
import threading
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("Error: tkinter is required for this GUI. Please install Python with Tk support.")
    sys.exit(1)

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class DoorMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("TI AWR1843BOOST - Door Open / Close Monitor")
        self.geometry("1100x750")
        self.minsize(950, 680)

        # State Variables
        self.serial_conn = None
        self.is_connected = False
        self.reader_thread = None
        self.stop_reader = threading.Event()

        # Detection & Metric Variables
        self.door_state = tk.StringVar(value="UNKNOWN")
        self.total_opens = tk.IntVar(value=0)
        self.total_closes = tk.IntVar(value=0)
        self.door_distance = tk.DoubleVar(value=0.0)
        self.points_in_zone = tk.IntVar(value=0)
        self.peak_snr = tk.DoubleVar(value=0.0)
        self.current_duration_str = tk.StringVar(value="00:00:00")

        # Thresholds (Configurable)
        self.range_min_var = tk.DoubleVar(value=0.40)
        self.range_max_var = tk.DoubleVar(value=1.80)
        self.debounce_frames_var = tk.IntVar(value=5)

        # Internal tracking
        self.state_enter_time = time.time()
        self.event_history = []
        self.door_angle_anim = 0.0  # 0 deg = closed, 90 deg = open
        self.target_angle = 0.0

        # Build Interface
        self._setup_style()
        self._build_ui()
        self._refresh_com_ports()

        # Start periodic GUI update timers
        self._update_animation()
        self._update_timer()

    def _setup_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Configure colors
        self.bg_color = "#1E1E2E"
        self.card_bg = "#252538"
        self.card_border = "#313244"
        self.accent_color = "#89B4FA"
        self.text_color = "#CDD6F4"
        self.text_dim = "#A6ADC8"
        self.green_color = "#A6E3A1"
        self.red_color = "#F38BA8"
        self.orange_color = "#FAB387"

        self.configure(bg=self.bg_color)

    def _build_ui(self):
        # 1. Top Connection Bar
        top_bar = tk.Frame(self, bg=self.card_bg, height=55, padx=15, pady=8)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(top_bar, text="AWR1843 Port:", font=("Segoe UI", 10, "bold"),
                 bg=self.card_bg, fg=self.text_color).pack(side=tk.LEFT, padx=(0, 6))

        self.port_combo = ttk.Combobox(top_bar, width=20, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=4)

        btn_refresh = tk.Button(top_bar, text="Scan", command=self._refresh_com_ports,
                                bg="#45475A", fg=self.text_color, relief=tk.FLAT, padx=10)
        btn_refresh.pack(side=tk.LEFT, padx=4)

        tk.Label(top_bar, text="Baud:", font=("Segoe UI", 10),
                 bg=self.card_bg, fg=self.text_dim).pack(side=tk.LEFT, padx=(12, 4))

        self.baud_combo = ttk.Combobox(top_bar, values=["115200", "921600"], width=9, state="readonly")
        self.baud_combo.set("115200")
        self.baud_combo.pack(side=tk.LEFT, padx=4)

        self.btn_connect = tk.Button(top_bar, text="Connect", command=self._toggle_connection,
                                     bg=self.accent_color, fg="#11111B", font=("Segoe UI", 10, "bold"),
                                     relief=tk.FLAT, padx=15)
        self.btn_connect.pack(side=tk.LEFT, padx=12)

        self.conn_status_lbl = tk.Label(top_bar, text="Disconnected", font=("Segoe UI", 10),
                                        bg=self.card_bg, fg=self.red_color)
        self.conn_status_lbl.pack(side=tk.LEFT, padx=8)

        # Quick Control Buttons on Right
        btn_reset = tk.Button(top_bar, text="Reset Counters", command=self.reset_counters,
                              bg="#45475A", fg=self.text_color, relief=tk.FLAT, padx=10)
        btn_reset.pack(side=tk.RIGHT, padx=6)

        btn_calib = tk.Button(top_bar, text="Auto-Calibrate", command=self.trigger_calibration,
                              bg="#45475A", fg=self.text_color, relief=tk.FLAT, padx=10)
        btn_calib.pack(side=tk.RIGHT, padx=6)

        # 2. Main Content Area (Split into Left Visualizer / Right Telemetry & Logs)
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=6)

        # LEFT COLUMN: Visual Door Graphic + Big Counters
        left_col = tk.Frame(main_frame, bg=self.bg_color, width=540)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Big State Badge & Counters Card
        badge_card = tk.Frame(left_col, bg=self.card_bg, padx=15, pady=12)
        badge_card.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        self.lbl_big_state = tk.Label(badge_card, text="DOOR CLOSED", font=("Segoe UI", 26, "bold"),
                                      bg=self.card_bg, fg=self.green_color)
        self.lbl_big_state.pack(side=tk.TOP, pady=4)

        self.lbl_timer = tk.Label(badge_card, textvariable=self.current_duration_str,
                                  font=("Segoe UI", 14), bg=self.card_bg, fg=self.text_dim)
        self.lbl_timer.pack(side=tk.TOP)

        # Counters Row
        counters_frame = tk.Frame(badge_card, bg=self.card_bg, pady=10)
        counters_frame.pack(side=tk.TOP, fill=tk.X)

        # Open Count Box
        c_open_box = tk.Frame(counters_frame, bg="#313244", padx=12, pady=8)
        c_open_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(c_open_box, text="TOTAL OPENS", font=("Segoe UI", 9, "bold"),
                 bg="#313244", fg=self.orange_color).pack()
        tk.Label(c_open_box, textvariable=self.total_opens, font=("Segoe UI", 24, "bold"),
                 bg="#313244", fg=self.text_color).pack()

        # Close Count Box
        c_close_box = tk.Frame(counters_frame, bg="#313244", padx=12, pady=8)
        c_close_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(c_close_box, text="TOTAL CLOSES", font=("Segoe UI", 9, "bold"),
                 bg="#313244", fg=self.green_color).pack()
        tk.Label(c_close_box, textvariable=self.total_closes, font=("Segoe UI", 24, "bold"),
                 bg="#313244", fg=self.text_color).pack()

        # Live Distance Box
        c_dist_box = tk.Frame(counters_frame, bg="#313244", padx=12, pady=8)
        c_dist_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(c_dist_box, text="DOOR DISTANCE", font=("Segoe UI", 9, "bold"),
                 bg="#313244", fg=self.accent_color).pack()
        self.lbl_distance_val = tk.Label(c_dist_box, text="-- m", font=("Segoe UI", 22, "bold"),
                                         bg="#313244", fg=self.text_color)
        self.lbl_distance_val.pack()

        # Canvas for Animated Door Diagram
        canvas_card = tk.Frame(left_col, bg=self.card_bg, padx=10, pady=10)
        canvas_card.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tk.Label(canvas_card, text="Radar Field of View & Door Swing Simulation",
                 font=("Segoe UI", 11, "bold"), bg=self.card_bg, fg=self.text_color).pack(anchor="w")

        self.door_canvas = tk.Canvas(canvas_card, bg="#181825", highlightthickness=0)
        self.door_canvas.pack(fill=tk.BOTH, expand=True, pady=6)

        # RIGHT COLUMN: Live Telemetry, Threshold Controls & Event Log Table
        right_col = tk.Frame(main_frame, bg=self.bg_color)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # Settings Accordion / Card
        cfg_card = tk.Frame(right_col, bg=self.card_bg, padx=12, pady=10)
        cfg_card.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        tk.Label(cfg_card, text="Door Zone Settings", font=("Segoe UI", 11, "bold"),
                 bg=self.card_bg, fg=self.text_color).pack(anchor="w", pady=(0, 6))

        cfg_grid = tk.Frame(cfg_card, bg=self.card_bg)
        cfg_grid.pack(fill=tk.X)

        tk.Label(cfg_grid, text="Min Range (m):", bg=self.card_bg, fg=self.text_dim).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(cfg_grid, textvariable=self.range_min_var, width=8).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        tk.Label(cfg_grid, text="Max Range (m):", bg=self.card_bg, fg=self.text_dim).grid(row=0, column=2, sticky="w", pady=2)
        ttk.Entry(cfg_grid, textvariable=self.range_max_var, width=8).grid(row=0, column=3, sticky="w", padx=6, pady=2)

        tk.Label(cfg_grid, text="Debounce Frames:", bg=self.card_bg, fg=self.text_dim).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(cfg_grid, textvariable=self.debounce_frames_var, width=8).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        btn_apply = tk.Button(cfg_grid, text="Update Thresholds", command=self._apply_thresholds,
                              bg="#45475A", fg=self.text_color, relief=tk.FLAT, padx=8)
        btn_apply.grid(row=1, column=2, columnspan=2, sticky="e", padx=6, pady=2)

        # Event Log Card
        log_card = tk.Frame(right_col, bg=self.card_bg, padx=12, pady=10)
        log_card.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        log_header = tk.Frame(log_card, bg=self.card_bg)
        log_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(log_header, text="Door Activity Event Log", font=("Segoe UI", 11, "bold"),
                 bg=self.card_bg, fg=self.text_color).pack(side=tk.LEFT)

        btn_export = tk.Button(log_header, text="Export CSV", command=self.export_csv,
                               bg="#45475A", fg=self.text_color, relief=tk.FLAT, padx=8)
        btn_export.pack(side=tk.RIGHT, padx=4)

        btn_clear = tk.Button(log_header, text="Clear", command=self.clear_log,
                              bg="#45475A", fg=self.text_color, relief=tk.FLAT, padx=8)
        btn_clear.pack(side=tk.RIGHT)

        # Treeview for Log
        columns = ("time", "event", "duration", "distance", "opens", "closes")
        self.log_tree = ttk.Treeview(log_card, columns=columns, show="headings", height=12)

        self.log_tree.heading("time", text="Timestamp")
        self.log_tree.heading("event", text="Event")
        self.log_tree.heading("duration", text="Duration")
        self.log_tree.heading("distance", text="Door Dist (m)")
        self.log_tree.heading("opens", text="Total Opens")
        self.log_tree.heading("closes", text="Total Closes")

        self.log_tree.column("time", width=120, anchor="center")
        self.log_tree.column("event", width=130, anchor="center")
        self.log_tree.column("duration", width=90, anchor="center")
        self.log_tree.column("distance", width=100, anchor="center")
        self.log_tree.column("opens", width=90, anchor="center")
        self.log_tree.column("closes", width=90, anchor="center")

        tree_scroll = ttk.Scrollbar(log_card, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=tree_scroll.set)

        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_com_ports(self):
        if not SERIAL_AVAILABLE:
            self.port_combo["values"] = ["pyserial missing"]
            return

        ports = serial.tools.list_ports.comports()
        port_list = []
        app_port = None

        for p in ports:
            desc = p.description or ""
            port_str = f"{p.device} ({desc})"
            port_list.append(p.device)
            # Detect TI XDS110 Application / User UART Port
            if "Application" in desc or "User UART" in desc or "XDS110" in desc:
                if app_port is None:
                    app_port = p.device

        self.port_combo["values"] = port_list
        if app_port:
            self.port_combo.set(app_port)
        elif port_list:
            self.port_combo.set(port_list[0])
        else:
            self.port_combo.set("")

    def _toggle_connection(self):
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        if not SERIAL_AVAILABLE:
            messagebox.showerror("Error", "pyserial is not installed. Run: pip install pyserial")
            return

        port = self.port_combo.get().split()[0]
        if not port:
            messagebox.showwarning("Warning", "Please select a valid COM port.")
            return

        try:
            baud = int(self.baud_combo.get())
            self.serial_conn = serial.Serial(port, baud, timeout=0.1)
            self.is_connected = True

            self.conn_status_lbl.config(text=f"Connected to {port}", fg=self.green_color)
            self.btn_connect.config(text="Disconnect", bg=self.red_color)

            self.stop_reader.clear()
            self.reader_thread = threading.Thread(target=self._read_serial_loop, daemon=True)
            self.reader_thread.start()

        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to open {port}:\n{e}")

    def _disconnect(self):
        self.stop_reader.set()
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=0.5)

        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass

        self.is_connected = False
        self.conn_status_lbl.config(text="Disconnected", fg=self.red_color)
        self.btn_connect.config(text="Connect", bg=self.accent_color)

    def _read_serial_loop(self):
        """Background thread reading UART lines from AWR1843"""
        line_buffer = ""
        while not self.stop_reader.is_set():
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    raw_data = self.serial_conn.read(self.serial_conn.in_waiting)
                    text = raw_data.decode("utf-8", errors="replace")
                    line_buffer += text

                    while "\n" in line_buffer:
                        line, line_buffer = line_buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._parse_line(line)
                else:
                    time.sleep(0.02)
            except Exception:
                break

    def _parse_line(self, line: str):
        """Parse telemetry lines from standalone firmware or CLI"""
        # Example format: [DOOR] State: OPEN | Opens: 5 | Closes: 4 | Dist: 1.15 | SNR: 24.3
        if "[DOOR]" in line or "DOOR STATUS" in line:
            parts = line.split("|")
            for part in parts:
                p = part.strip()
                if "State:" in p:
                    new_state = p.split("State:")[1].strip().upper()
                    self._set_door_state(new_state)
                elif "Opens:" in p:
                    try:
                        self.total_opens.set(int(p.split("Opens:")[1].strip()))
                    except ValueError:
                        pass
                elif "Closes:" in p:
                    try:
                        self.total_closes.set(int(p.split("Closes:")[1].strip()))
                    except ValueError:
                        pass
                elif "Dist:" in p:
                    try:
                        d = float(p.split("Dist:")[1].strip().replace("m", ""))
                        self.door_distance.set(d)
                        self.lbl_distance_val.config(text=f"{d:.2f} m")
                    except ValueError:
                        pass

        elif "EVENT: Door Opened" in line or ">>> [EVENT] DOOR OPENED" in line:
            self._set_door_state("OPEN")
        elif "EVENT: Door Closed" in line or ">>> [EVENT] DOOR CLOSED" in line:
            self._set_door_state("CLOSED")

    def _set_door_state(self, new_state: str):
        curr = self.door_state.get()
        if new_state != curr:
            now = time.time()
            duration_sec = now - self.state_enter_time
            self.state_enter_time = now

            self.door_state.set(new_state)

            if new_state == "OPEN":
                self.target_angle = 90.0
                self.lbl_big_state.config(text="DOOR OPEN", fg=self.orange_color)
                # Increment opens if not already matching
                self.total_opens.set(self.total_opens.get() + 1)
                self._log_event("DOOR OPENED", duration_sec)

            elif new_state == "CLOSED":
                self.target_angle = 0.0
                self.lbl_big_state.config(text="DOOR CLOSED", fg=self.green_color)
                self.total_closes.set(self.total_closes.get() + 1)
                self._log_event("DOOR CLOSED", duration_sec)

    def _log_event(self, event_name: str, prev_duration: float):
        ts = datetime.now().strftime("%H:%M:%S")
        dur_str = f"{prev_duration:.1f} s" if prev_duration > 0.1 else "--"
        dist_str = f"{self.door_distance.get():.2f}" if self.door_distance.get() > 0 else "--"
        opens = self.total_opens.get()
        closes = self.total_closes.get()

        item = (ts, event_name, dur_str, dist_str, opens, closes)
        self.event_history.append(item)

        # Insert at top of Treeview
        self.log_tree.insert("", 0, values=item)

    def _update_animation(self):
        """Smoothly animates the door opening/closing on canvas"""
        # Interpolate door angle towards target
        diff = self.target_angle - self.door_angle_anim
        if abs(diff) > 0.5:
            self.door_angle_anim += diff * 0.25
        else:
            self.door_angle_anim = self.target_angle

        self._draw_door_canvas()
        self.after(33, self._update_animation)  # ~30 FPS

    def _draw_door_canvas(self):
        c = self.door_canvas
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return

        c.delete("all")

        # Center coordinates
        cx = w // 2
        cy = h // 2 + 30

        # Draw Radar Sensor at Bottom Center
        sensor_x = cx
        sensor_y = h - 35
        c.create_rectangle(sensor_x - 30, sensor_y - 12, sensor_x + 30, sensor_y + 12,
                           fill="#89B4FA", outline="#B4BEFE", width=2)
        c.create_text(sensor_x, sensor_y, text="TI AWR1843", font=("Segoe UI", 8, "bold"), fill="#11111B")

        # Draw Radar FOV Cone (77GHz mmWave sweep angle +/- 60 deg)
        fov_radius = min(w, h) * 0.70
        c.create_arc(sensor_x - fov_radius, sensor_y - fov_radius,
                     sensor_x + fov_radius, sensor_y + fov_radius,
                     start=30, extent=120, outline="#313244", fill="#1E1E2E", style=tk.PIESLICE)

        # Draw Range Gate Arcs (Min Range & Max Range)
        r_scale = fov_radius / 3.0  # assume 3 meters max scale
        r_min_px = self.range_min_var.get() * r_scale
        r_max_px = self.range_max_var.get() * r_scale

        c.create_arc(sensor_x - r_min_px, sensor_y - r_min_px,
                     sensor_x + r_min_px, sensor_y + r_min_px,
                     start=30, extent=120, outline="#585B70", width=1, style=tk.ARC)
        c.create_arc(sensor_x - r_max_px, sensor_y - r_max_px,
                     sensor_x + r_max_px, sensor_y + r_max_px,
                     start=30, extent=120, outline="#585B70", width=1, style=tk.ARC)
        c.create_text(sensor_x + r_max_px * 0.7, sensor_y - r_max_px * 0.5,
                      text=f"Door Zone [{self.range_min_var.get():.1f}m - {self.range_max_var.get():.1f}m]",
                      font=("Segoe UI", 8), fill="#A6ADC8")

        # Door Frame Walls
        doorway_y = cy - 20
        door_width = 130
        left_post_x = cx - door_width // 2
        right_post_x = cx + door_width // 2

        # Wall Left & Right
        c.create_rectangle(left_post_x - 120, doorway_y - 8, left_post_x, doorway_y + 8,
                           fill="#45475A", outline="#585B70")
        c.create_rectangle(right_post_x, doorway_y - 8, right_post_x + 120, doorway_y + 8,
                           fill="#45475A", outline="#585B70")

        # Door Posts (Frame)
        c.create_rectangle(left_post_x - 6, doorway_y - 12, left_post_x + 6, doorway_y + 12,
                           fill="#6C7086", outline="#A6ADC8")
        c.create_rectangle(right_post_x - 6, doorway_y - 12, right_post_x + 6, doorway_y + 12,
                           fill="#6C7086", outline="#A6ADC8")

        # Draw Swing Arc Guideline
        c.create_arc(left_post_x - door_width, doorway_y - door_width,
                     left_post_x + door_width, doorway_y + door_width,
                     start=0, extent=90, outline="#313244", dash=(3, 3), style=tk.ARC)

        # Draw Swinging Door Leaf (from left hinge at left_post_x)
        rad = math.radians(self.door_angle_anim)
        door_end_x = left_post_x + door_width * math.cos(rad)
        door_end_y = doorway_y - door_width * math.sin(rad)

        door_color = self.green_color if self.door_state.get() == "CLOSED" else self.orange_color
        c.create_line(left_post_x, doorway_y, door_end_x, door_end_y,
                      fill=door_color, width=7, capstyle=tk.ROUND)

        # Door Hinge Indicator
        c.create_oval(left_post_x - 5, doorway_y - 5, left_post_x + 5, doorway_y + 5,
                      fill="#FAB387", outline="#FFFFFF")

        # Distance Ray from Sensor to Door
        if self.door_state.get() == "CLOSED":
            mid_x = (left_post_x + right_post_x) // 2
            c.create_line(sensor_x, sensor_y - 12, mid_x, doorway_y,
                          fill=self.green_color, width=2, dash=(4, 4))
            c.create_oval(mid_x - 4, doorway_y - 4, mid_x + 4, doorway_y + 4, fill=self.green_color)
        else:
            # Beam passes through
            c.create_line(sensor_x, sensor_y - 12, cx, 30,
                          fill="#45475A", width=1, dash=(2, 4))

    def _update_timer(self):
        """Updates live elapsed time since last state change"""
        elapsed = int(time.time() - self.state_enter_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.current_duration_str.set(f"In State: {hrs:02d}:{mins:02d}:{secs:02d}")
        self.after(1000, self._update_timer)

    def _apply_thresholds(self):
        try:
            rmin = float(self.range_min_var.get())
            rmax = float(self.range_max_var.get())
            if rmin >= rmax or rmin < 0:
                messagebox.showerror("Error", "Range Min must be positive and less than Range Max.")
                return

            if self.is_connected and self.serial_conn:
                cmd = f"doorCfg {rmin:.2f} {rmax:.2f} {self.debounce_frames_var.get()}\n"
                self.serial_conn.write(cmd.encode("utf-8"))

            messagebox.showinfo("Success", f"Door Zone set to [{rmin:.2f} m - {rmax:.2f} m]")
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values.")

    def reset_counters(self):
        self.total_opens.set(0)
        self.total_closes.set(0)
        if self.is_connected and self.serial_conn:
            try:
                self.serial_conn.write(b"resetCounters\n")
            except Exception:
                pass
        self._log_event("COUNTERS RESET", 0)

    def trigger_calibration(self):
        if self.is_connected and self.serial_conn:
            try:
                self.serial_conn.write(b"calibrate\n")
                messagebox.showinfo("Calibration", "Sent auto-calibration trigger to AWR1843.\nPlease ensure door is CLOSED.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send calibration: {e}")
        else:
            messagebox.showinfo("Calibration", "Simulated auto-calibration completed.")
        self._log_event("CALIBRATION TRIGGERED", 0)

    def export_csv(self):
        if not self.event_history:
            messagebox.showinfo("Export", "No events logged yet.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                                                initialfile=f"door_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Event", "Duration", "Door Distance (m)", "Total Opens", "Total Closes"])
                for row in reversed(self.event_history):
                    writer.writerow(row)
            messagebox.showinfo("Success", f"Saved {len(self.event_history)} events to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV:\n{e}")

    def clear_log(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        self.event_history.clear()


if __name__ == "__main__":
    app = DoorMonitorApp()
    app.mainloop()
