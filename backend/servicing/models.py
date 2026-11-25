from django.db import models

from setup.models import Attributed


class ServiceRecord(Attributed):
    """One service or repair of a piece of equipment (a coolroom, a freezer...): what was done, who did it, when,
    and the invoice. Edits are kept in the audit log; a delete (with a reason) leaves one audit line.

    `serviced_by` is the company or technician who did the work. `recorded_by` (from Attributed) is the staff member
    who typed it in."""

    equipment = models.CharField(max_length=100, help_text='What was serviced, e.g. Coolroom or Chest Freezer.')
    service_date = models.DateField(help_text='The day the work was done.')
    serviced_by = models.CharField(max_length=150, help_text='Company or technician who did the work.')
    work_done = models.TextField()
    invoice_number = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['-service_date', '-id']

    @property
    def number(self):
        return f'SVC-{self.pk:04d}'

    def __str__(self):
        return f'{self.number} {self.equipment}'


class ServiceFile(Attributed):
    """An invoice, report or photo attached to a service record. The file is kept in NCR_PHOTOS_DIR with the other
    attachments (see nonconformance/photos.py); deleted with a reason (see removal.py)."""

    service = models.ForeignKey(ServiceRecord, on_delete=models.PROTECT, related_name='files')
    path = models.CharField(max_length=200)
    original_name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    # Copies kept in Google Drive too, by place name (same idea as non-conformance photos).
    copied_to = models.JSONField(default=list, blank=True)
    copy_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.service.number} {self.original_name}'
