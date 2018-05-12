import unittest
from asyncio import get_event_loop, sleep as asleep
from yakusoku.operations import sleep, futurize
from yakusoku.typings import AbstractFuture


obj = object()


class AsyncIOTest(unittest.TestCase):

    def setUp(self):
        self.loop = get_event_loop()

    def test_aio_await_future(self):
        s = sleep(0.5, obj)

        x = self.loop.run_until_complete(s)

        self.assertTrue(s.done())
        self.assertFalse(s.cancelled())
        self.assertIsNone(s.exception())
        self.assertIs(s.result(), obj)
        self.assertIs(x, obj)

    def test_aio_await_futurized(self):
        @futurize
        async def sleeper():
            return await asleep(0.5, obj, loop=self.loop)

        x = self.loop.run_until_complete(sleeper())
        self.assertIs(x, obj)

    def test_aio_future_in_futurized(self):
        s = asleep(0.5, obj, loop=self.loop)

        @futurize
        async def sleeper():
            return await s

        async def runner():
            await s

        s: AbstractFuture[object] = sleeper()
        self.loop.create_task(runner())
        self.loop.run_until_complete(sleep(0.75))

        self.assertTrue(s.done())
        self.assertIs(s.result(), obj)
