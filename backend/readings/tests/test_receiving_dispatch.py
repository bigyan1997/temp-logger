from readings.models import DispatchReading, ReceivingCheck

from .base import ReadingTestCase


class ReceivingCheckTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)

    def test_chilled_delivery_in_range(self):
        response = self.receiving('4.2')
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['status'], 'near_limit')

    def test_warm_delivery_needs_a_corrective_action(self):
        self.assertEqual(self.receiving('13.0').status_code, 422)
        response = self.receiving('13.0', corrective={'action': 'rejected', 'notes': 'Sent back'})
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['status'], 'out_of_limit')

    def test_frozen_delivery_uses_the_frozen_limit(self):
        self.assertEqual(self.receiving('-18.0', product_type='frozen').status_code, 201)
        self.assertEqual(self.receiving('-10.0', date='2026-11-03', product_type='frozen').status_code, 422)

    def test_warm_baked_pies_can_be_moved_to_the_coolroom(self):
        response = self.receiving('7.5', product_type='baked_pie', corrective={'action': 'moved_to_coolroom'})
        self.assertEqual(response.status_code, 201, response.json())

    def test_damaged_packaging_needs_a_corrective_action_even_if_cold(self):
        self.assertEqual(self.receiving('3.0', packaging_ok=False).status_code, 422)
        self.assertEqual(
            self.receiving('3.0', packaging_ok=False, corrective={'action': 'rejected'}).status_code, 201
        )

    def test_no_delivery_is_recorded_without_a_temperature(self):
        response = self.receiving(no_delivery=True)
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(ReceivingCheck.objects.get().status, 'ok')

    def test_no_delivery_with_a_temperature_is_rejected(self):
        self.assertEqual(self.receiving('4.0', no_delivery=True).status_code, 400)

    def test_a_delivery_needs_a_temperature(self):
        self.assertEqual(self.receiving().status_code, 400)

    def test_one_entry_per_supplier_per_day(self):
        self.assertEqual(self.receiving('4.0').status_code, 201)
        self.assertEqual(self.receiving('3.0').status_code, 400)


class DispatchReadingTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)

    def test_in_range_and_near_limit(self):
        self.assertEqual(self.dispatch('3.5').json()['status'], 'ok')
        self.assertEqual(self.dispatch('4.9', run=self.run_a, date='2026-11-03').json()['status'], 'near_limit')

    def test_over_five_degrees_needs_a_corrective_action(self):
        self.assertEqual(self.dispatch('5.1').status_code, 422)
        response = self.dispatch('5.1', corrective={'action': 'contacted_operations_manager'})
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(DispatchReading.objects.get().status, 'out_of_limit')

    def test_one_reading_per_run_per_day(self):
        self.assertEqual(self.dispatch('4.0').status_code, 201)
        self.assertEqual(self.dispatch('4.2').status_code, 400)
