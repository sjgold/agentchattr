"""Static CSS guards so short desktop windows do not break the chat layout.

Primary target is 1440x1080; smaller windows only must not overlap or hide
controls. Layout cannot run in Node vm, so these read the shipped stylesheets;
the rendered result was checked in a browser at 1280x720 and 1024x768.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def rule_body(css, selector):
    """Declarations of every rule whose selector list is exactly `selector`."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return ' '.join(m.group(2) for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css) if m.group(1).strip() == selector)


class ShortWindowLayoutTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / 'static' / name).read_text(encoding='utf-8')

    def assert_gives_way(self, css, selector):
        body = rule_body(css, selector)
        self.assertTrue(body, f'{selector} rule missing')
        # Panels above the chat share the leftover height so the composer stays on screen.
        self.assertRegex(body, r'flex-shrink:\s*1\b', f'{selector} must be allowed to shrink')
        self.assertRegex(body, r'min-height:\s*\d+px', f'{selector} needs a small floor')
        self.assertRegex(body, r'overflow(-y)?:\s*auto', f'{selector} must scroll inside itself')

    def test_documents_panel_gives_way_to_the_composer(self):
        self.assert_gives_way(self.read('artifacts.css'), '.artifact-documents')

    def test_turn_attention_panel_gives_way_to_the_composer(self):
        self.assert_gives_way(self.read('sessions.css'), '.session-turn-controls')

    def test_composer_never_shrinks(self):
        self.assertRegex(rule_body(self.read('style.css'), 'footer'), r'flex-shrink:\s*0')

    def test_session_launcher_shows_templates_on_short_windows(self):
        block = re.search(r'@media\s*\(max-height:\s*(\d+)px\)\s*\{(.*?)\n\}', self.read('sessions.css'), re.S)
        self.assertIsNotNone(block, 'sessions.css needs a short-window rule for the launcher')
        self.assertIn('.session-source-editor textarea', block.group(2))


if __name__ == '__main__':
    unittest.main()
