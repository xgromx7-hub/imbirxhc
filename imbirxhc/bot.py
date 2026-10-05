import asyncio
import logging
import signal

import portalocker

from imbirxhc.config import Config
from imbirxhc.client import ImbirBot


async def run(config):
    bot = ImbirBot(config)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
    task = asyncio.create_task(bot.start(config.token, reconnect=True))
    stopper = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait([task, stopper], return_when=asyncio.FIRST_COMPLETED)
        if task in done:
            await task  # Fatal login/config errors exit nonzero for supervisor.
    finally:
        stopper.cancel()
        await bot.close()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, stopper, return_exceptions=True)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    config = Config.load()
    # Kernel releases this lock after crash; no stale PID-file issue.
    with portalocker.Lock(str(config.data / 'process.lock'), timeout=0):
        asyncio.run(run(config))


if __name__ == '__main__':
    main()
