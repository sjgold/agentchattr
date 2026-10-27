"""CLI template default_model: used only when a seat leaves the model blank."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_seats import SeatError, SeatStore, validate_seat  # noqa: E402
from cli_seats import build_cli_args  # noqa: E402


def seat(**changes):
    values = dict(id='writer', name='Writer', adapter='cli', provider='fake', model=None,
                  reasoning=None, secret_ref='', launch_profile='standard')
    values.update(changes)
    return values


TEMPLATE = {'command': sys.executable, 'cwd': '.', 'mcp_inject': 'env', 'mcp_env_var': 'FAKE_SETTINGS',
            'cli_model_args': ['--model', '{model}'], 'models': ['m-high', 'm-medium', 'm-low'],
            'default_model': 'm-medium'}


class DefaultModelTests(unittest.TestCase):
    def test_blank_seat_model_uses_the_template_default(self):
        self.assertEqual(build_cli_args(seat(), TEMPLATE), ['--model', 'm-medium'])

    def test_explicit_seat_model_always_wins(self):
        self.assertEqual(build_cli_args(seat(model='m-high'), TEMPLATE), ['--model', 'm-high'])

    def test_templates_without_a_default_are_unchanged(self):
        template = {k: v for k, v in TEMPLATE.items() if k != 'default_model'}
        self.assertEqual(build_cli_args(seat(), template), [])
        self.assertEqual(build_cli_args(seat(model='x'), template), ['--model', 'x'])

    def test_default_requires_a_model_argument_contract(self):
        template = {k: v for k, v in TEMPLATE.items() if k != 'cli_model_args'}
        with self.assertRaises(SeatError):
            validate_seat(seat(), {'fake': template})

    def test_unsafe_defaults_are_rejected_at_validation(self):
        for bad in ('', '   ', '-rf', 'a\nb', 7, ['m']):
            with self.subTest(default=bad), self.assertRaises(SeatError):
                validate_seat(seat(), {'fake': {**TEMPLATE, 'default_model': bad}})

    def test_describe_providers_reports_the_cli_default(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = {k: v for k, v in TEMPLATE.items() if k != 'default_model'}
            providers = {p['id']: p for p in SeatStore(directory, {'fake': TEMPLATE, 'plain': plain}).describe_providers()}
        self.assertEqual(providers['fake']['default_model'], 'm-medium')
        self.assertIsNone(providers['plain']['default_model'])
        self.assertEqual(providers['fake']['models'], ['m-high', 'm-medium', 'm-low'])


if __name__ == '__main__':
    unittest.main()
