"""Where report photos and other attached files are kept, and what is accepted.

Files live in a folder on the PC (NCR_PHOTOS_DIR), not in the database, and are only served to a signed-in day
login. The file type is checked from the file's own first bytes, never from its name alone. Pictures, PDF, Word,
Excel, PowerPoint, OpenDocument, RTF, text and CSV are kept. Web pages, scripts and programs are not: they could run
in the browser or on a PC, so they are refused whatever they are named."""

import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone

MAX_BYTES = 20 * 1024 * 1024
MAX_PER_REPORT = 20
HEAD_BYTES = 512  # enough to recognise every type below

# first bytes of the file -> (extension, content type)
SIGNATURES = [
    (b'\xff\xd8\xff', 'jpg', 'image/jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'png', 'image/png'),
    (b'GIF87a', 'gif', 'image/gif'),
    (b'GIF89a', 'gif', 'image/gif'),
]

# Documents: the name's ending says which one it is, and the file's first bytes must fit that kind of file.
ZIP_START = b'PK\x03\x04'  # .docx, .xlsx, .pptx and OpenDocument files are zip files inside
OLE_START = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'  # the older .doc, .xls, .ppt
OFFICE = 'application/vnd.openxmlformats-officedocument.'
OPEN_DOCUMENT = 'application/vnd.oasis.opendocument.'
DOCUMENTS = {
    # extension: (content type, first bytes it must start with; None means plain text)
    'pdf': ('application/pdf', b'%PDF'),
    'docx': (OFFICE + 'wordprocessingml.document', ZIP_START),
    'xlsx': (OFFICE + 'spreadsheetml.sheet', ZIP_START),
    'pptx': (OFFICE + 'presentationml.presentation', ZIP_START),
    'odt': (OPEN_DOCUMENT + 'text', ZIP_START),
    'ods': (OPEN_DOCUMENT + 'spreadsheet', ZIP_START),
    'odp': (OPEN_DOCUMENT + 'presentation', ZIP_START),
    'doc': ('application/msword', OLE_START),
    'xls': ('application/vnd.ms-excel', OLE_START),
    'ppt': ('application/vnd.ms-powerpoint', OLE_START),
    'rtf': ('application/rtf', b'{\\rtf'),
    'txt': ('text/plain', None),
    'csv': ('text/csv', None),
}


def shows_in_browser(content_type):
    """Pictures and PDFs open in a browser tab. Anything else is only ever sent as a download."""
    return content_type.startswith('image/') or content_type == 'application/pdf'


def sniff(head, name=''):
    """(extension, content type) for an accepted file, or None. `name` is only used to tell the documents apart."""
    for signature, extension, content_type in SIGNATURES:
        if head.startswith(signature):
            return extension, content_type
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp', 'image/webp'

    extension = Path(name).suffix.lower().lstrip('.')
    if extension not in DOCUMENTS:
        return None
    content_type, start = DOCUMENTS[extension]
    if start is None:  # plain text: no binary bytes, and not a web page
        return (extension, content_type) if b'\x00' not in head and not head.lstrip().startswith(b'<') else None
    return (extension, content_type) if head.startswith(start) else None


def folder():
    return Path(settings.NCR_PHOTOS_DIR)


def save(uploaded):
    """Write an uploaded file into the photos folder. Returns (relative path, content type, size).

    Raises ValueError with a plain message when the file is not an accepted kind or is too big."""
    if uploaded.size > MAX_BYTES:
        raise ValueError(f'{uploaded.name} is bigger than {MAX_BYTES // (1024 * 1024)} MB.')
    head = uploaded.read(HEAD_BYTES)
    uploaded.seek(0)
    kind = sniff(head, uploaded.name)
    if kind is None:
        raise ValueError(
            f'{uploaded.name} is not a file the app can keep. Use a photo (JPG, PNG, GIF, WEBP) or a document '
            '(PDF, Word, Excel, PowerPoint, OpenDocument, RTF, TXT or CSV).'
        )
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
