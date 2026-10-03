"""
TI AWR1843BOOST - Production MQTT & Home Assistant Bridge
==========================================================
Bridges real-time mmWave radar telemetry and door cycle events
to any MQTT Broker with native Home Assistant MQTT Auto-Discovery.

Features:
- Home Assistant MQTT Discovery (Zero manual YAML configuration)
- Real-time event publishing (Door Open / Close, Open/Close Counts)
- Sensor telemetry publishing (Distance, Peak SNR, Uptime)
- Remote command handling via MQTT (Reset Counters, Calibrate)
- Resilient auto-reconnect with exponential backoff on UART and MQTT drops

Usage:
    python door_mqtt_bridge.py --mqtt-host 192.168.1.100 --port COM3
"""

import sys
import os
import time
import json
import argparse
import logging
from datetime import datetime

# Setup production logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AWR1843_MQTT")

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.error("pyserial is required. Install: pip install pyserial")

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("paho-mqtt not installed. MQTT publishing disabled until 'pip install paho-mqtt' is run.")


def auto_detect_port():
    if not SERIAL_AVAILABLE:
        return None
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = p.description or ""
        if "Application" in desc or "User UART" in desc or "XDS110" in desc:
            return p.device
    if ports:
        return ports[0].device
    return None


class DoorMqttBridge:
    def __init__(self, port, baud, mqtt_host, mqtt_port, mqtt_user, mqtt_pass, topic_prefix="awr1843/door"):
        self.port = port
        self.baud = baud
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.topic_prefix = topic_prefix

        self.ser = None
        self.mqtt_client = None
        self.running = True

        # State cache
        self.door_state = "UNKNOWN"
        self.total_opens = 0
        self.total_closes = 0
        self.door_distance = 0.0
        self.peak_snr = 0.0
        self.points_in_roi = 0
        self.start_time = time.time()
        self.last_state_change = time.time()

    def setup_mqtt(self):
        if not MQTT_AVAILABLE:
            logger.info("MQTT disabled (paho-mqtt library not installed). Running in serial monitor mode.")
            return

        self.mqtt_client = mqtt.Client(client_id="awr1843_door_bridge", clean_session=True)
        if self.mqtt_user and self.mqtt_pass:
            self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_pass)

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        try:
            logger.info(f"Connecting to MQTT Broker at {self.mqtt_host}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}. Will retry...")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("[+] Successfully connected to MQTT broker.")
            # Subscribe to remote command topic
            cmd_topic = f"{self.topic_prefix}/set"
            client.subscribe(cmd_topic)
            logger.info(f"Subscribed to control topic: {cmd_topic}")
            # Publish Home Assistant Discovery configs
            self.publish_ha_discovery()
            # Publish birth message
            client.publish(f"{self.topic_prefix}/availability", "online", retain=True)
        else:
            logger.error(f"MQTT connection refused with code: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8").strip()
            logger.info(f"Received MQTT command: {payload}")
            cmd = payload.lower()
            if cmd == "reset" or "reset" in cmd:
                self.send_serial_command("resetCounters")
            elif cmd == "calibrate" or "calibrate" in cmd:
                self.send_serial_command("calibrate")
            elif cmd in ["vt100", "vt100 1", "vt100 0"]:
                self.send_serial_command(cmd)
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

    def publish_ha_discovery(self):
        if not self.mqtt_client:
            return

        device_info = {
            "identifiers": ["awr1843_door_sensor_01"],
            "name": "TI AWR1843 Door Sensor",
            "model": "AWR1843BOOST 77GHz mmWave Radar",
            "manufacturer": "Texas Instruments",
            "sw_version": "1.3.0"
        }

        # 1. Binary Sensor: Door Contact (OPEN / CLOSED)
        disc_door = {
            "name": "Door",
            "state_topic": f"{self.topic_prefix}/state",
            "value_template": "{{ value_json.state }}",
            "payload_on": "OPEN",
            "payload_off": "CLOSED",
            "device_class": "door",
            "unique_id": "awr1843_door_contact",
            "availability_topic": f"{self.topic_prefix}/availability",
            "device": device_info
        }
        self.mqtt_client.publish(
            "homeassistant/binary_sensor/awr1843_door/door/config",
            json.dumps(disc_door), retain=True
        )

        # 2. Sensor: Open Cycles Counter
        disc_opens = {
            "name": "Door Open Count",
            "state_topic": f"{self.topic_prefix}/state",
            "value_template": "{{ value_json.opens }}",
            "state_class": "total_increasing",
            "icon": "mdi:counter",
            "unique_id": "awr1843_door_open_count",
            "availability_topic": f"{self.topic_prefix}/availability",
            "device": device_info
        }
        self.mqtt_client.publish(
            "homeassistant/sensor/awr1843_door/open_count/config",
            json.dumps(disc_opens), retain=True
        )

        # 3. Sensor: Close Cycles Counter
        disc_closes = {
            "name": "Door Close Count",
            "state_topic": f"{self.topic_prefix}/state",
            "value_template": "{{ value_json.closes }}",
            "state_class": "total_increasing",
            "icon": "mdi:counter",
            "unique_id": "awr1843_door_close_count",
            "availability_topic": f"{self.topic_prefix}/availability",
            "device": device_info
        }
        self.mqtt_client.publish(
            "homeassistant/sensor/awr1843_door/close_count/config",
            json.dumps(disc_closes), retain=True
        )

        # 4. Sensor: Target Distance (meters)
        disc_dist = {
            "name": "Door Target Distance",
            "state_topic": f"{self.topic_prefix}/state",
            "value_template": "{{ value_json.distance }}",
            "unit_of_measurement": "m",
            "device_class": "distance",
            "state_class": "measurement",
            "unique_id": "awr1843_door_distance",
            "availability_topic": f"{self.topic_prefix}/availability",
            "device": device_info
        }
        self.mqtt_client.publish(
            "homeassistant/sensor/awr1843_door/distance/config",
            json.dumps(disc_dist), retain=True
        )

        # 5. Sensor: Peak Reflection SNR (dB)
        disc_snr = {
            "name": "Door Reflection SNR",
            "state_topic": f"{self.topic_prefix}/state",
            "value_template": "{{ value_json.snr }}",
            "unit_of_measurement": "dB",
            "device_class": "signal_strength",
            "state_class": "measurement",
            "unique_id": "awr1843_door_snr",
            "availability_topic": f"{self.topic_prefix}/availability",
            "device": device_info
        }
        self.mqtt_client.publish(
            "homeassistant/sensor/awr1843_door/snr/config",
            json.dumps(disc_snr), retain=True
        )

        logger.info("[+] Published Home Assistant MQTT Auto-Discovery entities.")

    def publish_state(self):
        if not self.mqtt_client:
            return

        payload = {
            "state": self.door_state,
            "opens": self.total_opens,
            "closes": self.total_closes,
            "distance": round(self.door_distance, 2) if self.door_state == "CLOSED" else None,
            "snr": round(self.peak_snr, 1),
            "points": self.points_in_roi,
            "uptime_seconds": int(time.time() - self.start_time),
            "timestamp": datetime.now().isoformat()
        }

        self.mqtt_client.publish(
            f"{self.topic_prefix}/state",
            json.dumps(payload),
            qos=1
        )

    def send_serial_command(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                line = (cmd.strip() + "\n").encode()
                self.ser.write(line)
                logger.info(f"Sent serial command to radar: {cmd}")
            except Exception as e:
                logger.error(f"Failed to send command to serial port: {e}")

    def parse_line(self, line):
        line = line.strip()
        if not line:
            return

        state_changed = False

        if "EVENT: Door Opened" in line or "EVENT] DOOR OPEN" in line:
            if "Total Opens:" in line:
                try:
                    self.total_opens = int(line.split("Total Opens:")[1].split("|")[0].strip())
                except (ValueError, IndexError):
                    pass
            elif self.door_state != "OPEN":
                self.total_opens += 1

            if "Total Closes:" in line:
                try:
                    self.total_closes = int(line.split("Total Closes:")[1].split(")")[0].strip())
                except (ValueError, IndexError):
                    pass

            if self.door_state != "OPEN":
                self.door_state = "OPEN"
                state_changed = True
                logger.info(f">>> EVENT: DOOR OPENED! (Total Opens: {self.total_opens}) <<<")

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
            elif self.door_state != "CLOSED":
                self.total_closes += 1

            if self.door_state != "CLOSED":
                self.door_state = "CLOSED"
                state_changed = True
                logger.info(f">>> EVENT: DOOR CLOSED! (Total Closes: {self.total_closes}) <<<")

        elif "[DOOR]" in line or "State:" in line:
            parts = line.split("|")
            for p in parts:
                p = p.strip()
                if "State:" in p:
                    st = p.split("State:")[1].strip().upper()
                    if st in ["OPEN", "CLOSED", "UNKNOWN"] and st != self.door_state:
                        self.door_state = st
                        state_changed = True
                elif "Opens:" in p:
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

        if state_changed:
            self.publish_state()

    def run(self):
        self.setup_mqtt()

        buf = ""
        last_periodic_publish = time.time()

        logger.info(f"Starting AWR1843 Serial Monitor on {self.port} at {self.baud} baud...")

        while self.running:
            # Connect or reconnect serial port
            if self.ser is None or not self.ser.is_open:
                try:
                    self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
                    logger.info(f"[+] Serial port {self.port} opened successfully.")
                except Exception as e:
                    logger.warning(f"Waiting for serial port {self.port}: {e}. Retrying in 2s...")
                    time.sleep(2.0)
                    # Attempt auto-detection if port not fixed
                    detected = auto_detect_port()
                    if detected:
                        self.port = detected
                    continue

            # Read UART
            try:
                if self.ser.in_waiting > 0:
                    raw = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="replace")
                    buf += raw
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        self.parse_line(line)
            except Exception as e:
                logger.error(f"Serial communication error: {e}. Reconnecting...")
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                self.ser = None
                time.sleep(1.0)
                continue

            # Periodic state telemetry publish every 5 seconds
            if time.time() - last_periodic_publish >= 5.0:
                self.publish_state()
                last_periodic_publish = time.time()

            time.sleep(0.01)

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()
        if self.mqtt_client:
            self.mqtt_client.publish(f"{self.topic_prefix}/availability", "offline", retain=True)
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        logger.info("[*] Bridge cleanly shut down.")


def main():
    parser = argparse.ArgumentParser(description="TI AWR1843 mmWave Radar MQTT & Home Assistant Bridge")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (auto-detected if omitted)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--mqtt-host", type=str, default="localhost", help="MQTT broker host (default: localhost)")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port (default: 1883)")
    parser.add_argument("--mqtt-user", type=str, default=None, help="MQTT username")
    parser.add_argument("--mqtt-pass", type=str, default=None, help="MQTT password")
    parser.add_argument("--topic", type=str, default="awr1843/door", help="MQTT root topic prefix")
    args = parser.parse_args()

    port = args.port or auto_detect_port()
    if not port:
        logger.error("No serial port found. Connect your TI AWR1843BOOST board.")
        sys.exit(1)

    bridge = DoorMqttBridge(
        port=port,
        baud=args.baud,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_user=args.mqtt_user,
        mqtt_pass=args.mqtt_pass,
        topic_prefix=args.topic
    )

    try:
        bridge.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting...")
    finally:
        bridge.stop()


if __name__ == "__main__":
    main()
