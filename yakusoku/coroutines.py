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
from concurrent.futures import Future, CancelledError
from typing import Any, Callable, NamedTuple, Optional

from yakusoku.future import wrap_future
from yakusoku.context import set_run_coro
from yakusoku.typings import PromiseCoroutine, AbstractFuture, T
from yakusoku.typings import FutureOrCoroutine


class ResultData(NamedTuple):
    result: Optional[Any]
    error: Optional[BaseException]


class Task(Future, AbstractFuture[T]):
    """
    A Task wraps a coroutine and runs it.

    During awaits, the coroutine may switch to another thread.
    """

    coro: PromiseCoroutine[T]

    def __init__(self, coro: PromiseCoroutine[T]):
        super(Task, self).__init__()
        self.coro = coro
        self.current_future: AbstractFuture[Any] = None
        self.add_done_callback(self._handle_cancel)

    def start(self):
        """
        Actually start running the coroutine.
        """
        self._send(None)

    def _handle_cancel(self, _):
        if self.current_future is None:
            return
        if not self.cancelled():
            return

        self.current_future.cancel()
        self.coro.close()

    def _handle_child_cancel(self, fut: AbstractFuture[Any]) -> None:
        if self.done():
            return

        if fut.cancelled():
            self._error(CancelledError())

    def _error(self, err):
        self._advance(self.coro.throw, err)

    def _send(self, data):
        self._advance(self.coro.send, data)

    def _advance(self, func: Callable[[Any], FutureOrCoroutine[Any]], data: Any):
        try:
            with set_run_coro():
                next_future = func(data)
        except StopIteration as e:
            result = ResultData(e.value, None)
        except BaseException as e:
            result = ResultData(None, e)
        else:
            return self._register_handlers(next_future)

        if result.error:
            self.set_exception(result.error)
        else:
            self.set_result(result.result)

    def _receive_call_completed(self, fut: AbstractFuture[Any]):
        if self.done():
            return

        if fut.exception():
            self._error(fut.exception())
        else:
            self._send(fut.result())

    def _register_handlers(self, future_or_coro: FutureOrCoroutine[Any]):
        self.current_future = wrap_future(future_or_coro)
        self.current_future.add_done_callback(self._handle_child_cancel)
        self.current_future.add_done_callback(self._receive_call_completed)


def run_coroutine(coro: PromiseCoroutine[T]) -> AbstractFuture[T]:
    """
    Runs the coroutine in the current thread.

    :param coro: The coroutine to run.
    :return: A future that will return once the coroutine finishes.
    """
    task = Task(coro)
    task.start()
    return task

