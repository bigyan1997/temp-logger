"""Which suppliers a login is asked about on a day."""

from setup.models import Supplier

from .models import ReceivingCheck


def suppliers_for(day, day_login):
    """The active suppliers to log on `day`. The day login sees every supplier. The night login sees only those ticked
    "night login only", plus any already logged that day (so an entry made in the day never disappears at night)."""
    suppliers = Supplier.objects.filter(active=True)
    if not day_login:
        logged = ReceivingCheck.objects.filter(date=day, voided=False).values('supplier_id')
        suppliers = suppliers.filter(night_only=True) | suppliers.filter(pk__in=logged)
    return suppliers.order_by('id')
