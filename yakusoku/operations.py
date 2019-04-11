# -*- encoding: utf-8 -*-
#
# Copyright 2018 StuxCrystal <stuxcrystal@encode.moe>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import functools
from numbers import Real
from types import coroutine
from typing import Callable, Sequence, Tuple, overload, Union, Optional, cast
from threading import Timer, Thread, Lock
from concurrent.futures import TimeoutError, CancelledError
from concurrent.futures import ALL_COMPLETED, FIRST_EXCEPTION, FIRST_COMPLETED

from yakusoku.future import Future
from yakusoku.typings import AwaitableFuture, T
from yakusoku.typings import PromiseCoroutineFunction, FutureOrCoroutine
from yakusoku.typings import DoneAndNotDoneFutures

from yakusoku.coroutines import run_coroutine
from yakusoku.future import wrap_future, copy

__all__ = [
    "resolve", "reject",
    "futurize", "synchronize",
    "sleep",
    "shield", "wait_for"
]


def resolve(data: T = None) -> AwaitableFuture[T]:
    """
    Returns a future that is already finished with the given value.

    :param data: The value to assign
    :return: A future resulting in the data.
    """
    fut: AwaitableFuture[T] = Future()
    fut.set_result(data)
    return fut


def reject(exc: BaseException) -> AwaitableFuture[None]:
    """
    Returns a future that has failed with the given exception.

    :param exc: The exception to throw.
    :return: A future that throws the given exception.
    """
    fut: AwaitableFuture[None] = Future()
    fut.set_exception(exc)
    return fut

@overload
def futurize(func=None, *, spawn: bool=True) -> Callable[[None, bool], Callable[..., AwaitableFuture[T]]]: pass
@overload
def futurize(func: PromiseCoroutineFunction[T], *, spawn: bool=True) -> Callable[..., AwaitableFuture[T]]: pass
def futurize(
        func: Optional[PromiseCoroutineFunction[T]]=None, *, spawn=True
) -> Union[
        Callable[[None, bool], Callable[..., AwaitableFuture[T]]],
        Callable[..., AwaitableFuture[T]]
]:
    """
    Makes this coroutine a function that returns a Future instead of a
    coroutine-object.

    :param func:  The function to convert.
    :param spawn: If true, this function will spawn a new thread to execute the functions.
    :return: The function that returns a future.
    """
    if func is None:
        def _decorator(func: PromiseCoroutineFunction[T]) -> Callable[..., AwaitableFuture[T]]:
            return cast(Callable[..., AwaitableFuture[T]], futurize(func, spawn=spawn))
        return _decorator

    func = coroutine(func)

    async def wrapped(coro):
        if spawn:
            await sleep(0)
        return await coro

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        c = func(*args, **kwargs)
        return run_coroutine(wrapped(c))

    return _wrapper


def synchronize(func: PromiseCoroutineFunction[T]) -> Callable[..., T]:
    """
    Will make the coroutine a synchronous function.

    :param func: The synchronous function.
    :return: The synchronous version of the function.
    """
    func = futurize(func, spawn=False)

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        return func(*args, **kwargs).result()

    return _wrapper


class _SleepForceThreadSwitch(Future):

    def add_done_callback(self, fn):
        def _fn(_):
            Thread(target=fn, args=(self,)).start()
        return super(_SleepForceThreadSwitch, self).add_done_callback(_fn)

@overload
def sleep(delay: Real, result: T = None, *, also_return_timer: bool=True) -> Tuple[AwaitableFuture[T], Timer]: pass
@overload
def sleep(delay: Real, result: T = None, *, also_return_timer: bool=False) -> AwaitableFuture[T]: pass
def sleep(
        delay: Real,
        result: T = None,
        *,
        also_return_timer: bool=False
) -> Union[Tuple[AwaitableFuture[T], Timer], AwaitableFuture[T]]:
    """
    Returns a future that resolves after the given amount of time.

    :param delay: The delay to wait. If zero, the future will just resolve in a new thread.
    :param result: The value that the future will resolve with.
    :param also_return_timer: Internal, do not use.
    :return: A future that resolves with the given result after a set amount of time.
    """
    def _expire(_=None):
        if fut.cancelled():
            t.cancel()

    if delay == 0:
        fut: AwaitableFuture[T] = _SleepForceThreadSwitch()
        fut.set_result(result)
        t = None
    else:
        fut: AwaitableFuture[T] = Future()
        fut.add_done_callback(_expire)
        t = Timer(float(delay), lambda: fut.set_result(result))
        t.start()

    if also_return_timer:
        return fut, t

    return fut


