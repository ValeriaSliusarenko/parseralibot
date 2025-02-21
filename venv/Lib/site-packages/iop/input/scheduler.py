import asyncio
import time

from iop.core.message import Message


async def timer(interval: int) -> Message:
    await asyncio.sleep(interval)
    return Message(time.time())
