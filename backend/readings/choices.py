from django.db import models


class Status(models.TextChoices):
    OK = 'ok', 'In range'
    NEAR_LIMIT = 'near_limit', 'Near limit'
    OUT_OF_LIMIT = 'out_of_limit', 'Out of limit'


class ProductType(models.TextChoices):
    """What was delivered. It decides which limit applies on receiving."""

    CHILLED = 'chilled', 'Chilled'
    FROZEN = 'frozen', 'Frozen'
    BAKED_PIE = 'baked_pie', 'Freshly baked pies'


class Action(models.TextChoices):
    """What was done about a reading that was out of limit (from the HACCP procedures)."""

    # Storage (SOP 4.1.2: the 2hr/4hr rule)
    USED_IMMEDIATELY = 'used_immediately', 'Used immediately'
    MOVED_TO_OTHER_UNIT = 'moved_to_other_unit', 'Moved to another unit'
    DISCARDED = 'discarded', 'Discarded'
    REPAIR_ARRANGED = 'repair_arranged', 'Repair or replacement arranged'

    # Receiving (SOP 4.1.1 and Table 1)
    REJECTED = 'rejected', 'Delivery rejected'
    ACCEPTED_SUPPLIER_PROVED_SAFE = 'accepted_supplier_proved_safe', 'Accepted: supplier showed the food is safe'
    MOVED_TO_COOLROOM = 'moved_to_coolroom', 'Moved to the coolroom immediately'
    SUPPLIER_NOTIFIED = 'supplier_notified', 'Supplier notified'

    # Dispatch (SOP 4.1.3)
    CONTACTED_OPERATIONS_MANAGER = 'contacted_operations_manager', 'Operations Manager contacted'
    RECHECKED = 'rechecked', 'Temperature re-checked'


class CheckKind(models.TextChoices):
    STORAGE = 'storage', 'Storage'
    RECEIVING = 'receiving', 'Receiving'
    DISPATCH = 'dispatch', 'Dispatch'


# Which actions can be chosen for each kind of check.
ACTIONS_FOR = {
    CheckKind.STORAGE: [
        Action.USED_IMMEDIATELY,
        Action.MOVED_TO_OTHER_UNIT,
        Action.DISCARDED,
        Action.REPAIR_ARRANGED,
    ],
    CheckKind.RECEIVING: [
        Action.REJECTED,
        Action.ACCEPTED_SUPPLIER_PROVED_SAFE,
        Action.MOVED_TO_COOLROOM,
        Action.SUPPLIER_NOTIFIED,
    ],
    CheckKind.DISPATCH: [
        Action.CONTACTED_OPERATIONS_MANAGER,
        Action.DISCARDED,
        Action.RECHECKED,
    ],
}
