"""
Unit tests for configuration loading, chirp profile validation, and settings schema
"""

import unittest
import sys
import os
import json

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))


class TestConfigValidation(unittest.TestCase):
    def test_default_settings_json_valid(self):
        settings_path = os.path.join(CONFIG_DIR, "default_settings.json")
        self.assertTrue(os.path.exists(settings_path), "default_settings.json must exist")

        with open(settings_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # Check required fields
        self.assertIn("detection", cfg)
        self.assertIn("door_range_min_m", cfg["detection"])
        self.assertIn("door_range_max_m", cfg["detection"])
        self.assertIn("debounce_open_frames", cfg["detection"])
        self.assertIn("debounce_close_frames", cfg["detection"])

        # Range bounds
        self.assertGreater(cfg["detection"]["door_range_max_m"], cfg["detection"]["door_range_min_m"])
        self.assertGreaterEqual(cfg["detection"]["debounce_open_frames"], 1)

    def test_chirp_profile_syntax(self):
        profile_path = os.path.join(CONFIG_DIR, "door_sensor_profile.cfg")
        self.assertTrue(os.path.exists(profile_path), "door_sensor_profile.cfg must exist")

        with open(profile_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("%")]

        # Ensure essential mmWave commands are present
        cmd_names = [l.split()[0] for l in lines]
        self.assertIn("dfeDataOutputMode", cmd_names)
        self.assertIn("channelCfg", cmd_names)
        self.assertIn("profileCfg", cmd_names)
        self.assertIn("chirpCfg", cmd_names)
        self.assertIn("frameCfg", cmd_names)
        self.assertIn("cfarCfg", cmd_names)
        self.assertIn("sensorStart", cmd_names)


if __name__ == "__main__":
    unittest.main()
