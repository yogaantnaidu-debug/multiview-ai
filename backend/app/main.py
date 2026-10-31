"""FastAPI app: one Twitch chat connection, many browser WebSockets.

Data flow:
  Twitch IRC -> on_chat_message -> StreamStats + ChatBuffer (per channel)
  tick_loop (every 1 s) -> stats to each browser; every 5 s the Director may move focus
  pulse_loop (every 2 s) -> at most one LLM call for the most overdue stream
  browser -> /ws: {"type": "set_channels"} / {"type": "manual_focus"}

All state lives in these module-level dicts (in memory). A restart forgets
everything, which is fine here: chat rates rebuild within minutes.
"""
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Load backend/.env before anything reads os.environ. Real environment
# variables (e.g. set on Render) win over the file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .channels import clean_channels
from .director import Director
from .hype import StreamStats
from .irc import TwitchChat
from .pulse import ChatBuffer, PulseEngine

TICK = 1.0
DIRECTOR_EVERY = 5  # ticks, i.e. the Director re-checks every 5 s
PULSE_CHECK = 2.0   # seconds between "is any stream due a Chat Pulse?" checks


class Client:
    """One open browser tab: its channel list and its own Director."""

    def __init__(self):
        self.channels = []
        self.director = Director()


stats = {}    # channel -> StreamStats, shared by every tab watching that channel
buffers = {}  # channel -> ChatBuffer (recent text for Chat Pulse)
clients = {}  # WebSocket -> Client


def on_chat_message(channel, user, text):
    s = stats.get(channel)
    if s:
        s.add_message(time.monotonic())
    b = buffers.get(channel)
    if b:
        b.add(text)  # usernames are dropped: the summary doesn't need them


chat = TwitchChat(on_chat_message)
pulse = PulseEngine.from_env()


async def sync_channels():
    """Join the union of what every tab wants; forget channels nobody watches."""
    wanted = {c for cl in clients.values() for c in cl.channels}
    now = time.monotonic()
    for c in wanted - stats.keys():
        stats[c] = StreamStats(now)
        buffers[c] = ChatBuffer()
    for c in stats.keys() - wanted:
        del stats[c]
        buffers.pop(c, None)
    await chat.set_channels(wanted)


def stats_message(client, now):
    streams = []
    for c in client.channels:
        s = stats.get(c)
        if s is None:
            continue
        b = buffers.get(c)
        pulse_out = None
        if b and b.pulse:
            pulse_out = {**b.pulse, "age": round(now - b.pulse_at)}
        streams.append({
            "channel": c,
            "rate": round(s.rate(now), 2),
            "baseline": None if s.baseline is None else round(s.baseline, 2),
            "hype": round(s.hype(now), 2),
            "warming_up": s.warming_up(now),
            "pulse": pulse_out,
        })
    ai_status = pulse.status(now)
    return {
        "type": "stats",
        "chat_connected": chat.connected,
        "lock_remaining": round(client.director.lock_remaining(now)),
        "ai": {
            "status": ai_status,
            "reason": pulse.pause_reason if ai_status == "paused" else None,
        },
        "streams": streams,
    }


async def tick_loop():
    tick = 0
    while True:
        await asyncio.sleep(TICK)
        tick += 1
        now = time.monotonic()
        for s in stats.values():
            s.update_baseline(now)
        # list(...) because a tab may disconnect while we're awaiting a send.
        for ws, client in list(clients.items()):
            try:
                await ws.send_json(stats_message(client, now))
                if tick % DIRECTOR_EVERY == 0:
                    # Streams still warming up have an unreliable baseline, so
                    # they can't win yet.
                    scores = {
                        c: stats[c].hype(now)
                        for c in client.channels
                        if c in stats and not stats[c].warming_up(now)
                    }
                    event = client.director.decide(scores, now)
                    if event:
                        await ws.send_json(event)
            except Exception:
                pass  # a closed tab; the /ws handler cleans it up


async def pulse_loop():
    # Separate from tick_loop because an LLM call can take seconds, and the
    # hype bars must keep updating every second while we wait.
    while True:
        await asyncio.sleep(PULSE_CHECK)
        try:
            await pulse.maybe_run(buffers, time.monotonic())
        except Exception:
            logging.getLogger("uvicorn.error").exception("Chat Pulse loop error")


@asynccontextmanager
async def lifespan(app):
    # Background tasks live as long as the server does.
    tasks = [
        asyncio.create_task(chat.run()),
        asyncio.create_task(tick_loop()),
        asyncio.create_task(pulse_loop()),
    ]
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="MultiView AI", lifespan=lifespan)


@app.get("/")
def root():
    # This server has no web pages; the UI is the Vite app (port 5173 locally).
    return {"service": "MultiView AI backend", "ui": "http://localhost:5173", "health": "/health", "websocket": "/ws"}


@app.get("/health")
def health():
    return {"ok": True, "chat_connected": chat.connected, "channels": sorted(stats)}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    client = Client()
    clients[ws] = client
    try:
        while True:
            # Parse by hand so one bad message is ignored instead of closing the socket.
            try:
                msg = json.loads(await ws.receive_text())
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            now = time.monotonic()
            if msg.get("type") == "set_channels":
                client.channels = clean_channels(msg.get("channels"))
                client.director.sync(client.channels, msg.get("focus"), now)
                await sync_channels()
            elif msg.get("type") == "manual_focus" and msg.get("channel") in client.channels:
                client.director.manual(msg["channel"], now)
    except WebSocketDisconnect:
        pass
    finally:
        clients.pop(ws, None)
        await sync_channels()
