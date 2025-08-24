"""WebSocket endpoint for interview sessions."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.connection_manager import ConnectionManager


router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/{interview_id}")
async def websocket_endpoint(websocket: WebSocket, interview_id: str) -> None:
    """Handle a WebSocket connection for a given interview."""

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

