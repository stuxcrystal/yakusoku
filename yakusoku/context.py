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
from threading import local
_current_state = local()


class set_run_coro(object):
    """
    Internal Context-Manager:

    It sets whether Yakusoku is running inside a :class:`yakusoku.coroutines.Task`-block.

    This context-manager is reentrant.
    """

    def __enter__(self):
        self.before = in_run_coro()
        _current_state.in_run_coro = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        _current_state.in_run_coro = self.before


def in_run_coro():
    """
    Returns if the current code is run inside a :class:`yakusoku.coroutines.Task`

    :return: True if the current code runs inside a :class:`yakusoku.coroutines.Task`
    """
    return getattr(_current_state, 'in_run_coro', False)
