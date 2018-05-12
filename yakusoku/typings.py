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
from typing import Generic, TypeVar,  Any, NamedTuple
from typing import Callable, Optional, Coroutine, Union, Sequence

T = TypeVar("T")

try:
    from typeshed.concurrent.futures import Future
except ImportError:
    class AbstractFuture(Generic[T]):
        def done(self) -> bool: pass

        def cancel(self) -> None: pass

        def cancelled(self) -> bool: pass

        def set_result(self, result: T) -> None: pass

        def set_exception(self, exception: BaseException) -> None: pass

        def add_done_callback(self, cb: Callable[['AbstractFuture[T]'], None]) -> None: pass

        def exception(self) -> Optional[BaseException]: pass

        def result(self) -> T: pass

        def __await__(self): pass


AsyncFunction = Callable[..., AbstractFuture[T]]
PromiseCoroutine = Coroutine[T, None, AbstractFuture[Any]]
PromiseCoroutineFunction = Callable[..., PromiseCoroutine]
FutureOrCoroutine = Union[AbstractFuture[T], PromiseCoroutine]


class DoneAndNotDoneFutures(NamedTuple):
    done: Sequence[AbstractFuture[Any]]
    not_done: Sequence[AbstractFuture[Any]]