def wait_for(fut: FutureOrCoroutine[T], timeout: float) -> AwaitableFuture[T]:
    """
    Returns a future that will be cancelled after timeout seconds have
    passed.

    If timeout is zero, it will not timeout.

    :param fut:     The future to wait for.
    :param timeout: When should the execution be cancelled.
    :return: A new future that will be cancelled after the given timeout.
    """

    def _expire(_):
        """Cancel future on expiry; fire a timeout exception."""
        if not fut.done():
            fut.cancel()
            result.set_exception(TimeoutError())

    def _complete(_):
        """Cancel the timeouter when future within the timeout."""
        timeouter.cancel()

    result: AwaitableFuture[T] = Future()
    timeouter = sleep(timeout) if timeout else Future()
    fut = wrap_future(fut)

    timeouter.add_done_callback(_expire)
    result.add_done_callback(_complete)

    copy(fut, result, copy_cancel=False)
    return result


def shield(fut: FutureOrCoroutine[T]) -> AwaitableFuture[T]:
    """
    Shields a future from being cancelled by the parent.

    If the future is cancelled that is passed to this function, the
    future returned by this function will reject with a
    :class:`concurrent.futures.CancelledError`.

    :param fut: The future to shield.
    :return: A future that will not propagate its cancellation to the parent.
    """
    def _bubble_child(_):
        if target.cancelled():
            pass
        if fut.cancelled():
            target.set_exception(CancelledError())

    target: AwaitableFuture[T] = Future()
    copy(fut, wrap_future(target), copy_cancel=False)
    fut.add_done_callback(_bubble_child)
    return target


def wait(
        futs_or_coros: Sequence[FutureOrCoroutine[T]],
        timeout: Real = 0,
        return_when=ALL_COMPLETED
) -> AwaitableFuture[DoneAndNotDoneFutures]:
    """
    Waits for multiple futures.

    If `return_when` is ALL_COMPLETED it will wait until
    all passed futures have finished.

    If `return_when` is FIRST_COMPLETED it will wait until
    the first future resolves or rejects.

    If `return_when` is FIRST_EXCEPTION it will wait until
    the first future rejects and otherwise wait until all
    futures finished.

    If `timeout` is greater than 0, it will wait maximally
    for the given amount of time. Then it will resolve.

    In all cases a named-tuple with `done` containing all futures
    that have finished until the wait-future resolved and `not_done`
    with all futures that still run.

    :param futs_or_coros: The futures and/or coroutines to wait for.
    :param timeout:       The maximal time to wait for them.
    :param return_when:   When to return.
    :return: A future that will resolve-conditions have passed.
    """
    cond = Future()
    result = Future()
    finished = []
    running = list(map(wrap_future, futs_or_coros))
    lock = Lock()

    def _single_finishes(fut: AwaitableFuture[T]):
        if cond.done():
            return

        with lock:
            running.remove(fut)
            if fut.cancelled():
                fut = reject(CancelledError())
            finished.append(fut)

            empty = not running

            if return_when == FIRST_COMPLETED:
                cond.set_result(None)
                return

            if fut.exception() and return_when == FIRST_EXCEPTION:
                cond.set_result(None)
                return

            if empty:
                cond.set_result(None)

    for f in running[:]:
        f.add_done_callback(_single_finishes)

    def _timeout(_):
        if result.done():
            return
        cond.set_result(None)

    def _completes(_):
        if result.cancelled():
            return
        result.set_result(DoneAndNotDoneFutures(done=finished, not_done=running))

    timeouter = sleep(timeout, None) if timeout else Future()
    timeouter.add_done_callback(_timeout)
    copy(result, timeouter, copy_result=False)

    # Copy cancel state to cond.
    copy(result, cond, copy_result=False)
    cond.add_done_callback(_completes)


    return result


def gather(
        *futs_or_coros: FutureOrCoroutine[T],
        return_exceptions: bool = False
) -> AwaitableFuture[Sequence[T]]:
    """
    Gathers the results of the exceptions.

    :param futs_or_coros:      The futures whose results are to be gathered.
    :param return_exceptions:  If false, if a future rejects, the gather future will reject.
    :return: A future that gathers the results.
    """
    if return_exceptions:
        wait_mode = ALL_COMPLETED
    else:
        wait_mode = FIRST_EXCEPTION

    futs = list(map(wrap_future, futs_or_coros))

    def _propagate_cancel(_):
        if not result.cancelled():
            return

        for fut in futs:
            if fut.done():
                continue
            fut.cancel()

    def _gather_result(_):
        result_list = []
        for fut in futs:
            if fut.cancelled():
                if return_exceptions:
                    result_list.append(CancelledError())
                    continue

                result.set_exception(CancelledError())
                break

            if fut.exception() is None:
                result_list.append(fut.result())
                continue

            if return_exceptions:
                result_list.append(fut.exception())
                continue

            result.set_exception(fut.exception())
            break
        result.set_result(result_list)

    result: AwaitableFuture[Sequence[T]] = Future()
    result.add_done_callback(_propagate_cancel)

    waiter: AwaitableFuture[DoneAndNotDoneFutures] = wait(futs, return_when=wait_mode)
    waiter.add_done_callback(_gather_result)

    copy(result, waiter, copy_result=False)
    return result
