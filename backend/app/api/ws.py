from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.trace_broadcaster import broadcaster

router = APIRouter()


@router.websocket("/ws/claims/{claim_id}/stream")
async def ws_claim_stream(websocket: WebSocket, claim_id: str):
    await websocket.accept()

    # Replay whatever has already happened (handles the submit -> connect race).
    for message in broadcaster.buffer(claim_id):
        await websocket.send_json(message)

    if broadcaster.is_done(claim_id):
        await websocket.close()
        return

    queue = broadcaster.subscribe(claim_id)
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
            if message.get("type") == "done":
                break
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.unsubscribe(claim_id, queue)
