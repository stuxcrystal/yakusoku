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
import sys
from types import CoroutineType
from concurrent.futures import Future
from typing import Generator

from yakusoku.context import in_run_coro
from yakusoku.typings import FutureOrCoroutine, AbstractFuture, T

PY36: bool = sys.version_info >= (3, 6)


def _await_(self: AbstractFuture[T]) -> Generator[T, AbstractFuture[T], T]:
    if in_run_coro():
        return (yield self)

    from asyncio import wrap_future
    return (yield from wrap_future(self))


if not hasattr(Future, '__iter__'):
    Future.__iter__ = _await_
if PY36 and not hasattr(Future, '__await__'):
        Future.__await__ = _await_


def copy(source: AbstractFuture[T], target: AbstractFuture[T], *, copy_cancel=True, copy_result=True) -> None:
    """
    Link the state from the source future to the target future.

    :param source: The future to copy state from.
    :param target: The future to link the state to.
    :param copy_cancel: If True, it will cancel the future if the source future is cancelled.
    :param copy_result: If True, it will set the result of the source future to the target future.
    """
    def _handle(_):
        if source.cancelled():
            if not copy_cancel:
                return

            target.cancel()
            return

        if copy_result:
            if source.exception():
                target.set_exception(source.exception())
            else:
                target.set_result(source.result())
    source.add_done_callback(_handle)


def _copy_aiofuture(loop, *args, **kwargs):
    loop.call_soon_threadsafe(lambda: copy(*args, **kwargs))


def wrap_future(fut: FutureOrCoroutine[T]) -> AbstractFuture[T]:
    """
    Wraps a :class:`asyncio.futures.Future` or any Coroutine into a Future. It will do
    nothing to the :class:`concurrent.futures.Future`

    :param fut: The future to wrap.
    :return: A new future.
    """
    if isinstance(fut, CoroutineType):
        from yakusoku.coroutines import run_coroutine
        return run_coroutine(fut)

    if not isinstance(fut, Future):
        target: AbstractFuture[T] = Future()

        from asyncio import Future as AIOFuture
        if isinstance(fut, AIOFuture):
            if not hasattr(fut, '_loop') and not hasattr(fut, 'get_loop'):
                raise AttributeError("Cannot fetch loop of future.")

            loop = getattr(fut, 'get_loop', lambda: fut._loop)()
            _copy_aiofuture(loop, fut, target)
        else:
            copy(fut, target)
        return target

    fut: AbstractFuture[T]  # Tell this thing that this is still an AbstractFuture[T]
    return fut
