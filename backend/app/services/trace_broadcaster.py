"""In-memory pub/sub used to fan out live agent-trace events to any
WebSocket clients watching a given claim_id. Buffers every message so a
client that connects slightly after submission (a normal race in the
submit -> open-socket flow) still replays the full trace from the start."""
import asyncio


class TraceBroadcaster:
    def __init__(self):
        self._buffers: dict[str, list[dict]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._done: set[str] = set()

    def buffer(self, claim_id: str) -> list[dict]:
        return list(self._buffers.get(claim_id, []))

    def is_done(self, claim_id: str) -> bool:
        return claim_id in self._done

    async def publish(self, claim_id: str, message: dict) -> None:
        self._buffers.setdefault(claim_id, []).append(message)
        for q in list(self._subscribers.get(claim_id, [])):
            await q.put(message)

    async def mark_done(self, claim_id: str) -> None:
        self._done.add(claim_id)
        await self.publish(claim_id, {"type": "done"})

    def subscribe(self, claim_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(claim_id, []).append(q)
        return q

    def unsubscribe(self, claim_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(claim_id, [])
        if q in subs:
            subs.remove(q)


broadcaster = TraceBroadcaster()
