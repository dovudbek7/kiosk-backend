import queue
import threading
import time as _time

# Simple in-memory pub/sub for development. Keyed by user_id.
_QUEUES = {}
_LOCK = threading.Lock()

# ── Ring response store (ringId → response dict) ──
# Entries expire after 5 minutes.
_RING_RESPONSES = {}
_RING_LOCK = threading.Lock()
_RING_TTL = 300  # seconds

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


# ── Ring response helpers ──

def set_ring_response(ring_id: str, response: str, responder_name: str = ''):
    """Store an employee's response to a ring so the kiosk can poll for it."""
    with _RING_LOCK:
        _RING_RESPONSES[ring_id] = {
            'response': response,
            'responderName': responder_name,
            'timestamp': _time.time(),
        }
        # Garbage-collect expired entries
        now = _time.time()
        expired = [k for k, v in _RING_RESPONSES.items() if now - v['timestamp'] > _RING_TTL]
        for k in expired:
            del _RING_RESPONSES[k]


def get_ring_response(ring_id: str):
    """Return the response dict for a ring_id, or None if not yet responded."""
    with _RING_LOCK:
        entry = _RING_RESPONSES.get(ring_id)
        if entry and (_time.time() - entry['timestamp'] <= _RING_TTL):
            return entry
        return None