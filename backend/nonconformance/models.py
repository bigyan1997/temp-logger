from django.db import models
from django.utils import timezone

from setup.models import Attributed


class NonConformance(Attributed):
    """One row of the paper Table 5 (HACCP Plan 1.6): a problem with a product, as first reported.

    Never edited or deleted. What happens afterwards (manufacturer told, their answer, the corrective action, closing it)
    is added as dated follow-ups, so the report reads as one story and nothing is overwritten."""

    date = models.DateField()
    product = models.CharField(max_length=200, help_text='Product name / code')
    customer = models.CharField(max_length=150, blank=True)
    manufacturer = models.CharField(max_length=150, blank=True)
    description = models.TextField(help_text='Description of the problem')
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-date', '-id']

    @property
    def number(self):
        return f'NCR-{self.pk:04d}'

    @property
    def is_closed(self):
        return self.updates.filter(kind=Update.Kind.CLOSED, voided=False).exists()

    def __str__(self):
        return f'{self.number} {self.product}'


class Update(Attributed):
    """A dated follow-up on a report. Never edited or deleted; a mistake is voided with a reason."""

    class Kind(models.TextChoices):
        NOTIFIED = 'notified', 'Manufacturer notified'
        RESPONSE = 'response', 'Manufacturer response'
        ACTION = 'action', 'Further corrective action'
        NOTE = 'note', 'Note'
        CLOSED = 'closed', 'Closed and signed off'

    report = models.ForeignKey(NonConformance, on_delete=models.PROTECT, related_name='updates')
    kind = models.CharField(max_length=12, choices=Kind.choices)
    happened_at = models.DateTimeField(default=timezone.now, help_text='When it happened, e.g. when the manufacturer was told.')
    text = models.TextField(blank=True)
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['happened_at', 'id']

    def __str__(self):
        return f'{self.report.number} {self.get_kind_display()}'


class Photo(Attributed):
    """A photo attached to a report. The file is kept in NCR_PHOTOS_DIR (see photos.py); never deleted, only voided."""

    report = models.ForeignKey(NonConformance, on_delete=models.PROTECT, related_name='photos')
    path = models.CharField(max_length=200, help_text='Where the file is, inside NCR_PHOTOS_DIR.')
    original_name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=40)
    size = models.PositiveIntegerField()
    # Copies kept somewhere else too (the same Google Drive places the report PDFs go to), by place name.
    copied_to = models.JSONField(default=list, blank=True)
    copy_error = models.CharField(max_length=300, blank=True)
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.report.number} {self.original_name}'
