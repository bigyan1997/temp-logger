from django.core.management.base import BaseCommand, CommandError

from nonconformance import oauth_drive


class Command(BaseCommand):
    help = (
        'One-time Google sign-in so non-conformance photos and PDFs go straight into a Google Drive. A browser opens: '
        'sign in as the account that should own them and click Allow.'
    )

    def handle(self, *args, **options):
        from google_auth_oauthlib.flow import InstalledAppFlow

        client = oauth_drive.client_path()
        if not client.is_file():
            raise CommandError(
                f'The Google OAuth client file was not found: {client}. Use the same "Desktop app" client file as the '
                'npd-tracker (drive-oauth-client.json) and put it there.'
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(client), [oauth_drive.DRIVE_SCOPE])
        # prompt=consent makes sure Google gives a refresh token even if this account said yes before.
        credentials = flow.run_local_server(port=0, access_type='offline', prompt='consent')
        if not credentials.refresh_token:
            raise CommandError("Google did not return a refresh token. Run this again.")
        path = oauth_drive.token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(credentials.to_json(), encoding='utf-8')

        drive = oauth_drive.OAuthDrive()
        self.stdout.write(self.style.SUCCESS(f'Done. Reports will be saved in: {oauth_drive.folder_url()}'))
