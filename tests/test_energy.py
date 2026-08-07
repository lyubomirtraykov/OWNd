"""Regression tests for energy message edge cases."""

import datetime
import unittest
from unittest.mock import patch

from OWNd.message import OWNEnergyCommand, OWNEnergyEvent


class FixedLeapDay(datetime.date):
    """Date double whose current day is 29 February 2024."""

    @classmethod
    def today(cls) -> FixedLeapDay:
        return cls(2024, 2, 29)


class EnergyEventTest(unittest.TestCase):
    """Malformed addresses remain safe to inspect."""

    def test_unsupported_where_is_fully_initialized(self) -> None:
        event = OWNEnergyEvent("*#18*123*113*50##")

        self.assertIsNone(event.message_type)
        self.assertEqual(event.active_power, 0)
        self.assertEqual(event.total_consumption, 0)
        self.assertEqual(event.hourly_consumption, {})
        self.assertEqual(event.daily_consumption, {})
        self.assertEqual(event.monthly_consumption, {})


class EnergyCommandTest(unittest.TestCase):
    """Date windows work on leap day too."""

    def test_hourly_consumption_on_leap_day(self) -> None:
        with patch("OWNd.message.datetime.date", FixedLeapDay):
            command = OWNEnergyCommand.get_hourly_consumption(
                "51", datetime.date(2023, 2, 28)
            )
            too_old = OWNEnergyCommand.get_hourly_consumption(
                "51", datetime.date(2023, 2, 27)
            )

        self.assertIsNotNone(command)
        self.assertEqual(str(command), "*#18*51*511#2#28##")
        self.assertIsNone(too_old)


if __name__ == "__main__":
    unittest.main()
