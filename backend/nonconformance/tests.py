import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from alerts.management.commands.send_alerts import Command  # noqa: F401  (imported so a broken import shows here)
from audit.models import AuditLog
from readings.tests.base import ReadingTestCase

from . import drive, photos
from .models import NonConformance, Photo, Update

REPORT = {'date': '2026-11-02', 'product': 'Choc brownies 12pk / BR12', 'customer': 'Corner Cafe', 'manufacturer': 'Posh Foods',
          'description': 'Melted product in the carton.' + chr(10) + 'Customer sent a photo.'}


def picture(kind='PNG', name='photo.png'):
    out = BytesIO()
    Image.new('RGB', (40, 30), (200, 30, 30)).save(out, kind)
    return SimpleUploadedFile(name, out.getvalue(), content_type='image/png')


class PhotoFileTests(SimpleTestCase):
    def test_the_type_comes_from_the_file_not_its_name(self):
        self.assertEqual(photos.sniff(b'\xff\xd8\xff\xe0' + b'0' * 12)[0], 'jpg')
        self.assertEqual(photos.sniff(b'\x89PNG\r\n\x1a\n' + b'0' * 8)[0], 'png')
        self.assertEqual(photos.sniff(b'RIFF1234WEBPVP8 ')[0], 'webp')
        self.assertIsNone(photos.sniff(b'MZ\x90\x00 this is a program'))
        self.assertIsNone(photos.sniff(b'<html><script>'))

    def test_a_path_outside_the_photos_folder_is_refused(self):
        with override_settings(NCR_PHOTOS_DIR=tempfile.gettempdir()):
            with self.assertRaises(ValueError):
                photos.full_path('../secret.txt')


class NonConformanceTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        override = override_settings(NCR_PHOTOS_DIR=str(self.folder / 'photos'))
        override.enable()
        self.addCleanup(override.disable)
        self.sign_in(self.admin)

    def create(self, **changes):
        return self.post('/api/non-conformances/', **{**REPORT, **changes})

    def update(self, report_id, kind, text='', **extra):
        return self.post(f'/api/non-conformances/{report_id}/updates/', kind=kind, text=text, **extra)

    def upload(self, report_id, *files):
        return self.client.post(f'/api/non-conformances/{report_id}/add_photos/', {'files': list(files), 'recorded_by': self.sam.pk}, format='multipart')

    # Reports ------------------------------------------------------------------

    def test_a_report_gets_a_number_and_remembers_who_wrote_it(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['number'], 'NCR-0001')
        self.assertEqual(body['status'], 'open')
        self.assertEqual(body['recorded_by_name'], 'Sam')
        self.assertEqual(NonConformance.objects.get().entered_by, self.admin)
        self.assertEqual(self.create().json()['number'], 'NCR-0002')

    def test_the_night_login_cannot_use_it(self):
        self.sign_in(self.night)
        self.assertEqual(self.create().status_code, 403)
        self.assertEqual(self.client.get('/api/non-conformances/').status_code, 403)
        self.assertEqual(self.client.get('/api/non-conformances/summary/').status_code, 403)

    def test_a_product_and_a_description_are_needed_and_the_date_cannot_be_in_the_future(self):
        self.assertEqual(self.create(product='  ').status_code, 400)
        self.assertEqual(self.create(description='').status_code, 400)
        self.assertEqual(self.create(date='2999-01-01').status_code, 400)
        self.assertEqual(self.create(customer='', manufacturer='').status_code, 201)  # the others are optional
        self.assertEqual(self.post('/api/non-conformances/', **{**REPORT, 'recorded_by': None}).status_code, 400)

    def test_the_description_keeps_its_line_breaks(self):
        self.assertIn(chr(10), self.create().json()['description'])

    # Follow-ups ------------------------------------------------------------------

    def test_follow_ups_are_added_in_order_and_closing_closes_the_report(self):
        report_id = self.create().json()['id']
        self.assertEqual(self.update(report_id, 'notified', happened_at='2026-11-03T10:30:00+11:00').status_code, 201)
        self.assertEqual(self.update(report_id, 'response', 'Credit note issued.').status_code, 201)
        self.assertEqual(self.update(report_id, 'action', 'Check the coolroom door seal.').status_code, 201)
        self.assertEqual(self.client.get('/api/non-conformances/summary/').json()['open'], 1)
        self.assertEqual(self.update(report_id, 'closed').status_code, 201)
        body = self.client.get(f'/api/non-conformances/{report_id}/').json()
        self.assertEqual(body['status'], 'closed')
        self.assertEqual([u['kind'] for u in body['updates']], ['notified', 'response', 'action', 'closed'])
        self.assertEqual(self.client.get('/api/non-conformances/summary/').json()['open'], 0)

    def test_a_response_or_action_or_note_must_say_something(self):
        report_id = self.create().json()['id']
        for kind in ('response', 'action', 'note'):
            self.assertEqual(self.update(report_id, kind, '  ').status_code, 400)
        self.assertEqual(self.update(report_id, 'notified').status_code, 201)  # a date and a name are enough

    def test_a_closed_report_only_takes_notes_until_the_closing_is_voided(self):
        report_id = self.create().json()['id']
        closing = self.update(report_id, 'closed').json()
        self.assertEqual(self.update(report_id, 'action', 'More work').status_code, 400)
        self.assertEqual(self.update(report_id, 'note', 'Customer thanked us').status_code, 201)
        voided = self.client.post(f'/api/non-conformances/updates/{closing["id"]}/void/', {'reason': 'Closed too early'}, format='json')
        self.assertEqual(voided.status_code, 200)
        self.assertEqual(self.client.get(f'/api/non-conformances/{report_id}/').json()['status'], 'open')
        self.assertEqual(self.update(report_id, 'action', 'More work').status_code, 201)

    def test_a_follow_up_time_cannot_be_in_the_future(self):
        report_id = self.create().json()['id']
        self.assertEqual(self.update(report_id, 'notified', happened_at='2999-01-01T10:00:00+11:00').status_code, 400)

    # Voiding and the audit log ----------------------------------------------------

    def test_voiding_needs_a_reason_is_audited_in_its_own_log_and_keeps_the_report(self):
        report_id = self.create().json()['id']
        self.assertEqual(self.client.post(f'/api/non-conformances/{report_id}/void/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/non-conformances/{report_id}/void/', {'reason': 'Entered twice'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/non-conformances/{report_id}/void/', {'reason': 'Again'}, format='json').status_code, 400)
        self.assertTrue(AuditLog.objects.filter(module='nonconformance', reason='Entered twice').exists())
        self.assertEqual(self.client.get('/api/audit-log/').json()['count'], 0)  # not in the Temperature Logger's log
        self.assertEqual(self.client.get('/api/non-conformances/').json()['count'], 0)
        self.assertEqual(self.client.get('/api/non-conformances/?include_voided=1').json()['count'], 1)
        self.assertEqual(self.client.get(f'/api/non-conformances/{report_id}/').json()['status'], 'voided')
        self.assertEqual(self.update(report_id, 'note', 'x').status_code, 400)
        self.assertEqual(NonConformance.objects.count(), 1)  # nothing is deleted

    def test_there_is_no_way_to_edit_or_delete_a_report(self):
        report_id = self.create().json()['id']
        self.assertEqual(self.client.patch(f'/api/non-conformances/{report_id}/', {'product': 'x'}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(f'/api/non-conformances/{report_id}/').status_code, 405)

    # Searching ------------------------------------------------------------------------

    def test_the_list_can_be_filtered_by_status_text_and_date(self):
        first = self.create().json()['id']
        self.create(product='Meat pies', customer='The Deli', manufacturer='Yianni', date='2026-11-09')
        self.update(first, 'closed')
        count = lambda query: self.client.get(f'/api/non-conformances/?{query}').json()['count']
        self.assertEqual(count('status=open'), 1)
        self.assertEqual(count('status=closed'), 1)
        self.assertEqual(count('q=deli'), 1)
        self.assertEqual(count('q=brownies'), 1)
        self.assertEqual(count('from=2026-11-05'), 1)
        self.assertEqual(count(''), 2)

    # Photos -----------------------------------------------------------------------------

    def test_a_photo_is_kept_on_this_pc_and_only_a_signed_in_day_login_can_see_it(self):
        report_id = self.create().json()['id']
        response = self.upload(report_id, picture())
        self.assertEqual(response.status_code, 201)
        photo = Photo.objects.get()
        self.assertTrue((self.folder / 'photos' / photo.path).is_file())
        shown = self.client.get(response.json()[0]['url'])
        self.assertEqual(shown.status_code, 200)
        self.assertEqual(shown['Content-Type'], 'image/png')
        self.assertEqual(shown['X-Content-Type-Options'], 'nosniff')
        self.sign_in(self.night)
        self.assertEqual(self.client.get(response.json()[0]['url']).status_code, 403)
        self.client.logout()
        self.assertIn(self.client.get(response.json()[0]['url']).status_code, (401, 403))

    def test_only_real_pictures_are_accepted(self):
        report_id = self.create().json()['id']
        fake = SimpleUploadedFile('photo.jpg', b'<html><script>alert(1)</script>', content_type='image/jpeg')
        self.assertEqual(self.upload(report_id, fake).status_code, 400)
        self.assertEqual(Photo.objects.count(), 0)
        self.assertEqual(self.client.post(f'/api/non-conformances/{report_id}/add_photos/', {'recorded_by': self.sam.pk}, format='multipart').status_code, 400)

    def test_a_photo_that_is_too_big_or_too_many_photos_are_refused(self):
        report_id = self.create().json()['id']
        with mock.patch.object(photos, 'MAX_BYTES', 50):
            self.assertEqual(self.upload(report_id, picture()).status_code, 400)
        with mock.patch.object(photos, 'MAX_PER_REPORT', 2):
            self.assertEqual(self.upload(report_id, picture(), picture(), picture()).status_code, 400)
            self.assertEqual(self.upload(report_id, picture(), picture()).status_code, 201)
            self.assertEqual(self.upload(report_id, picture()).status_code, 400)

    def test_a_photo_can_be_voided_and_its_file_stays(self):
        report_id = self.create().json()['id']
        photo_id = self.upload(report_id, picture()).json()[0]['id']
        self.assertEqual(self.client.post(f'/api/non-conformances/photos/{photo_id}/void/', {'reason': 'Wrong product'}, format='json').status_code, 200)
        self.assertTrue((self.folder / 'photos' / Photo.objects.get().path).is_file())
        self.assertTrue(AuditLog.objects.filter(module='nonconformance', reason='Wrong product').exists())

    # PDFs ----------------------------------------------------------------------------------

    def test_the_report_and_the_register_make_pdfs_even_with_a_voided_follow_up_and_a_photo(self):
        report_id = self.create().json()['id']
        self.upload(report_id, picture())
        self.update(report_id, 'notified', happened_at='2026-11-03T10:30:00+11:00')
        wrong = self.update(report_id, 'response', 'Typed in the wrong report').json()
        self.client.post(f'/api/non-conformances/updates/{wrong["id"]}/void/', {'reason': 'Wrong report'}, format='json')
        one = self.client.get(f'/api/non-conformances/{report_id}/pdf/')
        self.assertEqual(one.status_code, 200)
        self.assertTrue(one.content.startswith(b'%PDF'))
        register = self.client.get('/api/non-conformances/register/?from=2026-11-01&to=2026-11-30')
        self.assertEqual(register.status_code, 200)
        self.assertTrue(register.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get('/api/non-conformances/register/?from=2026-11-30&to=2026-11-01').status_code, 400)

    def test_a_missing_photo_file_does_not_break_the_pdf(self):
        report_id = self.create().json()['id']
        self.upload(report_id, picture())
        (self.folder / 'photos' / Photo.objects.get().path).unlink()
        self.assertEqual(self.client.get(f'/api/non-conformances/{report_id}/pdf/').status_code, 200)


class DriveCopyTests(ReadingTestCase):
    """A second copy of each photo goes where the report PDFs go (Google Drive for desktop folder or the Drive API)."""

    def setUp(self):
        super().setUp()
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.drive_folder = self.base / 'Drive'
        self.drive_folder.mkdir()
        override = override_settings(NCR_PHOTOS_DIR=str(self.base / 'photos'), REPORTS_EXPORT_DIR=str(self.drive_folder))
        override.enable()
        self.addCleanup(override.disable)
        self.sign_in(self.admin)
        self.report_id = self.post('/api/non-conformances/', **REPORT).json()['id']

    def upload(self, *files):
        return self.client.post(f'/api/non-conformances/{self.report_id}/add_photos/', {'files': list(files), 'recorded_by': self.sam.pk}, format='multipart')

    def test_the_report_pdf_can_be_saved_to_drive_and_this_pc(self):
        self.upload(picture())
        local = self.base / 'local'
        with override_settings(REPORTS_LOCAL_DIR=local):
            response = self.client.post(f'/api/non-conformances/{self.report_id}/save_to_drive/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['problems'], [])
        for root in (local, self.drive_folder):
            files = list((root / 'Non-Conformance Reports').glob('NCR-0001 - Choc brownies 12pk BR12 - *.pdf'))
            self.assertEqual(len(files), 1, root)
            self.assertTrue(files[0].read_bytes().startswith(b'%PDF'))

    def test_notified_time_on_a_new_report_becomes_the_first_follow_up(self):
        response = self.post('/api/non-conformances/', notified_at='2026-11-02T09:30:00+11:00', **REPORT)
        self.assertEqual(response.status_code, 201, response.content)
        report = NonConformance.objects.get(pk=response.json()['id'])
        update = report.updates.get()
        self.assertEqual((update.kind, update.recorded_by), ('notified', self.sam))

    def test_a_photo_can_come_with_a_follow_up_and_shows_in_the_pdf_row(self):
        update_id = self.post(f'/api/non-conformances/{self.report_id}/updates/', kind='response', text='Sorry', recorded_by=self.sam.pk).json()['id']
        response = self.client.post(f'/api/non-conformances/{self.report_id}/add_photos/',
                                    {'files': [picture()], 'recorded_by': self.sam.pk, 'update': update_id}, format='multipart')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()[0]['update'], update_id)
        self.assertEqual(Photo.objects.get().update_id, update_id)
        self.assertTrue(self.client.get(f'/api/non-conformances/{self.report_id}/pdf/').content.startswith(b'%PDF'))

    def test_a_photo_cannot_be_tied_to_another_reports_follow_up(self):
        other = self.post('/api/non-conformances/', **REPORT).json()['id']
        update_id = self.post(f'/api/non-conformances/{other}/updates/', kind='note', text='x', recorded_by=self.sam.pk).json()['id']
        response = self.client.post(f'/api/non-conformances/{self.report_id}/add_photos/',
                                    {'files': [picture()], 'recorded_by': self.sam.pk, 'update': update_id}, format='multipart')
        self.assertEqual(response.status_code, 404)

    def test_drive_link_comes_from_the_url_or_the_folder_id(self):
        self.assertEqual(self.client.get('/api/non-conformances/summary/').json()['drive_url'], '')
        with override_settings(GOOGLE_DRIVE_FOLDER_ID='abc123'):
            self.assertEqual(self.client.get('/api/non-conformances/summary/').json()['drive_url'], 'https://drive.google.com/drive/folders/abc123')
        with override_settings(GOOGLE_DRIVE_URL='https://drive.google.com/x', GOOGLE_DRIVE_FOLDER_ID='abc123'):
            self.assertEqual(self.client.get('/api/non-conformances/summary/').json()['drive_url'], 'https://drive.google.com/x')

    def test_a_photo_is_copied_into_a_folder_for_the_report(self):
        response = self.upload(picture(name='brownies: carton?.png'))
        photo = Photo.objects.get()
        copy = self.drive_folder / 'Non-Conformance Photos' / 'NCR-0001 - Choc brownies 12pk BR12' / f'{photo.pk}-brownies carton .png'
        self.assertTrue(copy.is_file(), list(self.drive_folder.rglob('*')))
        self.assertEqual(copy.read_bytes(), (self.base / 'photos' / photo.path).read_bytes())
        self.assertEqual(response.json()[0]['copy_status'], 'saved')

    def test_when_the_drive_folder_is_not_there_the_photo_is_kept_and_copied_later(self):
        shutil.rmtree(self.drive_folder)  # e.g. Google Drive for desktop is not running
        response = self.upload(picture())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()[0]['copy_status'], 'waiting')
        self.assertIn('Could not copy yet', response.json()[0]['copy_error'])
        self.assertTrue((self.base / 'photos' / Photo.objects.get().path).is_file())
        self.drive_folder.mkdir()  # it comes back
        self.assertEqual(drive.copy_pending(), 1)
        self.assertEqual(self.client.get(f'/api/non-conformances/{self.report_id}/').json()['photos'][0]['copy_status'], 'saved')
        self.assertEqual(len(list(self.drive_folder.rglob('*.png'))), 1)
        self.assertEqual(drive.copy_pending(), 0)  # nothing more to do, and no duplicate

    def test_no_copy_is_made_or_reported_when_no_drive_place_is_set_up(self):
        with override_settings(REPORTS_EXPORT_DIR='', GOOGLE_DRIVE_FOLDER_ID=''):
            response = self.upload(picture())
            self.assertEqual(response.json()[0]['copy_status'], 'off')
            self.assertEqual(drive.copy_pending(), 0)
        self.assertEqual(list(self.drive_folder.rglob('*.png')), [])

    def test_the_google_drive_api_gets_its_own_copy_once_even_if_the_folder_copy_fails_first(self):
        saved = []

        class FakeDrive:
            label = 'Google Drive folder abc'

            def __init__(self, *args):
                pass

            def save_in(self, subfolders, name, data, content_type):
                saved.append((subfolders, name, content_type))

        shutil.rmtree(self.drive_folder)
        with override_settings(GOOGLE_DRIVE_FOLDER_ID='abc', GOOGLE_SERVICE_ACCOUNT_FILE='key.json'):
            with mock.patch('reports.destinations.GoogleDrive', FakeDrive):
                # LocalFolder raises while building the list when its folder is missing, so nothing is copied yet.
                self.upload(picture())
                self.assertEqual(saved, [])
                self.drive_folder.mkdir()
                drive.copy_pending()
                drive.copy_pending()
        self.assertEqual(len(saved), 1)  # once, not on every retry
        self.assertEqual(saved[0][0], ['Non-Conformance Photos', 'NCR-0001 - Choc brownies 12pk BR12'])
        self.assertEqual(saved[0][2], 'image/png')
        self.assertEqual(Photo.objects.get().copied_to, ['Google Drive folder abc', str(self.drive_folder)])
