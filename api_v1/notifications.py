import queue
import threading

# Simple in-memory pub/sub for development. Keyed by user_id.
_QUEUES = {}
_LOCK = threading.Lock()

def subscribe(user_id):
    with _LOCK:
        q = _QUEUES.get(user_id)
        if q is None:
            q = queue.Queue()
            _QUEUES[user_id] = q
        return q

def publish(user_id, event: dict):
    with _LOCK:
        q = _QUEUES.get(user_id)
        if q:
            q.put(event)

def unsubscribe(user_id):
    with _LOCK:
        q = _QUEUES.pop(user_id, None)
        if q:
            try:
                q.put_nowait({'type': 'closed'})
            except Exception:
                pass