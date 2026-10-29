"""The temperature rules, kept separate from the web code so they are easy to read and test."""

from decimal import Decimal

from .choices import ProductType, Status

CHILLED_MAX = Decimal('5.0')     # chilled food must be this cold or colder
FROZEN_MAX = Decimal('-15.0')    # frozen food must be this cold or colder
NEAR_MARGIN = Decimal('1.0')     # within this many degrees of the limit counts as "near"

# No real reading is outside this range, so anything else is a typing mistake.
POSSIBLE_RANGE = (Decimal('-40'), Decimal('40'))
BIG_JUMP = Decimal('10')         # change since the last reading that is worth double-checking


def limit_for_product(product_type):
    return FROZEN_MAX if product_type == ProductType.FROZEN else CHILLED_MAX


def status_for(value, limit):
    """In range, near the limit, or out of limit. Colder is always better."""
    if value > limit:
        return Status.OUT_OF_LIMIT
    if value > limit - NEAR_MARGIN:
        return Status.NEAR_LIMIT
    return Status.OK


def unusual_reasons(value, limit, previous=None):
    """Plain-language reasons a reading looks wrong. The user must confirm it anyway to save it."""
    reasons = []
    if limit <= FROZEN_MAX and value > 0:
        reasons.append('A frozen reading above 0 °C usually means a missing minus sign.')
    if limit > FROZEN_MAX and value < -5:
        reasons.append('A chilled reading below -5 °C is very unusual.')
    if previous is not None and abs(value - previous) > BIG_JUMP:
        reasons.append(f'That is more than {BIG_JUMP} °C different from the last reading ({previous} °C).')
    return reasons
