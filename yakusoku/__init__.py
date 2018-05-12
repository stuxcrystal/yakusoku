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
"""
Yakusoku allows you to provide a unified API for Threading and
AsyncIO based systems.
"""
from yakusoku.operations import resolve, reject, sleep
from yakusoku.operations import futurize, synchronize
from yakusoku.operations import wait_for, shield
from yakusoku.operations import wait, gather
from yakusoku.coroutines import run_coroutine


__all__ = [
    "resolve", "reject", "sleep",
    "futurize", "synchronize",
    "wait_for", "shield",
    "run_coroutine"
]
