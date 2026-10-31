"""The AI Director: picks which stream goes into the focus tile.

Despite the name it's a few if-statements on top of the hype scores. It's
deterministic: the same scores always give the same choice, and every choice
can be explained.
"""

THRESHOLD = 2.0    # a stream must be at least this much busier than its normal
MIN_HOLD = 20.0    # seconds a focus must stay before the Director may switch (anti-flicker)
MANUAL_LOCK = 60.0  # seconds the Director stays hands-off after the user picks a stream


class Director:
    def __init__(self):
        self.focus = None
        self.focus_since = float("-inf")
        self.locked_until = float("-inf")

    def sync(self, channels, focus, now):
        """The frontend sent its channel list (and what it's showing in focus)."""
        if focus in channels and focus != self.focus:
            self.focus, self.focus_since = focus, now
        elif self.focus not in channels:
            # Our focus was removed: fall back the same way the frontend does.
            self.focus = channels[0] if channels else None
            self.focus_since = now

    def manual(self, channel, now):
        """The user's choice beats the Director for MANUAL_LOCK seconds."""
        self.focus, self.focus_since = channel, now
        self.locked_until = now + MANUAL_LOCK

    def lock_remaining(self, now):
        return max(0.0, self.locked_until - now)

    def decide(self, scores, now):
        """scores: {channel: hype} for streams allowed to win.

        Returns a focus event to send to the browser, or None to stay put.
        """
        if not scores or now < self.locked_until:
            return None
        best = max(scores, key=scores.get)
        if best == self.focus or scores[best] <= THRESHOLD:
            return None
        # Hysteresis: even a strong spike must wait until the current focus
        # has had MIN_HOLD seconds, so two busy chats don't ping-pong.
        if now - self.focus_since < MIN_HOLD:
            return None
        self.focus, self.focus_since = best, now
        return {
            "type": "focus",
            "channel": best,
            "reason": f"chat is {scores[best]:.1f}x its normal pace",
        }
