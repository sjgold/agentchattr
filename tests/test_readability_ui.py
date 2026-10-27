"""Objective readability guards for the pre-flight and chat screens.

Computes WCAG 2.x contrast from the shipped :root colour tokens and checks
minimum text sizes in the stylesheets these screens use. Target window is
1440x1080 on the dark theme.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'


def tokens():
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    root = re.search(r':root\s*\{(.*?)\}', css, re.S).group(1)
    return dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;', root))


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def strip_comments(css):
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


class ContrastTests(unittest.TestCase):
    SURFACES = ('bg', 'bg-header', 'bg-input', 'bg-msg')

    def test_dim_helper_text_meets_aa_on_every_surface(self):
        t = tokens()
        for surface in self.SURFACES:
            with self.subTest(surface=surface):
                self.assertGreaterEqual(contrast(t['text-dim'], t[surface]), 4.5)

    def test_system_text_meets_aa_where_system_lines_render(self):
        t = tokens()
        for surface in ('bg', 'bg-msg'):
            with self.subTest(surface=surface):
                self.assertGreaterEqual(contrast(t['text-system'], t[surface]), 4.5)

    def test_dim_text_stays_below_body_text_so_hierarchy_survives(self):
        t = tokens()
        self.assertLess(contrast(t['text-dim'], t['bg']), contrast(t['text'], t['bg']))
        self.assertLessEqual(contrast(t['text-system'], t['bg']), contrast(t['text-dim'], t['bg']))

    def test_accent_purple_is_too_dark_for_text(self):
        # --accent (#7c3aed) is fine for fills, borders and focus rings; text uses
        # --user-color instead. The per-screen sheets are checked in their own tests.
        t = tokens()
        self.assertLess(contrast(t['accent'], t['bg']), 4.5)
        self.assertGreaterEqual(contrast(t['user-color'], t['bg-header']), 4.5)


def smallest_font(css):
    sizes = [float(v) for v in re.findall(r'font-size:\s*(\d+(?:\.\d+)?)px', strip_comments(css))]
    return min(sizes) if sizes else None


def uses_accent_as_text(css):
    return re.search(r'(?<![-\w])color:\s*var\(--accent\)', strip_comments(css)) is not None


def sheet(name):
    return (STATIC / name).read_text(encoding='utf-8')


class PreflightReadabilityTests(unittest.TestCase):
    def test_preflight_text_is_at_least_11px(self):
        self.assertGreaterEqual(smallest_font(sheet('preflight.css')), 11)

    def test_preflight_field_hints_are_at_least_12px(self):
        rule = re.search(r'\.preflight-page label small\s*\{([^}]*)\}', strip_comments(sheet('preflight.css'))).group(1)
        self.assertGreaterEqual(float(re.search(r'font-size:\s*(\d+)px', rule).group(1)), 12)

    def test_seat_state_stripe_outranks_the_base_seat_rule(self):
        # Regression: '.preflight-page fieldset.pf-seat' set border-left and beat the
        # '.pf-seat[data-state=...]' colours, so the ready/problem stripe never showed.
        css = strip_comments(sheet('preflight.css'))
        for state in ('ready', 'starting', 'failed'):
            with self.subTest(state=state):
                self.assertRegex(css, r'\.preflight-page fieldset\.pf-seat\[data-state="%s"\]' % state)

    def test_preflight_never_uses_accent_as_text(self):
        self.assertFalse(uses_accent_as_text(sheet('preflight.css')))


def rule(css, selector):
    css = strip_comments(css)
    return ' '.join(m.group(2) for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css) if m.group(1).strip() == selector)


def px(body):
    return float(re.search(r'font-size:\s*(\d+(?:\.\d+)?)px', body).group(1))


class HelpGuideReadabilityTests(unittest.TestCase):
    def test_guide_text_sizes(self):
        css = sheet('style.css')
        self.assertGreaterEqual(px(rule(css, '.hg-module-desc')), 13)
        self.assertGreaterEqual(px(rule(css, '.hg-module-tip')), 12)
        self.assertGreaterEqual(px(rule(css, '.hg-loc')), 11)

    def test_guide_text_uses_aa_tokens_without_extra_fading(self):
        # Tips were rgba(106,106,128,0.7) (about 2.2:1) and tags were faded with opacity.
        css = sheet('style.css')
        for selector in ('.hg-module-desc', '.hg-module-tip', '.hg-loc'):
            with self.subTest(selector=selector):
                body = rule(css, selector)
                self.assertRegex(body, r'color:\s*var\(--text(-dim)?\)')
                self.assertNotIn('opacity', body)


class SessionsReadabilityTests(unittest.TestCase):
    def test_sessions_text_is_at_least_11px(self):
        self.assertGreaterEqual(smallest_font(sheet('sessions.css')), 11)

    def test_sessions_never_use_accent_as_text(self):
        # Role names, phase numbers, the session-bar template and "View output" were
        # accent purple text (about 3.3:1).
        self.assertFalse(uses_accent_as_text(sheet('sessions.css')))

    def test_launcher_copy_is_plain_sentence_case(self):
        js = (STATIC / 'sessions.js').read_text(encoding='utf-8')
        self.assertNotIn('Start a Session<', js)
        self.assertNotIn(' -- Cast', js)


class SessionTemplateKeyboardTests(unittest.TestCase):
    def test_template_cards_are_reachable_and_operable_by_keyboard(self):
        # The cards were plain clickable divs: Tab skipped them, so a keyboard user
        # could not choose a template at all.
        js = (STATIC / 'sessions.js').read_text(encoding='utf-8')
        card = re.search(r'<div class="session-tmpl-card" onclick="showCastPreview[^>]*>', js).group(0)
        self.assertIn('tabindex="0"', card)
        self.assertIn('role="button"', card)
        self.assertRegex(card, r'onkeydown="[^"]*Enter')
        self.assertRegex(rule(sheet('sessions.css'), '.session-tmpl-card:focus-visible'), r'outline:')


class DocumentsReadabilityTests(unittest.TestCase):
    def test_placeholders_look_like_placeholders_and_still_meet_aa(self):
        # The Documents instruction box and the review-source box painted their
        # example text in full body colour, so an empty box looked filled in. They
        # used body colour only because the old dim token failed AA; it passes now.
        t = tokens()
        self.assertGreaterEqual(contrast(t['text-dim'], t['bg-input']), 4.5)
        for name, selector in (('artifacts.css', '.artifact-documents textarea::placeholder'),
                               ('sessions.css', '.document-input textarea::placeholder')):
            with self.subTest(selector=selector):
                self.assertRegex(rule(sheet(name), selector), r'color:\s*var\(--text-dim\)')

    def test_documents_heading_matches_preflight_hierarchy(self):
        self.assertRegex(rule(sheet('artifacts.css'), '.artifact-heading h2'), r'color:\s*var\(--text-muted\)')


class ManageChannelsReadabilityTests(unittest.TestCase):
    def test_dialog_header_does_not_inherit_the_app_header_bar(self):
        # style.css styles every <header> as the app bar (background, shadow, padding);
        # the dialog's own <header> picked that up and rendered as a boxed band.
        body = rule(sheet('channel-lifecycle.css'), '.channel-manager-header')
        self.assertRegex(body, r'background:\s*(none|transparent)')
        self.assertRegex(body, r'box-shadow:\s*none')


if __name__ == '__main__':
    unittest.main()
