from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from readings import rules
from readings.choices import Status
from readings.schedule import is_storage_slot

D = Decimal
SYDNEY = ZoneInfo('Australia/Sydney')


class StatusTests(SimpleTestCase):
    def test_chilled(self):
        limit = rules.CHILLED_MAX
        self.assertEqual(rules.status_for(D('2.0'), limit), Status.OK)
        self.assertEqual(rules.status_for(D('4.0'), limit), Status.OK)
        self.assertEqual(rules.status_for(D('4.1'), limit), Status.NEAR_LIMIT)
        self.assertEqual(rules.status_for(D('5.0'), limit), Status.NEAR_LIMIT)
        self.assertEqual(rules.status_for(D('5.1'), limit), Status.OUT_OF_LIMIT)

    def test_frozen(self):
        limit = rules.FROZEN_MAX
        self.assertEqual(rules.status_for(D('-18.2'), limit), Status.OK)
        self.assertEqual(rules.status_for(D('-15.5'), limit), Status.NEAR_LIMIT)
        self.assertEqual(rules.status_for(D('-12.0'), limit), Status.OUT_OF_LIMIT)

    def test_limit_for_product(self):
        self.assertEqual(rules.limit_for_product('frozen'), D('-15.0'))
        self.assertEqual(rules.limit_for_product('chilled'), D('5.0'))
        self.assertEqual(rules.limit_for_product('baked_pie'), D('5.0'))


class UnusualReadingTests(SimpleTestCase):
    def test_positive_frozen_reading_suggests_missing_minus(self):
        reasons = rules.unusual_reasons(D('15.6'), rules.FROZEN_MAX)
        self.assertEqual(len(reasons), 1)
        self.assertIn('minus', reasons[0])

    def test_normal_frozen_reading_is_fine(self):
        self.assertEqual(rules.unusual_reasons(D('-17.0'), rules.FROZEN_MAX, previous=D('-18.0')), [])

    def test_very_cold_chilled_reading(self):
        self.assertEqual(len(rules.unusual_reasons(D('-8'), rules.CHILLED_MAX)), 1)

    def test_big_jump_from_last_reading(self):
        self.assertEqual(len(rules.unusual_reasons(D('14.0'), rules.CHILLED_MAX, previous=D('2.0'))), 1)
        self.assertEqual(rules.unusual_reasons(D('9.0'), rules.CHILLED_MAX, previous=D('2.0')), [])


class ScheduleTests(SimpleTestCase):
    def slot(self, day, hour, minute=0):
        return datetime(2026, 11, day, hour, minute, tzinfo=SYDNEY)

    def test_scheduled_times(self):
        self.assertTrue(is_storage_slot(self.slot(1, 21)))      # Sunday 9 PM
        self.assertTrue(is_storage_slot(self.slot(2, 9)))       # Monday 9 AM
        self.assertTrue(is_storage_slot(self.slot(6, 15)))      # Friday 3 PM

    def test_unscheduled_times(self):
        self.assertFalse(is_storage_slot(self.slot(1, 9)))      # Sunday has no morning reading
        self.assertFalse(is_storage_slot(self.slot(2, 10)))     # not on the hour that is scheduled
        self.assertFalse(is_storage_slot(self.slot(2, 9, 30)))
        self.assertFalse(is_storage_slot(self.slot(6, 21)))     # Friday has no 9 PM reading
        self.assertFalse(is_storage_slot(self.slot(7, 9)))      # Saturday
