"""Regression tests for heating frames and commands."""

import unittest

import OWNd
from OWNd.connection import OWNGateway
from OWNd.message import (
    LOCAL_CONTROL_NORMAL,
    LOCAL_CONTROL_OFF,
    LOCAL_CONTROL_OFFSET,
    LOCAL_CONTROL_OVERRIDE,
    LOCAL_CONTROL_PROTECTION,
    LOCAL_CONTROL_UNKNOWN,
    MESSAGE_TYPE_ACTION,
    MESSAGE_TYPE_LOCAL_OFFSET,
    MESSAGE_TYPE_LOCAL_TARGET_TEMPERATURE,
    MESSAGE_TYPE_TARGET_TEMPERATURE,
    OWNHeatingCommand,
    OWNHeatingEvent,
)


class HeatingEventTest(unittest.TestCase):
    def test_target_temperatures_remain_distinct(self):
        local = OWNHeatingEvent("*#4*3*12*0350*3##")
        central = OWNHeatingEvent("*#4*3*14*0250*3##")

        self.assertEqual(local.message_type, MESSAGE_TYPE_LOCAL_TARGET_TEMPERATURE)
        self.assertEqual(local.local_set_temperature, 35.0)
        self.assertEqual(central.message_type, MESSAGE_TYPE_TARGET_TEMPERATURE)
        self.assertEqual(central.set_temperature, 25.0)

    def test_numeric_local_offsets(self):
        cases = {
            "00": (0, LOCAL_CONTROL_NORMAL),
            "01": (1, LOCAL_CONTROL_OFFSET),
            "03": (3, LOCAL_CONTROL_OFFSET),
            "11": (-1, LOCAL_CONTROL_OFFSET),
            "13": (-3, LOCAL_CONTROL_OFFSET),
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                event = OWNHeatingEvent(f"*#4*3*13*{raw}##")
                self.assertEqual(event.message_type, MESSAGE_TYPE_LOCAL_OFFSET)
                self.assertEqual(
                    (event.local_offset, event.local_control_state), expected
                )
                self.assertEqual(event.local_offset_raw, raw)

    def test_special_local_control_states_are_not_offsets(self):
        cases = {
            "4": LOCAL_CONTROL_OFF,
            "5": LOCAL_CONTROL_PROTECTION,
            "6": LOCAL_CONTROL_OVERRIDE,
            "7": LOCAL_CONTROL_UNKNOWN,
            "8": LOCAL_CONTROL_UNKNOWN,
        }
        for raw, state in cases.items():
            with self.subTest(raw=raw):
                event = OWNHeatingEvent(f"*#4*3*13*{raw}##")
                self.assertIsNone(event.local_offset)
                self.assertEqual(event.local_control_state, state)
                self.assertEqual(event.local_offset_raw, raw)

    def test_valve_reply_and_request(self):
        event = OWNHeatingEvent("*#4*3*19*0*0##")
        command = OWNHeatingCommand.valves_status("3")

        self.assertEqual(event.message_type, MESSAGE_TYPE_ACTION)
        self.assertFalse(event.is_active())
        self.assertEqual(str(command), "*#4*3*19##")


class CompatibilityTest(unittest.TestCase):
    def test_legacy_manufacturer_list_is_normalized(self):
        gateway = OWNGateway(
            {
                "address": "192.0.2.1",
                "manufacturer": ["BTicino S.p.A."],
                "modelName": "Test",
            }
        )

        self.assertEqual(gateway.manufacturer, "BTicino S.p.A.")

    def test_runtime_version_matches_package(self):
        self.assertEqual(OWNd.__version__, "1.0.11")


if __name__ == "__main__":
    unittest.main()
