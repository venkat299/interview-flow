from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/{interview_id}")
async def websocket_endpoint(websocket: WebSocket, interview_id: str):
    """Placeholder WebSocket endpoint."""
    await websocket.accept()
    await websocket.close()
