from accounts.models import User
from audit.models import AuditLog
from readings.models import ReceivingCheck
from setup.models import StaffMember, Supplier

from .base import ReadingTestCase


class DeleteListItemsTests(ReadingTestCase):
    """An admin can delete a Settings item that nothing uses; one with records must be deactivated."""

    def setUp(self):
        super().setUp()
        self.sign_in(self.night)
        self.receiving('4.0')  # Posh Foods has a check, taken by Sam, saved by the night login
        self.sign_in(self.admin)

    def test_an_item_with_records_cannot_be_deleted(self):
        for url in (
            f'/api/suppliers/{self.supplier.pk}/',
            f'/api/staff/{self.sam.pk}/',
            f'/api/users/{self.night.pk}/',
        ):
            response = self.client.delete(url)
            self.assertEqual(response.status_code, 409, url)
            self.assertEqual(response.json()['code'], 'in_use')
            self.assertIn('Deactivate it instead', response.json()['message'])
        self.assertTrue(Supplier.objects.filter(pk=self.supplier.pk).exists())
        self.assertTrue(StaffMember.objects.filter(pk=self.sam.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.night.pk).exists())

    def test_the_message_names_the_item(self):
        message = self.client.delete(f'/api/suppliers/{self.supplier.pk}/').json()['message']
        self.assertIn('Posh Foods', message)

    def test_an_unused_staff_name_and_login_can_be_deleted(self):
        spare = StaffMember.objects.create(name='Spare')
        extra = User.objects.create_user('x@x.com', email='x@x.com', password='pw-12345-xyz', role='night')
        self.assertEqual(self.client.delete(f'/api/staff/{spare.pk}/').status_code, 204)
        self.assertEqual(self.client.delete(f'/api/users/{extra.pk}/').status_code, 204)
        self.assertFalse(StaffMember.objects.filter(name='Spare').exists())
        self.assertFalse(User.objects.filter(email='x@x.com').exists())
        self.assertEqual(AuditLog.objects.filter(action='deleted').count(), 2)

    def test_you_cannot_delete_your_own_login(self):
        response = self.client.delete(f'/api/users/{self.admin.pk}/')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_records_themselves_still_cannot_be_deleted(self):
        check = ReceivingCheck.objects.get()
        self.assertEqual(self.client.delete(f'/api/receiving-checks/{check.pk}/').status_code, 405)
        self.assertEqual(self.client.delete('/api/audit-log/').status_code, 405)
