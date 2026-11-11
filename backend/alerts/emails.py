"""Builds and sends an alert as a proper email: plain text for old mail programs, plus a styled HTML version.

The HTML uses inline styles and tables only (no images), because that is what email programs show reliably.
"""

from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

# tone -> (accent colour, soft background, icon, label in the banner)
TONES = {
    'reminder': ('#a35a00', '#fff4e0', '⏰', 'DUE SOON'),
    'reminder2': ('#b4233c', '#fdecee', '⚠️', 'STILL NOT LOGGED'),
    'ok': ('#1b7f4b', '#e6f4ec', '✅', 'WORKING'),
    'failed': ('#b4233c', '#fdecee', '⚠️', 'ACTION NEEDED'),
}
BRAND = '#0b7a75'

# Which part of the app an alert is about: its name, icon, header colour and the page its button opens.
# The "system" ones (backup, test) are about the whole app.
MODULES = {
    'temperature': {'name': 'Temperature Logger', 'icon': '🌡️', 'colour': BRAND, 'path': '/log/storage', 'button': 'Open the Temperature Logger'},
    'cleaning': {'name': 'Cleaning & Maintenance', 'icon': '🧹', 'colour': '#2f6f9f', 'path': '/cleaning/notifications', 'button': 'Open Notifications'},
    'calibration': {'name': 'Calibration', 'icon': '📏', 'colour': '#6b4fa3', 'path': '/calibration', 'button': 'Open Calibration'},
    'system': {'name': 'Achieve HACCP', 'icon': '🛡️', 'colour': '#4a5a60', 'path': '', 'button': ''},
}
# alert kind -> module (see checks.py and the other *_check.py files). Anything not listed is about the whole app.
KIND_MODULE = {
    'reminder': 'temperature', 'reminder2': 'temperature', 'out_of_limit': 'temperature', 'sample': 'temperature',
    'cleaning_due': 'cleaning', 'cleaning_late': 'cleaning',
    'calibration': 'calibration', 'calibration_overdue': 'calibration',
}


def module_for(kind):
    return MODULES[KIND_MODULE.get(kind, 'system')]
INK = '#12262b'
MUTED = '#5a6e73'
LINE = '#d8e3e4'
FONT = "font-family:'Segoe UI',Helvetica,Arial,sans-serif;"


def unit_rows(items, accent):
    rows = ''.join(
        f'<tr><td style="padding:10px 14px;border-top:1px solid {LINE};font-size:15px;color:{INK};{FONT}">'
        f'<span style="display:inline-block;width:14px;height:14px;border:2px solid {accent};border-radius:3px;'
        f'vertical-align:middle;margin-right:10px;"></span>{escape(name)}</td>'
        f'<td align="right" style="padding:10px 14px;border-top:1px solid {LINE};{FONT}">'
        f'<span style="font-size:12px;font-weight:600;color:{accent};">Not logged</span></td></tr>'
        for name in items
    )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border:1px solid {LINE};border-radius:10px;border-collapse:separate;margin-top:18px;">'
        f'<tr><td colspan="2" style="padding:12px 14px;font-size:13px;font-weight:700;color:{MUTED};'
        f'text-transform:uppercase;letter-spacing:.06em;{FONT}">Still to log ({len(items)})</td></tr>{rows}</table>'
    )


def render_html(subject, lead, items, tone, module):
    accent, soft, icon, label = TONES[tone]
    app_url = settings.APP_URL.rstrip('/')
    # Storage reminders only link to the screen when units are still to log; the other modules always have a page to open.
    show_button = app_url and module['path'] and (items or module is not MODULES['temperature'])
    button = (
        f'<p style="margin:26px 0 4px;"><a href="{escape(app_url)}{module["path"]}" '
        f'style="background:{module["colour"]};color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;'
        f'padding:12px 22px;border-radius:8px;display:inline-block;{FONT}">{escape(module["button"])}</a></p>'
        if show_button else ''
    )
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f8f8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f8f8;padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0"
       style="max-width:560px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid {LINE};">
  <tr><td style="background:{module['colour']};padding:18px 24px;{FONT}">
    <span style="font-size:20px;">{module['icon']}</span>
    <span style="color:#ffffff;font-size:18px;font-weight:700;vertical-align:middle;margin-left:6px;">{escape(module['name'])}</span>
    <div style="color:#ffffff;opacity:.85;font-size:12px;margin-top:2px;">Achieve HACCP &middot; Achieve Cafe Provisions</div>
  </td></tr>
  <tr><td style="background:{soft};padding:22px 24px;border-bottom:3px solid {accent};{FONT}">
    <div style="font-size:12px;font-weight:700;letter-spacing:.08em;color:{accent};">{icon}&nbsp; {label}</div>
    <div style="font-size:22px;font-weight:700;color:{INK};margin-top:6px;line-height:1.25;">{escape(subject)}</div>
  </td></tr>
  <tr><td style="padding:22px 24px 26px;{FONT}color:{INK};">
    <div style="font-size:16px;line-height:1.5;">{escape(lead)}</div>
    {unit_rows(items, accent) if items else ''}
    {button}
  </td></tr>
  <tr><td style="padding:14px 24px;background:#f4f8f8;border-top:1px solid {LINE};font-size:12px;color:{MUTED};{FONT}">
    Sent automatically by Achieve HACCP ({escape(module['name'])}). You will not get this same alert again.
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def send_alert_email(alert, to):
    """Send one Alert (see checks.py) to a list of addresses, as text and HTML."""
    module = module_for(alert.kind)
    message = EmailMultiAlternatives(f'{module["name"]}: {alert.subject}', alert.body, None, to)
    message.attach_alternative(render_html(alert.subject, alert.lead, alert.items, alert.tone, module), 'text/html')
    message.send()
