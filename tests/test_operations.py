import time
import unittest
from concurrent.futures import Future, TimeoutError, CancelledError
from concurrent.futures import FIRST_COMPLETED, FIRST_EXCEPTION

from yakusoku import operations

obj = object()
obj2 = object()
obj3 = object()
exc = Exception()


class FutureCreatorTest(unittest.TestCase):

    def test_resolve(self):
        fut = operations.resolve(obj)
        self.assertTrue(fut.done())
        self.assertFalse(fut.cancelled())
        self.assertIsNone(fut.exception())
        self.assertIs(fut.result(), obj)

    def test_reject(self):
        fut = operations.reject(exc)
        self.assertTrue(fut.done())
        self.assertFalse(fut.cancelled())
        self.assertIs(fut.exception(), exc)

    def test_sleep(self):
        start = time.time()
        fut = operations.sleep(1, obj)
        self.assertIs(fut.result(), obj)
        self.assertGreaterEqual(time.time() - start, 1)

    def test_sleep_cancel(self):
        fut, t = operations.sleep(2, obj, also_return_timer=True)
        time.sleep(1)
        fut.cancel()
        self.assertTrue(t.finished.is_set())

    def test_sleep_0(self):
        fut, t = operations.sleep(0, obj, also_return_timer=True)
        self.assertIsNone(t)
        self.assertIsInstance(fut, operations._SleepForceThreadSwitch)
        self.assertIs(fut.result(), obj)


class DecoratorTest(unittest.TestCase):

    def test_futurize(self):
        @operations.futurize
        async def _func(a, *, c):
            if a != 4 and c != 8: raise Exception()
            await operations.sleep(0.25)
            return a
        fut = _func(4, c=8)
        self.assertIsInstance(fut, Future)
        self.assertEqual(fut.result(), 4)

    def test_futurize_exception(self):
        @operations.futurize
        async def _func(a, *, c):
            if a != 4 and c != 8:
                raise exc
        fut = _func(5, c=9)
        self.assertIsInstance(fut, Future)
        self.assertIs(exc, fut.exception())

    def test_synchronize(self):
        @operations.synchronize
        async def _func(a, *, c):
            if a != 4 and c != 8: raise Exception()
            await operations.sleep(0.25)
            return a
        self.assertEqual(_func(4,c=8), 4)

    def test_synchronize_exception(self):
        @operations.synchronize
        async def _func(a, *, c):
            if a != 4 and c != 8:
                raise exc
        with self.assertRaises(Exception):
            _func(5, c=9)


class WrapperTest(unittest.TestCase):

    def test_waitfor_endless(self):
        fut = operations.wait_for(operations.sleep(0.5, obj), 0)
        self.assertIs(fut.result(), obj)

    def test_waitfor_within_time(self):
        fut = operations.wait_for(operations.sleep(0.5, obj), 1)
        self.assertIs(fut.result(), obj)

    def test_waitfor_failed_within_time(self):
        @operations.futurize
        async def _func():
            await operations.sleep(.5)
            raise exc
        fut = operations.wait_for(_func(), 1)
        self.assertIs(fut.exception(), exc)

    def test_waitfor_timed_out(self):
        s = operations.sleep(0.5, obj)
        fut = operations.wait_for(s, 0.25)
        self.assertIsInstance(fut.exception(), TimeoutError)
        self.assertTrue(s.cancelled())

    def test_shield_success(self):
        s = operations.sleep(0.5, obj)
        fut = operations.shield(s)
        self.assertIs(fut.result(), obj)

    def test_shield_failure(self):
        @operations.futurize
        async def _func():
            raise exc
        fut = operations.shield(_func())
        self.assertIs(fut.exception(), exc)

    def test_shield_not_cancelled(self):
        s = operations.sleep(0.5, obj)
        fut = operations.shield(s)
        fut.cancel()
        self.assertFalse(s.cancelled())
        self.assertTrue(fut.cancelled())
        s.cancel()

    def test_shield_child_cancel_bubbles(self):
        s = operations.sleep(0.5, obj)
        fut = operations.shield(s)
        s.cancel()
        self.assertFalse(fut.cancelled())
        self.assertIsInstance(fut.exception(), CancelledError)


