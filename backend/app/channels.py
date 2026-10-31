"""Channel-name validation. Same rules as the frontend's channels.js.

The backend can't trust the browser: anyone can open a WebSocket and send
whatever they like, so every list is re-checked here.
"""
import re

CHANNEL_RE = re.compile(r"[a-z0-9_]{4,25}")
MAX_STREAMS = 6


def clean_channels(raw):
    """Return a safe list: valid names only, lowercase, no duplicates, max 6."""
    if not isinstance(raw, list):
        return []
    out = []
    for c in raw:
        # Only strings: str(None) would become "none", a valid-looking channel.
        if not isinstance(c, str):
            continue
        c = c.strip().lower()
        # fullmatch, not match: match() would also accept "name\n" or "name!!!"
        # if the pattern isn't anchored at the end.
        if CHANNEL_RE.fullmatch(c) and c not in out:
            out.append(c)
    return out[:MAX_STREAMS]
