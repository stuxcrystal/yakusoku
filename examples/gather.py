import time, random
from yakusoku import futurize, gather

# Make the results reproducible
random.seed(0)


@futurize
async def slow_function(n):
    print(f"{n} > Working!")
    time.sleep(random.randint(1, 50) / 10)
    print(f"{n} > Done!")
    return n + 1


@futurize
async def concurrent_execute():
    futs = [slow_function(n) for n in range(5)]
    return await gather(*futs)


future = concurrent_execute()
assert future.result() == [1, 2, 3, 4, 5]