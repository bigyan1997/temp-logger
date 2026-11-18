"""A link that opens an /api/... address straight in the browser (a PDF, a photo) must never show a technical page when
the login has ended. It shows a plain "sign in again" page instead. The app's own data requests ask for JSON, so they
are left alone and the screens handle those themselves."""

from django.http import HttpResponse

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Please sign in again</title></head>
<body style="margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:#f4f8f8;color:#173a3a;">
<main style="max-width:420px;margin:12vh auto;padding:28px;background:#fff;border:1px solid #cfe3e3;border-radius:14px;">
<h1 style="font-size:22px;margin:0 0 10px;">Please sign in again</h1>
<p style="line-height:1.5;margin:0 0 20px;">Your login has ended, or this login is not allowed to open that.
Sign in again to carry on.</p>
<a href="/login" style="display:inline-block;background:#0f766e;color:#fff;text-decoration:none;font-weight:600;padding:12px 22px;border-radius:8px;">Go to sign in</a>
</main></body></html>"""


class SignInAgainPage:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        opened_by_a_link = 'text/html' in request.headers.get('Accept', '')
        if request.path.startswith('/api/') and response.status_code in (401, 403) and opened_by_a_link:
            return HttpResponse(PAGE, status=response.status_code)
        return response
