import re

from django.conf import settings
from django.http import JsonResponse


def app_version(request):
    """Which frontend build is being served, so an open page can offer a reload after a deploy.
    The built index.html names a script file whose hash changes on every build."""
    try:
        text = (settings.FRONTEND_DIST / 'index.html').read_text(encoding='utf-8')
        match = re.search(r'assets/(index-[^"]+\.js)', text)
    except OSError:
        match = None
    return JsonResponse({'version': match.group(1) if match else None})
