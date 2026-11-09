"""A cancellable wait for one expensive, read-only Designer request at a time."""

import asyncio
from functools import wraps
from inspect import signature
from threading import Thread


class ReadWorker:
    def __init__(self):
        self._busy = asyncio.Lock()

    def wrap(self, endpoint):
        @wraps(endpoint)
        async def read(*args, **kwargs):
            await self._busy.acquire()
            loop = asyncio.get_running_loop()
            result = loop.create_future()

            def deliver(value, error):
                self._busy.release()
                if not result.done():
                    if error is None:
                        result.set_result(value)
                    else:
                        result.set_exception(error)

            def work():
                try:
                    value, error = endpoint(*args, **kwargs), None
                except Exception as exc:
                    value, error = None, exc
                try:
                    loop.call_soon_threadsafe(deliver, value, error)
                except RuntimeError:
                    if not loop.is_closed():
                        raise

            # Cancellation drops the HTTP wait, but keeps the lane occupied
            # until the read finishes. No ledger or source writes run here.
            try:
                Thread(target=work, name="Designer read", daemon=True).start()
            except BaseException:
                self._busy.release()
                raise
            return await result

        read.__signature__ = signature(endpoint, eval_str=True)
        return read
