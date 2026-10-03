"""
Unit tests for AWR1843 UART telemetry parsing and state tracking
"""

import unittest
import sys
import os

# Add python_gui to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python_gui")))

from door_vt100 import DoorVT100Monitor, make_gauge


class TestDoorParser(unittest.TestCase):
    def setUp(self):
        self.monitor = DoorVT100Monitor(port="MOCK_COM", baud=115200, csv_path=None, beep_on_open=False)

    def test_gauge_generator(self):
        # Empty gauge
        g0 = make_gauge(0.0, 2.5, length=10)
        self.assertEqual(g0, "[          ]")

        # Half-full gauge
        g_half = make_gauge(1.25, 2.5, length=10)
        self.assertTrue("=" in g_half)
        self.assertTrue(">" in g_half)

        # Full gauge
        g_full = make_gauge(3.0, 2.5, length=10)
        self.assertEqual(g_full, "[=========>]")

    def test_parse_telemetry_line(self):
        line = "[DOOR] State: CLOSED | Opens: 5 | Closes: 4 | Dist: 1.25m | Pts: 8 | SNR: 23.5dB"
        self.monitor.parse_line(line)

        self.assertEqual(self.monitor.door_state, "CLOSED")
        self.assertEqual(self.monitor.total_opens, 5)
        self.assertEqual(self.monitor.total_closes, 4)
        self.assertAlmostEqual(self.monitor.door_distance, 1.25, places=2)
        self.assertEqual(self.monitor.points_in_roi, 8)
        self.assertAlmostEqual(self.monitor.peak_snr, 23.5, places=1)

    def test_event_transition_recording(self):
        # Initial transition from UNKNOWN to CLOSED
        self.monitor.parse_line("[DOOR] State: CLOSED | Opens: 1 | Closes: 1 | Dist: 1.10m | Pts: 6 | SNR: 20.0dB")
        self.assertEqual(self.monitor.door_state, "CLOSED")
        self.assertEqual(len(self.monitor.history), 1)
        self.assertEqual(self.monitor.history[0]["event"], "DOOR CLOSED")

        # Instant open event
        self.monitor.parse_line(">>> [EVENT] DOOR OPEN! (Total Opens: 2 | Total Closes: 1) <<<")
        self.assertEqual(self.monitor.door_state, "OPEN")
        self.assertEqual(self.monitor.total_opens, 2)
        self.assertEqual(len(self.monitor.history), 2)
        self.assertEqual(self.monitor.history[0]["event"], "DOOR OPENED")

        # Instant close event
        self.monitor.parse_line(">>> [EVENT] DOOR CLOSED! (Total Opens: 2 | Total Closes: 2) <<<")
        self.assertEqual(self.monitor.door_state, "CLOSED")
        self.assertEqual(self.monitor.total_closes, 2)
        self.assertEqual(len(self.monitor.history), 3)
        self.assertEqual(self.monitor.history[0]["event"], "DOOR CLOSED")

    def test_malformed_telemetry_resilience(self):
        # Ensure garbage lines don't crash parser
        self.monitor.parse_line("")
        self.monitor.parse_line("   \r\n")
        self.monitor.parse_line("Malformed garbage data @#$%^&*()")
        self.monitor.parse_line("[DOOR] State: CORRUPT | Opens: NaN | Dist: ??m")
        # Monitor should survive without exceptions
        self.assertEqual(self.monitor.door_state, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
