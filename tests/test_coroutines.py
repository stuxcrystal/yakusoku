import time
import unittest

from threading import Thread
from concurrent.futures import CancelledError, Future

from yakusoku.coroutines import run_coroutine
from yakusoku.operations import resolve, reject, sleep


obj = object()
err = Exception()


class CoroutineTest(unittest.TestCase):

    def test_call_other_coro(self):
        async def coro2():
            return await resolve(obj)

        async def coro():
            return await coro2()
        fut = run_coroutine(coro())
        self.assertIs(fut.result(), obj)

    def test_coro_resolve_exact(self):
        async def _func():
            f = await resolve(obj)
            return f
        fut = run_coroutine(_func())
        self.assertIs(fut.result(), obj)

    def test_coro_reject_exact(self):
        async def _func():
            await reject(err)
        fut = run_coroutine(_func())
        self.assertIs(fut.exception(), err)

    def test_coro_wrap_raise(self):
        async def _func():
            raise err
        fut = run_coroutine(_func())
        self.assertIs(fut.exception(), err)

    def test_coro_child_cancel_bubble(self):
        timeout = sleep(2)
        err = None
        async def _func():
            nonlocal err
            try:
                await timeout
            except CancelledError as e:
                err = e

        fut = run_coroutine(_func())
        time.sleep(.5)
        timeout.cancel()
        fut.result()
        self.assertIsInstance(err, CancelledError)

    def test_coro_parent_cancel_exit(self):
        timeout = sleep(2)
        err = None
        async def _func():
            nonlocal err
            try:
                await timeout
            except GeneratorExit as e:
                err = e

        fut = run_coroutine(_func())
        time.sleep(.5)
        fut.cancel()
        self.assertTrue(timeout.cancelled())
        self.assertIsInstance(err, GeneratorExit)

    def test_noncancellable_child_parent_cancel(self):
        def _fake_timeout(t):
            def _tg(f):
                time.sleep(t)
                f()
            fut = Future()
            Thread(target=lambda:_tg(lambda:fut.set_result(None))).start()
            return fut
        timeout = _fake_timeout(2)
        err = None
        async def _func():
            nonlocal err
            try:
                await timeout
            except GeneratorExit as e:
                err = e

        fut = run_coroutine(_func())
        time.sleep(.5)
        fut.cancel()
        self.assertTrue(timeout.cancelled())
        self.assertIsInstance(err, GeneratorExit)