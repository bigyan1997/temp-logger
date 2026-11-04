import tempfile
from pathlib import Path

from django.test import SimpleTestCase


class AppVersionTests(SimpleTestCase):
    def get_version(self, index_html):
        with tempfile.TemporaryDirectory() as folder:
            if index_html is not None:
                (Path(folder) / 'index.html').write_text(index_html, encoding='utf-8')
            with self.settings(FRONTEND_DIST=Path(folder)):
                return self.client.get('/api/version/').json()['version']

    def test_version_is_the_hashed_script_name(self):
        html = '<script type="module" src="/assets/index-AbC123.js"></script>'
        self.assertEqual(self.get_version(html), 'index-AbC123.js')

    def test_version_changes_when_the_build_changes(self):
        first = self.get_version('<script src="/assets/index-one.js"></script>')
        second = self.get_version('<script src="/assets/index-two.js"></script>')
        self.assertNotEqual(first, second)

    def test_no_build_gives_no_version(self):
        self.assertIsNone(self.get_version(None))
