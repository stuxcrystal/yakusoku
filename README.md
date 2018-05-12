# Yakusoku
[![CircleCI](https://circleci.com/gh/stuxcrystal/yakusoku/tree/master.svg?style=svg)](https://circleci.com/gh/stuxcrystal/yakusoku/tree/master)

## Introduction

It is hard to support both AsyncIO and Threading. Sometimes you can't solely support AsyncIO.
This is where Yakusoku comes into play.

It makes Futures awaitable by wrapping them into AsyncIO-Futures and allows you to use Coroutines using concurrent.futures and returning
concurrent.futures that can be used both in AsyncIO and Threading-based libraries.

This allows you to use a single unified codebase for supporting both AsyncIO and Threading.

## Code Samples

```py
import time, random
from yakusoku import futurize, gather

random.seed(0)

@futurize
async def slow_function(n):
    print(f"{n} > Working!")
    time.sleep(random.randint(1, 50)/10)
    print(f"{n} > Done!")
    return n+1

@futurize
async def concurrent_execute():
    futs = [slow_function(n) for n in range(5)]
    print(futs)
    return await gather(*futs)
   
future = concurrent_execute()
assert future.result() == [1,2,3,4,5]
```

Should output:
```
0 > Working!
1 > Working!
2 > Working!
3 > Working!
4 > Working!
3 > Done!
4 > Done!
0 > Done!
2 > Done!
1 > Done!
```

## Installation

Install the current version via GIT and PIP.
```bash
$ pip install git+https://github.com/stuxcrystal/yakusoku
```