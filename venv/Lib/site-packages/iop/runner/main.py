import asyncio
import os
import sys
import logging
import argparse

from iop.core import flows
from iop.core.util import Stop


async def mont_flow(flow, module, penalty):
    logger = logging.getLogger(module)
    logger.info("started")
    while True:
        try:
            await flow()
        except Stop:
            break
        except Exception as ex:
            logger.error(ex, exc_info=True)
            await asyncio.sleep(penalty)
    logger.info("stopped")


async def monitor(routings, penalty):
    tasks = []
    for routing, module in routings:
        t = asyncio.get_event_loop().create_task(mont_flow(routing, module, penalty))
        tasks.append(t)
    await asyncio.wait(tasks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--penalty', type=float, default=3, help='Restart timeout after exception')
    parser.add_argument('scripts_location', default=os.getcwd(), nargs='?')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    root = logging.getLogger('iop')
    location = os.path.abspath(args.scripts_location)

    sys.path.append(os.path.dirname(os.path.abspath(location)))

    for script in os.listdir(location):
        path = os.path.join(location, script)
        if path.endswith('.py'):
            root.info('found %s', path)
            name = os.path.basename(location)
            getattr(__import__(name + '.' + script[:-3]), script[:-3])

    asyncio.get_event_loop().run_until_complete(monitor(flows, args.penalty))


if __name__ == '__main__':
    main()
