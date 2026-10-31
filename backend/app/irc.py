"""Read-only, anonymous Twitch chat over IRC-on-WebSocket.

Twitch lets anyone read public chat with a "justinfan<digits>" nickname and
no token. We can't send messages that way, which is exactly what we want.
"""
import asyncio
import logging
import random

import websockets

IRC_URL = "wss://irc-ws.chat.twitch.tv:443"
RECONNECT_DELAY = 5  # seconds; Twitch restarts servers now and then

log = logging.getLogger("uvicorn.error")


def parse_line(line):
    """Turn one raw IRC line into a small tuple we care about.

    Returns ("PING", payload), ("PRIVMSG", channel, user, text), or None
    for everything else (welcome banners, JOIN echoes, ...).

    Example chat line:
      :alice!alice@alice.tmi.twitch.tv PRIVMSG #shroud :what a shot
    """
    line = line.rstrip("\r\n")
    if not line:
        return None
    # IRCv3 tags ("@badges=...;color=... :prefix ..."). We don't request them,
    # but skipping them keeps the parser safe if Twitch sends them anyway.
    if line.startswith("@"):
        _, _, line = line.partition(" ")
    if line.startswith("PING"):
        return ("PING", line[5:])  # echo back whatever Twitch sent, e.g. ":tmi.twitch.tv"

    prefix = ""
    if line.startswith(":"):
        prefix, _, line = line[1:].partition(" ")
    command, _, rest = line.partition(" ")
    if command != "PRIVMSG":
        return None
    # The message text starts after the first " :", and may itself contain ":".
    target, _, text = rest.partition(" :")
    if not target.startswith("#"):
        return None
    user = prefix.split("!", 1)[0]
    return ("PRIVMSG", target[1:].lower(), user, text)


class TwitchChat:
    """One IRC connection that joins/leaves channels as the app needs them."""

    def __init__(self, on_message):
        self.on_message = on_message  # called as on_message(channel, user, text)
        self.wanted = set()  # channels the app wants
        self.joined = set()  # channels we've sent JOIN for on this connection
        self.ws = None
        self.connected = False

    async def set_channels(self, wanted):
        self.wanted = set(wanted)
        await self._sync_joins()

    async def _sync_joins(self):
        # If we're offline, run() will join self.wanted after reconnecting.
        if self.ws is None:
            return
        to_join = self.wanted - self.joined
        to_part = self.joined - self.wanted
        # One connection can JOIN several channels in a single comma-separated line.
        if to_join:
            await self.ws.send("JOIN " + ",".join("#" + c for c in sorted(to_join)))
        if to_part:
            await self.ws.send("PART " + ",".join("#" + c for c in sorted(to_part)))
        self.joined = set(self.wanted)

    async def run(self):
        """Stay connected forever; reconnect after any error."""
        while True:
            try:
                async with websockets.connect(IRC_URL) as ws:
                    await ws.send(f"NICK justinfan{random.randint(10000, 99999)}")
                    self.ws, self.joined, self.connected = ws, set(), True
                    log.info("Connected to Twitch chat")
                    await self._sync_joins()
                    async for frame in ws:
                        # One WebSocket frame can hold several IRC lines.
                        for line in frame.split("\r\n"):
                            msg = parse_line(line)
                            if msg is None:
                                continue
                            if msg[0] == "PING":
                                # Twitch drops clients that don't answer PING.
                                await ws.send("PONG " + msg[1])
                            else:
                                self.on_message(*msg[1:])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("Twitch chat connection lost: %r", exc)
            finally:
                self.ws, self.connected = None, False
            await asyncio.sleep(RECONNECT_DELAY)
