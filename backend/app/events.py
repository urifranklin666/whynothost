"""SSE pub/sub for live job progress and activity feed."""
import asyncio
import json
import queue
import threading

_subs: list[queue.Queue] = []
_lock = threading.Lock()


def subscribe() -> queue.Queue:
    q = queue.Queue(maxsize=200)
    with _lock:
        _subs.append(q)
    return q


def unsubscribe(q: queue.Queue):
    with _lock:
        if q in _subs:
            _subs.remove(q)


def publish(event: dict):
    with _lock:
        subs = list(_subs)
    payload = json.dumps(event)
    for q in subs:
        try:
            q.put_nowait(payload)
        except queue.Full:
            pass


async def event_stream(q: queue.Queue):
    loop = asyncio.get_running_loop()
    try:
        yield f"data: {json.dumps({'type': 'hello'})}\n\n"
        while True:
            try:
                payload = await loop.run_in_executor(None, q.get, True, 15)
                yield f"data: {payload}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        unsubscribe(q)