from .base import ReadingTestCase

DAY = '2026-11-02'


class NightOnlySupplierTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.supplier.night_only = True
        self.supplier.save()

    def names(self, user):
        self.sign_in(user)
        return [s['name'] for s in self.client.get(f'/api/day/?date={DAY}').json()['receiving']]

    def test_the_night_login_sees_only_night_suppliers_and_the_day_login_sees_all(self):
        self.assertEqual(self.names(self.night), [self.supplier.name])
        self.assertGreater(len(self.names(self.admin)), 1)
        self.assertIn(self.supplier.name, self.names(self.admin))

    def test_a_delivery_logged_in_the_day_still_shows_at_night(self):
        other = self.supplier.__class__.objects.exclude(pk=self.supplier.pk).first()
        self.sign_in(self.admin)
        self.post('/api/receiving-checks/', supplier=other.pk, date=DAY, temp='3.0', product_type='chilled', packaging_ok=True)
        self.assertIn(other.name, self.names(self.night))

    def test_the_lists_page_shows_every_supplier_to_admin(self):
        self.sign_in(self.admin)
        names = [s['name'] for s in self.client.get('/api/suppliers/?all=1').json()]
        self.assertIn(self.supplier.name, names)
