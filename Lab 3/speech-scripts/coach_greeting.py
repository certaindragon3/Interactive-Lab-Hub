"""One Live-native opening per connection, without a synthetic user food report.

Protocol: https://developers.openai.com/api/docs/guides/live-conversations
Keep input PCM flowing while requesting and acknowledging the greeting. An
acknowledgment means accepted instructions, not heard or completed playback.
"""
import asyncio
from uuid import uuid4


GREETING_INSTRUCTIONS = """Open this new check-in immediately in English; do not wait for the user to speak first. In one or two short sentences, greet them as Orange, their sharp-tongued but supportive food coach, and invite them to tell you what they have eaten today. Keep it under 25 words, with a little playful attitude; then pause and listen. No specific foods have been reported: do not invent any, judge their day, or mention a score. This is only a greeting, not a food report or a request for backend work: do not delegate or log food for it. If the user starts speaking, yield, listen, and respond to what they actually say instead of restarting your greeting."""


class OpeningGreeting:
    """Send once and correlate acceptance/errors without blocking event dispatch."""

    def __init__(self, timeout=8.0):
        self.event_id = "coach_greeting_" + uuid4().hex
        self.timeout = timeout
        self.requested = False
        self.accepted = asyncio.Event()

    async def request(self, connection):
        if self.requested:
            return
        # Mark before the await; an uncertain send must never be retried blindly.
        self.requested = True
        try:
            async with asyncio.timeout(self.timeout):
                await connection.session.instructions.append(
                    event_id=self.event_id,
                    delegation_id=None,
                    content=GREETING_INSTRUCTIONS,
                )
                await self.accepted.wait()
        except TimeoutError:
            raise RuntimeError("Opening greeting instructions were not acknowledged") from None

    def handle(self, event):
        """Return True only for our accepted append; reject a correlated error."""
        if not self.requested:
            return False
        if event.type == "session.instructions.appended":
            if getattr(event, "client_event_id", None) != self.event_id:
                return False
            self.accepted.set()
            return True
        if event.type in ("error", "session.error"):
            error = getattr(event, "error", None)
            if getattr(error, "client_event_id", None) == self.event_id:
                raise RuntimeError("Opening greeting instructions were rejected")
        return False
