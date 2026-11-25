import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from audit.models import AuditLog
from readings.tests.base import ReadingTestCase

from .models import ServiceFile, ServiceRecord

SERVICE = {'equipment': 'Coolroom', 'service_date': '2026-11-02', 'serviced_by': 'Cool Care Refrigeration',
           'work_done': 'Cleaned the condenser and checked the gas.', 'invoice_number': 'INV-1042'}
PDF = b'%PDF-1.7 a small invoice'


class ServiceRecordTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        override = override_settings(NCR_PHOTOS_DIR=str(self.folder))
        override.enable()
        self.addCleanup(override.disable)
        self.sign_in(self.admin)

    def create(self, **changes):
        return self.post('/api/service-records/', **{**SERVICE, **changes})

    def upload(self, service_id, *files):
        return self.client.post(f'/api/service-records/{service_id}/add_files/', {'files': list(files), 'recorded_by': self.sam.pk}, format='multipart')

    def test_a_service_gets_a_number_and_remembers_who_typed_it(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['number'], f"SVC-{body['id']:04d}")
        self.assertEqual(body['recorded_by_name'], 'Sam')
        self.assertEqual(body['serviced_by'], 'Cool Care Refrigeration')
        self.assertEqual(ServiceRecord.objects.get().entered_by, self.admin)

    def test_the_night_login_cannot_use_it(self):
        self.sign_in(self.night)
        self.assertEqual(self.create().status_code, 403)
        self.assertEqual(self.client.get('/api/service-records/').status_code, 403)

    def test_what_who_and_when_are_needed(self):
        self.assertEqual(self.create(equipment=' ').status_code, 400)
        self.assertEqual(self.create(serviced_by='').status_code, 400)
        self.assertEqual(self.create(work_done='').status_code, 400)
        self.assertEqual(self.create(service_date='2999-01-01').status_code, 400)
        self.assertEqual(self.create(invoice_number='').status_code, 201)  # the invoice number is optional

    def test_an_invoice_of_any_kind_can_be_attached_and_is_copied_to_drive(self):
        service_id = self.create().json()['id']
        pdf = SimpleUploadedFile('invoice.pdf', PDF, content_type='application/pdf')
        word = SimpleUploadedFile('quote.docx', b'PK\x03\x04' + b'0' * 20)
        with mock.patch('servicing.views.copy_file') as copy:
            response = self.upload(service_id, pdf, word)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(copy.call_count, 2)  # each file goes to Google Drive too
        self.assertEqual(ServiceFile.objects.count(), 2)

        files = self.client.get(f'/api/service-records/{service_id}/').json()['files']
        opened = self.client.get(files[0]['url'])
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(b''.join(opened.streaming_content), PDF)
        self.assertIn('attachment', self.client.get(files[1]['url'])['Content-Disposition'])  # Word is only downloaded

    def test_a_program_named_as_an_invoice_is_refused(self):
        service_id = self.create().json()['id']
        fake = SimpleUploadedFile('invoice.pdf', b'MZ\x90\x00 a program')
        self.assertEqual(self.upload(service_id, fake).status_code, 400)
        self.assertEqual(ServiceFile.objects.count(), 0)

    def test_a_drive_copy_is_made_where_the_non_conformance_photos_go(self):
        service_id = self.create().json()['id']
        place = mock.Mock(label='Test place')
        with mock.patch('servicing.drive.configured_labels', return_value=['Test place']), \
                mock.patch('servicing.drive.destinations', return_value=([place], [])):
            self.upload(service_id, SimpleUploadedFile('invoice.pdf', PDF))
        folders = place.save_in.call_args.args[0]
        self.assertEqual(folders[1:], ['Service Records', f'SVC-{service_id:04d} - Coolroom'])
        self.assertEqual(ServiceFile.objects.get().copied_to, ['Test place'])

    def test_a_record_can_be_edited_and_the_audit_log_keeps_what_changed(self):
        service_id = self.create().json()['id']
        url = f'/api/service-records/{service_id}/edit/'
        self.assertEqual(self.client.post(url, {'serviced_by': 'Zero'}, format='json').status_code, 400)  # a name is needed
        self.assertEqual(self.post(url, serviced_by='  ').status_code, 400)
        response = self.post(url, serviced_by='Zero Refrigeration', invoice_number='INV-7')
        self.assertEqual(response.status_code, 200, response.content)
        service = ServiceRecord.objects.get()
        self.assertEqual((service.serviced_by, service.invoice_number, service.equipment), ('Zero Refrigeration', 'INV-7', 'Coolroom'))
        self.assertEqual(service.recorded_by, self.sam)  # who typed it in does not change
        line = AuditLog.objects.get(action='edited')
        self.assertEqual(line.module, 'servicing')
        self.assertIn('Cool Care Refrigeration -> Zero Refrigeration', line.summary)
        self.post(url, serviced_by='Zero Refrigeration')  # nothing changed: no new audit line
        self.assertEqual(AuditLog.objects.filter(action='edited').count(), 1)

    def test_a_record_is_deleted_with_its_files_and_one_audit_line_keeps_what_went(self):
        service_id = self.create().json()['id']
        self.upload(service_id, SimpleUploadedFile('invoice.pdf', PDF))
        self.assertEqual(len(list(self.folder.rglob('*.pdf'))), 1)
        url = f'/api/service-records/{service_id}/delete/'
        self.assertEqual(self.post(url, reason='').status_code, 400)  # a reason is needed
        self.assertEqual(self.client.post(url, {'reason': 'made by mistake'}, format='json').status_code, 400)  # and a name
        response = self.post(url, reason='made by mistake')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'deleted': True, 'problems': []})
        self.assertEqual((ServiceRecord.objects.count(), ServiceFile.objects.count()), (0, 0))
        self.assertEqual(list(self.folder.rglob('*.pdf')), [])  # gone from this PC
        line = AuditLog.objects.get(action='deleted')
        self.assertEqual(line.module, 'servicing')
        self.assertIn('Cool Care Refrigeration', line.summary)
        self.assertEqual(line.reason, 'made by mistake')

    def test_one_file_can_be_deleted_and_the_record_stays(self):
        service_id = self.create().json()['id']
        self.upload(service_id, SimpleUploadedFile('invoice.pdf', PDF))
        file_id = ServiceFile.objects.get().pk
        self.assertEqual(self.post(f'/api/service-records/files/{file_id}/delete/', reason='wrong invoice').status_code, 200)
        self.assertEqual((ServiceRecord.objects.count(), ServiceFile.objects.count()), (1, 0))
        self.assertEqual(list(self.folder.rglob('*.pdf')), [])
        self.assertEqual(AuditLog.objects.get(action='deleted').module, 'servicing')

    def test_the_night_login_cannot_delete(self):
        service_id = self.create().json()['id']
        self.sign_in(self.night)
        self.assertEqual(self.post(f'/api/service-records/{service_id}/delete/', reason='no').status_code, 403)
        self.assertEqual(ServiceRecord.objects.count(), 1)