class WaitTest(unittest.TestCase):

    def test_wait_all_completed(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        result = operations.wait([s1, s2, s3]).result()
        self.assertEqual(len(result.done), 3)
        self.assertEqual(len(result.not_done), 0)

    def test_wait_first_complete(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        result = operations.wait([s1, s2, s3], return_when=FIRST_COMPLETED).result()
        self.assertEqual(len(result.done), 1)
        self.assertEqual(len(result.not_done), 2)

        self.assertTrue(s1.done())
        self.assertFalse(s2.done())
        self.assertFalse(s3.done())

        s2.cancel()
        s3.cancel()

    def test_wait_first_complete_with_error(self):
        @operations.futurize
        async def _func():
            await operations.sleep(.25)
            raise exc
        s1 = _func()
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        result = operations.wait([s1, s2, s3], return_when=FIRST_COMPLETED).result()
        self.assertEqual(len(result.done), 1)
        self.assertEqual(len(result.not_done), 2)

        self.assertTrue(s1.done())
        self.assertFalse(s2.done())
        self.assertFalse(s3.done())

        s2.cancel()
        s3.cancel()

    def test_wait_first_exception_no_error(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        result = operations.wait([s1, s2, s3], return_when=FIRST_EXCEPTION).result()
        self.assertEqual(len(result.done), 3)
        self.assertEqual(len(result.not_done), 0)

        self.assertTrue(s1.done())
        self.assertTrue(s2.done())
        self.assertTrue(s3.done())

    def test_wait_first_exception(self):
        @operations.futurize
        async def _func():
            await operations.sleep(.5)
            raise exc

        s1 = operations.sleep(0.25, obj)
        s2 = _func()
        s3 = operations.sleep(0.75, obj3)

        result = operations.wait([s1, s2, s3], return_when=FIRST_EXCEPTION).result()
        self.assertEqual(len(result.done), 2)
        self.assertEqual(len(result.not_done), 1)

        self.assertTrue(s1.done())
        self.assertTrue(s2.done())
        self.assertFalse(s3.done())

        s3.cancel()

    def test_wait_shield_parent_cancel(self):
        s1 = operations.sleep(0.5, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        w = operations.wait([s1, s2, s3])
        time.sleep(0.25)
        w.cancel()

        self.assertFalse(s1.cancelled())
        self.assertFalse(s2.cancelled())
        self.assertFalse(s3.cancelled())
        s1.cancel()
        s2.cancel()
        s3.cancel()

    def test_wait_graceful_child_cancel(self):
        s1 = operations.sleep(0.5, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        w = operations.wait([s1, s2, s3])
        time.sleep(0.25)
        s1.cancel()

        self.assertFalse(w.cancelled())
        self.assertTrue(s1.cancelled())
        self.assertFalse(s2.cancelled())
        self.assertFalse(s3.cancelled())

        done, not_done = w.result()
        self.assertEqual(len(done), 3)
        self.assertEqual(len(not_done), 0)

        self.assertTrue(any(isinstance(d.exception(), CancelledError) for d in done))

    def test_wait_graceful_child_cancel_exception(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        w = operations.wait([s1, s2, s3], return_when=FIRST_EXCEPTION)
        time.sleep(0.5)
        s2.cancel()

        self.assertFalse(w.cancelled())
        self.assertFalse(s1.cancelled())
        self.assertTrue(s2.cancelled())
        self.assertFalse(s3.cancelled())

        done, not_done = w.result()
        self.assertEqual(len(done), 2)
        self.assertEqual(len(not_done), 1)

        self.assertTrue(any(isinstance(d.exception(), CancelledError) for d in done))

    def test_wait_timeout_completed(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        result = operations.wait([s1, s2, s3], timeout=1).result()
        self.assertEqual(len(result.done), 3)
        self.assertEqual(len(result.not_done), 0)

    def test_wait_timeout_premature(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        result = operations.wait([s1, s2, s3], timeout=0.5).result()
        self.assertEqual(len(result.done), 1)
        self.assertEqual(len(result.not_done), 2)


class GatherTest(unittest.TestCase):

    def test_gather_simple(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        r1, r2, r3 = operations.gather(s1, s2, s3).result()
        self.assertIs(r1, obj)
        self.assertIs(r2, obj2)
        self.assertIs(r3, obj3)

    def test_gather_error(self):
        s1 = operations.sleep(0.25, obj)
        @operations.futurize
        def _s2():
            yield operations.sleep(0.5)
            raise exc
        s2 = _s2()
        s3 = operations.sleep(0.75, obj3)

        try:
            operations.gather(s1, s2, s3).result()
        except Exception as e:
            self.assertIs(e, exc)
        else:
            self.fail("Did not trigger exception")

        self.assertTrue(s1.done())
        self.assertFalse(s1.cancelled())
        self.assertTrue(s2.done())
        self.assertFalse(s2.cancelled())
        self.assertFalse(s3.done())
        self.assertFalse(s3.cancelled())

    def test_gather_error_return(self):
        s1 = operations.sleep(0.25, obj)
        @operations.futurize
        def _s2():
            yield operations.sleep(0.5)
            raise exc
        s2 = _s2()
        s3 = operations.sleep(0.75, obj3)

        r1, r2, r3 = operations.gather(s1, s2, s3, return_exceptions=True).result()
        self.assertIs(r1, obj)
        self.assertIs(r2, exc)
        self.assertIs(r3, obj3)

    def test_gather_return(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.5, obj2)
        s3 = operations.sleep(0.75, obj3)

        r1, r2, r3 = operations.gather(s1, s2, s3, return_exceptions=True).result()
        self.assertIs(r1, obj)
        self.assertIs(r2, obj2)
        self.assertIs(r3, obj3)

    def test_gather_propagate_cancel(self):
        s1 = operations.sleep(0.5, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        g = operations.gather(s1, s2, s3)
        time.sleep(0.25)
        g.cancel()
        self.assertTrue(s1.cancelled())
        self.assertTrue(s2.cancelled())
        self.assertTrue(s3.cancelled())

    def test_gather_propagate_partial_complete(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        g = operations.gather(s1, s2, s3)
        time.sleep(0.5)
        g.cancel()
        self.assertFalse(s1.cancelled())
        self.assertIs(s1.result(), obj)
        self.assertTrue(s2.cancelled())
        self.assertTrue(s3.cancelled())

    def test_gather_shield_child_cancel(self):
        s1 = operations.sleep(0.5, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        g = operations.gather(s1, s2, s3)
        time.sleep(0.25)
        s1.cancel()
        self.assertFalse(g.cancelled())
        self.assertTrue(s1.cancelled())
        self.assertFalse(s2.cancelled())
        self.assertFalse(s3.cancelled())

        try:
            g.result()
        except CancelledError:
            pass
        except:
            self.fail("Incorrect error")

    def test_gather_shield_child_cancel_return(self):
        s1 = operations.sleep(0.5, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        g = operations.gather(s1, s2, s3, return_exceptions=True)
        time.sleep(0.25)
        s1.cancel()

        self.assertFalse(g.cancelled())
        self.assertTrue(s1.cancelled())
        self.assertFalse(s2.cancelled())
        self.assertFalse(s3.cancelled())

        r1, r2, r3 = g.result()
        self.assertIsInstance(r1, CancelledError)
        self.assertIs(r2, obj2)
        self.assertIs(r3, obj3)

    def test_gather_cancel_fater_first_completion(self):
        s1 = operations.sleep(0.25, obj)
        s2 = operations.sleep(0.75, obj2)
        s3 = operations.sleep(1, obj3)

        g = operations.gather(s1, s2, s3, return_exceptions=True)
        time.sleep(0.5)
        s2.cancel()

        self.assertFalse(g.cancelled())
        self.assertFalse(s1.cancelled())
        self.assertTrue(s2.cancelled())
        self.assertFalse(s3.cancelled())

        r1, r2, r3 = g.result()
        self.assertIs(r1, obj)
        self.assertIsInstance(r2, CancelledError)
        self.assertIs(r3, obj3)