"""Where report photos are kept and what is accepted.

Photos live in a folder on the PC (NCR_PHOTOS_DIR), not in the database, and are only served to a signed-in day
login. The file type is checked from the file's own first bytes, never from its name."""

import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone

MAX_BYTES = 10 * 1024 * 1024
MAX_PER_REPORT = 20

# first bytes of the file -> (extension, content type)
SIGNATURES = [
    (b'\xff\xd8\xff', 'jpg', 'image/jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'png', 'image/png'),
    (b'GIF87a', 'gif', 'image/gif'),
    (b'GIF89a', 'gif', 'image/gif'),
]


def sniff(head):
    """(extension, content type) for an accepted picture, or None."""
    for signature, extension, content_type in SIGNATURES:
        if head.startswith(signature):
            return extension, content_type
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp', 'image/webp'
    return None


def folder():
    return Path(settings.NCR_PHOTOS_DIR)


def save(uploaded):
    """Write an uploaded file into the photos folder. Returns (relative path, content type, size).

    Raises ValueError with a plain message when the file is not an accepted picture or is too big."""
    if uploaded.size > MAX_BYTES:
        raise ValueError(f'{uploaded.name} is bigger than {MAX_BYTES // (1024 * 1024)} MB.')
    head = uploaded.read(16)
    uploaded.seek(0)
    kind = sniff(head)
    if kind is None:
        raise ValueError(f'{uploaded.name} is not a photo the app can keep (use JPG, PNG, GIF or WEBP).')
    extension, content_type = kind

    today = timezone.localdate()
    relative = f'{today:%Y}/{today:%m}/{uuid.uuid4().hex}.{extension}'
    target = folder() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'wb') as out:
        for chunk in uploaded.chunks():
            out.write(chunk)
    return relative, content_type, uploaded.size


def full_path(relative):
    """The file's real location, refusing anything that points outside the photos folder."""
    base = folder().resolve()
    target = (base / relative).resolve()
    if base not in target.parents:
        raise ValueError('Not a photo path.')
    return target
