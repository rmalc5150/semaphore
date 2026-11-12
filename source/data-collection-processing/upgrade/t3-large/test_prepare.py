import unittest
from unittest.mock import patch
import prepare

class Tests(unittest.TestCase):
    def test_limits_require_large_and_real_capacity(self):
        self.assertFalse(prepare.hardware_ok('t3.medium',8*prepare.GIB))
        self.assertFalse(prepare.hardware_ok('t3.large',4*prepare.GIB))
        self.assertTrue(prepare.hardware_ok('t3.large',int(7.7*prepare.GIB)))
    def test_apply_refuses_small_host_before_changes(self):
        with patch.object(prepare,'hardware',return_value=('t3.medium',4*prepare.GIB)), patch.object(prepare,'install') as install:
            with self.assertRaisesRegex(RuntimeError,'Requires t3.large'): prepare.apply()
            install.assert_not_called()
if __name__=='__main__': unittest.main()
