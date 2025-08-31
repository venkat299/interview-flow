from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from interview_session_service.service import ConnectionManager

app = FastAPI(title="Interview Session Service")
manager = ConnectionManager()


@app.websocket("/api/v1/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
