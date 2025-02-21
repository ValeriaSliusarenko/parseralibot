from iop.ipc.input import _Direct


async def direct(destination, message, wait=True):
    d = _Direct.get(destination)
    if wait:
        return await d.queue.put(message)
    return d.queue.put_nowait(message)
