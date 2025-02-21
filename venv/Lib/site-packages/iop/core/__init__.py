import asyncio

flows = []


def flow(f):
    if asyncio.iscoroutinefunction(f):
        flows.append((f, f.__module__.split('.')[-1] + "." + f.__name__))
    return f
