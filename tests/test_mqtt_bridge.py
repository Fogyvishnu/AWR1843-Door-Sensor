"""
Unit tests for Home Assistant MQTT Auto-Discovery payloads and Bridge logic
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python_gui")))

from door_mqtt_bridge import DoorMqttBridge


class TestMqttBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = DoorMqttBridge(
            port="MOCK_COM",
            baud=115200,
            mqtt_host="127.0.0.1",
            mqtt_port=1883,
            mqtt_user=None,
            mqtt_pass=None
        )

    def test_bridge_state_parsing(self):
        line = "[DOOR] State: OPEN | Opens: 12 | Closes: 11 | Dist: 0.00m | Pts: 0 | SNR: 3.2dB"
        self.bridge.parse_line(line)

        self.assertEqual(self.bridge.door_state, "OPEN")
        self.assertEqual(self.bridge.total_opens, 12)
        self.assertEqual(self.bridge.total_closes, 11)
        self.assertEqual(self.bridge.points_in_roi, 0)

    def test_bridge_event_transition(self):
        line_open = ">>> [EVENT] DOOR OPEN! (Total Opens: 1 | Total Closes: 0) <<<"
        self.bridge.parse_line(line_open)
        self.assertEqual(self.bridge.door_state, "OPEN")
        self.assertEqual(self.bridge.total_opens, 1)

        line_close = ">>> [EVENT] DOOR CLOSED! (Total Opens: 1 | Total Closes: 1) <<<"
        self.bridge.parse_line(line_close)
        self.assertEqual(self.bridge.door_state, "CLOSED")
        self.assertEqual(self.bridge.total_closes, 1)


if __name__ == "__main__":
    unittest.main()
