import unittest
from asyncio import Future as AIOFuture
from concurrent.futures import Future

from yakusoku.future import copy, wrap_future
from yakusoku.coroutines import Task
from yakusoku.context import set_run_coro


obj = object()
exc = Exception()


class FutureTest(unittest.TestCase):

    def test_resolve_aio(self):
        fut = Future()
        self.assertIsInstance(next(iter(fut)), AIOFuture)

    def test_resolve_self(self):
        fut = Future()
        with set_run_coro():
            self.assertIsInstance(next(iter(fut)), Future)


class WrapTest(unittest.TestCase):

    def test_wrap_unscathed(self):
        fut = Future()
        self.assertIs(wrap_future(fut), fut)

    def test_wrap_coro(self):
        async def coro():
            pass
        self.assertIsInstance(wrap_future(coro()), Task)

    def test_wrap_aio(self):
        fut = AIOFuture()
        self.assertIsInstance(wrap_future(fut), Future)


class CopyTest(unittest.TestCase):

    def test_copy_success(self):
        source = Future()
        target = Future()

        copy(source, target)
        source.set_result(obj)

        self.assertFalse(target.cancelled())
        self.assertTrue(target.done())
        self.assertIsNone(target.exception())
        self.assertIs(target.result(), obj)

    def test_copy_exception(self):
        source = Future()
        target = Future()

        copy(source, target)
        source.set_exception(exc)

        self.assertFalse(target.cancelled())
        self.assertTrue(target.done())
        self.assertIs(target.exception(), exc)

    def test_copy_cancel(self):
        source = Future()
        target = Future()

        copy(source, target)
        source.cancel()

        self.assertTrue(target.cancel())
        self.assertTrue(target.done())

    def test_no_result_copy_success(self):
        source = Future()
        target = Future()

        copy(source, target, copy_result=False)
        source.set_result(obj)

        self.assertFalse(target.cancelled())
        self.assertFalse(target.done())

    def test_no_result_copy_exception(self):
        source = Future()
        target = Future()

        copy(source, target, copy_result=False)
        source.set_exception(exc)

        self.assertFalse(target.cancelled())
        self.assertFalse(target.done())

    def test_no_result_copy_cancel(self):
        source = Future()
        target = Future()

        copy(source, target, copy_result=False)
        source.cancel()

        self.assertTrue(target.cancel())
        self.assertTrue(target.done())

    def test_no_cancel_copy_success(self):
        source = Future()
        target = Future()

        copy(source, target, copy_cancel=False)
        source.set_result(obj)

        self.assertFalse(target.cancelled())
        self.assertTrue(target.done())
        self.assertIsNone(target.exception())
        self.assertIs(target.result(), obj)

    def test_no_cancel_copy_exception(self):
        source = Future()
        target = Future()

        copy(source, target, copy_cancel=False)
        source.set_exception(exc)

        self.assertFalse(target.cancelled())
        self.assertTrue(target.done())
        self.assertIs(target.exception(), exc)

    def test_no_cancel_copy_cancel(self):
        source = Future()
        target = Future()

        copy(source, target, copy_cancel=False)
        source.cancel()

        self.assertFalse(target.cancelled())
        self.assertFalse(target.done())