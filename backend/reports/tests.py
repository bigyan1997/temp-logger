from datetime import date

from django.test import SimpleTestCase

from readings.tests.base import MONDAY_9AM, MONDAY_9PM, ReadingTestCase

from .grids import clock_label, corrective_rows, dispatch_grid, receiving_grid, storage_sheets, week_sundays

SUNDAY = date(2026, 11, 1)
START, END = date(2026, 11, 2), date(2026, 11, 6)  # the Monday to Friday after that Sunday
FIX = {'action': 'discarded'}


class WeekTests(SimpleTestCase):
    def test_a_weekday_range_belongs_to_the_week_that_started_on_the_sunday_before(self):
        self.assertEqual(week_sundays(START, END), [SUNDAY])

    def test_ranges_covering_several_weeks(self):
        sundays = week_sundays(date(2026, 11, 2), date(2026, 11, 17))
        self.assertEqual(sundays, [date(2026, 11, 1), date(2026, 11, 8), date(2026, 11, 15)])

    def test_a_week_that_ended_before_the_range_is_skipped(self):
        # Saturday 7 November: the week of Sunday 1 November is already over.
        self.assertEqual(week_sundays(date(2026, 11, 7), date(2026, 11, 10)), [date(2026, 11, 8)])

    def test_times_are_written_like_the_paper_sheet(self):
        from datetime import time
        self.assertEqual([clock_label(time(9)), clock_label(time(15)), clock_label(time(21))], ['9.00 AM', '3.00 PM', '9.00 PM'])


class StorageSheetTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)

    def test_layout_matches_the_paper_table(self):
        sheet = storage_sheets(START, END)[0]
        self.assertEqual(sheet['units'], ['Coolroom', 'Old Coolroom', 'Freezer', 'Chest Freezer'])
        self.assertEqual(sheet['weeks'], [SUNDAY, None, None, None])

        labels = [row['label'] for row in sheet['rows']]
        self.assertEqual(labels[:5], ['Sunday / Date:', '9.00 PM', 'Monday / Date:', '9.00 AM', '9.00 PM'])
        self.assertEqual(labels[-3:], ['Friday / Date:', '9.00 AM', '3.00 PM'])
        self.assertEqual(len(labels), 17)

        sunday_dates = sheet['rows'][0]['dates']
        self.assertEqual(sunday_dates, [SUNDAY, None, None, None])
        self.assertEqual(sheet['rows'][2]['dates'][0], date(2026, 11, 2))  # Monday

    def test_readings_land_in_the_right_cell_and_out_of_limit_is_starred(self):
        self.storage(self.coolroom, '2.4', slot=MONDAY_9AM)
        self.storage(self.freezer, '-12.0', slot=MONDAY_9AM, corrective=FIX)
        self.storage(self.coolroom, '3.1', slot=MONDAY_9PM)

        rows = storage_sheets(START, END)[0]['rows']
        monday_morning, monday_night = rows[3], rows[4]
        self.assertEqual(monday_morning['cells'][0], ['2.4', '', '-12.0*', ''])
        self.assertEqual(monday_morning['cells'][1], ['', '', '', ''])  # no second week
        self.assertEqual(monday_night['cells'][0][0], '3.1')

    def test_voided_readings_are_left_out(self):
        reading = self.storage(self.coolroom, '2.4', slot=MONDAY_9AM).json()
        self.sign_in(self.admin)
        self.client.post(f"/api/storage-readings/{reading['id']}/void/", {'reason': 'typo'}, format='json')
        self.assertEqual(storage_sheets(START, END)[0]['rows'][3]['cells'][0][0], '')

    def test_more_than_four_weeks_continue_on_a_second_sheet(self):
        sheets = storage_sheets(date(2026, 11, 1), date(2026, 12, 6))
        self.assertEqual(len(sheets), 2)
        self.assertEqual(sheets[1]['weeks'], [date(2026, 11, 29), date(2026, 12, 6), None, None])

    def test_a_deactivated_unit_with_readings_keeps_its_column(self):
        self.storage(self.coolroom, '2.4', slot=MONDAY_9AM)
        self.coolroom.active = False
        self.coolroom.save()
        self.assertIn('Coolroom', storage_sheets(START, END)[0]['units'])

        other = storage_sheets(date(2026, 12, 7), date(2026, 12, 11))[0]['units']
        self.assertNotIn('Coolroom', other)


class WeeklyGridTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)

    def test_receiving_has_a_sunday_night_row_then_monday_to_friday(self):
        grid = receiving_grid(START, END)
        days = ['Sunday night', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.assertEqual([r['day'] for r in grid['rows']], days)
        self.assertEqual(grid['rows'][0]['date'], SUNDAY)
        self.assertEqual(grid['rows'][1]['date'], date(2026, 11, 2))
        self.assertIn('Posh Foods', grid['columns'])

    def test_dispatch_calls_the_first_row_sunday(self):
        self.assertEqual(dispatch_grid(START, END)['rows'][0]['day'], 'Sunday')

    def test_receiving_marks_no_delivery_packaging_and_out_of_limit(self):
        self.receiving('4.0')
        self.post('/api/receiving-checks/', supplier=self.supplier.pk, date='2026-11-03', no_delivery=True)
        self.post(
            '/api/receiving-checks/', supplier=self.supplier.pk, date='2026-11-04', temp='3.0',
            packaging_ok=False, corrective={'action': 'rejected'},
        )
        self.post(
            '/api/receiving-checks/', supplier=self.supplier.pk, date='2026-11-05', temp='13.0',
            corrective={'action': 'rejected'},
        )
        grid = receiving_grid(START, END)
        column = grid['columns'].index('Posh Foods')
        self.assertEqual([row['cells'][column] for row in grid['rows']], ['', '4.0', '-', '3.0 (pkg)*', '13.0*', ''])

    def test_sunday_night_entries_have_their_own_row(self):
        self.receiving('4.5', date='2026-11-01')
        self.receiving('4.0', date='2026-11-02')
        grid = receiving_grid(START, END)
        column = grid['columns'].index('Posh Foods')
        self.assertEqual([grid['rows'][0]['cells'][column], grid['rows'][1]['cells'][column]], ['4.5', '4.0'])

    def test_a_saturday_row_appears_only_when_something_was_logged(self):
        self.assertEqual(len(receiving_grid(START, END)['rows']), 6)
        self.receiving('4.0', date='2026-11-07')
        rows = receiving_grid(START, END)['rows']
        self.assertEqual(rows[-1]['day'], 'Saturday')

    def test_dispatch_columns_have_no_run_f_or_i(self):
        self.dispatch('5.1', corrective={'action': 'rechecked'})
        grid = dispatch_grid(START, END)
        self.assertEqual(grid['columns'], [f'Run {c}' for c in 'ABCDEGHJKLM'])
        self.assertEqual(grid['rows'][1]['cells'][0], '5.1*')  # the Monday row

    def test_corrective_actions_say_who_logged_them_and_on_which_login(self):
        self.dispatch('5.1', corrective={'action': 'rechecked'})  # entered by the night login, as Sam
        rows = corrective_rows(START, END, 'dispatch')
        self.assertEqual(rows['headers'][3], 'Logged by')
        self.assertEqual(rows['rows'][0][3], 'Sam (night)')
        self.assertEqual(rows['rows'][0][4], 'Not signed off')

    def test_weeks_are_marked_so_the_pdf_can_draw_a_heavier_line(self):
        rows = dispatch_grid(date(2026, 11, 2), date(2026, 11, 10))['rows']
        self.assertEqual([r['new_week'] for r in rows], [True, False, False, False, False, False] * 2)


class ReportApiTests(ReadingTestCase):
    def test_admin_gets_a_pdf_for_each_table(self):
        self.sign_in(self.night)
        self.storage(self.coolroom, '2.4', slot=MONDAY_9AM)
        self.storage(self.freezer, '-12.0', slot=MONDAY_9PM, corrective=FIX)
        self.receiving('4.0')
        self.dispatch('5.1', corrective={'action': 'rechecked'})

        self.sign_in(self.admin)
        for kind in ('storage', 'receiving', 'dispatch'):
            response = self.client.get(f'/api/reports/{kind}.pdf?from=2026-11-02&to=2026-11-08')
            self.assertEqual(response.status_code, 200, kind)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertTrue(response.content.startswith(b'%PDF'), kind)

    def test_the_longest_allowed_period_still_makes_a_pdf(self):
        self.sign_in(self.admin)
        for kind in ('storage', 'receiving', 'dispatch'):
            response = self.client.get(f'/api/reports/{kind}.pdf?from=2026-09-01&to=2026-11-01')
            self.assertEqual(response.status_code, 200, kind)

    def test_night_cannot_get_reports(self):
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/reports/storage.pdf').status_code, 403)

    def test_bad_requests_are_explained(self):
        self.sign_in(self.admin)
        self.assertEqual(self.client.get('/api/reports/storage.pdf?from=nope').status_code, 400)
        self.assertEqual(self.client.get('/api/reports/storage.pdf?from=2026-11-09&to=2026-11-02').status_code, 400)
        self.assertEqual(self.client.get('/api/reports/storage.pdf?from=2026-01-01&to=2026-11-02').status_code, 400)
        self.assertEqual(self.client.get('/api/reports/other.pdf').status_code, 404)


class TrendsApiTests(ReadingTestCase):
    def test_trend_points_for_a_unit(self):
        self.sign_in(self.night)
        self.storage(self.coolroom, '2.4', slot=MONDAY_9AM)
        self.storage(self.coolroom, '6.5', slot=MONDAY_9PM, corrective=FIX)
        self.storage(self.freezer, '-18.0', slot=MONDAY_9AM)

        self.sign_in(self.admin)
        data = self.client.get(f'/api/trends/?unit={self.coolroom.pk}&from=2026-11-02&to=2026-11-08').json()
        self.assertEqual(data['unit']['name'], 'Coolroom')
        self.assertEqual([p['value'] for p in data['points']], ['2.4', '6.5'])
        self.assertEqual(data['points'][1]['status'], 'out_of_limit')

    def test_unit_is_required_and_night_is_refused(self):
        self.sign_in(self.admin)
        self.assertEqual(self.client.get('/api/trends/').status_code, 400)
        self.sign_in(self.night)
        self.assertEqual(self.client.get(f'/api/trends/?unit={self.coolroom.pk}').status_code, 403)
