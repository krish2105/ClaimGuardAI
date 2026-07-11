"""Streaming variant of the pipeline runner used by /claims/submit + the
live trace WebSocket. Runs the (synchronous) LangGraph execution in a
worker thread, and republishes each completed node's state to the
TraceBroadcaster so any subscribed WebSocket sees the agents "think"
step by step. A small per-step pacing delay makes the live trace panel
legible as a demo — matches ARCHITECTURE.md Section 9's call-out that this
is the best demo moment."""
import asyncio
import time

from app.agents.graph import claim_pipeline
from app.agents.state import ClaimState
from app.services.pipeline_service import _persist
from app.services.trace_broadcaster import broadcaster

STEP_DELAY_SECONDS = 0.35


def _state_from_update(update) -> ClaimState:
    return update if isinstance(update, ClaimState) else ClaimState(**update)


async def run_and_broadcast(claim_id: str, raw_document_text: str) -> ClaimState:
    loop = asyncio.get_event_loop()
    initial = ClaimState(claim_id=claim_id, raw_document_text=raw_document_text)
    holder: dict = {}

    def _blocking_stream():
        last_state = initial
        for update in claim_pipeline.stream(initial, stream_mode="values"):
            state = _state_from_update(update)
            last_state = state
            if not state.agent_trace:
                continue  # initial entry-state emission before any node has run
            latest_step = state.agent_trace[-1]
            message = {
                "type": "step",
                "agent": latest_step.agent,
                "summary": latest_step.summary,
                "status": latest_step.status,
                "state": state.model_dump(mode="json"),
            }
            asyncio.run_coroutine_threadsafe(
                broadcaster.publish(claim_id, message), loop
            ).result()
            time.sleep(STEP_DELAY_SECONDS)
        holder["state"] = last_state

    await asyncio.to_thread(_blocking_stream)
    final_state: ClaimState = holder["state"]

    await asyncio.to_thread(_persist, final_state)

    await broadcaster.publish(claim_id, {
        "type": "final",
        "final_decision": final_state.final_decision,
        "state": final_state.model_dump(mode="json"),
    })
    await broadcaster.mark_done(claim_id)
    return final_state
