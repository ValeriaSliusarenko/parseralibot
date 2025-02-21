import asyncio


class _Direct:
    items = {}

    def __init__(self):
        self.queue = asyncio.Queue(1)

    @staticmethod
    def get(name):
        d = _Direct.items.get(name, None)
        if d is None:
            d = _Direct()
            _Direct.items[name] = d
        return d


async def direct(destination):
    d = _Direct.get(destination)
    return await d.queue.get()
