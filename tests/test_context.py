import unittest

import time
from threading import Thread
from yakusoku.context import in_run_coro, set_run_coro


class ContextTest(unittest.TestCase):

    def test_separated(self):
        check1 = False
        check2 = False

        def _t1():
            nonlocal check1, check2

            time.sleep(.25)
            check1 = in_run_coro()
            time.sleep(.5)
            check2 = in_run_coro()

        def _t2():
            with set_run_coro():
                time.sleep(.5)

        t1 = Thread(target=_t1)
        t1.start()
        t2 = Thread(target=_t2)
        t2.start()

        t1.join()
        t2.join()

        self.assertFalse(check1)
        self.assertFalse(check2)

    def test_simple(self):
        self.assertFalse(in_run_coro())
        with set_run_coro():
            self.assertTrue(in_run_coro())
        self.assertFalse(in_run_coro())

    def test_error(self):
        self.assertFalse(in_run_coro())
        with self.assertRaises(Exception):
            with set_run_coro():
                raise Exception
        self.assertFalse(in_run_coro())

    def test_reentrant(self):
        self.assertFalse(in_run_coro())
        with set_run_coro():
            self.assertTrue(in_run_coro())
            with set_run_coro():
                self.assertTrue(in_run_coro())
            self.assertTrue(in_run_coro())
        self.assertFalse(in_run_coro())
