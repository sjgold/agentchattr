import sys
import unittest
from unittest.mock import patch

@unittest.skipUnless(sys.platform == 'win32', 'Windows console transport')
class InjectionReceiptTests(unittest.TestCase):
    def test_failed_text_write_never_reports_injection_success(self):
        import wrapper_windows as w
        with patch.object(w.kernel32, 'CreateFileW', return_value=7), patch.object(w.kernel32, 'CloseHandle') as close, patch.object(w.kernel32, 'WriteConsoleInputW', return_value=0):
            with self.assertRaises(OSError):
                w.inject('test', delay=0)
            close.assert_called_once_with(7)

    def test_failed_enter_write_never_reports_success(self):
        import wrapper_windows as w
        with patch.object(w.kernel32, 'WriteConsoleInputW', return_value=0):
            with self.assertRaises(OSError):
                w._write_key(7, '\r', True, vk=w.VK_RETURN)

    def test_unreadable_output_does_not_refresh_stale_activity(self):
        import wrapper_windows as w
        trigger = [True]
        with patch.object(w.kernel32, 'CreateFileW', return_value=7), \
             patch.object(w.kernel32, 'GetConsoleScreenBufferInfo', return_value=0), \
             patch.object(w.kernel32, 'CloseHandle') as close:
            check = w.get_activity_checker([None], trigger_flag=trigger)
            self.assertTrue(check())
            self.assertIsNone(check(), 'Unreadable console kept reporting active')
            self.assertEqual(close.call_count, 2)

    def test_partial_text_write_is_uncertain(self):
        import wrapper_windows as w
        def partial(handle, records, count, written):
            written._obj.value = count - 1
            return 1
        with patch.object(w.kernel32, 'CreateFileW', return_value=7), \
             patch.object(w.kernel32, 'CloseHandle'), \
             patch.object(w.kernel32, 'WriteConsoleInputW', side_effect=partial):
            with self.assertRaises(OSError):
                w.inject('test', delay=0)
